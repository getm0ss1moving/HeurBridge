"""Program contract and sandbox (task T2.1, verification layer V0).

Contract
    def heuristic(design, upstream, rng) -> pos | (pos, orient)
  design    DesignView: read-only numpy arrays (normalized to the core box)
  upstream  (N,2) positions from the upstream stage or None
  rng       numpy.random.Generator (the only source of randomness)
  returns   pos (N,2) float normalized centres; optional orient (N,) ints 0..7
The harness turns the result into a Layout; fixed objects and objects outside the
stage scope must be returned unchanged (checked by core.contract).

Enforcement
  1. AST allow-list: imports only from ALLOWED_MODULES; no dunder attributes, no
     I/O-capable attributes (np.load, scipy.io, nx.read_*, ...), no eval/exec/open/
     getattr/globals/...; no threads.
  2. Execution in a separate interpreter (``python -s -P``, clean env) with RLIMIT_CPU and
     RLIMIT_AS, a wall-clock timeout, an empty working directory, and a PEP 578
     audit hook that raises on file, OS, socket, subprocess, ctypes and thread
     events and on any import of a module that was not pre-loaded.
  3. Output shape/dtype/range validation (+ contract check by the caller).
  4. Determinism: two runs with the same seed must be bit-identical.
  5. MR1 permutation equivariance on a small design: relabel objects and nets;
     the output must equal the permuted output (same seed).  Programs should
     iterate in ``design.canonical_order`` and draw randomness in that order.
Programs are stored content-addressed (sha256) under archive/programs/.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core import orient as O
from ..core.design import Design, Layout

ALLOWED_MODULES = ("numpy", "scipy", "networkx", "math", "heapq", "itertools", "collections")
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "memoryview", "help", "exit", "quit", "dir", "type", "object",
    "os", "sys", "subprocess", "socket", "threading", "multiprocessing", "ctypes", "importlib", "builtins",
    "pickle", "shutil", "pathlib", "io", "signal", "resource", "gc", "inspect",
}
FORBIDDEN_ATTRS = {
    "load", "loads", "save", "savez", "savez_compressed", "savetxt", "loadtxt", "genfromtxt", "fromfile", "tofile",
    "memmap", "open_memmap", "fromregex", "DataSource", "ctypeslib", "f2py", "distutils", "io", "lib", "testing",
    "system", "popen", "spawn", "fork", "remove", "unlink", "rmdir", "mkdir", "makedirs", "rename", "chdir",
    "utils", "readwrite", "drawing", "linalg_lapack", "show_config", "dump", "dumps",
}
FORBIDDEN_ATTR_PREFIX = ("read_", "write_", "generate_", "parse_", "__")
PRELOAD = ("numpy", "scipy", "scipy.sparse", "scipy.sparse.csgraph", "scipy.sparse.linalg", "scipy.spatial",
           "scipy.optimize", "scipy.linalg", "scipy.cluster.vq", "scipy.cluster.hierarchy", "scipy.ndimage",
           "scipy.stats", "networkx", "math", "heapq", "itertools", "collections")


# ============================================================================ design view
class DesignView:
    """Read-only view of a Design for heuristic programs (normalized core coordinates)."""

    FIELDS = ("size", "is_macro", "is_fixed", "is_io", "movable", "init_pos", "orient", "pin_obj", "pin_off",
              "net_ptr", "pin_idx", "net_weight", "obj_key", "canonical_order", "group", "macro_idx", "cluster",
              "cluster_area", "core_wh", "macro_order", "macro_size", "macro_group", "macro_aff", "io_pull", "io_w",
              "obstacles", "misc")

    def __init__(self, arrays: dict):
        for k, v in arrays.items():
            if isinstance(v, np.ndarray):
                v = v.copy()
                v.setflags(write=False)
            object.__setattr__(self, k, v)

    def __setattr__(self, k, v):
        raise AttributeError("DesignView is read-only")

    @property
    def n(self) -> int:
        return len(self.size)

    @property
    def n_nets(self) -> int:
        return len(self.net_ptr) - 1

    def net_pins(self, k: int) -> np.ndarray:
        return self.pin_idx[self.net_ptr[k]:self.net_ptr[k + 1]]

    def to_arrays(self) -> dict:
        return {k: getattr(self, k) for k in self.FIELDS if hasattr(self, k)}


def stable_key(name: str) -> int:
    return int.from_bytes(hashlib.blake2b(name.encode(), digest_size=8).digest(), "little") >> 1


def macro_view(design: Design, layout: Layout, cluster: np.ndarray, keys: np.ndarray) -> dict:
    """Derived macro-level arrays (trusted code) so programs need not rebuild connectivity.

    macro_order  movable macros sorted by label-free key (canonical order); all macro_* arrays follow it
    macro_size   (M,2) normalized effective sizes (orientation applied)
    macro_group  (M,) interchangeable group id (same master and footprint)
    macro_aff    (M,M) symmetric affinity: direct nets (w/(deg-1)) + 0.5 * normalized 2-hop via cell clusters
    io_pull      (M,2) weighted mean position of the fixed objects each macro connects to; io_w (M,) weights
    obstacles    (F,4) fixed-macro rectangles [xl, yl, xh, yh] in normalized coordinates
    """
    import scipy.sparse as sp
    d = design
    wh = d.core_wh
    mm = np.flatnonzero(d.is_macro & ~d.is_fixed)
    mm = mm[np.argsort(keys[mm], kind="stable")]
    M = len(mm)
    eff = O.effective_size(d.size, layout.orient) / wh
    masters = d.masters or ["%.6g_%.6g" % tuple(v) for v in d.size]
    gid, gmap = np.zeros(M, dtype=np.int64), {}
    for j, i in enumerate(mm):
        gid[j] = gmap.setdefault((masters[i], round(float(eff[i, 0]), 9), round(float(eff[i, 1]), 9)), len(gmap))
    col = -np.ones(d.n_objects, dtype=np.int64)
    col[mm] = np.arange(M)
    fixed = np.flatnonzero(d.is_fixed & layout.placed)
    fcol = -np.ones(d.n_objects, dtype=np.int64)
    fcol[fixed] = np.arange(len(fixed))
    ncl = int(cluster.max()) + 1 if (cluster >= 0).any() else 0
    deg = d.degrees()
    net_of = d.net_of_pin()
    objs = d.pin_obj[d.pin_idx]
    w = (d.net_weight / np.maximum(deg - 1, 1))[net_of]
    nn = d.n_nets

    def inc(mask, colmap, ncols):
        r = net_of[mask]
        c = colmap[objs[mask]]
        A = sp.coo_matrix((np.ones(len(r)), (r, c)), shape=(nn, max(ncols, 1))).tocsr()
        A.data[:] = 1.0
        return A
    Wn = sp.diags(d.net_weight / np.maximum(deg - 1, 1))
    Am = inc(col[objs] >= 0, col, M)
    aff = (Am.T @ Wn @ Am).toarray() if M else np.zeros((0, 0))
    if ncl and M:
        Ac = inc(cluster[objs] >= 0, cluster, ncl)
        mc = (Am.T @ Wn @ Ac)
        two = (mc @ mc.T).toarray()
        np.fill_diagonal(two, 0.0)
        if two.max() > 0:
            two *= (aff.max() if aff.max() > 0 else 1.0) / two.max()
        aff = aff + 0.5 * two
    if M:
        np.fill_diagonal(aff, 0.0)
    io_pull, io_w = np.full((M, 2), 0.5), np.zeros(M)
    if M and len(fixed):
        Af = inc(fcol[objs] >= 0, fcol, len(fixed))
        mf = (Am.T @ Wn @ Af).tocsr()
        fp = layout.pos[fixed]
        tot = np.asarray(mf.sum(1)).ravel()
        nz = tot > 0
        io_pull[nz] = (mf @ fp)[nz] / tot[nz, None]
        io_w = tot
    fm = np.flatnonzero(d.is_macro & d.is_fixed & layout.placed)
    obst = np.c_[layout.pos[fm] - eff[fm] / 2, layout.pos[fm] + eff[fm] / 2] if len(fm) else np.zeros((0, 4))
    return {"macro_order": mm, "macro_size": eff[mm], "macro_group": gid, "macro_aff": aff.astype(np.float64),
            "io_pull": io_pull, "io_w": io_w, "obstacles": obst}


def make_view(design: Design, layout: Layout, cluster: np.ndarray | None = None, halo: float = 0.0) -> DesignView:
    wh = design.core_wh
    keys = np.array([stable_key(n) for n in design.names], dtype=np.int64)
    masters = design.masters or ["%.6g_%.6g" % tuple(s) for s in design.size]
    gid, groups = np.full(design.n_objects, -1, dtype=np.int64), {}
    for i in np.flatnonzero(design.is_macro):
        k = (masters[i], float(design.size[i, 0]), float(design.size[i, 1]))
        gid[i] = groups.setdefault(k, len(groups))
    cl = np.full(design.n_objects, -1, dtype=np.int64) if cluster is None else np.asarray(cluster, dtype=np.int64)
    ncl = int(cl.max()) + 1 if (cl >= 0).any() else 0
    carea = np.bincount(cl[cl >= 0], weights=design.area[cl >= 0], minlength=ncl) / float(wh[0] * wh[1]) if ncl else np.zeros(0)
    init = layout.pos.copy()
    misc = {"row_h": (design.site[1] / wh[1]) if design.site else 0.0,
            "site_w": (design.site[0] / wh[0]) if design.site else 0.0,
            "halo": (halo / wh[0], halo / wh[1]), "aspect": float(wh[0] / wh[1]), "design_id": design.id}
    mv = macro_view(design, layout, cl, keys)
    return DesignView({
        **mv,
        "size": design.size / wh, "is_macro": design.is_macro.copy(), "is_fixed": design.is_fixed.copy(),
        "is_io": design.is_io.copy(), "movable": ~design.is_fixed, "init_pos": init,
        "orient": layout.orient.astype(np.int64), "pin_obj": design.pin_obj.copy(), "pin_off": design.pin_off / wh,
        "net_ptr": design.net_ptr.copy(), "pin_idx": design.pin_idx.copy(), "net_weight": design.net_weight.copy(),
        "obj_key": keys, "canonical_order": np.argsort(keys, kind="stable"), "group": gid,
        "macro_idx": np.flatnonzero(design.is_macro & ~design.is_fixed), "cluster": cl, "cluster_area": carea,
        "core_wh": wh.copy(), "misc": misc,
    })


# ============================================================================ static checks
def check_source(src: str) -> list:
    """AST allow-list.  Returns a list of violations (empty = ok)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return ["syntax: %s" % e]
    bad = []
    has_fn = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "heuristic":
            has_fn = True
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_MODULES:
                    bad.append("import %s" % a.name)
                for part in a.name.split("."):
                    if part in FORBIDDEN_ATTRS:
                        bad.append("import %s" % a.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or mod.split(".")[0] not in ALLOWED_MODULES:
                bad.append("from %s import" % mod)
            for part in mod.split("."):
                if part in FORBIDDEN_ATTRS:
                    bad.append("from %s import" % mod)
            for a in node.names:
                if a.name in FORBIDDEN_ATTRS or a.name == "*" or a.name.startswith(FORBIDDEN_ATTR_PREFIX):
                    bad.append("from %s import %s" % (mod, a.name))
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            bad.append("name %s" % node.id)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS or node.attr.startswith(FORBIDDEN_ATTR_PREFIX):
                bad.append("attribute .%s" % node.attr)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bad.append("global/nonlocal")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            bad.append("async")
    if not has_fn:
        bad.append("no function 'heuristic'")
    return sorted(set(bad))


def program_hash(src: str) -> str:
    return hashlib.sha256(src.encode()).hexdigest()


def store_program(src: str, root: str | Path, meta: dict | None = None) -> Path:
    h = program_hash(src)
    d = Path(root) / "programs"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (h + ".py")
    if not p.exists():
        p.write_text(src)
    if meta:
        (d / (h + ".json")).write_text(json.dumps(meta, indent=1, default=str))
    return p


# ============================================================================ execution
_CHILD = r'''
import io, sys, struct, time
import numpy as np
inp = sys.stdin.buffer.read()
n_src = struct.unpack("<Q", inp[:8])[0]
src = inp[8:8 + n_src].decode()
z = np.load(io.BytesIO(inp[8 + n_src:]), allow_pickle=False)
arrays = {k: z[k] for k in z.files}
import json
misc = json.loads(str(arrays.pop("__misc__")))
seed = int(arrays.pop("__seed__"))
upstream = arrays.pop("__upstream__")
upstream = None if upstream.size == 0 else upstream
cpu, mem = float(arrays.pop("__cpu__")), float(arrays.pop("__mem__"))
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (int(cpu), int(cpu) + 1))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (int(mem), int(mem)))
    except (ValueError, OSError):
        pass
except Exception:
    pass
import importlib
for m in PRELOAD:
    try:
        importlib.import_module(m)
    except Exception:
        pass

class DesignView:
    def __init__(self, a):
        for k, v in a.items():
            if isinstance(v, np.ndarray):
                v.setflags(write=False)
            object.__setattr__(self, k, v)
    def __setattr__(self, k, v):
        raise AttributeError("DesignView is read-only")
    @property
    def n(self):
        return len(self.size)
    @property
    def n_nets(self):
        return len(self.net_ptr) - 1
    def net_pins(self, k):
        return self.pin_idx[self.net_ptr[k]:self.net_ptr[k + 1]]

arrays["misc"] = misc
view = DesignView(arrays)
out_stream = sys.stdout.buffer
sys.stdout = io.StringIO()
code = compile(src, "<heuristic>", "exec")
ALLOWED = ALLOWED_MODULES
BLOCK = ("open", "os.", "subprocess.", "socket.", "ctypes.", "shutil.", "urllib.", "http.", "ftplib.",
         "smtplib.", "webbrowser.", "sqlite3.", "pty.", "fcntl.", "mmap.", "resource.", "signal.",
         "sys.settrace", "sys.setprofile", "sys._getframe", "threading.", "_thread.", "code.__new__",
         "function.__code__", "marshal.", "pickle.", "winreg.", "gc.")
state = {"locked": False}
NX_ARGMAP = "<class 'networkx.utils.decorators.argmap'> compilation"
def nx_generated(event, args):
    # networkx's argmap decorator compiles its own wrapper from a fixed template on first call
    if event == "compile":
        fn = args[1] if len(args) > 1 else ""
        return isinstance(fn, str) and fn.startswith(NX_ARGMAP)
    if event == "exec":
        return str(getattr(args[0], "co_filename", "")).startswith(NX_ARGMAP)
    return False
def hook(event, args):
    if not state["locked"]:
        return
    if event == "import":
        name = args[0]
        if name not in sys.modules or name.split(".")[0] not in ALLOWED:
            raise PermissionError("sandbox: import %s" % name)
    elif event in ("exec", "compile"):
        if not nx_generated(event, args):
            raise PermissionError("sandbox: %s" % event)
    elif event.startswith(BLOCK):
        raise PermissionError("sandbox: %s" % event)
g = {"__builtins__": {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
     for k in SAFE_BUILTINS if (k in __builtins__ if isinstance(__builtins__, dict) else hasattr(__builtins__, k))},
     "__name__": "heuristic_module"}
imp = __import__
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in ALLOWED:
        raise PermissionError("sandbox: import %s" % name)
    return imp(name, globals, locals, fromlist, level)
g["__builtins__"]["__import__"] = safe_import
exec(code, g)
fn = g["heuristic"]
rng = np.random.default_rng(seed)
sys.addaudithook(hook)
state["locked"] = True
t0 = time.process_time()
status, err = "ok", ""
try:
    res = fn(view, upstream, rng)
except BaseException as e:
    status, err, res = "error", "%s: %s" % (type(e).__name__, str(e)[:500]), None
cpu_used = time.process_time() - t0
buf = io.BytesIO()
if status == "ok":
    try:
        if isinstance(res, tuple) and len(res) == 2:
            pos, ori = np.asarray(res[0], dtype=np.float64), np.asarray(res[1])
        else:
            pos, ori = np.asarray(res, dtype=np.float64), np.asarray(view.orient)
        np.savez(buf, pos=pos, orient=ori)
    except BaseException as e:
        status, err = "error", "bad return value: %s" % e
head = ("%s|%.6f|%s" % (status, cpu_used, err.replace("|", "/"))).encode()
out_stream.write(b"HBOUT" + struct.pack("<QQ", len(head), len(buf.getvalue())) + head + buf.getvalue())
out_stream.flush()
'''

SAFE_BUILTINS = ("abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int",
                 "isinstance", "iter", "len", "list", "map", "max", "min", "next", "pow", "range", "reversed",
                 "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip", "print", "hash", "issubclass",
                 "callable", "repr", "format", "ord", "chr", "bin", "hex", "complex", "property", "staticmethod",
                 "classmethod", "super", "Exception", "ValueError", "IndexError", "KeyError", "RuntimeError",
                 "ZeroDivisionError", "StopIteration", "ArithmeticError", "AssertionError", "TypeError",
                 "NotImplementedError", "OverflowError", "FloatingPointError", "LookupError", "True", "False", "None",
                 "__build_class__")


@dataclass
class RunResult:
    status: str                      # ok | error | timeout | rejected | crash
    pos: np.ndarray | None = None
    orient: np.ndarray | None = None
    cpu_s: float = 0.0
    wall_s: float = 0.0
    error: str = ""


def run_program(src: str, view: DesignView, upstream: np.ndarray | None, seed: int, cpu_s: float = 60.0,
                mem_gb: float = 4.0, wall_s: float | None = None, python: str | None = None) -> RunResult:
    viol = check_source(src)
    if viol:
        return RunResult("rejected", error="; ".join(viol))
    arrays = {k: v for k, v in view.to_arrays().items() if k != "misc"}
    buf = io.BytesIO()
    np.savez(buf, __misc__=np.array(json.dumps(view.misc)), __seed__=np.array(seed),
             __upstream__=np.zeros((0,)) if upstream is None else np.asarray(upstream, dtype=np.float64),
             __cpu__=np.array(cpu_s), __mem__=np.array(mem_gb * 2 ** 30), **arrays)
    payload = struct.pack("<Q", len(src.encode())) + src.encode() + buf.getvalue()
    child = _CHILD.replace("PRELOAD", repr(PRELOAD)).replace("ALLOWED_MODULES", repr(ALLOWED_MODULES)) \
                  .replace("SAFE_BUILTINS", repr(SAFE_BUILTINS))
    env = {"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
           "PYTHONHASHSEED": "0"}
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="hb_sbx_") as cwd:
        try:
            # -s -P (no user site, no unsafe sys.path entry) instead of -I so that PYTHONHASHSEED applies
            flags = ["-s", "-P"] if sys.version_info >= (3, 11) else ["-s"]
            proc = subprocess.run([python or sys.executable, *flags, "-c", child], input=payload, capture_output=True,
                                  cwd=cwd, env=env, timeout=wall_s or (cpu_s * 1.5 + 10))
        except subprocess.TimeoutExpired:
            return RunResult("timeout", wall_s=time.time() - t0, error="wall-clock timeout")
    wall = time.time() - t0
    out = proc.stdout
    k = out.find(b"HBOUT")
    if k < 0:
        err = proc.stderr.decode(errors="replace")[-800:]
        status = "timeout" if proc.returncode in (-9, -24, 152, 137) else "crash"
        return RunResult(status, wall_s=wall, error="rc=%s %s" % (proc.returncode, err))
    lh, lb = struct.unpack("<QQ", out[k + 5:k + 21])
    head = out[k + 21:k + 21 + lh].decode()
    body = out[k + 21 + lh:k + 21 + lh + lb]
    status, cpu, err = head.split("|", 2)
    if status != "ok":
        return RunResult("error", cpu_s=float(cpu), wall_s=wall, error=err)
    with np.load(io.BytesIO(body), allow_pickle=False) as z:
        return RunResult("ok", pos=z["pos"], orient=z["orient"], cpu_s=float(cpu), wall_s=wall)


# ============================================================================ certification
@dataclass
class Certificate:
    ok: bool
    sha256: str
    reasons: list = field(default_factory=list)
    cpu_s: float = 0.0
    checks: dict = field(default_factory=dict)


def to_layout(design: Design, base: Layout, res: RunResult) -> Layout:
    return Layout(pos=np.asarray(res.pos, dtype=np.float64), orient=np.asarray(res.orient).astype(np.int8),
                  schema=base.schema, meta={"from": "program"})


def validate_output(design: Design, base: Layout, res: RunResult, scope: np.ndarray) -> list:
    n = design.n_objects
    bad = []
    if res.pos is None or res.pos.shape != (n, 2):
        return ["pos shape %s != (%d, 2)" % (None if res.pos is None else res.pos.shape, n)]
    if res.orient is None or res.orient.shape != (n,) or not np.issubdtype(res.orient.dtype, np.integer):
        return ["orient shape/dtype %s/%s" % (getattr(res.orient, "shape", None), getattr(res.orient, "dtype", None))]
    if not np.isfinite(res.pos[scope]).all():
        bad.append("non-finite positions in scope")
    if np.any((res.orient < 0) | (res.orient > 7)):
        bad.append("orientation outside 0..7")
    keep = ~scope
    a, b = res.pos[keep], base.pos[keep]
    if not (np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[np.isfinite(a)], b[np.isfinite(b)])):
        bad.append("objects outside the stage scope were changed")
    if not np.array_equal(res.orient[design.is_fixed], base.orient[design.is_fixed]):
        bad.append("fixed objects re-oriented")
    return bad


def permute_design(design: Design, layout: Layout, perm: np.ndarray, net_perm: np.ndarray):
    """Relabel objects (new i = old perm[i]) and nets; returns (design', layout', inverse)."""
    inv = np.empty_like(perm)
    inv[perm] = np.arange(len(perm))
    d = design
    pins_by_net = [d.pin_idx[d.net_ptr[k]:d.net_ptr[k + 1]] for k in range(d.n_nets)]
    new_lists, pin_obj, pin_off = [], [], []
    for k in net_perm:
        lst = []
        for p in pins_by_net[k]:
            lst.append(len(pin_obj))
            pin_obj.append(inv[d.pin_obj[p]])
            pin_off.append(d.pin_off[p])
        new_lists.append(lst)
    from ..core.design import build_csr
    ptr, idx = build_csr(new_lists)
    d2 = Design(id=d.id + "_perm", family=d.family, tech=d.tech, names=[d.names[i] for i in perm], size=d.size[perm],
                is_macro=d.is_macro[perm], is_fixed=d.is_fixed[perm], is_io=d.is_io[perm],
                pin_obj=np.array(pin_obj, dtype=np.int64), pin_off=np.array(pin_off).reshape(-1, 2), net_ptr=ptr,
                pin_idx=idx, net_weight=d.net_weight[net_perm], die=d.die, core=d.core,
                masters=None if d.masters is None else [d.masters[i] for i in perm], rows=d.rows, site=d.site,
                dbu=d.dbu, source=dict(d.source))
    l2 = Layout(pos=layout.pos[perm].copy(), orient=layout.orient[perm].copy(), schema=d2.schema_hash())
    return d2, l2, inv


def certify(src: str, design: Design, layout: Layout, scope: np.ndarray, seeds=(0,), probe: tuple | None = None,
            cpu_s: float = 60.0, mem_gb: float = 4.0, cluster=None, check_mr1: bool = True) -> Certificate:
    """V0 certification: static check, run, output validation, determinism, MR1 on a small probe design."""
    cert = Certificate(ok=False, sha256=program_hash(src))
    viol = check_source(src)
    cert.checks["ast"] = not viol
    if viol:
        cert.reasons += viol
        return cert
    view = make_view(design, layout, cluster)
    outs = []
    for s in list(seeds) + [seeds[0]]:
        r = run_program(src, view, None, s, cpu_s=cpu_s, mem_gb=mem_gb)
        if r.status != "ok":
            cert.reasons.append("run(seed=%d): %s %s" % (s, r.status, r.error))
            return cert
        v = validate_output(design, layout, r, scope)
        if v:
            cert.reasons += v
            return cert
        cert.cpu_s = max(cert.cpu_s, r.cpu_s)
        outs.append(r)
    det = np.array_equal(outs[0].pos, outs[-1].pos) and np.array_equal(outs[0].orient, outs[-1].orient)
    cert.checks["determinism"] = bool(det)
    if not det:
        cert.reasons.append("non-deterministic for a fixed seed")
        return cert
    if check_mr1:
        pd, pl = probe if probe is not None else (design, layout)
        rng = np.random.default_rng(12345)
        perm, nperm = rng.permutation(pd.n_objects), rng.permutation(pd.n_nets)
        d2, l2, inv = permute_design(pd, pl, perm, nperm)
        r1 = run_program(src, make_view(pd, pl), None, seeds[0], cpu_s=cpu_s, mem_gb=mem_gb)
        r2 = run_program(src, make_view(d2, l2), None, seeds[0], cpu_s=cpu_s, mem_gb=mem_gb)
        ok = r1.status == "ok" and r2.status == "ok" and np.allclose(r2.pos, r1.pos[perm], atol=1e-9, equal_nan=True) \
            and np.array_equal(r2.orient, r1.orient[perm])
        cert.checks["mr1"] = bool(ok)
        if not ok:
            cert.reasons.append("MR1 permutation equivariance failed")
            return cert
    cert.ok = True
    return cert
