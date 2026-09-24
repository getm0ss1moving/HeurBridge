"""Bookshelf (.aux/.nodes/.nets/.wts/.pl/.scl) loader and .pl writer.

Conventions of the format: .pl gives the lower-left corner; pin offsets in
.nets are relative to the node centre (R0 frame).  Terminals are fixed; a
terminal no larger than one row height in both dimensions (or ``terminal_NI``)
is an IO, otherwise a fixed macro.  A movable node taller than one row is a
movable macro.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from . import orient as O
from .design import Design, Layout, build_csr


def _lines(path: Path):
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if line and not line.startswith("UCLA"):
                yield line


def parse_aux(aux: Path) -> dict:
    aux = Path(aux)
    files = {}
    for line in _lines(aux):
        if ":" in line:
            for tok in line.split(":", 1)[1].split():
                files[Path(tok).suffix.lstrip(".")] = aux.parent / tok
    return files


def parse_nodes(path: Path):
    names, sizes, term, term_ni = [], [], [], []
    for line in _lines(path):
        if line.startswith(("NumNodes", "NumTerminals")):
            continue
        t = line.split()
        names.append(t[0])
        sizes.append((float(t[1]), float(t[2])))
        kind = t[3] if len(t) > 3 else ""
        term.append(kind.startswith("terminal"))
        term_ni.append(kind == "terminal_NI")
    return names, np.array(sizes, dtype=np.float64).reshape(-1, 2), np.array(term), np.array(term_ni)


def parse_nets(path: Path, index: dict):
    nets, net_names, pin_obj, pin_off, pin_dir = [], [], [], [], []
    cur = None
    for line in _lines(path):
        if line.startswith(("NumNets", "NumPins")):
            continue
        if line.startswith("NetDegree"):
            t = line.replace(":", " ").split()
            net_names.append(t[2] if len(t) > 2 else "net%d" % len(net_names))
            cur = []
            nets.append(cur)
            continue
        t = line.replace(":", " ").split()
        obj = index[t[0]]
        d = t[1] if len(t) > 1 else "B"
        dx = float(t[2]) if len(t) > 3 else 0.0
        dy = float(t[3]) if len(t) > 3 else 0.0
        cur.append(len(pin_obj))
        pin_obj.append(obj)
        pin_off.append((dx, dy))
        pin_dir.append(d)
    return nets, net_names, np.array(pin_obj, dtype=np.int64), np.array(pin_off, dtype=np.float64).reshape(-1, 2), pin_dir


def parse_wts(path: Path | None, net_names: list) -> np.ndarray:
    w = np.ones(len(net_names))
    if path is None or not Path(path).exists():
        return w
    idx = {n: i for i, n in enumerate(net_names)}
    for line in _lines(path):
        t = line.split()
        if len(t) >= 2 and t[0] in idx:
            try:
                w[idx[t[0]]] = float(t[1])
            except ValueError:
                pass
    return w


def parse_pl(path: Path, index: dict, n: int):
    ll = np.full((n, 2), np.nan)
    ori = np.zeros(n, dtype=np.int8)
    fixed = np.zeros(n, dtype=bool)
    for line in _lines(path):
        t = line.replace(":", " ").split()
        if t[0] not in index:
            continue
        i = index[t[0]]
        ll[i] = (float(t[1]), float(t[2]))
        rest = t[3:]
        for tok in rest:
            if tok.startswith("/FIXED"):
                fixed[i] = True
            elif tok.upper() in O.DEF_NAMES:
                ori[i] = O.from_def(tok)
    return ll, ori, fixed


def parse_scl(path: Path):
    rows, cur = [], {}
    for line in _lines(path):
        t = line.replace(":", " ").split()
        key = t[0].lower()
        if key == "corerow":
            cur = {}
        elif key == "coordinate":
            cur["y"] = float(t[1])
        elif key == "height":
            cur["h"] = float(t[1])
        elif key == "sitewidth":
            cur["sw"] = float(t[1])
        elif key == "sitespacing":
            cur["ss"] = float(t[1])
        elif key == "subroworigin":
            cur["x"] = float(t[1])
            if len(t) >= 4 and t[2].lower() == "numsites":
                cur["n"] = float(t[3])
        elif key == "end" and cur:
            ss = cur.get("ss", cur.get("sw", 1.0))
            rows.append((cur.get("x", 0.0), cur["y"], cur.get("n", 0.0) * ss, cur["h"], cur.get("sw", ss)))
            cur = {}
    arr = np.array(rows, dtype=np.float64).reshape(-1, 5)
    return arr[:, :4], (float(np.median(arr[:, 4])) if len(arr) else None)


def load_bookshelf(aux: str | Path, design_id: str | None = None, family: str = "",
                   tech: str = "bookshelf") -> tuple[Design, Layout]:
    aux = Path(aux)
    f = parse_aux(aux)
    names, size, term, term_ni = parse_nodes(f["nodes"])
    index = {n: i for i, n in enumerate(names)}
    nets, net_names, pin_obj, pin_off, pin_dir = parse_nets(f["nets"], index)
    wts = parse_wts(f.get("wts"), net_names)
    ll, ori, pl_fixed = parse_pl(f["pl"], index, len(names))
    rows, site_w = parse_scl(f["scl"]) if "scl" in f else (np.zeros((0, 4)), None)
    row_h = float(np.median(rows[:, 3])) if len(rows) else float(np.median(size[:, 1]))
    if len(rows):
        core = (rows[:, 0].min(), rows[:, 1].min(), (rows[:, 0] + rows[:, 2]).max(), (rows[:, 1] + rows[:, 3]).max())
    else:
        fin = np.isfinite(ll).all(1)
        core = (ll[fin, 0].min(), ll[fin, 1].min(), (ll[fin] + size[fin])[:, 0].max(), (ll[fin] + size[fin])[:, 1].max())
    is_fixed = term | pl_fixed
    small = (size[:, 0] <= row_h + 1e-9) & (size[:, 1] <= row_h + 1e-9)
    is_io = term_ni | (term & small)
    is_macro = (size[:, 1] > row_h + 1e-9) & ~is_io
    ptr, idx = build_csr(nets)
    die = core
    fin = np.isfinite(ll).all(1)
    if fin.any():
        die = (min(core[0], ll[fin, 0].min()), min(core[1], ll[fin, 1].min()),
               max(core[2], (ll[fin] + size[fin])[:, 0].max()), max(core[3], (ll[fin] + size[fin])[:, 1].max()))
    d = Design(
        id=design_id or aux.stem, family=family, tech=tech, names=names, size=size,
        is_macro=is_macro, is_fixed=is_fixed, is_io=is_io, pin_obj=pin_obj, pin_off=pin_off,
        net_ptr=ptr, pin_idx=idx, net_weight=wts, die=tuple(map(float, die)), core=tuple(map(float, core)),
        net_names=net_names, rows=rows, site=(site_w, row_h) if site_w else None,
        dbu=1.0,
        source={"format": "bookshelf", "aux": str(aux),
                "files": {k: str(v) for k, v in f.items()}, "row_height": row_h},
    )
    d.validate()
    eff = O.effective_size(size, ori)
    centre = ll + eff / 2.0
    lay = Layout(pos=d.to_norm(centre), orient=ori, schema=d.schema_hash(), meta={"source": str(f["pl"])})
    return d, lay


def _fmt(v: float) -> str:
    """Integers stay integers (absorbs float round-off from normalization); else 9 decimals."""
    r = round(float(v))
    if abs(float(v) - r) < 1e-6:
        return str(int(r))
    return "%.9f" % float(v)


def write_pl(design: Design, layout: Layout, out: str | Path, template: str | Path | None = None) -> Path:
    """Write a .pl.  Lower-left = centre - effective size / 2.  FIXED flags are kept from the template."""
    out = Path(out)
    tpl = Path(template) if template else Path(design.source["files"]["pl"])
    flags = {}
    for line in _lines(tpl):
        t = line.replace(":", " ").split()
        tail = [x for x in t[3:] if x.startswith("/")]
        flags[t[0]] = " ".join(tail)
    ll = design.to_abs(layout.pos) - O.effective_size(design.size, layout.orient) / 2.0
    with open(out, "w") as fh:
        fh.write("UCLA pl 1.0\n# written by heurbridge.core.bookshelf\n\n")
        for i, name in enumerate(design.names):
            if not np.isfinite(ll[i]).all():
                continue
            tail = flags.get(name, "")
            fh.write("%s %s %s : %s%s\n" % (name, _fmt(ll[i, 0]), _fmt(ll[i, 1]), O.to_def(layout.orient[i]),
                                              (" " + tail) if tail else ""))
    return out


def write_bookshelf_copy(design: Design, layout: Layout, out_dir: str | Path, name: str | None = None) -> Path:
    """Copy a bookshelf design into out_dir with a new .pl (other files symlinked). Returns the .aux path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {k: Path(v) for k, v in design.source["files"].items()}
    base = name or Path(design.source["aux"]).stem
    for k, src in files.items():
        if k == "pl":
            continue
        dst = out_dir / (base + "." + k)
        if not dst.exists():
            dst.symlink_to(src.resolve())
    write_pl(design, layout, out_dir / (base + ".pl"), template=files["pl"])
    aux = out_dir / (base + ".aux")
    order = [k for k in ("nodes", "nets", "wts", "pl", "scl", "shapes", "route") if k in files]
    aux.write_text("RowBasedPlacement : " + " ".join(base + "." + k for k in order) + "\n")
    return aux


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
