"""scripts/run_cell_stage.py with the flow faked: planning, rows, racing, and that baselines are never run."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_cell_stage as RC  # noqa: E402
import run_seed_orfs as RS  # noqa: E402
from heurbridge.cellstage.recipe import CellRecipe  # noqa: E402
from heurbridge.core import synth  # noqa: E402
from heurbridge.eval import orfs  # noqa: E402
from heurbridge.paths import eda_dir  # noqa: E402

pytestmark = pytest.mark.skipif(eda_dir() is None, reason="needs eda/harness/metrics_schema.py")

REC = {"returncode": 0, "gr_wl": 1000.0, "gr_overflow_total": 0.0, "setup_wns_ns": -0.1, "setup_tns_ns": -1.0,
       "hold_wns_ns": 0.01, "total_power_w": 0.1, "detailed_wirelength_um": 1000.0, "vias": 100.0, "drc_violations": 0}


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    des, ref = synth.make_design(seed=5, n_macros=4, n_cells=50, n_io=8)
    camp = tmp_path / "camp"
    camp.mkdir()
    for f in ("baseline.json", "baseline_f2.json"):
        (camp / f).write_text(json.dumps({"records": [REC]}))
    mm = des.is_macro & ~des.is_fixed
    cand = ref.pos[mm].copy()
    cand[0] += 0.001                               # a layout of its own (an identical one would reuse M1's rows)
    row = {"run_id": "d.cand.f2", "program": "LS", "status": "ok", "pos_macros": cand.tolist(),
           "orient_macros": ref.orient[mm].tolist()}
    (camp / "evals_f2.jsonl").write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(RS, "load_design", lambda ns, name, rdir, d: (des, ref, ref.copy(), None))
    dirs = {k: tmp_path / k for k in ("logs", "results", "reports", "objects")}
    monkeypatch.setattr(orfs.OrfsRun, "dirs", lambda self, variant=None: dirs)
    calls = []

    def fake_run(run):
        calls.append(run)
        mv = dict(kv.partition("=")[::2] for kv in run.make_vars_extra)
        return dict(REC, gr_wl=900.0 if mv.get("PLACE_DENSITY_LB_ADDON") == "0.2" else 1000.0,
                    detailed_wirelength_um=900.0 if mv.get("PLACE_DENSITY_LB_ADDON") == "0.2" else 1000.0)
    monkeypatch.setattr(orfs, "run", fake_run)
    recipes = [CellRecipe(name="default"), CellRecipe(name="d02", density=("addon", 0.2)),
               CellRecipe(name="d05", density=("addon", 0.05))]
    rpath = tmp_path / "recipes.json"
    rpath.write_text(json.dumps([r.to_dict() for r in recipes]))
    return camp, rpath, recipes, calls, tmp_path


def _argv(monkeypatch, camp, rpath, tmp, *more):
    monkeypatch.setattr(sys, "argv", ["run_cell_stage.py", "--flow", str(tmp), "--design", "nangate45/d", "--recipes",
                                      str(rpath), "--layouts", "M1,d.cand.f2", "--tag", "t", "--campaign-dir", str(camp),
                                      "--work-home", str(tmp / "wh")] + list(more))


def test_f1_runs_every_recipe_on_every_layout(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "1")
    RC.main()
    rows = RC.jl(camp / "evals_cs_t.jsonl")
    assert len(rows) == 6 and len({r["run_id"] for r in rows}) == 6
    assert all(r["status"] == "ok" and r["program"] == "CS" and r["cs_slot"] == 0 for r in rows)
    assert {(r["cs_layout"], r["cs_recipe_name"]) for r in rows} == {(l, n) for l in ("M1", "d.cand.f2")
                                                                    for n in ("default", "d02", "d05")}
    assert all(r["record"]["cell_stage"]["recipe_id"] == r["cs_recipe"] for r in rows)
    assert json.loads((camp / "cs_t" / "meta.json").read_text())["plan"]["M1"] == [r.id for r in recipes]
    assert not (camp / "meta.json").exists()                       # the campaign's meta.json is never written
    d02 = [c for c in calls if "PLACE_DENSITY_LB_ADDON=0.2" in c.make_vars_extra]
    assert len(d02) == 2 and all(c.stage == "grt" for c in calls)


def test_f2_race_keeps_the_default_and_the_best(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "1")
    RC.main()
    calls.clear()
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "2", "--race", "1")
    RC.main()
    f2 = [r for r in RC.jl(camp / "evals_cs_t.jsonl") if r["fidelity"] == 2]
    assert sorted({r["cs_recipe_name"] for r in f2}) == ["d02", "default"] and len(f2) == 4
    assert all(c.stage == "finish" for c in calls)


def test_refuses_without_campaign_baselines(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    (camp / "baseline_f2.json").unlink()
    _argv(monkeypatch, camp, rpath, tmp)
    with pytest.raises(SystemExit, match="no campaign baselines"):
        RC.main()
    assert calls == []


def test_unknown_layout_and_duplicate_recipes_are_refused(campaign, monkeypatch, tmp_path):
    camp, rpath, recipes, calls, tmp = campaign
    _argv(monkeypatch, camp, rpath, tmp)
    sys.argv[sys.argv.index("--layouts") + 1] = "nope"
    with pytest.raises(SystemExit, match="none of the campaign's ledgers"):
        RC.main()
    dup = tmp_path / "dup.json"
    dup.write_text(json.dumps([CellRecipe(name="a").to_dict(), CellRecipe(name="b").to_dict()]))
    with pytest.raises(ValueError, match="own settings"):
        RC.load_recipes(dup)


def test_default_rows_are_imported_not_run(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    des, ref = RS.load_design(None, "d", camp, None)[:2]
    mm = des.is_macro & ~des.is_fixed
    lay = {"pos_macros": ref.pos[mm].tolist(), "orient_macros": ref.orient[mm].tolist()}
    src = tmp / "evals_tb.jsonl"
    decoy = dict(lay, run_id="d.other.f2", evaluator="orfs_cs_%s" % recipes[1].id, fidelity=2, status="ok", record=REC)
    plain = dict(lay, run_id="d.tb.ref.s0.f2", evaluator="orfs", fidelity=2, status="ok", record=dict(REC, gr_wl=950.0))
    src.write_text(json.dumps(decoy) + "\n" + json.dumps(plain) + "\n")
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "2", "--default-rows", str(src))
    RC.main()
    rows = {(r["cs_layout"], r["cs_recipe_name"]): r for r in RC.jl(camp / "evals_cs_t.jsonl")}
    got = rows[("M1", "default")]
    assert got["imported_from"] == "%s:2" % src and got["imported_run_id"] == "d.tb.ref.s0.f2"
    assert got["record"]["gr_wl"] == 950.0 and got["evaluator"] == "orfs_cs_%s" % recipes[0].id
    assert "imported_from" not in rows[("d.cand.f2", "default")]          # no row of that layout: it ran
    assert len(calls) == 5 and len(rows) == 6


def test_slots_need_the_test_shifts(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    _argv(monkeypatch, camp, rpath, tmp, "--slots", "1")
    with pytest.raises(SystemExit, match="--shifts tb"):
        RC.main()


def test_slots_limit_the_test_shifts(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "1", "--shifts", "tb", "--slots", "1,6")
    RC.main()
    rows = RC.jl(camp / "evals_cs_t.jsonl")
    assert sorted({(r["cs_slot"], tuple(r["cs_shift"])) for r in rows}) == [(1, (2, 0)), (6, (-1, -1))]
    assert len(rows) == 2 * 2 * 3


def _sources(camp, tmp, m1_gr_wl):
    des, ref = RS.load_design(None, "d", camp, None)[:2]
    mm = des.is_macro & ~des.is_fixed
    rows = []
    for rid, pos in (("d.tb.ref.f2", ref.pos[mm]), ("d.tb.cand.f2", ref.pos[mm].copy())):
        if rid.endswith("cand.f2"):
            pos[0] += 0.001                                  # the candidate of the campaign fixture
        rec = dict(REC, gr_wl=m1_gr_wl if "ref" in rid else 1000.0, detailed_wirelength_um=1000.0)
        rows.append(dict(run_id=rid, evaluator="orfs", fidelity=2, status="ok", record=rec,
                         pos_macros=pos.tolist(), orient_macros=ref.orient[mm].tolist()))
    src = tmp / "evals_tb.jsonl"
    src.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return src


def test_verified_default_rows_are_imported_only_when_identical(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    src = _sources(camp, tmp, 1000.0)                        # what the faked flow gives the default recipe
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "2", "--default-rows", str(src), "--verify-default", "1")
    RC.main()
    rows = {(r["cs_layout"], r["cs_recipe_name"]): r for r in RC.jl(camp / "evals_cs_t.jsonl")}
    assert "imported_from" not in rows[("M1", "default")]              # the verification run
    assert rows[("d.cand.f2", "default")]["imported_from"] == "%s:2" % src
    assert len(calls) == 5


def test_a_differing_verification_run_imports_nothing(campaign, monkeypatch):
    camp, rpath, recipes, calls, tmp = campaign
    src = _sources(camp, tmp, 950.0)                         # the source row of M1 differs from the flow's result
    _argv(monkeypatch, camp, rpath, tmp, "--fidelity", "2", "--default-rows", str(src), "--verify-default", "1")
    RC.main()
    rows = RC.jl(camp / "evals_cs_t.jsonl")
    assert not any("imported_from" in r for r in rows) and len(calls) == 6
    assert RC.same_run({"status": "ok", "record": {"gr_wl": 1.0, "duration_s": 5}},
                       {"status": "ok", "record": {"gr_wl": 1.0, "duration_s": 9}}) == (True, {})
