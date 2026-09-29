# Demo: DREAMPlace started from the macro bridge's cell sketch

| Field | Value |
|---|---|
| Report | demo_sketch_start |
| Date | 2026-09-29 17:36 |
| Node | 231 (RTX 4090, GPU 4) |
| Track | A (DREAMPlace f1: GP + LG with the macros fixed, f0 metrics; J on the seeding campaign's M1 scale) |
| HeurBridge version / git | 0.14.0 / c1447c27e0dd8718e3d0efc51951028fd9e99f1f |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (owner's request, 29 Sep; exploratory) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (exploratory demo) |

## Setup

The 64 bridge-refined macro layouts of the E0 demo (ibm04, ibm06: 16 programs x 2 seeds; the guard's alpha read from the E0 demo's rows, the bridge endpoint recomputed; the first case reproduces the E0 demo's J to 1e-8). Each layout is placed three times; only where the standard cells start differs:

- **centre**: DREAMPlace's default (random_center_init_flag = 1), today's f1;
- **sketch**: every cell at its cluster's position in the bridge's guarded output (the stage hand-off, `heurbridge/bridge/handoff.py`);
- **quadratic**: every cell at its cluster's quadratic position around the same macros (control).

## Results

| arm | mean J |
|---|---|
| centre | 0.4822 |
| sketch | 0.4828 |
| quadratic | 0.4948 |

| comparison (paired, J difference; negative = first is better) | n | median | mean | wins | losses | one-sided p (first < second) |
|---|---|---|---|---|---|---|
| sketch-centre (all) | 64 | +0.0004 | +0.0006 | 28 | 36 | 0.972 |
| sketch-centre (alpha>0) | 54 | +0.0008 | +0.0007 | 23 | 31 | 0.98 |
| quadratic-centre (all) | 64 | +0.0004 | +0.0126 | 28 | 36 | 0.966 |
| quadratic-centre (alpha>0) | 54 | +0.0007 | +0.0150 | 23 | 31 | 0.974 |
| sketch-quadratic (all) | 64 | +0.0000 | -0.0120 | 28 | 26 | 0.437 |
| sketch-quadratic (alpha>0) | 54 | -0.0002 | -0.0143 | 28 | 26 | 0.437 |

**Where the cells end up (DA0).** Area-weighted RMS distance, in normalized core units, from each start to the cluster centroids of the centre-start placement: sketch median 0.240, quadratic median 0.262 (the sketch is closer in 35 of 64 cases). The final cluster centroids of the three placements of one layout differ far less: centre vs sketch start median RMS 0.023, centre vs quadratic 0.018 (unweighted).

**Determinism.** The 10 cases whose guard kept the raw heuristic (alpha = 0) give the sketch and the quadratic arm the same start; their J are identical in 10.

## Reading

DREAMPlace's global placement converges to nearly the same placement from any of the three starts, and the bridge's cluster sketch is about ten times farther from that placement than the placements are from each other. Starting positions are therefore not a useful port for handing the sketch to DREAMPlace, and the sketch itself is a weak prediction of where the cells go (the bridge weights clusters at 0.1 x their area relative to macros in its loss).

## Reproduce

```
python scripts/demo_sketch_start.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp --e0-demo runs/e0_demo --bridge checkpoints/algR_trackA_final/best.pt --out runs/demo_sketch
python scripts/demo_sketch_start.py --report runs/demo_sketch --out reports/demo_sketch_start.md
```
