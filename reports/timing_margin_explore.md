# What a timing margin costs in J (exploratory)

| Field | Value |
|---|---|
| Report | timing_margin_explore |
| Date | 2026-10-04 |
| Why | the owner's question of 4 Oct: can we give up a little J to pass the timing gates more often? |
| Label | exploratory (descriptive, existing f2 rows and shifted bands only; no new runs; no test) |
| Code | scripts/explore_timing_margin.py (its output below) |

Margin of a layout = the smaller of its setup and hold slack minus the gate threshold (the campaign's same-path replay
median minus 0.02 ns, D6's reference). Table 1: the best J before the gates among each campaign's 20 f2 layouts whose
margin is at least m (n = how many have it). Table 2: the three candidates with a shifted band (the `band` phase:
re-run at three one-site / one-row shifts) and how many of their four positions pass the gates against the tool's replay
at the same shift (decision D11 (b)).

| design | layouts at f2 | best J, margin >= 0.00 ns (n) | best J, margin >= 0.01 ns (n) | best J, margin >= 0.02 ns (n) | best J, margin >= 0.03 ns (n) | best J, margin >= 0.05 ns (n) |
|---|---|---|---|---|---|---|
| bp_fe_top | 20 | 0.8809 (16) | 0.8809 (14) | 0.8809 (13) | 0.8809 (9) | 0.8809 (6) |
| bp_be_top | 20 | 0.9306 (9) | 0.9681 (2) | - (0) | - (0) | - (0) |
| ariane136 | 20 | 0.9757 (10) | 0.9757 (8) | 0.9759 (4) | 0.9760 (3) | 0.9762 (1) |
| swerv_wrapper | 20 | 0.8674 (9) | 0.8674 (5) | 0.8674 (4) | 0.8770 (2) | - (0) |

| design | candidate | positions passing the gates (same-shift tool replay) | J before the gates, min-max |
|---|---|---|---|
| bp_fe_top | bp_fe_top.ls0.n4.f2 | 4 of 4 | 0.8809-0.9060 |
| bp_fe_top | bp_fe_top.ls1.n1.f2 | 3 of 4 | 0.8788-0.9487 |
| bp_fe_top | bp_fe_top.ls7.n2.f2 | 3 of 4 | 0.8741-0.9344 |
| bp_be_top | bp_be_top.M2.v1.s0.f2 | 2 of 4 | 0.9500-1.0643 |
| bp_be_top | bp_be_top.M3.v1.s3.f2 | 2 of 4 | 0.9522-1.0386 |
| bp_be_top | bp_be_top.ls7.n1.f2 | 4 of 4 | 0.9306-1.0002 |
| ariane136 | ariane136.ls5.n5.f2 | 3 of 4 | 0.9753-0.9759 |
| ariane136 | ariane136.ls6.n4.f2 | 3 of 4 | 0.9758-0.9763 |
| ariane136 | ariane136.ls7.n3.f2 | 2 of 4 | 0.9757-0.9766 |

Reading (exploratory):
- **ariane136:** a 0.03-ns margin costs +0.0003 J and a 0.05-ns margin +0.0005 J; ls5.n5 passes the gates at 3 of 4
  band positions against 2 of 4 for TB#3's candidate ls7.n3, at the same J. A margin-aware pick was nearly free here.
- **bp_fe_top:** the best layout already has a margin of more than 0.05 ns.
- **swerv_wrapper:** a 0.03-ns margin costs +0.0096 J.
- **bp_be_top:** expensive: the tool's hold slack there is high (+0.055 ns), so even a 0.01-ns margin costs +0.0375 J
  and no layout has 0.02 ns.
- Sources: local run files `runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/evals_f2.jsonl` and
  `runs/remote/seedB_band_<design>/runs/seed_orfs/<design>/evals_f2.jsonl`.
