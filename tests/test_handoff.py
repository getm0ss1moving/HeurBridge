"""Stage hand-off (T3.9 interface): the macro bridge's cluster sketch passed to the next bridge stage."""

import math

import numpy as np
import pytest
import torch

from heurbridge.bridge import handoff as H
from heurbridge.bridge.graph import build_graph
from heurbridge.bridge.model import BridgeConfig, BridgeNet
from heurbridge.bridge.sample import bridge_endpoints, refine, source_nodes
from heurbridge.core import project, synth
from heurbridge.eval import f0
from heurbridge.heuristics.cell.cluster import cluster_cells
from heurbridge.heuristics.macro.registry import all_programs
from heurbridge.online.solve import solve_macro
from heurbridge.pipeline import bridge_data as BD

TINY = BridgeConfig(width=64, layers=2, edge_dim=16, pe_freqs=6, t_dim=32)


def small_case(seed=0, n_macros=6, n_cells=60, cl_seed=0, n_cl=8):
    des, ref = synth.make_design(seed=seed, n_macros=n_macros, n_cells=n_cells, n_io=8)
    cl = cluster_cells(des, n=n_cl, seed=cl_seed)
    return des, ref, build_graph(des, ref, cl)


def model(seed=0, scale=0.5):
    torch.manual_seed(seed)
    m = BridgeNet(TINY)
    for blk in m.blocks:
        torch.nn.init.normal_(blk.film.weight, std=scale)
    torch.nn.init.normal_(m.dec[-1].weight, std=scale)
    return m.eval()


def f0_scorer(des, ref):
    ctx = f0.F0Context(des, ref.orient)
    norm = f0.reference_normalizers(ctx, ref.pos)
    return lambda l: float(f0.surrogate_j0(ctx, torch.as_tensor(l.pos, dtype=torch.float32), norm)[0])


def refined(seed=4):
    des, ref, g = small_case(seed=seed)
    lay = project.legalize_macros(des, ref)[0]
    src = source_nodes(g, lay)
    r = refine(model(seed), g, des, [lay], f0_scorer(des, ref), K=6, sources=src[None])[0]
    return des, ref, g, lay, src, r


def test_off_switch_is_source_nodes():
    des, ref, g = small_case(seed=1)
    lay = project.legalize_macros(des, ref)[0]
    assert np.array_equal(H.next_stage_source(g, lay), source_nodes(g, lay))            # no hand-off: unchanged
    q = H.quadratic_handoff(g, lay)
    assert q.origin == "quadratic" and q.alpha == 0.0
    assert np.array_equal(H.next_stage_source(g, lay, q), source_nodes(g, lay))         # quadratic hand-off: same


def test_sketch_is_the_guarded_candidate():
    des, ref, g, lay, src, r = refined()
    h = H.handoff_from_result(g, r, src, meta={"bridge": "tiny"})
    cand = src + r.alpha * (r.x_bridge - src)                                           # what the guard scored
    assert np.array_equal(h.sketch, np.clip(cand[g.cluster_nodes], 0.0, 1.0))
    assert np.array_equal(h.macros, r.layout.pos[g.obj[g.macro_nodes]])                # the deployed legal macros
    x = H.next_stage_source(g, r.layout, h)
    assert np.array_equal(x[g.cluster_nodes], h.sketch)
    assert np.array_equal(x[g.macro_nodes], r.layout.pos[g.obj[g.macro_nodes]])
    assert h.meta["bridge"] == "tiny" and h.meta["n_clusters"] == g.n_clusters


def test_alpha_endpoints_and_linearity():
    des, ref, g = small_case(seed=2)
    rng = np.random.default_rng(0)
    src = rng.uniform(0.1, 0.9, (g.n, 2))
    end = rng.uniform(0.1, 0.9, (g.n, 2))
    cl = g.cluster_nodes
    assert np.array_equal(H.guarded_sketch(g, src, end, 0.0), src[cl])
    assert np.allclose(H.guarded_sketch(g, src, end, 1.0), end[cl], atol=1e-15)
    assert np.allclose(H.guarded_sketch(g, src, end, 0.5), 0.5 * (src[cl] + end[cl]), atol=1e-15)
    far = end.copy()
    far[cl] = 3.0                                                                      # outside the core
    h = H.make_handoff(g, project.legalize_macros(des, ref)[0], src, far, 1.0)
    assert h.sketch.max() == 1.0 and h.meta["n_clipped"] == len(cl)


def test_translation_equivariance():
    des, ref, g = small_case(seed=3)
    rng = np.random.default_rng(1)
    src = rng.uniform(0.3, 0.6, (g.n, 2))
    end = rng.uniform(0.3, 0.6, (g.n, 2))
    t = np.array([0.07, -0.05])
    for a in (0.25, 0.5, 1.0):
        assert np.allclose(H.guarded_sketch(g, src + t, end + t, a), H.guarded_sketch(g, src, end, a) + t, atol=1e-12)


def test_save_load_roundtrip(tmp_path):
    des, ref, g, lay, src, r = refined(seed=5)
    h = H.handoff_from_result(g, r, src, meta={"ckpt": "abc123", "K": 6})
    p = h.save(tmp_path / "h" / "cand.npz")
    k = H.Handoff.load(p)
    assert k.design_id == h.design_id and k.graph_hash == h.graph_hash and k.alpha == h.alpha and k.origin == h.origin
    assert np.array_equal(k.sketch, h.sketch) and np.array_equal(k.macros, h.macros) and k.meta == h.meta
    H.check(k, g, r.layout)                                                            # still applies after reload


def test_mismatches_are_refused():
    des, ref, g, lay, src, r = refined(seed=6)
    h = H.handoff_from_result(g, r, src)
    H.check(h, g, r.layout)
    other = build_graph(des, ref, cluster_cells(des, n=8, seed=7))                    # another clustering
    if not np.array_equal(other.cluster_of, g.cluster_of):
        with pytest.raises(H.HandoffMismatch):
            H.check(h, other)
    moved = r.layout.copy()
    moved.pos[g.obj[g.macro_nodes[0]]] += 0.01                                        # not the layout it belongs to
    with pytest.raises(H.HandoffMismatch):
        H.next_stage_source(g, moved, h)
    for bad in (np.nan, 1.5, -0.1):
        b = H.Handoff(**{**h.__dict__, "sketch": h.sketch.copy()})
        b.sketch[0, 0] = bad
        with pytest.raises(H.HandoffMismatch):
            H.check(b, g)
    with pytest.raises(H.HandoffMismatch):
        H.check(H.Handoff(**{**h.__dict__, "design_id": "other"}), g)


def test_graph_hash_is_stable_and_sensitive():
    des, ref, g = small_case(seed=8)
    _, _, g2 = small_case(seed=8)
    assert H.graph_hash(g) == H.graph_hash(g2)                                        # deterministic
    _, _, g3 = small_case(seed=8, n_cl=6)
    assert H.graph_hash(g3) != H.graph_hash(g)


def test_anchored_clusters_limits_and_monotone():
    des, ref, g = small_case(seed=9)
    lay = project.legalize_macros(des, ref)[0]
    x = source_nodes(g, lay)
    rng = np.random.default_rng(2)
    s = rng.uniform(0.05, 0.95, (g.n_clusters, 2))
    assert np.array_equal(H.anchored_clusters(g, x, s, 0.0), g.quadratic_clusters(x))   # mu = 0: quadratic
    assert np.abs(H.anchored_clusters(g, x, s, 1e9) - s).max() < 1e-6                    # mu -> inf: the sketch
    d = [np.abs(H.anchored_clusters(g, x, s, mu) - s).mean() for mu in (0.01, 0.1, 1.0, 10.0, 100.0)]
    assert all(a > b for a, b in zip(d, d[1:]))
    h = H.quadratic_handoff(g, lay)
    y = H.next_stage_source(g, lay, h, anchor_mu=5.0)                                  # quadratic anchored to itself
    assert np.allclose(y, source_nodes(g, lay), atol=1e-9)
    with pytest.raises(ValueError):
        H.anchored_clusters(g, x, s, -1.0)


def test_transfer_sketch():
    s = np.array([[0.1, 0.2], [0.8, 0.6], [0.5, 0.5]])
    src_c = np.array([0, 0, 1, 1, 2, -1])
    w = np.array([1.0, 3.0, 2.0, 2.0, 1.0, 5.0])
    assert np.array_equal(H.transfer_sketch(s, src_c, src_c, w), s)                   # same clustering: identical
    fine = np.array([0, 1, 2, 2, 3, -1])                                              # nested (finer) clustering
    t = H.transfer_sketch(s, src_c, fine, w)
    assert np.array_equal(t, s[[0, 0, 1, 2]])
    mixed = np.array([0, 0, 0, 1, 1, 1])                                              # members from several clusters
    t = H.transfer_sketch(s, src_c, mixed, w)
    assert np.allclose(t[0], (1 * s[0] + 3 * s[0] + 2 * s[1]) / 6.0)
    assert np.allclose(t[1], (2 * s[1] + 1 * s[2]) / 3.0)                             # object 5 has no source cluster
    with pytest.raises(H.HandoffMismatch):
        H.transfer_sketch(s, np.array([0, -1]), np.array([0, 1]), np.ones(2))          # dst cluster 1 has no member


def test_member_positions_and_fidelity():
    des, ref, g = small_case(seed=10)
    lay = project.legalize_macros(des, ref)[0]
    h = H.quadratic_handoff(g, lay)
    p = H.member_positions(h.sketch, g.cluster_of)
    m = g.cluster_of >= 0
    assert np.array_equal(p[m], h.sketch[g.cluster_of[m]]) and np.isnan(p[~m]).all()
    assert H.sketch_fidelity(g, h.sketch, h.sketch) == 0.0
    t = np.array([0.03, -0.04])
    assert H.sketch_fidelity(g, h.sketch + t, h.sketch) == pytest.approx(0.05, abs=1e-12)   # RMS of a uniform shift
    ref_c = g.cluster_centroids(lay)
    a = H.sketch_fidelity(g, h.sketch, ref_c)
    assert a == pytest.approx(H.sketch_fidelity(g, ref_c, h.sketch)) and math.isfinite(a)


def test_evaluation_path_does_not_use_handoff():
    """Nothing G0' runs imports the hand-off: partners, E0 driver, evaluators, guard."""
    import importlib
    import inspect
    for mod in ("heurbridge.partners", "heurbridge.bridge.sample", "heurbridge.pipeline.evaluators",
                "heurbridge.eval.dreamplace", "heurbridge.eval.f0"):
        assert "handoff" not in inspect.getsource(importlib.import_module(mod))
    src = open("scripts/run_e0.py").read()
    assert "handoff" not in src


def test_online_keep_handoff_is_opt_in():
    des, ref = synth.make_design(seed=90, n_macros=6, n_cells=60, n_io=8)
    cl = cluster_cells(des, n=8)
    base = ref.copy()
    base.pos[~des.is_macro & ~des.is_io & ~des.is_fixed] = np.nan
    b = BD.make_bundle(des, base, cl)
    progs = [p for p in all_programs() if p["id"] in ("M6.v0", "M7.v0")]
    bridge = BridgeNet(TINY).eval()
    kw = dict(f2=b.scorer, baseline_J2=math.inf, k=2, seeds=2, K=4)
    r0 = solve_macro(des, base, b.view, b.graph, progs, bridge, b.scorer, **kw)
    assert all("handoff" not in c for c in r0.candidates)                             # default: unchanged output
    r1 = solve_macro(des, base, b.view, b.graph, progs, bridge, b.scorer, keep_handoff=True, **kw)
    assert [c["id"] for c in r1.candidates] == [c["id"] for c in r0.candidates]
    assert [c.get("J1") for c in r1.candidates] == [c.get("J1") for c in r0.candidates]   # same decisions
    assert r1.deployed == r0.deployed and r1.J == r0.J
    beam = sorted([c for c in r1.candidates if c["status"] == "ok"], key=lambda c: c["J1"])[:2]
    for c in r1.candidates:
        assert ("handoff" in c) == (c in beam)                                        # only the beam carries one
    for c in beam:
        h = c["handoff"]
        H.check(h, b.graph)
        assert h.origin == "bridge" and h.alpha == c["alpha"]
