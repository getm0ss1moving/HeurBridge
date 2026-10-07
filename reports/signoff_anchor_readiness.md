# Signoff (f3) and external-anchor readiness

| Field | Value |
|---|---|
| Report | signoff_anchor_readiness |
| Date | 2026-10-02 |
| Status of the claim | infrastructure (no result claim) |
| Checked on | 224 (the EDA server), the repo's ORFS checkout `third_party/ORFS-2024-12` |

## 1 Can f3 signoff (DRC and LVS) run in the current server environment?

**No.** f3 is "f2 plus Magic/KLayout DRC and Netgen LVS" (HEURBRIDGE_TASKS.md:173) and is recorded as unavailable on
the servers (reports/PROGRESS.md:160). Blockers, as checked on 2026-10-02:

| # | Missing component | Evidence | Consequence |
|---|---|---|---|
| 1 | KLayout binary | `command -v klayout` on 224: missing (this check). Our f2 stops at 6_report because ORFS's `finish` streams the GDS through KLayout (heurbridge/eval/orfs.py:155-157) | no GDS, no KLayout DRC |
| 2 | Magic and Netgen binaries | `command -v magic netgen netgen-lvs` on 224: missing (this check) | no Magic DRC, no Netgen LVS |
| 3 | LVS rule deck for nangate45 | the platform config points to `lvs/FreePDK45.lylvs` (third_party/ORFS-2024-12/flow/platforms/nangate45/config.mk:88); the `lvs/` directory does not exist in the checkout (this check). The DRC deck exists (third_party/ORFS-2024-12/flow/platforms/nangate45/config.mk:85, `drc/FreePDK45.lydrc`) | LVS cannot run as configured even with KLayout installed |
| 4 | Layout of the RAM macros | the platform's `gds/` holds only `NangateOpenCellLibrary.gds`; the `fakeram45_*` macros exist as LEF abstracts only (this check) | full-chip DRC and LVS of the macro designs cannot be complete: the macros are black boxes by construction |

What f2 uses instead: the detailed router's DRC count as the canonical DRC when no signoff DRC exists
(heurbridge/eval/orfs.py:392); the LVS gate stays "unchecked" (configs/cost.yaml:12-24).

**Path to f3 (needs the owner's approval for third-party binary downloads, a standing red line):** KLayout, Magic
and Netgen from conda packages into a separate environment with the micromamba already on 224
(`/data/dzy/heura_repr/tools/micromamba`, this check); an LVS deck for FreePDK45 from a newer ORFS checkout; the
fakeram macros treated as black boxes in DRC and LVS (a documented deviation). Effort and success are not
documented in the repo.

**Consequence for claims:** no Track-B result can be called signoff-clean in the production sense; the strongest
statement is "passes the f2 gates (detailed-route DRC count = 0, setup and hold within 0.02 ns of the reference)"
(configs/cost.yaml:12-24). Any production or state-of-the-art claim is blocked until f3 exists.

## 2 External anchor

**Anchor found (in the repo tree): ORFS's own reference metrics of the unmodified flow.** Each ORFS design ships
`metadata-base-ok.json` (a reference run by the ORFS maintainers) and `rules-base.json` (their regression limits).
Our unmodified-flow f2 baseline (two deterministic runs per design) against that reference:

| design | ORFS reference: OpenROAD version, date | routed WL (um) ref / ours | setup WS (ns) ref / ours | power (W) ref / ours | DRC ref / ours |
|---|---|---|---|---|---|
| bp_fe_top | v2.0-17598-ga008522d8, 2024-12-11 | 2,376,571 / 2,376,571 | -0.0771 / -0.0771 | 0.165043 / 0.165043 | 0 / 0 |
| bp_be_top | v2.0-16535-g199588e84, 2024-10-15 | 3,084,898 / 3,011,744 | -0.8636 / -0.2853 | 0.145966 / 0.142159 | 0 / 0 |
| ariane136 | v2.0-17322-g75f345819, 2024-11-26 | 8,685,138 / 8,018,589 | 1.064 / 1.040 | 0.272923 / 0.264648 | 0 / 0 |
| ariane133 | v2.0-7484-ga8187d5b7, 2023-04-01 | 6,466,033 / 7,656,562 | -0.4928 / -0.0146 | not in the reference / 0.345307 | 0 / 0 |
| swerv_wrapper | (reference exists) | 4,967,270 / campaign running | -0.9580 / - | 0.267351 / - | 0 / - |

Sources: reference values, third_party/ORFS-2024-12/flow/designs/nangate45/bp_fe_top/metadata-base-ok.json:103,
:122, :186, :197, :376, :379; bp_be_top/metadata-base-ok.json:87, :107, :159, :170, :320, :323;
ariane136/metadata-base-ok.json:103, :118, :178, :189, :368, :371; ariane133/metadata-base-ok.json:111, :133, :175,
:273, :276. Our values: the local run records runs/remote/seedB_orfs7_<design>/runs/seed_orfs/<design>/baseline_f2.json:11,
:13, :14, :16 (not in the public repo). Our flow: OpenROAD 676f8451, ORFS 2024-12-13 (ENV_REPORT.md:138-139);
ariane133 runs with RTLMP_MAX_LEVEL=1 (reports/PROGRESS.md:326).

Reading (descriptive): our flow reproduces the ORFS reference exactly on bp_fe_top, whose reference was generated two
days before the ORFS commit we pin; the other references come from other OpenROAD versions, so their differences
mix tool versions with our setup and are not attributable. The anchor's use: every Track-B J is normalized to our
own unmodified-flow run (J = 1.00 at f2 by construction, reports/T2_trackB_orfs_bp_fe_top.md:47); the table shows
that this run is the tool's own result, not a weakened baseline.

**No public ranking comparison exists in the repo.** For Track A there is no table of published ICCAD04 or ISPD2005
results in the repo; Track-A J is normalized to our own DREAMPlace mixed-size run (reports/T2_trackA_ibm_dreamplace.md:23)
and measures HPWL after global placement and legalization only (heurbridge/eval/dreamplace.py:104-113: no detailed
placement), so a published HPWL table would not be comparable without a detailed placer and the same benchmark
conventions. Not documented in the repo.
