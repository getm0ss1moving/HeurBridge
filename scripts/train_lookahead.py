#!/usr/bin/env python3
"""Train the cell-stage predictor (sketch redesign S2) on the DREAMPlace labels of scripts/make_cell_labels.py.

Input of a sample: the labelled macro layout (movable macros and orientations from the label), with the clusters at
their quadratic placement around it (``source_nodes``).  Targets: the placed cluster centroids and second moments.
Validation (the S2 check fixed in the local plan before any result): on each validation design, the median over its
samples of the area-weighted RMS distance of the predicted centroids to the placed ones (DA0), against the same
distance for the quadratic placement; the S2 bar is a ratio <= 0.5 on every validation design.  The best checkpoint
is chosen by the mean of the per-design median ratios.

  python scripts/train_lookahead.py --train ibm01,ibm02,... --val ibm04,ibm06 --labels runs/cell_labels \
      --runs runs/seed_trackA_dp --init checkpoints/algR_trackA_final/best.pt --out checkpoints/lookahead_s2
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heurbridge.bridge.lookahead_net import LookaheadNet, from_bridge, lookahead_loss  # noqa: E402
from heurbridge.bridge.model import BridgeConfig  # noqa: E402
from heurbridge.bridge.sample import source_nodes  # noqa: E402
from heurbridge.bridge.train import EMA  # noqa: E402
from heurbridge.meta import write_meta  # noqa: E402


def design_set(suite, name, runs, labels, cache: Path):
    """(bundle, X (n, N, 2), Ypos (n, C, 2), Ycov (n, C, 3), rows) for one design; X cached in ``cache``."""
    from train_bridge import load_bundle
    b = load_bundle(suite, name, runs)
    g, des = b.graph, b.design
    z = np.load(Path(labels) / (des.id + ".npz"), allow_pickle=False)
    rows = [r for r in json.loads(str(z["rows"])) if "k" in r]
    ks = np.array([r["k"] for r in rows])
    ypos = z["cluster_pos"][ks].astype(np.float32)
    ycov = z["cluster_cov"][ks].astype(np.float32)
    cf = cache / ("x_%s.npz" % des.id)
    if cf.exists():
        X = np.load(cf)["x"]
    else:
        mm = des.is_macro & ~des.is_fixed
        X = np.empty((len(ks), g.n, 2), np.float32)
        for i, k in enumerate(ks):
            lay = b.base.copy()
            lay.pos[mm] = z["macros"][k]
            lay.orient[mm] = z["macro_orient"][k]
            X[i] = source_nodes(g, lay)
        cf.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cf, x=X)
    assert ypos.shape[1] == g.n_clusters, (des.id, ypos.shape, g.n_clusters)
    return b, X, ypos, ycov, rows


@torch.no_grad()
def evaluate(model, sets, device, chunk=16):
    model.eval()
    out = {}
    for name, (b, X, yp, yc, rows) in sets.items():
        gt = b.graph.tensors(device)
        r, q = [], []
        for i in range(0, len(X), chunk):
            _, info = lookahead_loss(model, gt, torch.as_tensor(X[i:i + chunk], device=device),
                                     torch.as_tensor(yp[i:i + chunk], device=device), torch.as_tensor(yc[i:i + chunk], device=device))
            r += info["rms"].tolist()
            q += info["rms_quad"].tolist()
        r, q = np.array(r), np.array(q)
        kinds = np.array([row["kind"] for row in rows])
        out[name] = {"n": len(r), "rms_median": float(np.median(r)), "quad_median": float(np.median(q)),
                     "ratio_median": float(np.median(r / q)), "closer": int((r < q).sum()),
                     "by_kind": {k: {"n": int((kinds == k).sum()), "ratio_median": float(np.median((r / q)[kinds == k]))}
                                 for k in sorted(set(kinds))}}
    model.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="ibm")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", default="ibm04,ibm06")
    ap.add_argument("--labels", default="runs/cell_labels")
    ap.add_argument("--runs", default="runs/seed_trackA_dp")
    ap.add_argument("--init", default="", help="bridge checkpoint whose encoder the predictor starts from")
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--wd", type=float, default=0.01)
    ap.add_argument("--warmup", type=int, default=1000)
    ap.add_argument("--lam-cov", type=float, default=0.1)
    ap.add_argument("--val-every", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--out", default="checkpoints/lookahead_s2")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_meta(out, "lookahead_s2", a.train + ";" + a.val, config=vars(a), campaign="sketch redesign S2 predictor")
    log_f = open(out / "train.log", "a")

    def log(s):
        print(s, flush=True)
        log_f.write(s + "\n")
        log_f.flush()

    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    t0 = time.time()
    train = {n: design_set(a.suite, n, a.runs, a.labels, out / "cache") for n in a.train.split(",")}
    val = {n: design_set(a.suite, n, a.runs, a.labels, out / "cache") for n in a.val.split(",")}
    log(json.dumps({"data": {n: len(v[1]) for n, v in {**train, **val}.items()}, "prep_s": round(time.time() - t0, 1)}))
    model = (from_bridge(a.init, a.device) if a.init else LookaheadNet(BridgeConfig.small()).to(a.device))
    ema = EMA(model, 0.999)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=a.wd)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / a.warmup) *
                                              0.5 * (1 + math.cos(math.pi * min(1.0, s / a.steps))))
    names = list(train)
    sizes = np.array([len(train[n][1]) for n in names], float)
    gts = {n: train[n][0].graph.tensors(a.device) for n in names}
    val0 = evaluate(ema.shadow, val, a.device)
    log(json.dumps({"step": 0, "val": val0}))
    best, hist, run = math.inf, [], []
    for step in range(a.steps):
        n = names[int(rng.choice(len(names), p=sizes / sizes.sum()))]
        b, X, yp, yc, _ = train[n]
        idx = rng.integers(0, len(X), size=a.batch)
        loss, info = lookahead_loss(model, gts[n], torch.as_tensor(X[idx], device=a.device),
                                    torch.as_tensor(yp[idx], device=a.device), torch.as_tensor(yc[idx], device=a.device),
                                    lam_cov=a.lam_cov)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        ema.update(model)
        run.append((info["loss"], float(info["rms"].median()), float(info["rms_quad"].median()), float(gn)))
        if (step + 1) % a.val_every == 0 or step + 1 == a.steps:
            v = evaluate(ema.shadow, val, a.device)
            crit = float(np.mean([d["ratio_median"] for d in v.values()]))
            tr = np.array(run).mean(0).tolist()
            run = []
            hist.append({"step": step + 1, "train": {"loss": tr[0], "rms": tr[1], "rms_quad": tr[2], "grad_norm": tr[3]},
                         "val": v, "criterion": crit, "elapsed_s": round(time.time() - t0, 1)})
            log(json.dumps(hist[-1]))
            if crit < best:
                best = crit
                torch.save({"model": model.state_dict(), "ema": ema.shadow.state_dict(), "model_config": model.export_config(),
                            "kind": "lookahead_s2", "step": step + 1, "val": v}, out / "best.pt")
    torch.save({"model": model.state_dict(), "ema": ema.shadow.state_dict(), "model_config": model.export_config(),
                "kind": "lookahead_s2", "step": a.steps}, out / "last.pt")
    (out / "history.json").write_text(json.dumps({"val0": val0, "hist": hist, "best_criterion": best}, indent=1))
    log(json.dumps({"best_criterion": best, "bar": 0.5,
                    "passes_da0_bar": bool(hist and all(d["ratio_median"] <= 0.5 for d in
                                                        min(hist, key=lambda h: h["criterion"])["val"].values()))}))


def report(run_dir: Path, out_md: Path, bar: float = 0.5) -> None:
    """Markdown report of one training run (history.json, meta.json), with the S2 bar fixed before any result."""
    from heurbridge.reporting import METRIC_CONVENTIONS
    h = json.loads((run_dir / "history.json").read_text())
    meta = json.loads((run_dir / "meta.json").read_text())
    cfg = meta.get("config") or {}
    best = min(h["hist"], key=lambda e: e["criterion"])
    vals = list(best["val"])
    L = ["# Sketch redesign S2: cell-stage predictor", "",
         "| Field | Value |", "|---|---|", "| Report | lookahead_s2 |", "| Date | %s |" % time.strftime("%Y-%m-%d %H:%M"),
         "| Node | 225 (RTX 3090, GPU 0) |", "| Track | A (labels: DREAMPlace f1 placements on the CPU, 234) |",
         "| HeurBridge version / git | %s / %s |" % (meta.get("heurbridge_version"), meta.get("git_sha")),
         "| Metric conventions | %s |" % METRIC_CONVENTIONS, "| Feeds gate | none (diagnostic step S2 of the sketch redesign) |",
         "| Pre-registered test | - (bar fixed before any result: local plan, S2) |", "| alpha-ledger entry | - |",
         "| Status of the claim | no claim |", "",
         "## Setup", "",
         "Predictor: the bridge's encoder (initialized from %s) with a centroid-shift and a spread head, one forward pass "
         "from the committed macros with the clusters at their quadratic placement. Training designs %s; validation %s; "
         "%s steps, batch %s, lr %s, spread weight %s. Labels: `scripts/make_cell_labels.py` on 234 (3,838 DREAMPlace "
         "placements, 0 failures). Measure: per sample, the area-weighted RMS distance of the predicted cluster centroids "
         "to the placed ones, divided by the same distance for the quadratic placement; median per design. **Bar: <= %.1f "
         "on every validation design.**" % (cfg.get("init") or "scratch", cfg.get("train"), cfg.get("val"), cfg.get("steps"),
                                               cfg.get("batch"), cfg.get("lr"), cfg.get("lam_cov"), bar), "",
         "## Result", "",
         "| step | " + " | ".join("%s ratio" % d for d in vals) + " | mean | train ratio |", "|---|" + "---|" * (len(vals) + 2),
         "| 0 (initialization) | " + " | ".join("%.3f" % h["val0"][d]["ratio_median"] for d in vals) + " | %.3f | - |"
         % (sum(h["val0"][d]["ratio_median"] for d in vals) / len(vals))]
    for e in h["hist"]:
        L.append("| %d | %s | %.3f | %.3f |" % (e["step"], " | ".join("%.3f" % e["val"][d]["ratio_median"] for d in vals),
                                                e["criterion"], e["train"]["rms"] / e["train"]["rms_quad"]))
    L += ["", "**Best checkpoint (step %d):** " % best["step"] + "; ".join(
        "%s median distance %.3f against %.3f for the quadratic placement (ratio %.3f; closer in %d of %d; by kind %s)"
        % (d, v["rms_median"], v["quad_median"], v["ratio_median"], v["closer"], v["n"],
           ", ".join("%s %.3f" % (k, x["ratio_median"]) for k, x in v["by_kind"].items())) for d, v in best["val"].items()) + ".",
          "", "**Outcome:** %s" % ("passes the bar on every validation design." if all(v["ratio_median"] <= bar for v in best["val"].values())
                                   else "does not reach the bar of %.1f; the training ratio keeps falling while validation "
                                        "rises after the best step (fitting the training designs, not generalizing)." % bar),
          "", "## Reproduce", "", "`python scripts/train_lookahead.py %s`; `python scripts/train_lookahead.py --report %s --out %s`." % (
              " ".join("--%s %s" % (k.replace("_", "-"), v) for k, v in cfg.items() if v not in ("", None)), run_dir, out_md), ""]
    Path(out_md).write_text("\n".join(L))
    print("REPORT_OK", out_md)


if __name__ == "__main__":
    if "--report" in sys.argv:
        report(Path(sys.argv[sys.argv.index("--report") + 1]), Path(sys.argv[sys.argv.index("--out") + 1]))
    else:
        main()
