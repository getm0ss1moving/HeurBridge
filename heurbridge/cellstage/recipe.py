"""Cell-stage recipes for imported macro layouts (Track B: ORFS 2024-12 8ae3ae36, OpenROAD 676f8451).

A recipe fixes how the flow places the standard cells around a macro layout that ORFS imports through
MACRO_PLACEMENT_TCL.  It applies only to OrfsEvaluator runs, which always import a layout; with an imported layout
ORFS never runs rtl_macro_placer (third_party/ORFS-2024-12/flow/scripts/macro_place_util.tcl:31-68), so no recipe
setting, PLACE_DENSITY included (its target utilization, :59), can move the macros.  The unmodified flow's baseline
runs never see a recipe.

Fields, and the flow behaviour each relies on (paths under third_party/ORFS-2024-12/flow or
third_party/OpenROAD-676f8451/src):
  density        ("addon", v): PLACE_DENSITY_LB_ADDON = v.  ("absolute", v): PLACE_DENSITY = v and the design's
                 addon cleared, since the addon wins whenever it is set (scripts/util.tcl:153-168).
  pad_global, pad_detail   CELL_PAD_IN_SITES_GLOBAL_PLACEMENT / CELL_PAD_IN_SITES_DETAIL_PLACEMENT, in sites.
  timing_driven, routability_driven   GPL_TIMING_DRIVEN / GPL_ROUTABILITY_DRIVEN (ORFS defaults 1 and 1:
                 scripts/variables.yaml:356-367).
  gpl            more global_placement keys, merged into GLOBAL_PLACEMENT_ARGS after the campaign's own; ORFS passes
                 that variable to both global placements, 3_1 and 3_3 (scripts/global_place_skip_io.tcl:8-11,
                 scripts/global_place.tcl:28).
  start          where the standard cells start: "centre" (unplaced; every cell starts at the core centre, the
                 default for an imported layout), "quadratic" (their cluster's quadratic position,
                 OrfsEvaluator._warm_start_tcl) or "positions" (a full placement named by ``source``: "hbgp",
                 "npz:<file>" or "npzdir:<dir>", heurbridge/cellstage/positions.py from_source).
  hold           what the main global placement 3_3 does with that start.  3_1 runs with -skip_io, which sets the
                 initial-placement iterations to 0, and then a placed cell starts where it is (gpl/src/replace.tcl:110-114,
                 gpl/src/initialPlace.cpp:135-140); 3_2 places the IO pins from 3_1's result
                 (scripts/io_placement.tcl:4-6); 3_3 runs initial placement again, from the core centre.
                 "restart" keeps that default (a start shapes 3_1 and the IO pins only); "continue" adds
                 -skip_initial_place, so 3_3 continues from 3_1's placement; "keep" adds -skip_initial_place and
                 -skip_nesterov_place, so the start is kept through 3_1 and 3_3 until resizing and detailed placement
                 (gpl/src/replace.tcl:97-104, :317-326).
  density_caps   partial placement blockages (rectangle in microns, max density in percent), created at the macro
                 stage after the macros.  Soft, so detailed placement ignores them (dpl/src/Grid.cpp:162-165), while
                 global placement fills (100 - max density) percent of their sites (gpl/src/placerBase.cpp:1152-1169).
  route_adjust   routing-capacity reductions (rectangle in microns, layer, share 0-1) for every global route of the
                 run: a per-run FASTROUTE_TCL that first does what the design's own FASTROUTE_TCL or the platform
                 default does (scripts/util.tcl:7-17), then set_global_routing_region_adjustment
                 (grt/src/GlobalRouter.tcl:75-124).
A recipe's id is a hash of its canonical settings (the name is a label and is not part of it).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

STARTS = ("centre", "quadratic", "positions")
HOLDS = ("restart", "continue", "keep")
HOLD_FLAGS = {"restart": (), "continue": ("-skip_initial_place",), "keep": ("-skip_initial_place", "-skip_nesterov_place")}

# global_placement's keys (take a value) and flags in OpenROAD 676f8451 (gpl/src/replace.tcl:71-95)
GPL_KEYS = frozenset("""-bin_grid_count -density -init_density_penalty -init_wirelength_coef -min_phi_coef -max_phi_coef
-overflow -reference_hpwl -initial_place_max_iter -initial_place_max_fanout -routability_check_overflow
-routability_max_density -routability_max_inflation_iter -routability_target_rc_metric -routability_inflation_ratio_coef
-routability_max_inflation_ratio -routability_rc_coefficients -timing_driven_net_reweight_overflow
-timing_driven_net_weight_max -timing_driven_nets_percentage -keep_resize_below_overflow -pad_left -pad_right""".split())
GPL_FLAGS = frozenset("""-skip_initial_place -skip_nesterov_place -timing_driven -routability_driven -routability_use_grt
-disable_timing_driven -disable_routability_driven -skip_io -incremental""".split())
# arguments another recipe field (or ORFS itself) owns: one way to say each thing
OWNED = frozenset({"-density", "-pad_left", "-pad_right", "-skip_io", "-incremental", "-timing_driven",
                   "-routability_driven", "-disable_timing_driven", "-disable_routability_driven",
                   "-skip_initial_place", "-skip_nesterov_place"})
_LAYER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _num(x) -> str:
    return "%.6g" % float(x)


def _rect(r, what: str) -> tuple:
    r = tuple(float(v) for v in r)
    if len(r) != 4 or not (r[0] < r[2] and r[1] < r[3]) or not all(np.isfinite(r)):
        raise ValueError("%s: a rectangle is (xl, yl, xh, yh) with xl < xh and yl < yh, got %r" % (what, r))
    return r


def _clip(r: tuple, box, what: str) -> tuple:
    xl, yl, xh, yh = max(r[0], box[0]), max(r[1], box[1]), min(r[2], box[2]), min(r[3], box[3])
    if not (xl < xh and yl < yh):
        raise ValueError("%s %r lies outside %r" % (what, r, tuple(box)))
    return xl, yl, xh, yh


# ------------------------------------------------------------------ GLOBAL_PLACEMENT_ARGS as a Tcl list
def tcl_words(text: str) -> list:
    """Split a Tcl list as ``{*}$::env(GLOBAL_PLACEMENT_ARGS)`` does: whitespace-separated words, {...} groups (nested)
    and "..." strings; the outer braces or quotes are removed."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        if text[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                depth += {"{": 1, "}": -1}.get(text[j], 0)
                j += 1
            if depth:
                raise ValueError("unbalanced braces in %r" % text)
            out.append(text[i + 1:j - 1])
            i = j
        elif text[i] == '"':
            j = text.find('"', i + 1)
            if j < 0:
                raise ValueError("unbalanced quote in %r" % text)
            out.append(text[i + 1:j])
            i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace():
                j += 1
            out.append(text[i:j])
            i = j
    return out


def parse_gpl_args(text: str) -> list:
    """GLOBAL_PLACEMENT_ARGS -> [(key, value or None for a flag), ...]; an argument global_placement does not know
    is an error here rather than a failed flow run later."""
    words, out, i = tcl_words(text or ""), [], 0
    while i < len(words):
        w = words[i]
        if w in GPL_FLAGS:
            out.append((w, None))
            i += 1
        elif w in GPL_KEYS:
            if i + 1 >= len(words):
                raise ValueError("global_placement key %s has no value in %r" % (w, text))
            out.append((w, words[i + 1]))
            i += 2
        else:
            raise ValueError("unknown global_placement argument %r in %r" % (w, text))
    return out


def render_gpl_args(pairs) -> str:
    def word(v: str) -> str:
        return "{%s}" % v if (not v or any(c.isspace() for c in v)) else v
    return " ".join(k if v is None else "%s %s" % (k, word(str(v))) for k, v in pairs)


def merge_gpl_args(base: str, extra: str) -> str:
    """The campaign's GLOBAL_PLACEMENT_ARGS with a recipe's: a key both set takes the recipe's value in the
    campaign's position; anything new is appended; flags are kept once."""
    out = parse_gpl_args(base)
    pos = {k: i for i, (k, _) in enumerate(out)}
    for k, v in parse_gpl_args(extra):
        if k in pos:
            out[pos[k]] = (k, v)
        else:
            pos[k] = len(out)
            out.append((k, v))
    return render_gpl_args(out)


def merge_make_vars(base, extra) -> tuple:
    """KEY=VALUE make variables: ``extra`` wins over ``base`` key by key, except GLOBAL_PLACEMENT_ARGS, which is merged
    argument by argument (merge_gpl_args), so a campaign setting such as ariane133's virtual resizing survives."""
    out = {}
    for kv in base:
        k, eq, v = str(kv).partition("=")
        if not eq:
            raise ValueError("make variable %r is not KEY=VALUE" % kv)
        out[k] = v
    for kv in extra:
        k, eq, v = str(kv).partition("=")
        if not eq:
            raise ValueError("make variable %r is not KEY=VALUE" % kv)
        out[k] = merge_gpl_args(out[k], v) if k == "GLOBAL_PLACEMENT_ARGS" and k in out else v
    return tuple("%s=%s" % kv for kv in out.items())


# ------------------------------------------------------------------ the recipe
@dataclass(frozen=True)
class DensityCap:
    rect: tuple            # (xl, yl, xh, yh) in microns
    max_density: float     # percent of the region's sites that standard cells may fill, 0-100

    def __post_init__(self):
        object.__setattr__(self, "rect", _rect(self.rect, "density cap"))
        object.__setattr__(self, "max_density", float(self.max_density))
        if not 0.0 <= self.max_density <= 100.0:
            raise ValueError("density cap: max_density is a percentage in [0, 100], got %r" % self.max_density)


@dataclass(frozen=True)
class RouteAdjust:
    rect: tuple            # (xl, yl, xh, yh) in microns
    layer: str             # routing layer name, e.g. "metal3"
    adjustment: float      # share of the layer's routing capacity removed in the region, 0-1

    def __post_init__(self):
        object.__setattr__(self, "rect", _rect(self.rect, "route adjustment"))
        object.__setattr__(self, "adjustment", float(self.adjustment))
        if not _LAYER.match(str(self.layer)):
            raise ValueError("route adjustment: bad layer name %r" % self.layer)
        if not 0.0 <= self.adjustment <= 1.0:
            raise ValueError("route adjustment: adjustment is a share in [0, 1], got %r" % self.adjustment)


@dataclass(frozen=True)
class CellRecipe:
    name: str = "default"
    density: tuple | None = None            # ("addon", v) | ("absolute", v) | None: the design's own
    pad_global: int | None = None
    pad_detail: int | None = None
    timing_driven: bool | None = None
    routability_driven: bool | None = None
    gpl: tuple = ()                         # ((key, value), ...) of GPL_KEYS not owned by another field
    start: str = "centre"
    source: str = ""                        # start "positions" only: "hbgp", "npz:<file>" or "npzdir:<dir>"
    hold: str = "restart"
    density_caps: tuple = ()
    route_adjust: tuple = ()

    def __post_init__(self):
        if self.start not in STARTS:
            raise ValueError("start must be one of %s, got %r" % (STARTS, self.start))
        if (self.start == "positions") != bool(self.source):
            raise ValueError("start 'positions' needs a source ('hbgp', 'npz:<file>' or 'npzdir:<dir>'), and only it "
                             "has one")
        if self.source and not (self.source == "hbgp" or self.source.startswith("npz:") and len(self.source) > 4
                                or self.source.startswith("npzdir:") and len(self.source) > 7):
            raise ValueError("source must be 'hbgp', 'npz:<file>' or 'npzdir:<dir>', got %r" % self.source)
        if self.hold not in HOLDS:
            raise ValueError("hold must be one of %s, got %r" % (HOLDS, self.hold))
        if self.hold == "keep" and self.start == "centre":
            raise ValueError("hold 'keep' with start 'centre' would keep every cell at the core centre")
        if self.density is not None:
            kind, v = self.density
            v = float(v)
            if kind == "addon" and not 0.0 <= v < 1.0 or kind == "absolute" and not 0.0 < v <= 1.0 or \
                    kind not in ("addon", "absolute"):
                raise ValueError("density is ('addon', 0 <= v < 1) or ('absolute', 0 < v <= 1), got %r" % (self.density,))
            object.__setattr__(self, "density", (kind, v))
        for f in ("pad_global", "pad_detail"):
            v = getattr(self, f)
            if v is not None and (int(v) != v or v < 0):
                raise ValueError("%s is a whole number of sites >= 0, got %r" % (f, v))
        gpl = []
        for k, v in self.gpl:
            if k not in GPL_KEYS:
                raise ValueError("gpl: %r is not a global_placement key (flags belong to other fields)" % k)
            if k in OWNED:
                raise ValueError("gpl: %r is set by another recipe field or by ORFS itself" % k)
            gpl.append((k, str(v)))
        object.__setattr__(self, "gpl", tuple(gpl))
        object.__setattr__(self, "density_caps", tuple(c if isinstance(c, DensityCap) else DensityCap(*c)
                                                       for c in self.density_caps))
        object.__setattr__(self, "route_adjust", tuple(a if isinstance(a, RouteAdjust) else RouteAdjust(*a)
                                                       for a in self.route_adjust))

    # ---- identity
    def settings(self) -> dict:
        return {"density": list(self.density) if self.density else None, "pad_global": self.pad_global,
                "pad_detail": self.pad_detail, "timing_driven": self.timing_driven,
                "routability_driven": self.routability_driven, "gpl": [list(p) for p in self.gpl],
                "start": self.start, "source": self.source, "hold": self.hold,
                "density_caps": [[list(c.rect), c.max_density] for c in self.density_caps],
                "route_adjust": [[list(a.rect), a.layer, a.adjustment] for a in self.route_adjust]}

    @property
    def id(self) -> str:
        return hashlib.sha256(json.dumps(self.settings(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]

    def is_default(self) -> bool:
        return self.settings() == CellRecipe().settings()

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.id, **self.settings()}

    @classmethod
    def from_dict(cls, d: dict) -> "CellRecipe":
        r = cls(name=d.get("name", "default"), density=tuple(d["density"]) if d.get("density") else None,
                pad_global=d.get("pad_global"), pad_detail=d.get("pad_detail"), timing_driven=d.get("timing_driven"),
                routability_driven=d.get("routability_driven"), gpl=tuple(tuple(p) for p in d.get("gpl", ())),
                start=d.get("start", "centre"), source=d.get("source", ""), hold=d.get("hold", "restart"),
                density_caps=tuple(DensityCap(tuple(c[0]), c[1]) for c in d.get("density_caps", ())),
                route_adjust=tuple(RouteAdjust(tuple(a[0]), a[1], a[2]) for a in d.get("route_adjust", ())))
        if d.get("id") not in (None, r.id):
            raise ValueError("recipe %r: stored id %s does not match its settings (%s)" % (r.name, d["id"], r.id))
        return r

    # ---- what the flow gets
    def make_vars(self) -> list:
        """ORFS make variables (KEY=VALUE); GLOBAL_PLACEMENT_ARGS is merged with the campaign's by merge_make_vars."""
        v = []
        if self.density is not None:
            kind, x = self.density
            v += ["PLACE_DENSITY_LB_ADDON=%s" % _num(x)] if kind == "addon" else \
                 ["PLACE_DENSITY=%s" % _num(x), "PLACE_DENSITY_LB_ADDON="]
        if self.pad_global is not None:
            v.append("CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=%d" % self.pad_global)
        if self.pad_detail is not None:
            v.append("CELL_PAD_IN_SITES_DETAIL_PLACEMENT=%d" % self.pad_detail)
        if self.timing_driven is not None:
            v.append("GPL_TIMING_DRIVEN=%d" % int(bool(self.timing_driven)))
        if self.routability_driven is not None:
            v.append("GPL_ROUTABILITY_DRIVEN=%d" % int(bool(self.routability_driven)))
        args = list(self.gpl) + [(f, None) for f in HOLD_FLAGS[self.hold]]
        if args:
            v.append("GLOBAL_PLACEMENT_ARGS=%s" % render_gpl_args(args))
        return v

    def hint_tcl(self, core) -> str:
        """Density caps as soft partial placement blockages, clipped to the core box (xl, yl, xh, yh) in microns; a
        cap wholly outside the core is an error, not a silent drop."""
        if not self.density_caps:
            return ""
        rows = []
        for c in self.density_caps:
            xl, yl, xh, yh = _clip(c.rect, core, "density cap")
            rows.append("  %.4f %.4f %.4f %.4f %s" % (xl, yl, xh, yh, _num(c.max_density)))
        return "\n".join(["# HeurBridge cell-stage density caps (recipe %s %s): soft partial placement blockages"
                          % (self.name, self.id),
                          "set _hb_block [ord::get_db_block]", "set _hb_dbu [$_hb_block getDbUnitsPerMicron]",
                          "foreach {_hb_xl _hb_yl _hb_xh _hb_yh _hb_d} {"] + rows +
                         ["} {",
                          "  set _hb_b [odb::dbBlockage_create $_hb_block [expr {round($_hb_xl * $_hb_dbu)}] "
                          "[expr {round($_hb_yl * $_hb_dbu)}] [expr {round($_hb_xh * $_hb_dbu)}] "
                          "[expr {round($_hb_yh * $_hb_dbu)}]]",
                          "  $_hb_b setSoft", "  $_hb_b setMaxDensity $_hb_d", "}",
                          "puts \"HB_DENSITY_CAPS created %d\"" % len(rows)]) + "\n"

    def fastroute_tcl(self, design_fastroute: str | None, die) -> str:
        """The per-run FASTROUTE_TCL: the design's own (or the platform default, scripts/util.tcl:10-15), then the
        region adjustments clipped to the die box."""
        lines = ["# HeurBridge cell-stage routing hints (recipe %s %s): the design's own global-routing setup first"
                 % (self.name, self.id)]
        if design_fastroute:
            lines.append("source {%s}" % design_fastroute)
        else:
            lines += ["set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) "
                      "$::env(ROUTING_LAYER_ADJUSTMENT)",
                      "set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)",
                      "if {[env_var_exists_and_non_empty MACRO_EXTENSION]} {",
                      "  set_macro_extension $::env(MACRO_EXTENSION)", "}"]
        for a in self.route_adjust:
            xl, yl, xh, yh = _clip(a.rect, die, "route adjustment")
            lines.append("set_global_routing_region_adjustment {%.4f %.4f %.4f %.4f} -layer %s -adjustment %s"
                         % (xl, yl, xh, yh, a.layer, _num(a.adjustment)))
        lines.append("puts \"HB_ROUTE_ADJUST applied %d\"" % len(self.route_adjust))
        return "\n".join(lines) + "\n"


def design_variable(flow_dir: str, design_config: str, name: str, make_vars=(), timeout: int = 120) -> str:
    """A design's ORFS make variable as make sees it (``make print-NAME``), '' when unset."""
    p = subprocess.run(["make", "-s", "-C", flow_dir, "DESIGN_CONFIG=%s" % design_config] + list(make_vars) +
                       ["print-%s" % name], capture_output=True, text=True, timeout=timeout)
    m = re.search(r"^%s = (.*)$" % re.escape(name), p.stdout, re.M)
    if p.returncode != 0 or m is None:
        raise RuntimeError("make print-%s failed: %s" % (name, (p.stdout + p.stderr)[-400:]))
    return m.group(1).strip()


LOG_MARKS = ("HB_WARM_START", "HB_DENSITY_CAPS", "HB_ROUTE_ADJUST")
DRIFT_STEPS = ("3_1_place_gp_skip_io", "3_3_place_gp", "3_5_place_dp")
DUMP_TCL = """read_db {%(odb)s}
set _hb_block [ord::get_db_block]
set _hb_dbu [$_hb_block getDbUnitsPerMicron]
set _hb_fh [open {%(out)s} w]
foreach _hb_i [$_hb_block getInsts] {
  set _hb_loc [$_hb_i getLocation]
  puts $_hb_fh "[$_hb_i getName]\t[expr {[lindex $_hb_loc 0] / double($_hb_dbu)}]\t[expr {[lindex $_hb_loc 1] / double($_hb_dbu)}]"
}
close $_hb_fh
puts "HB_DUMP done"
"""


def log_marks(log_dir: Path) -> dict:
    """{step: {mark: count of its lines}} for the cell stage's own log lines in the run's step logs."""
    out = {}
    for f in sorted(Path(log_dir).glob("*.log")):
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        got = {m: text.count(m + " ") for m in LOG_MARKS if (m + " ") in text}
        if got:
            out[f.stem] = got
    return out


def drift(names: list, start_ll: np.ndarray, dumped: dict) -> dict:
    """How far the started cells are from their start in one step's database (microns): count compared, median,
    max, and the share that moved more than 0.01 um; cells the database lacks are counted, never skipped silently."""
    have = [i for i, n in enumerate(names) if n in dumped]
    if not have:
        return {"compared": 0, "missing": len(names)}
    d = np.linalg.norm(np.array([dumped[names[i]] for i in have]) - start_ll[have], axis=1)
    return {"compared": len(have), "missing": len(names) - len(have), "median_um": float(np.median(d)),
            "max_um": float(d.max()), "moved_share": float((d > 0.01).mean())}


@dataclass
class CellStage:
    """One recipe for every run of an OrfsEvaluator (its ``cell_stage`` field).  ``positions`` gives the start for
    start == "positions": a callable (design, layout) -> (standard-cell indices, lower-left corners in microns); by
    default it comes from the recipe's source (heurbridge/cellstage/positions.py from_source).
    ``design_fastroute`` is the design's own FASTROUTE_TCL ('' = the platform default); None resolves it from ORFS
    on the first run that needs it.  ``check_drift``: after a run whose cells started at given positions, read
    every started cell's location after 3_1, 3_3 and 3_5 (the run's databases, before the evaluator deletes them).
    ``inspect_runs``: read the run's step logs for the cell stage's own lines (off in unit tests)."""
    recipe: CellRecipe
    positions: object = None
    design_fastroute: str | None = None
    check_drift: bool = False
    inspect_runs: bool = True

    def __post_init__(self):
        self._starts = {}
        if self.positions is None and self.recipe.source:
            from .positions import from_source
            self.positions = from_source(self.recipe.source)

    def prepare(self, ev, design, layout, run_id: str, workdir: Path) -> tuple:
        """(Tcl for the macro stage, make variables) of one run."""
        from ..eval import orfs
        r, text = self.recipe, ""
        if r.start == "quadratic":
            if ev.cluster_of is None:
                raise ValueError("recipe %s starts cells at their cluster's position: the evaluator needs cluster_of" % r.id)
            text += ev._warm_start_tcl(design, layout)
        elif r.start == "positions":
            if self.positions is None:
                raise ValueError("recipe %s starts cells at given positions: CellStage.positions is not set" % r.id)
            got = self.positions(design, layout)           # (cells, ll) or (cells, ll, info)
            cells, ll = got[0], got[1]
            info = got[2] if len(got) > 2 else None
            self._starts[run_id] = ([design.names[int(i)] for i in cells], np.asarray(ll, float), info)
            text += orfs.cell_locations_tcl(design, cells, ll, "cell-stage recipe %s %s" % (r.name, r.id))
        text += r.hint_tcl(design.core)
        mv = r.make_vars()
        if r.route_adjust:
            if self.design_fastroute is None:
                self.design_fastroute = design_variable(ev.flow_dir, ev.design_config, "FASTROUTE_TCL",
                                                        ev.make_vars_extra)
            p = Path(workdir) / ("%s.fastroute.tcl" % run_id)
            p.write_text(r.fastroute_tcl(self.design_fastroute, design.die))
            mv.append("FASTROUTE_TCL=%s" % p.resolve())
        return text, mv

    def merge(self, base, extra) -> tuple:
        return merge_make_vars(base, extra)

    def describe(self, make_vars) -> dict:
        return {"recipe": self.recipe.to_dict(), "recipe_id": self.recipe.id, "make_vars": list(make_vars),
                "design_fastroute": self.design_fastroute}

    def inspect(self, run) -> dict:
        """The run's own log lines and, with check_drift, the started cells' drift per step.  Errors are recorded,
        not raised: the evaluation itself stands."""
        out = {}
        if not self.inspect_runs:
            return out
        try:
            d = run.dirs()
            out["log_marks"] = log_marks(d["logs"])
            start = self._starts.pop(run.variant, None)
            if start is not None and isinstance(start[2], dict):
                out["positions_info"] = {k: v for k, v in start[2].items() if isinstance(v, (int, float, str))}
            if self.check_drift and start is not None:
                from .. import tools
                names, ll = start[0], start[1]
                out["drift"] = {}
                for step in DRIFT_STEPS:
                    odb = d["results"] / ("%s.odb" % step)
                    if not odb.exists():
                        out["drift"][step] = "no database (the run stopped earlier)"
                        continue
                    tsv, tcl = d["results"] / ("%s.hb_locations.tsv" % step), d["results"] / ("%s.hb_dump.tcl" % step)
                    tcl.write_text(DUMP_TCL % {"odb": odb, "out": tsv})
                    p = tools.run_group([tools.binary("openroad"), "-no_init", "-no_splash", "-exit", str(tcl)],
                                        timeout=1800)
                    if p.returncode != 0 or not tsv.exists():
                        out["drift"][step] = "dump failed: %s" % (p.stdout + p.stderr)[-300:]
                        continue
                    dumped = {}
                    for line in tsv.read_text().splitlines():
                        f = line.split("\t")
                        if len(f) == 3:
                            dumped[f[0]] = (float(f[1]), float(f[2]))
                    out["drift"][step] = drift(names, ll, dumped)
        except Exception as e:                       # noqa: BLE001 - recorded in the row
            out["inspect_error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
        return out
