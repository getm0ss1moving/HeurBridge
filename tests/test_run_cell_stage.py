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
