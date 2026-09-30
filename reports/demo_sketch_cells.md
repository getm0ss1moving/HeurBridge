# Demo 2: a reinforced cell-level sketch, and the DREAMPlace inputs that can carry it

| Field | Value |
|---|---|
| Report | demo_sketch_cells |
| Date | 2026-09-30 09:22 |
| Node | 231 (RTX 4090, GPU 4) |
| Track | A (DREAMPlace f1: GP + LG with the macros fixed, f0 metrics; J on the seeding campaign's M1 scale) |
| HeurBridge version / git | 0.14.0 / f0253408aa426d320bda31e31a410ef16bc1ea1e |
| Metric conventions | timing setup_hold_v1_2026-09-22; metrics_v2_2026-09-22; HPWL centre (pin_offset_v2); cost cost_v3_2026-09-29 |
| Feeds gate | none (owner's request, 30 Sep; exploratory) |
| Pre-registered test | - |
| alpha-ledger entry | - |
| Status of the claim | no claim (exploratory demo) |

## Setup

The E0 demo's 64 bridge-refined macro layouts (ibm04, ibm06), as in demo 1 (`reports/demo_sketch_start.md`). Each is placed by DREAMPlace in every arm below; J is the E0 cost. The reinforced sketch spreads each cluster's cells over the cluster's own area (total cell area / 0.9, a square around the cluster's sketch position) and orders them inside it by where their outside connections pull them; the spread_* arms first spread the clusters globally to the free area, keeping their order (alternating x/y quantile mapping in bands, macros removed). keep arms multiply DREAMPlace's initial density weight (8e-5 x the wirelength/density gradient ratio) by 100.0, so the density penalty is felt from the first iteration and the start is not first collapsed into a wirelength-optimal clump. infl_* arms widen the cells in the top 10 % of the spread sketch's RUDY utilization (factor u / u_q90, at most 1.3, total added area at most 10 %), through the cell sizes DREAMPlace reads (whole sites: each fraction rounded up with its own probability); J is measured with the real sizes.

## Results

Stopped at the owner's request on 30 Sep 09:14, once ibm04 had answered the question: ibm04 is complete (32 cases in every arm, except the two inflation arms, re-run after a fix and stopped at 22 of 32 cases); ibm06 had reached 4 cases.

Rows of ibm06 are kept in the run directory but not analysed (incomplete).

9 cases repeat another case exactly (the same program with the other seed gave the same layout, and every arm the same J); each is counted once below, leaving 23 distinct cases.

Arm means are over the cases each arm has (n); the paired comparisons below use the cases both arms have.

| arm | n | mean J | mean rWL term | mean OF term | median GP iterations |
|---|---|---|---|---|---|
| centre | 23 | 0.5107 | 9.325e+06 | 0.2861 | 556 |
| cells_sketch | 23 | 0.5131 | 9.344e+06 | 0.2996 | 452 |
| keep_centre | 23 | 0.5133 | 9.345e+06 | 0.3006 | 447 |
| keep_sketch | 23 | 0.5214 | 9.383e+06 | 0.3550 | 354 |
| keep_quad | 23 | 0.5175 | 9.367e+06 | 0.3288 | 379 |
| spread_keep_sketch | 23 | 0.5338 | 9.491e+06 | 0.4231 | 276 |
| spread_keep_quad | 23 | 0.5385 | 9.529e+06 | 0.4498 | 275 |
| infl_sketch | 16 | 0.5031 | 9.33e+06 | 0.2224 | 554 |
| infl_quad | 16 | 0.5052 | 9.336e+06 | 0.2373 | 555 |

| comparison (paired J difference; negative = first is better) | n | median | mean | wins | losses | one-sided p (first < second) |
|---|---|---|---|---|---|---|
| cells_sketch-centre | 23 | +0.0018 | +0.0024 | 5 | 18 | 0.993 |
| keep_sketch-keep_centre | 23 | +0.0059 | +0.0081 | 4 | 19 | 0.999 |
| keep_quad-keep_centre | 23 | +0.0019 | +0.0043 | 6 | 17 | 0.976 |
| keep_sketch-keep_quad | 23 | +0.0055 | +0.0038 | 6 | 15 | 0.992 |
| spread_keep_sketch-keep_centre | 23 | +0.0123 | +0.0205 | 4 | 19 | 0.999 |
| spread_keep_quad-keep_centre | 23 | +0.0139 | +0.0253 | 0 | 23 | 1 |
| spread_keep_sketch-spread_keep_quad | 23 | +0.0000 | -0.0047 | 10 | 11 | 0.217 |
| keep_centre-centre | 23 | +0.0015 | +0.0025 | 4 | 19 | 0.994 |
| spread_keep_sketch-centre | 23 | +0.0134 | +0.0231 | 3 | 20 | 1 |
| infl_sketch-centre | 16 | +0.0029 | +0.0041 | 1 | 15 | 0.999 |
| infl_quad-centre | 16 | +0.0043 | +0.0062 | 0 | 16 | 1 |
| infl_sketch-infl_quad | 16 | -0.0004 | -0.0021 | 11 | 4 | 0.0304 |

Inflation: a median 2687 cells widened per run; the widths DREAMPlace read added a median 2.1 % (range 1.3-2.5 %) of the cell area.

**Where the clusters end up (DA0).** Area-weighted RMS distance, in normalized core units, from each cluster prediction to the cluster centroids of the centre-start placement (median over 23 cases):

| prediction | median distance |
|---|---|
| sketch | 0.235 |
| spread_sketch | 0.344 |
| quad | 0.253 |
| spread_quad | 0.335 |

The spread sketch is closer than the spread quadratic placement in 14 of 23 cases.

## Reproduce

```
python scripts/demo_sketch_cells.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp --e0-demo runs/e0_demo --bridge checkpoints/algR_trackA_final/best.pt --out runs/demo_sketch2 --keep 100.0
python scripts/demo_sketch_cells.py --designs ibm04,ibm06 --runs runs/seed_trackA_dp --e0-demo runs/e0_demo --bridge checkpoints/algR_trackA_final/best.pt --out runs/demo_sketch2_infl --keep 100.0 --arms infl_sketch,infl_quad
python scripts/demo_sketch_cells.py --report runs/demo_sketch2 --also runs/demo_sketch2_infl --designs ibm04 --out reports/demo_sketch_cells.md
```
