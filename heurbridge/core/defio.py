"""LEF/DEF loader and DEF placement writer.

Master sizes and pin centres come from ``eda/harness/lef_def.lef_info`` (the
canonical HA-PR parser) when the harness is available, so pin offsets are
identical to the HA-PR HPWL metric; ``_lef_pins_fallback`` reproduces the same
algorithm when it is not.  The supplementary pass reads what lef_def does not:
macro CLASS, SITE sizes, routing LAYER direction/pitch and UNITS.

DEF: COMPONENTS (with PLACED/FIXED/COVER/UNPLACED status), PINS, NETS
(connections before the first ``+`` attribute, plus ``+ WEIGHT``), DIEAREA,
ROW, GCELLGRID.  SPECIALNETS are skipped, as in lef_def.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from . import orient as O
from .design import Design, Layout, build_csr

_COMP_POS = re.compile(r"\+\s*(PLACED|FIXED|COVER)\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*(\w+)")
_UNPLACED = re.compile(r"\+\s*UNPLACED")
_CONN = re.compile(r"\(\s*(\S+)\s+(\S+)(?:\s+\+\s*\w+)*\s*\)")
_WEIGHT = re.compile(r"\+\s*WEIGHT\s+(-?\d+(?:\.\d+)?)")
_PIN_NET = re.compile(r"\+\s*NET\s+(\S+)")
_PIN_DIR = re.compile(r"\+\s*DIRECTION\s+(\w+)")
_PIN_USE = re.compile(r"\+\s*USE\s+(\w+)")
_PIN_POS = re.compile(r"\+\s*(PLACED|FIXED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\w+)")
_PIN_RECT = re.compile(r"\+\s*LAYER\s+(\S+)(?:\s+\w+\s+\d+)*\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)")


# ============================================================================ LEF
def _lef_pins_fallback(text: str) -> dict:
    """Same algorithm as eda/harness/lef_def.lef_info (used only without the harness)."""
    masters, cur, cur_pin, in_port, rects = {}, None, None, False, []
    origin, size = (0.0, 0.0), (0.0, 0.0)
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("MACRO "):
            cur = line.split()[1]
            masters[cur] = {"size": (0.0, 0.0), "origin": (0.0, 0.0), "pins": {}}
            cur_pin, in_port, rects, origin, size = None, False, [], (0.0, 0.0), (0.0, 0.0)
            continue
        if cur is None:
            continue
        parts = line.split()
        if line.startswith("ORIGIN ") and len(parts) >= 3:
            try:
                origin = (float(parts[1]), float(parts[2]))
            except ValueError:
                pass
        elif line.startswith("SIZE ") and len(parts) >= 4:
            try:
                size = (float(parts[1]), float(parts[3]))
            except ValueError:
                pass
        elif line.startswith("PIN "):
            cur_pin, rects, in_port = parts[1], [], False
        elif line == "PORT":
            in_port = True
        elif line == "END" and in_port:
            in_port = False
        elif line.startswith("RECT ") and cur_pin and in_port and len(parts) >= 5:
            try:
                rects.append(tuple(float(v) for v in parts[1:5]))
            except ValueError:
                pass
        elif line.startswith("END ") and cur_pin and len(parts) >= 2 and parts[1] == cur_pin:
            if rects:
                cx = (min(r[0] for r in rects) + max(r[2] for r in rects)) / 2.0 - origin[0]
                cy = (min(r[1] for r in rects) + max(r[3] for r in rects)) / 2.0 - origin[1]
                masters[cur]["pins"][cur_pin] = (round(cx, 6), round(cy, 6))
            else:
                masters[cur]["pins"][cur_pin] = (0.0, 0.0)
            cur_pin = None
        elif line.startswith("END ") and len(parts) >= 2 and parts[1] == cur:
            masters[cur]["size"], masters[cur]["origin"] = size, origin
            cur = None
    return masters


def parse_lef(paths) -> dict:
    """Parse one or more LEF files.

    Returns {"masters": {name: {size, origin, pins, cls}}, "sites": {name: (w,h)},
             "layers": [{name, dir, pitch, width, offset}], "dbu": int|None, "pin_source": str}.
    """
    masters, sites, layers, dbu = {}, {}, [], None
    pin_source = "fallback"
    try:
        from .._eda import harness
        lef_info = harness("lef_def").lef_info
        pin_source = "eda.harness.lef_def"
    except Exception:
        lef_info = None
    for path in ([paths] if isinstance(paths, (str, Path)) else paths):
        text = Path(path).read_text(errors="replace")
        pins = lef_info(path) if lef_info else _lef_pins_fallback(text)
        for name, info in pins.items():
            masters[name] = dict(info, cls="")
        cur_macro = cur_site = cur_layer = None
        for raw in text.splitlines():
            line = raw.strip().rstrip(";").strip()
            parts = line.split()
            if not parts:
                continue
            key = parts[0]
            if key == "MACRO":
                cur_macro = parts[1]
            elif key == "SITE" and cur_macro is None and len(parts) == 2:
                cur_site = parts[1]
            elif key == "LAYER" and cur_macro is None and len(parts) == 2 and cur_site is None:
                cur_layer = {"name": parts[1], "type": None, "dir": None, "pitch": None, "width": None, "offset": None}
            elif key == "END" and len(parts) == 2:
                if cur_macro and parts[1] == cur_macro:
                    cur_macro = None
                elif cur_site and parts[1] == cur_site:
                    cur_site = None
                elif cur_layer and parts[1] == cur_layer["name"]:
                    if cur_layer["type"] == "ROUTING":
                        layers.append(cur_layer)
                    cur_layer = None
            elif key == "CLASS" and cur_macro and cur_macro in masters:
                masters[cur_macro]["cls"] = " ".join(parts[1:])
            elif key == "SIZE" and cur_site and len(parts) >= 4:
                sites[cur_site] = (float(parts[1]), float(parts[3]))
            elif cur_layer is not None and cur_macro is None:
                try:
                    if key == "TYPE":
                        cur_layer["type"] = parts[1]
                    elif key == "DIRECTION":
                        cur_layer["dir"] = parts[1][0]      # H or V
                    elif key == "PITCH":
                        cur_layer["pitch"] = float(parts[1])
                    elif key == "WIDTH":
                        cur_layer["width"] = float(parts[1])
                    elif key == "OFFSET":
                        cur_layer["offset"] = float(parts[1])
                except (ValueError, IndexError):
                    pass
            elif key == "DATABASE" and len(parts) >= 3 and parts[1] == "MICRONS":
                dbu = int(float(parts[2]))
    return {"masters": masters, "sites": sites, "layers": layers, "dbu": dbu, "pin_source": pin_source}


# ============================================================================ DEF
def _section_iter(text: str):
    """Yield (section, statement) for statements inside COMPONENTS/PINS/NETS."""
    for sec in ("COMPONENTS", "PINS", "NETS"):
        m = re.search(r"^\s*%s\s+\d+\s*;(.*?)^\s*END\s+%s" % (sec, sec), text, re.S | re.M)
        if not m:
            continue
        for stmt in m.group(1).split(";"):
            stmt = stmt.strip()
            if stmt.startswith("-"):
                yield sec, stmt


def parse_def(path) -> dict:
    text = Path(path).read_text(errors="replace")
    out = {"path": str(path)}
    m = re.search(r"^\s*DESIGN\s+(\S+)\s*;", text, re.M)
    out["design"] = m.group(1) if m else Path(path).stem
    m = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", text)
    dbu = int(m.group(1)) if m else 1000
    out["dbu"] = dbu
    m = re.search(r"DIEAREA((?:\s*\(\s*-?\d+\s+-?\d+\s*\))+)\s*;", text)
    if m:
        pts = np.array(re.findall(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)", m.group(1)), dtype=np.float64)
        out["die_dbu"] = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
    rows = []
    for m in re.finditer(r"^\s*ROW\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\w+)(?:\s+DO\s+(\d+)\s+BY\s+(\d+)(?:\s+STEP\s+(\d+)\s+(\d+))?)?", text, re.M):
        nx, ny = int(m.group(6) or 1), int(m.group(7) or 1)
        sx, sy = int(m.group(8) or 0), int(m.group(9) or 0)
        rows.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5), nx, ny, sx, sy))
    out["rows"] = rows
    gcg = {"X": [], "Y": []}
    for m in re.finditer(r"GCELLGRID\s+([XY])\s+(-?\d+)\s+DO\s+(\d+)\s+STEP\s+(\d+)", text):
        gcg[m.group(1)].append((int(m.group(2)), int(m.group(3)), int(m.group(4))))
    out["gcellgrid"] = gcg
    comps, pins, nets = [], [], []
    for sec, stmt in _section_iter(text):
        head = stmt[1:].split()
        if sec == "COMPONENTS":
            pm = _COMP_POS.search(stmt)
            if pm:
                comps.append((head[0], head[1], pm.group(1), float(pm.group(2)), float(pm.group(3)), pm.group(4)))
            else:
                comps.append((head[0], head[1], "UNPLACED", None, None, "N"))
        elif sec == "PINS":
            name = head[0]
            net = _PIN_NET.search(stmt)
            d = _PIN_DIR.search(stmt)
            u = _PIN_USE.search(stmt)
            pos = _PIN_POS.search(stmt)
            rect = _PIN_RECT.search(stmt)
            pins.append({
                "name": name, "net": net.group(1) if net else None, "dir": d.group(1) if d else None,
                "use": u.group(1) if u else "SIGNAL",
                "status": pos.group(1) if pos else "UNPLACED",
                "x": float(pos.group(2)) if pos else None, "y": float(pos.group(3)) if pos else None,
                "orient": pos.group(4) if pos else "N",
                "rect": tuple(int(rect.group(i)) for i in range(2, 6)) if rect else None,
                "layer": rect.group(1) if rect else None,
            })
        else:
            name = head[0]
            cut = re.search(r"\s\+\s", stmt)
            conn_text = stmt[:cut.start()] if cut else stmt
            conns = [(a, b) for a, b in _CONN.findall(conn_text) if a != "*"]
            w = _WEIGHT.search(stmt)
            nets.append((name, conns, float(w.group(1)) if w else 1.0))
    out["components"], out["pins"], out["nets"] = comps, pins, nets
    return out


# ============================================================================ Design
def load_def_design(def_path, lef_paths, design_id: str | None = None, family: str = "", tech: str = "",
                    lef: dict | None = None, pin_fallback: str = "centre") -> tuple[Design, Layout]:
    """Build a Design + Layout from DEF + LEF(s).

    Object order: DEF COMPONENTS order, then DEF PINS (IOs).  IO pins are
    zero-size fixed objects at their DEF placement point (the lef_def convention).
    pin_fallback: where a component pin missing from LEF is placed ("centre", or
    "origin" = lower-left, the lef_def behaviour); misses are counted in source.
    """
    d = parse_def(def_path)
    lef = lef or parse_lef(lef_paths)
    masters = lef["masters"]
    dbu = float(d["dbu"])
    comps, iopins = d["components"], d["pins"]
    n_c, n_io = len(comps), len(iopins)
    n = n_c + n_io
    names = [c[0] for c in comps] + ["PIN:" + p["name"] for p in iopins]
    master_names = [c[1] for c in comps] + ["__IO__"] * n_io
    size = np.zeros((n, 2))
    is_macro = np.zeros(n, dtype=bool)
    is_fixed = np.zeros(n, dtype=bool)
    is_io = np.zeros(n, dtype=bool)
    ll = np.full((n, 2), np.nan)
    ori = np.zeros(n, dtype=np.int8)
    missing_masters = set()
    for i, (name, master, status, x, y, o) in enumerate(comps):
        info = masters.get(master)
        if info is None:
            missing_masters.add(master)
            info = {"size": (0.0, 0.0), "pins": {}, "cls": ""}
        size[i] = info["size"]
        cls = info.get("cls", "").upper()
        is_macro[i] = cls.startswith("BLOCK") or cls.startswith("RING")
        is_fixed[i] = status in ("FIXED", "COVER")
        ori[i] = O.from_def(o) if o in O.DEF_NAMES else 0
        if x is not None:
            ll[i] = (x / dbu, y / dbu)
    for k, p in enumerate(iopins):
        i = n_c + k
        is_io[i] = True
        is_fixed[i] = True
        if p["x"] is not None:
            ll[i] = (p["x"] / dbu, p["y"] / dbu)
    index = {nm: i for i, nm in enumerate(names)}
    pin_obj, pin_off, pin_names, net_lists, net_names, weights = [], [], [], [], [], []
    misses = 0
    for net_name, conns, w in d["nets"]:
        lst = []
        for inst, pin in conns:
            if inst == "PIN":
                i = index.get("PIN:" + pin)
                if i is None:
                    continue
                off = (0.0, 0.0)
            else:
                i = index.get(inst)
                if i is None:
                    continue
                info = masters.get(master_names[i]) or {"pins": {}, "size": (0.0, 0.0)}
                p = info["pins"].get(pin)
                w_, h_ = size[i]
                if p is None:
                    misses += 1
                    off = (0.0, 0.0) if pin_fallback == "centre" else (-w_ / 2.0, -h_ / 2.0)
                else:
                    off = (p[0] - w_ / 2.0, p[1] - h_ / 2.0)
            lst.append(len(pin_obj))
            pin_obj.append(i)
            pin_off.append(off)
            pin_names.append(pin)
        net_lists.append(lst)
        net_names.append(net_name)
        weights.append(w)
    ptr, idx = build_csr(net_lists)
    die = tuple(v / dbu for v in d.get("die_dbu", (0, 0, 0, 0)))
    site_sizes = lef["sites"]
    row_arr = []
    for (rname, site, x, y, o, nx, ny, sx, sy) in d["rows"]:
        sw, sh = site_sizes.get(site, (sx / dbu if sx else 0.0, 0.0))
        row_arr.append((x / dbu, y / dbu, nx * (sx / dbu if sx else sw), ny * sh if ny > 1 else sh))
    rows = np.array(row_arr, dtype=np.float64).reshape(-1, 4)
    if len(rows):
        core = (rows[:, 0].min(), rows[:, 1].min(), (rows[:, 0] + rows[:, 2]).max(), (rows[:, 1] + rows[:, 3]).max())
    else:
        core = die
    site = None
    if d["rows"]:
        s = d["rows"][0][1]
        site = site_sizes.get(s)
    gcg = d["gcellgrid"]
    gcell = None
    if gcg["X"] and gcg["Y"]:
        gcell = {"X": gcg["X"], "Y": gcg["Y"], "dbu": dbu, "layers": lef["layers"]}
    des = Design(
        id=design_id or d["design"], family=family, tech=tech, names=names, size=size,
        is_macro=is_macro, is_fixed=is_fixed, is_io=is_io,
        pin_obj=np.array(pin_obj, dtype=np.int64), pin_off=np.array(pin_off, dtype=np.float64).reshape(-1, 2),
        net_ptr=ptr, pin_idx=idx, net_weight=np.array(weights, dtype=np.float64),
        die=tuple(map(float, die)), core=tuple(map(float, core)), masters=master_names,
        net_names=net_names, pin_names=pin_names, rows=rows, site=site, gcell_grid=gcell, dbu=dbu,
        source={"format": "def", "def": str(def_path), "lef": [str(p) for p in ([lef_paths] if isinstance(lef_paths, (str, Path)) else lef_paths)],
                "pin_source": lef["pin_source"], "pin_misses": misses, "missing_masters": sorted(missing_masters),
                "n_components": n_c, "n_io": n_io, "layers": lef["layers"]},
    )
    des.validate()
    eff = O.effective_size(size, ori)
    lay = Layout(pos=des.to_norm(ll + eff / 2.0), orient=ori, schema=des.schema_hash(), meta={"source": str(def_path)})
    return des, lay


# ============================================================================ writer
def write_def(design: Design, layout: Layout, out_path, template=None, only=None,
              status_for_unplaced: str = "PLACED") -> Path:
    """Rewrite the COMPONENTS placement of ``template`` (default: the source DEF) from ``layout``.

    Lower-left corners are rounded to integer DBU.  ``only`` (bool mask over
    objects) restricts which components are rewritten (e.g. macros only);
    others keep their template text.  FIXED/COVER status is preserved.
    """
    tpl = Path(template or design.source["def"])
    text = tpl.read_text(errors="replace")
    n_c = design.source["n_components"]
    ll = design.to_abs(layout.pos) - O.effective_size(design.size, layout.orient) / 2.0
    ll_dbu = np.round(ll * design.dbu)
    mask = np.ones(design.n_objects, dtype=bool) if only is None else np.asarray(only, dtype=bool)
    index = {nm: i for i, nm in enumerate(design.names[:n_c])}

    m = re.search(r"^\s*COMPONENTS\s+\d+\s*;(.*?)^\s*END\s+COMPONENTS", text, re.S | re.M)
    if not m:
        raise ValueError("no COMPONENTS section in %s" % tpl)
    body = m.group(1)

    def fix(stmt: str) -> str:
        s = stmt.strip()
        if not s.startswith("-"):
            return stmt
        name = s[1:].split()[0]
        i = index.get(name)
        if i is None or not mask[i] or not np.isfinite(ll_dbu[i]).all():
            return stmt
        o = O.to_def(layout.orient[i])
        x, y = int(ll_dbu[i, 0]), int(ll_dbu[i, 1])
        pm = _COMP_POS.search(stmt)
        if pm:
            status = pm.group(1)
            return stmt[:pm.start()] + "+ %s ( %d %d ) %s" % (status, x, y, o) + stmt[pm.end():]
        um = _UNPLACED.search(stmt)
        if um:
            return stmt[:um.start()] + "+ %s ( %d %d ) %s" % (status_for_unplaced, x, y, o) + stmt[um.end():]
        return stmt.rstrip() + " + %s ( %d %d ) %s " % (status_for_unplaced, x, y, o)

    new_body = ";".join(fix(s) for s in body.split(";"))
    out = text[:m.start(1)] + new_body + text[m.end(1):]
    out_path = Path(out_path)
    out_path.write_text(out)
    return out_path
