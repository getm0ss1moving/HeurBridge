# HeurBridge — session handoff log

Newest entry first.  Each entry: what was done, commands, artifacts, open issues.

---

## 2026-09-29 — Session 3 (16:30): spec bigblue3 done; stage hand-off written; code versions of bigblue4

- **Done and checked:** `e0x_spec_bigblue3_r2` (231, 15:50). The task-list bigblue3 component is `e0x_spec_bigblue3`
  {spec_bigblue3, _s1, _s3} + `e0x_spec_bigblue3_r2` {_s2, _s2b}: 300 rows = 50 x 6, no duplicate, one budget
  845.246 s. **Exclude** the dead `spec_bigblue3_s2` inside `e0x_spec_bigblue3` (11 rows, no meta). 13 of 16 parts
  complete; 231 is idle.
- **Code versions of bigblue4 (for the E0 report's deviations):** slices 0-3 run `9b3c8e8`, slices 4-5 `5e1c009`.
  The only change on the E0 path is that `run_placer` reruns a placer SIGKILLed by the host OOM killer instead of
  scoring the case as failed. Results are identical unless such a kill happens. At combine time, check that no
  placer failure appears in slices 0-3 and no `killed (host out of memory)` note in slices 4-7. Slices 6-7 are
  pinned to `5e1c009-20260929112219` (plan key `code`, passed by `relaunch.py` as `hbv run --code`). **Do not
  push code to 225 before bigblue4 ends** (pinning also guards it).
- **T3.9 extension adopted** (owner, 16:00). Bridge-to-bridge parts go ahead now; anything handed to DREAMPlace or
  OpenROAD waits for G0'. `heurbridge/bridge/handoff.py` + `tests/test_handoff.py` (bc19c89); nothing on the
  evaluation path uses it (tested). The plan is kept local (gitignored).
- **Track B:** `seedB_band_bp_fe_top` done (15:56); `reports/T2_trackB_orfs_bp_fe_top.md` regenerated from it.

---

## 2026-09-29 — Session 3 (15:30): bigblue3 equal guard done; bigblue4 timing; slices 6-7 launch rule

- **Done and checked:** `e0x_eq_bigblue3` (231, 14:44): fetched (`hbv.py fetch --port 231`; 231's vault is in RAM,
  fetch promptly), 4 slice dirs `eq_bigblue3{,_s1,_s2,_s3}` = 300 rows = 50 cases x 6 partners, rc 0, no duplicate,
  one budget 846.566 s (`cache:measured`). With ibm08, adaptec1-4 and bigblue1 x 2: 12 of 16 parts complete.
- **bigblue4 timing (rows' wall_s and file times only):** per case ~4.75 h = placer ~10 min per row, memetic ~44 min,
  repertoire ~58 min, bridge-type partners ~43 min + scoring. Slice sizes (30 sources / 8): 4,4,3,4 | 4,3 | 4,4.
  The 3-case slices (s2, s5) end ~01:00-03:00 on 30 Sep, the others ~06:00-07:30.
- **Launch rule for slices 6-7** (keeps at most 12 bigblue4 slices on 225): after two slices have finished (the
  watcher prints `225 SLICE_DONE <run> <dir>`), `e0split/make_bigblue4.py wave spec 6,7 2259.007` then
  `e0split/relaunch.py 225 plan_e0x_spec_bigblue4_w67.json`; after the next two, the same with `eq 6,7 2230.7`.
  Check `free -g` first (available >= ~40 GB). Add the new job names to `watch_extra_225.txt`.
- **Watcher:** also reports finished bigblue4 slices; a wave job's empty prepare dir is no longer flagged stale.
- **Owner's question (downstream-aware bridges):** answered with a gated plan extending T3.9, in the meeting brief
  (version 9) and in a local proposal document (`HEURBRIDGE_PLAN_*.md`, gitignored: unpublished). Open decision.

---

## 2026-09-28 — Session 3 (20:00): full E0 restarted as slices (user-approved); meeting brief

- **Why:** the full E0 is CPU-bound -- memetic and repertoire each spend the bridge's whole budget per case, and
  every output is scored with DREAMPlace: 10-27 min per case on adaptec1-4/bigblue1, ~77 min on bigblue3. As
  launched, G0' would have come ~5 Oct (bigblue4 ~7 days per protocol).
- **What:** `run_e0.py --slice K/N` (commit 9f38847) splits a component's source list over processes; the budget and
  the random-control scale are fixed once per component (`<cache>/budget_<design>.json`; `--budget-s` carries the
  first measurement over a restart, the scale is recomputed from the bridge's unguarded endpoints). Verified: smoke
  test on ibm04 (`e0smoke_slices`: slices share the budget; recomputed displacements identical, diff 0.0; combine
  OK) and on the restarted components (recomputed scale == the original probe's, bigblue1 0.07522169482228229,
  adaptec2 0.08942288385014388). `e0_combine.py` refuses duplicate cases and mixed budgets. DREAMPlace GPU OOM is
  rerun, not scored (4330c96).
- **Restart (user: "yes, restart the E0 jobs as slices"):** the 8 jobs on 225 and `e0_bigblue3` on 231 were
  stopped (each archived its rows: `e0_*` finals), sources saved encrypted (`save_src_{adaptec4,adaptec3,bigblue1,
  adaptec2,bigblue3,bigblue4}`, identical spec/eq copies by sha256), and relaunched as `e0x_*` jobs with
  `--resume-from` + `--after save_src_*` (scratchpad `e0split/relaunch.py`, command files `e0split/*.cmd`). 225: 16
  processes; 231: bigblue3 spec (budget 845.246 s, carried over) and eq (measures its own), 4 slices each.
  `e0_{spec,eq}_bigblue4` stopped on 231 before any row; bigblue4 runs whole on 225 once its designs finish
  (the encrypted source archive was copied to 225's vault).
- **When everything ends:** fetch the `e0x_*` jobs; E0#1 = `e0_combine.py --runs` all spec slices of the 7 ISPD
  designs `--ledger-entry E0#1` (combine checks duplicates and one budget per design); E0#2 the eq slices; E0#3
  spec ibm08 + ibm12.
  **Which directories (29 Sep):** spec bigblue3 = `e0x_spec_bigblue3` {spec_bigblue3, _s1, _s3} (37 cases; its
  slice 2 was OOM-killed at 22:46 on 28 Sep -- its dir there holds 11 rows and no meta: do NOT include it) +
  `e0x_spec_bigblue3_r2` {spec_bigblue3_s2 (restored 11 rows + the rest of sources 25-31), spec_bigblue3_s2b
  (31-38)}. bigblue4 (30 sources) = `e0x_{spec,eq}_bigblue4` {_bigblue4, _s1, _s2, _s3} + `e0x_{spec,eq}_bigblue4_w45`
  {_s4, _s5} + the later wave for slices 6 and 7 (not the w45 jobs' empty prepare dir). Budgets: spec bigblue4
  2259.007 s, eq 2230.7 s (HB_RUDY_IMPL=bmm for every bigblue4 process). Then `report_e0.py` per entry; commit ledger + reports; T5 only if G0' passes.
- **Track-B noise band** (live, `seedB_orfs7_*`): f2 J over replay + 3 one-site shifts 1.03-1.40 (bp_fe_top),
  1.02-1.16 (bp_be_top), 1.001-1.009 (ariane136); the same-path replay fails the f2 timing gate on 4 of 5 designs
  -> proposal (open, user): reference the f2 gates to the same-path replay.
- **Meeting brief** (private artifact, refreshed 19:00): https://claude.ai/artifact/WEwo1A2vGXnV5a55BrYJAr
- **29 Sep afternoon (user decisions):** cost_v3 -- Track-B timing gates vs the same-path replay (median of replay
  + shifts); 225's reproduction monitors stopped. **225's tmux sessions `agent1`, `agent2`, `tmp` belong to another
  project (`/mnt/nas-new/home/<user>/taorui/auto_project`): never stop them.** Reproduction folders staged in
  `/data/dzy/heura_repr/_to_delete_20260929/` on 224 (68 GB), 225 (31 GB), 231 (7 GB); the user runs the final rm.

---

## 2026-09-28 — Session 3 (16:10): T3.7 done; E0 demo positive; full E0 pre-registered and running

- **T3.7** finished: rounds 0 and 1 promoted, round 2 not -> final checkpoint round 1 (`reports/T3_algorithmR_trackA.md`).
- **E0 demo** (ibm04/ibm06, exploratory): the co-trained bridge has the lowest J under both protocols (spec and equal
  guard), p <= 5e-9 vs memetic/repertoire; the random-direction control is close (0.508 vs 0.482) but beaten
  (p = 2.3e-9) -> much of the gain is the f1 guard, the learned direction adds on top. Reports
  `reports/E0_demo_{spec,eq}.md`.
- **Full E0 pre-registered** (commit d186667, 16:06, `reports/E0_preregistration.md`; ledger E0#1 primary ISPD2005
  task-list protocol, E0#2 equal guard, E0#3 IBM held-out) and **running since 16:08**: 225 GPUs 0-3 (8 slots: the
  five smaller ISPD designs x both protocols, ibm08/ibm12) and 231 GPU 4 (bigblue4 x2, bigblue3 x2); inputs from the
  encrypted bundles `e0_inputs`, `bridge_final`, `eda_harness`; vault excludes the source caches.
- **When the runs end**: fetch all 11 jobs; `e0_combine.py --runs <the 7 ISPD spec runs> --ledger-entry E0#1`, the eq
  runs into E0#2, ibm08/ibm12 into E0#3; `report_e0.py` for each; commit ledger + reports. Then T5 if G0' passes.

---

## 2026-09-28 — Session 3 (13:40): user decisions; T4 E0 demo started (0.14.0)

**User decisions:** LLM = deepseek-flash (code default now); f1 timing gates reported, enforced at f2/f3 (cost_v2);
every experiment first as a demo on 225, then at full capacity if the effect is good (possibly on another server in
parallel -- 231 still needs explicit approval).

**E0 demo** on 225 GPUs 1-3 (`e0demo_{spec,eq}_{ibm04,ibm06}`, CHANGELOG 0.14.0): ibm04/ibm06 are outside the
confirmatory set (held-out ibm08/ibm12 + ISPD2005), so the go/no-go does not peek at the test designs. Results
~18:00-18:30: fetch the four runs, `report_e0.py` per variant, compare spec vs equal guard and the random control.
Then, with the final T3.7 checkpoint: pre-register and launch the full E0 (5 seeds) if the demo points the right way.

**231 approved (user, 2026-09-28) for the full E0.** Only GPU 4 is free; root disk full, so everything lives in RAM
(`/dev/shm`: vault `.hbv`, env `.hbenv/hb` pinned to 225's versions, DREAMPlace for sm_89 in `.hbtools`, benchmarks
`.hbdata`). `setup_231` job builds and smoke-tests it (`scripts/server/setup_231.sh`). A reboot of 231 wipes all of
it: fetch results promptly. Designs are assigned whole to one server (3090 vs 4090 results are not bit-identical).

**Track B** (14:00): continued as `seedB_orfs7_*` on 9546dd4 (cost_v2, noise band). Findings (CHANGELOG "Observed"):
the same-path M1 replay is worse than base M1 (bp_fe_top f2 J 1.32, nearly all TNS) -> pair candidates with the
replay and use the noise band; candidate placement failures come from timing-driven GPL (probe: fine with it off).

**E0 tooling ready** for the full run: `e0_preregister.py` (reserve E0#1-3, write reports/E0_preregistration.md,
commit), per-design `run_e0.py --component E0`, pooled `e0_combine.py --ledger-entry E0#1` (and #2, #3).

---

## 2026-09-28 — Session 3 (11:30): ISPD2005 campaign and E3 done; T3 exit gate passed; T0.3 complete

- **ISPD2005 Track A done** (`reports/T2_trackA_ispd_dreamplace.md`): DREAMPlace's M1 best on all 8 designs;
  bigblue2's programs cannot run (dense macro affinity > 4 GB sandbox; see CHANGELOG). **E3 on ISPD2005**
  (`reports/E3_calibration_trackA_ispd.md`): Kendall 0.54, regret 54 % of random, G0 not met.
- **T3.7 round 0 promoted** (T3 exit gate): on ibm04/ibm06 the f1-guarded bridge's final J 0.4815 vs the raw
  heuristics' 0.8870, paired one-sided Wilcoxon p = 2.6e-9 at alpha_j 0.025 (ledger `algR_trackA#1`). Caveat for the
  report and E0: the guard picks alpha with the same f1 that scores the final cost (alpha = 0 is the raw layout).
  Rounds 1-3 continue (round 1 regenerated the heuristic sources, ~4 h; rounds 2-3 reuse round 0's cache, CHANGELOG).
- **T0.3 complete**: ariane133 through detailed routing on ORFS 2024-12 (ENV_REPORT).
- Track B: failures now named (GRT-0116 congestion on several bp_be_top SA layouts; 2-h timeouts in 5_1_grt).

**Running**: 224 `seedB_orfs6_*` (5 jobs, continuing `seedB_orfs5_*` with `--resume-from`: deterministic-failure
reuse and the same-path M1 control, CHANGELOG); 225 GPU 0 `algR_trackA2` (round 2 of 0-3); 225 GPU 1 free.
Progress against the task list: `reports/PROGRESS.md`.

**Next**: T3.7 report (`report_algr.py`) and the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`; then
T4 E0 — needs the user's protocol decision (open issue 8: the co-trained bridge's f1 guard vs f0-only partners;
proposal `--equal-guard` + `--random-control` as pre-registered secondary analyses) and the design set (held-out
ibm08/ibm12; ISPD2005 as the held-out family is ~10x the evaluation cost).

---

## 2026-09-28 — Session 3 (00:40): ORFS timeout fix (0.13.2); Track-B campaign restarted

Some candidate layouts (e.g. SA seeds that scatter macros through the core) keep FastRoute in its overflow
"extra run" for hours; the 7,200 s candidate timeout then fires. It would have killed only the top `make` and left
the sub-make and OpenROAD running beside the next candidate (red line A.2). Fixed before any timeout occurred:
`tools.run_group` kills the whole process group; `hbv.py stop` kills the job's session; `hbv.py run --resume` now
keeps the restored files in later archives (both verified on 224). All five ORFS jobs restarted as
`seedB_orfs5_*` (same arguments; ariane133 with `--make-var RTLMP_MAX_LEVEL=1`; new vault exclude pattern that
keeps the base synthesis/floorplan, see SERVER_RUNBOOK).

Expect a slow Track-B campaign: a normal bp_fe_top candidate takes ~10 min to f1, a route-hostile one 2 h
(timeout, recorded as a failure). If the throughput is a problem: split a design's programs across two jobs
(`--programs`; up to 8 parallel jobs are allowed, 5 in use).

**T3.7 rerun** (0.13.3): `algR_trackA` stopped at its first validation on the GPU (bridge inference defaulted to
the CPU while the model was on CUDA; no training step lost). Fixed; `algR_trackA2` restores the cached sources
and pairs (`--after algR_trackA`; preparation ~100 s per design instead of 1,000-2,000 s) and trains on GPU 0.

**Running**: 224 `seedB_orfs5_*` (5 jobs); 225 GPU 0 `algR_trackA2`; 225 GPU 1 `seedA_ispd_s1`, `seedA_ispd_s2`
(adaptec1-4, bigblue1 done: DREAMPlace's M1 is the best layout on each, next best +6.5-17% J).

**Open (for the ISPD2005 report and T5):** on bigblue2 (23,084 movable macros, MMS convention) all 80 program runs
crash with MemoryError in the sandbox: the program view's dense macro affinity `macro_aff` (M x M float64) is
4.3 GB, above the 4 GB sandbox address-space limit (bigblue4: 8,170 macros, 0.53 GB, fine). Recorded by name;
bigblue2's archive holds M1 only. A sparse affinity for very large M would change the program API (T2.1/T5 template).
Track B: SA layouts often fail ORFS's default global route (GRT-0116) or hit the 2-h timeout; failures are named
since 0.13.4.

---

## 2026-09-27 — Session 3 (late night): ariane133 deviation narrowed; ISPD2005 Track-A campaign started

**ariane133**: the halo-8 settings made its M1 converge but failed the 2024-12 PDN (PDN-0179, 6-um channels at the
core edge). `scripts/orfs_probe.py` (floorplan-only probe on 224) shows `RTLMP_MAX_LEVEL=1` alone converges (6 min)
and passes the PDN with every other value from 2024-12; that single setting (upstream 98b961bb3c) is now the
deviation. `seedB_orfs3_ariane133` stopped (logs in `runs/remote/`), `seedB_orfs4_ariane133` running (CHANGELOG).

**ISPD2005 Track A** (T1.7/T2.7, spec tools) on 225 GPU 1, which the IBM campaign freed (so no third GPU is
needed): `seedA_ispd_s1` (adaptec1, bigblue1, bigblue4) and `seedA_ispd_s2` (adaptec2-4, bigblue2, bigblue3), MMS
convention (all 543-23,084 macros movable), `--out runs/seed_trackA_ispd --archive archive_A0_ispd_s{1,2}`.
Estimate ~12 h (IBM18: 23 s per f1; bigblue4 is 10x larger). bigblue2's 23k macros will hit program time caps
(recorded as failures).

**Running**
- 225 GPU 0: `algR_trackA` (T3.7; data preparation at ibm16 of 13 training + 2 validation designs, CPU; then
  3 rounds x 20k steps on the GPU).
- 225 GPU 1: `seedA_ispd_s1`, `seedA_ispd_s2`.
- 224: `seedB_orfs3_{bp_fe_top,bp_be_top}`, `seedB_orfs2_{swerv_wrapper,ariane136}`, `seedB_orfs4_ariane133`.

**Next**: as in the entry below, plus the ISPD2005 report (`report_trackA.py --label ispd_dreamplace`) and merge of
`archive_A0_ispd_s{1,2}`. Open user decisions: T5 LLM model, E0 protocol (open issue 8), timing gates at f1 (9).

---

## 2026-09-27 — Session 3 (night): OpenROAD built from source; Track-A campaign, E3, T3.7 running

**Track A (spec tools) done**: `reports/T2_trackA_ibm_dreamplace.md` (DREAMPlace M1 is strong: programs win only on
ibm02 -- anomalous M1 -- and ibm06) and `reports/E3_calibration_trackA_dreamplace.md` (G0 not met; f1 guard stands).

**Track B tools**: OpenROAD 676f8451 (the ORFS 8ae3ae36 pin) built from source on 224
(`scripts/server/build_openroad.sh`, launcher `openroad_676.sh`, version `676f8451bb-src`); ORFS checkout patched for a
GUI-less build (`patch_orfs.py`). ariane133's tool-native Hier-RTLMP does not converge at 8 threads (MPL-0040 with
both builds): its runs use upstream's later MPL settings via `--make-var` (documented deviation; user may prefer to
exclude it or allow more threads for M1).

**Running**
- 225 GPU 0: `algR_trackA` (T3.7; data preparation, then 20k steps per round, V5 test with DREAMPlace f1).
- 224: `seedB_orfs3_{bp_fe_top,bp_be_top,ariane133}`, `seedB_orfs2_{swerv_wrapper,ariane136}` (ORFS T1.7/T2.7).

**Next**: fetch and report T3.7 (merge the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`); Track-B
reports per design (`report_trackb_dev.py --runs runs/remote/<job>/runs/seed_orfs --label orfs`) and the f1->f2
calibration; merge the per-design Track-B archives; then T4 (E0, protocol pending the user) and T5 (model pending).

---

## 2026-09-27 — Session 3 (evening): Track B moves to the real ORFS flow; T3.4 done

**Track B = ORFS 2024-12-13 (8ae3ae36) + OpenROAD a008522d8 + Yosys 0.48** (0.13.0). The mini-flow could not be made
ORFS-equivalent on this build (each alignment exposed the next gap; ORFS's kept-resize placement diverges there).
The real flow works: bp_fe_top M1 to 6_report in 15 minutes (setup WNS -0.077 ns, DRC 0). `run_seed_orfs.py` does
the T1.7 baselines and the T2.7 seeding; candidates reuse the base synthesis/floorplan; identical layouts are
evaluated once. In the driver test M2.v0 beat ORFS's own M1 at f2 with every gate passed (J 0.937).

**T3.4 done**: `reports/T3_pretrain_small.md` (checkpoint in the 225 vault as `pretrain_small`).

**Running**
- 224: `seedB_orfs_{bp_fe_top,bp_be_top,swerv_wrapper,ariane133,ariane136}` (hours to days; ariane136's M1 has no
  RTLMP limits and ran > 2 h in the mini-flow — watch it).
- 225 GPU 1: `seedA_dp_s1/_s2` (Track-A spec campaign; ibm17/ibm18 left at 20:10).

**Next**
1. When `seedA_dp_*` end: fetch; `report_trackA.py --label ibm_dreamplace ...`; E3 calibration
   (`calibrate_dev.py`, combined runs dir); launch T3.7 on 225 GPU 0 (command: scratch `algr_cmd.txt`, i.e.
   `--after seedA_dp_s1 seedA_dp_s2 pretrain_small --data eda_harness:eda`, merge the two archives, then
   `algorithm_r.py ... --val ibm04,ibm06 --final dreamplace --pretrained checkpoints/pretrain_small/pretrain_small.pt`;
   ibm08/ibm12 are held back for E0). Merge the job's new alpha-ledger lines into `stats/alpha_ledger.jsonl`.
2. When the ORFS jobs end: fetch; merge `archive_B0_orfs_*`; Track-B report.
3. User decisions still open: T5 LLM model, E0 protocol, a third 225 GPU (ISPD2005).

---

## 2026-09-27 — Session 3 (continued): OpenROAD 2024-12, 225 GPU work, Track B on the servers, DREAMPlace

**User decisions received:** 225's GPUs may be used; the prebuilt OpenROAD 2024-12 package may be downloaded.
(c) — the faulty GPUs on 224/227 — still needs the admin.

**Done (0.11.1 - 0.12.1, CHANGELOG):**
- T0.3: OpenROAD 2.0-17598-ga008522d8 unpacked without root on 224; every required command incl. Hier-RTLMP.
  Flow fixes for this build: virtual timing-driven GPL (it diverged), ORFS density rule (LB_ADDON designs), OpenMP
  capped at 8 threads (**one run exceeded the red line before the cap — disclosed in CHANGELOG 0.12.0**), M1 with 8
  threads as ORFS (bp_fe_top's M1 is identical either way), clock-gate map for swerv_wrapper, fail-fast steps.
- Track B on 224: bp_fe_top M1 at f2 twice, bit-identical, DRC 0 (setup WNS -1.905 ns, TNS -54.9 ns, hold +0.096).
- 225: env `/tmp/.hbenv/hb` (torch 2.6.0+cu118), GPU smoke PASS; a bf16 bug that would have stopped all GPU
  training fixed. **DREAMPlace 4.3.1 built on 225** (`/tmp/.hbtools/dreamplace`); Track-A f1 per spec
  (`DreamplaceEvaluator`, orientations baked, macros FIXED) and M1 = DREAMPlace mixed-size; smoke PASS on ibm01.
- `--final dreamplace` in `algorithm_r.py` / `run_e0.py`; `scripts/report_trackA.py`.
- Unintended write found and fixed: one `.pyc` in the HA-PR harness tree on 224 (remove after `seedA_ibm`).

**Update 16:15:** Track-B flow now follows ORFS for floorplan areas, RTLMP arguments + `-target_util`, synthesis
order and density (CHANGELOG); bp_fe_top's M1 changes with `-target_util`, so all five baselines rerun as `tb5_*` on
224 (fetch: `python scripts/hbv.py fetch --port 224 --run tb5_<design>`); then restart the Track-B seeding
(`seedB_*`). Superseded: `tb3_*`, `tb4_*`, `seedB_bp_fe_top`.

**Running:** 225 GPU 0 `pretrain_small` (T3.4, 200k steps, ~0.048 s/step); 225 GPU 1 `seedA_dp_s1`/`_s2` (Track-A
T1.7/T2.7 with DREAMPlace, 17 IBM designs, ~12 h); 224 `tb3_{ariane133,bp_fe_top,bp_be_top,swerv_wrapper}` (M1 ->
f1 -> f2 x2; ariane133 through detailed routing = the T0.3 Track-B condition); 224 `seedA_ibm` (HB-GP dev
campaign, ibm18 left).

**Next:** ariane136 Track-B baseline; Track-A reports (`report_trackA.py`) when the campaigns end; T3.7 Algorithm R
on 225 with `--final dreamplace --pretrained checkpoints/pretrain_small/pretrain_small.pt` (validation designs to be
fixed in the run's config, e.g. ibm03/ibm06); ISPD2005 Track-A campaign (upload the benchmarks to 225; bigblue4 is
2.2M objects); T2.7 Track-B seeding (programs x seeds at f1, top-10 at f2) once the five baselines exist.

**Decisions for the user:** (1) T5 LLM: `deepseek-v4-pro` (flagship, ~4x the price) or `deepseek-flash` — both think by
default; the old `deepseek-reasoner` name silently maps to flash. (2) The E0 protocol (open issue 8 below) before
T4 is pre-registered. (3) A third 225 GPU for the ISPD2005 campaign (only GPUs 0 and 1 are in use now).

---

## 2026-09-27 — Session 3: server access, encrypted workflow, T0 on 224

**Access.** Key-only SSH works on ports 224, 225, 227, 231, 232, 234 (the lab note `LAB_PORTS_AND_API_KEY.md`
is local-only). The login is shared by several people: everything of ours on the servers goes through
`scripts/hbv.py` (encrypted vault, key on the Mac, RAM workspaces wiped at job end) — see `docs/SERVER_RUNBOOK.md`.
Back up `~/.config/heurbridge/vault.key`: without it the vault cannot be decrypted.

**T0 on 224** (details in ENV_REPORT s.6): T0.1 PASS; T0.4 benchmarks uploaded and verified; T0.6 DeepSeek PASS;
T0.5 env built but **CUDA fails on 224 and 227** (faulty GPU 0 breaks the driver: report to the admin);
**225's four RTX 3090 work but need the user's approval** (A.2); T0.3: conda OpenROAD builds lack Hier-RTLMP and
`place_macro` — a prebuilt 2024-12 package (.deb, unpacked without root) awaits approval to download.

**Running:** `seedA_ibm` on 224 — T1.7/T2.7 Track-A seeding of 17 IBM designs with the deterministic HB-GP f1
(outputs in the vault; `python scripts/hbv.py fetch --port 224 --run seedA_ibm` when done).

**Decisions for the user:** (a) GPU 225 for T3.4 pretraining / T3.7 training; (b) download the prebuilt OpenROAD
package for Track B; (c) ask the admin to reset the faulty GPUs on 224/227.

---

## 2026-09-26 — Session 2: audit of the work so far, Track-B flow fixed and aligned with ORFS, T5 driver

**Server access still blocked** (key-only SSH to 224/227/234: publickey denied), so all work is local.

**Audit findings (each fixed, tested, and in CHANGELOG 0.10.0 / Unreleased)**
- Track-B mini-flow was not ORFS-faithful: placement density 0.6 (ORFS platform default 0.30), core margin 2,
  generic tracks, no tapcells / power grid / port buffers / dont-use. Now layered ORFS config + the ORFS stage
  order (macros -> tapcell -> pdngen -> GP -> resize -> DP -> GRT).
- f1 lost 7 of 18 evaluations: `estimate_parasitics -global_routing` is broken in the local OpenROAD
  (bad_alloc exit, segfault, OOM kill) -> timing/power from placement parasitics for every layout; GR timing
  opt-in. `report_power` segfaulted once the grid existed -> bisected to pdngen's VDD/VSS block pins.
  Every failure is named; the baseline is evaluated 3x (bit-identical at 6 threads; thread count matters).
- FastRoute stopped with GRT-0119 on congested layouts, so OF could never be measured -> `-allow_congestion`.
- P_M: (a) largest-first greedy failed on 0.5% of dense layouts -> fallback orders incl. bottom-left
  packing (1,000/1,000 legal); (b) Track-B spacing must be 2 x MACRO_PLACE_HALO (per-side halo in
  rtl_macro_placer); with 1 x the edge channels broke pdngen on 6 of 16 layouts (PDN-0179).
- V0 certificate rejected every program on real designs (NaN != NaN for unplaced cells) — found by the first
  end-to-end evolution dry run. RLCE groups were unbounded (one 246-macro "group") -> bounded to 8.
- The earlier f0-vs-f1 calibration JSON scored one layout per design -> redone (`scripts/calibrate_dev.py`).
- Run metadata recorded the end-of-run commit with the start-of-run code version -> commit at start.
- Local absolute paths removed from tracked docs; reports relativize paths; dev archives untracked.

**Development results (no claims; stand-ins for the server experiments)**
- T1.1: bookshelf load -> write -> load identity on all 26 designs (`reports/T1_roundtrip_bookshelf.json`).
- E3-lite (one row per distinct layout): f0 J0 (the guard's scorer) vs f1 — Track A (HB-GP,
  `reports/E3_calibration_dev_ibm.md`) Kendall 0.70 / 0.51 / 0.16 on ibm01 / 02 / 03; Track B (mini-flow,
  `reports/E3_calibration_dev_bp_fe_top.md`) Kendall 0.35, top-5 recall 0, f0's pick worse than random. G0 rule
  not met on either track: f0 must not make macro-stage decisions (the spec's f1 guard / fitness stand).
- T3 dev bridge (`reports/T3_bridge_macro_dev.md`): f0 criterion 2.0125 vs raw 2.0411 on ibm03 (91% of sources
  improved) while the validation residual and terminal error rose.
- E0 dev on held-out ibm04 / ibm06 (`reports/E0_partner_ablation_dev.md`; 16 programs x 5 seeds, every partner
  decides on f0, final J = HB-GP f1): G0' dev **FAIL** (co-trained vs memetic p = 0.99, vs repertoire p = 0.68;
  ledger E0_dev#1). The bridge's mean J is lower (0.509 vs raw 0.587) only because it rescues catastrophic
  sources (M5.v1: J 3.45 -> 0.76); paired vs raw it wins 71 / loses 89 (median +0.0004; ibm06: 15 / 40): the
  f0 guard accepts moves that f1 rejects. Portfolio J (best program per design) is the same for all partners
  (0.429-0.432). With the bridge's guard at f1 and the equal f1 guard for the others (E0_dev#2), G0' passes
  (p = 2.1e-5 / 0.0052) — but a random displacement of matched length with the same guard does as well as the
  bridge (geometric-mean J ratio vs raw 0.933 vs 0.931, bridge vs control p = 0.071; E0_dev#3), and HB-GP was
  not reproducible in these runs (winner's curse on noise). **Deterministic rerun with all controls**
  (`reports/E0_partner_ablation_dev_deterministic.md`, E0_dev#4): G0' criterion met (p = 8.6e-5 / 0.0061), the
  learned-transport check inconclusive (bridge vs random direction p = 0.056: 22 : 1 for the bridge on ibm06,
  6 : 11 on ibm04). With a CPU-trained 2-design bridge this is suggestive only; the server E0 decides.
- Track-B dev seeding on bp_fe_top with the corrected flow (`reports/T2_trackB_dev_bp_fe_top.md`): 80/80
  evaluations completed, gates passed on 62% (all failures setup WNS), 15 distinct gated layouts beat the M1
  baseline (J 0.95); best M5.v0 0.8559; dev archive top-5 0.856-0.879 (fidelity 1).
- Track-B f2 verification (`reports/E3_calibration_dev_bp_fe_top_f1f2.md`; ORFS-style staged f2: CTS,
  repair_timing, DRT, OpenRCX): 14/14 layouts routed with DRC 0. f1 -> f2 Kendall 0.50; the f1 gates predict
  the f2 gates badly (10 of 12 f1-passing layouts fail at f2; one f1-failing layout passes). Two layouts beat
  M1 with every f2 gate passed: M4.v2 J 0.959 (gated out at f1) and M3.v0 0.989. The best f2 J (M3.v2 0.9445,
  better setup WNS than M1) fails only because its met hold slack (+0.074 ns) is > 0.02 ns below M1's (+0.095).

**New tools**: `scripts/run_evolution.py` (T5 driver; `--llm mock` dry runs, all five proposers work end to
end), `scripts/run_f2_miniflow.py` + `MiniflowF2Evaluator` (Track-B dev f2: CTS, repair_timing, GRT, DRT,
fill, OpenRCX, STA — untested on the tool yet), `scripts/calibrate_dev.py`, `run_e0.py --guard-fidelity
--equal-guard`.

**Open issues / decisions for the user (additions)**
8. E0 protocol (T4, before it is pre-registered) — supported by the dev runs above: the co-trained bridge's guard sees f1, memetic and
   repertoire decide on f0 only. With a weakly calibrated f0 (Kendall 0.03-0.65 above) the bridge can win
   through the guard's access to f1 alone. Proposal: run E0 with `--equal-guard` (every partner's output
   kept only if it beats the raw layout at the same fidelity) and `--random-control` (the bridge's guard along
   a random displacement of matched length); both are implemented. Also required: reproducible evaluators
   (fixed thread counts; HB-GP was not) and a final cost evaluated independently of the guard's evaluations
   (on the server the f1 guard and the f2 final cost are separate runs, which already satisfies this).
9. Timing gates at f1 — now with f2 evidence: at f1 (pre-CTS, no timing repair) 38% of bp_fe_top layouts fail
   the 0.02 ns setup-WNS gate against M1, but the f1 gates predict the f2 gates badly (10 of 12 f1-passing
   layouts fail at f2, and the best gated f2 layout, M4.v2, was gated out at f1). Proposal: at f1 report the
   gates but rank by J before the gates; enforce the gates at f2/f3 (needs your decision: frozen rule B.3).
   Related: the frozen guard also fails a *met* check whose slack shrinks by > 0.02 ns (hold +0.095 -> +0.074
   ns keeps the best f2 layout out). If that is not intended, a "met stays met" rule for positive baselines is
   the alternative — your call; nothing was changed.
10. The (1+OF) term (open issue 6) is confirmed on Track B: GR overflow 8 against a zero-overflow baseline
    raises J from ~0.95 to 2.14.

---

## 2026-09-25 — Session 1 (later): local Track-B flow, dev bridge training, overflow-proxy fix

**Local Track B (development).** `heurbridge/eval/miniflow.py` runs a minimal Nangate45 flow in the local
OpenLane container (OpenROAD b16bda7e, Yosys 0.38; current ORFS does not run there). On `nangate45/bp_fe_top`:
hierarchical synthesis 15 s, floorplan 4 s, tool-native `rtl_macro_placer` (M1) 285 s, f1 126 s (GR WL 1.758e6 um,
overflow 0, setup WNS -2.20 ns / TNS -310.9 ns pre-CTS, hold +0.086 ns, 0.128 W). Placement/GR results are
deterministic across repeats; the old build segfaults intermittently after GR (evaluator retries once and
records the crash). `place_macro -exact` is not available in this build (made optional).
*[2026-09-26: these are flow-v1 values (density 0.6, no tapcells/power grid, GR-stage timing); superseded —
see the 2026-09-26 entry.]*
```bash
nohup .venv/bin/python scripts/run_seed_miniflow.py --design nangate45/bp_fe_top --seeds 2 > logs/seed_miniflow_bp_fe_top.log 2>&1 &
```
The first attempt failed on every candidate because of `-exact` (a harness bug, recorded as eval_failed);
its records are kept in `runs/seed_miniflow/bp_fe_top/failed_attempt_1/`.

**Track-A overflow proxy fixed.** Raw RUDY overflow in microns made (1+OF)~ explode against zero-overflow
baselines (ibm02 J up to 2e4; an artificial 25% "gain" on ibm03). Proxy is now `rudy_of_pct`; the development
archive was rebuilt from stored records: `archive_dev_v2` (`scripts/rescore_archive.py`). With it the benchmark
macro positions are the best layout on ibm01-03 and the seed heuristics are 1.8-9.5% worse.

**Dev bridge (round 0).** `scripts/train_bridge.py --train ibm01,ibm02 --val ibm03 --archive archive_dev_v2`
(CPU, 1.13M params, 256 pairs). Guarded post-projection f0 on held-out ibm03: 2.0393 / 2.0389 / 2.0322 vs raw
2.0411 at steps 400 / 800 / 1200 (up to 0.44% better; the guard picks alpha > 0 for 40-53% of sources).
Development evidence only (two training designs, f0 criterion); not the T3 exit gate.

**Also added:** ODB loader (verified on nangate45 gcd), V5 promotion gate + H8 null injection, ORFS signoff
stage (f3), MMD^2, Algorithm R driver, report generators, `docs/SERVER_RUNBOOK.md`, T1 baseline table (dev).

**Open issues (additions)**
6. The (1+OF)~ normalization also makes the Track-B J very sensitive when the baseline GR overflow is ~0
   (decision for the user: keep frozen weights, or use e.g. log(1+OF) / an absolute cap).
7. The bridge is not conditioned on x^h (deviation from T3.2, evidence in CHANGELOG 0.3.0).

---

## 2026-09-25 — Session 1 (continued): T0.4 local, T1-T7 software, first development campaign

**Server access is still blocked** (key not authorized), so everything below ran on the Mac. Versions v0.2.0 ..
v0.8.x are on GitHub (`getm0ss1moving/HeurBridge`, tags `v*`); CHANGELOG.md lists every change.

**Done (local, tested; 100+ tests)**
- T0.4 benchmarks on the Mac with sha256 manifests (`configs/manifests/`): IBM-MSwPins bookshelf + LEF/DEF,
  ISPD2005 (originals offline; Drive copy, header statistics match), ORFS Nangate45 macro designs (sparse clone).
- T0.3 probe on the local OpenLane OpenROAD (b16bda7e): every required command and flag present
  (`reports/env/openroad_probe_local_openlane_b16bda7e.txt`). `ENV_REPORT.md` is a draft.
- T1.4 f1 (OpenROAD Track-B script + parser; Track-A metrics; HB-GP dev placer), Track-B ORFS glue
  (`eval/orfs.py`: MACRO_PLACEMENT_TCL injection, stage grt = f1, finish = f2).
- T2.2 seed population (16 programs, V0-certified), T2.5 P_M, T2.6 archive, T2.7 driver (resumable).
- T3 bridge (graph, model, pairs + symmetry matching, loss, trainer, guarded inference); all T3.10 unit tests
  pass. Deviation: no x^h conditioning (evidence in CHANGELOG 0.3.0).
- T4 partners + E0 driver; T5 prompts/skill v0, RLCE, fitness, MAP-Elites, engine with 5 proposers;
  T6.1 online solve (macro stage); T6.2 calibration + gate G0; T7.1 V1 metamorphic tests; T7.2/7.3 stats and
  alpha ledger; T7.5 originality check.

**Development campaign (Track-A stand-in, NOT a pre-registered experiment)**
```bash
.venv/bin/python scripts/run_seed_archive.py --suite ibm --designs ibm01,ibm02,ibm03 --evaluator hbgp \
    --out runs/seed_dev --archive archive_dev --min-fidelity 1
```
Archive `archive_dev/` (labelled DEV, fidelity 1). ibm01 top J: baseline 0.450, best heuristic 0.493;
ibm02: 0.450 / 0.458 (Track-A partial J = 0.30 rWL~ + 0.15 (1+OF)~ with HPWL and RUDY proxies).

**Open issues / decisions for the user**
1. SSH key authorization (blocks T0.1-server, T0.2, T0.3 install, T0.5, and every real f1/f2 run).
2. DeepSeek key: put `DEEPSEEK_LAB_API_KEY` in the server environment (not in chat).
3. Track-A cost: bookshelf designs have no timing/power; J uses rWL (HPWL proxy) + OF (RUDY proxy) only,
   and Track-A archives would admit fidelity-1 elites. Needs your confirmation.
4. HB-GP is a stand-in (not DREAMPlace) and does not converge on ibm18; DREAMPlace must be built on the server.
5. `eda/harness/lef_def.py` orientation handling (CHANGELOG 0.1.0 findings) -- **confirmed 2026-09-26 with
   OpenROAD's pin geometry** (`reports/V3_pin_geometry_vs_openroad.json`: OpenROAD = HeurBridge exactly;
   lef_def +5.25..5.96% on spm). Decision for the user: revise the HA-PR `hpwl_um` numbers or not.

---

## 2026-09-25 — Session 1: T0.1 (local), T1 foundations

**Environment.** Local clone of `github.com/getm0ss1moving/HeurBridge` (git `main`). HA-PR harness: the
English copy `heura_repro_en/eda` next to the repo on the Mac, exported as `$HEURA_EDA_BASE` (the task list's
`papers/heura_repro` no longer exists). Local venv: Python 3.11, torch 2.14 (CPU), PyG 2.8.

**T0.1 inherit state (local): PASS.**
```bash
cd "$HEURA_EDA_BASE"    # the HA-PR harness (English copy)
python3 harness/smoke_test.py            # SMOKE_TEST_PASS
python3 harness/session_status.py        # v2=222, control coverage 46/46
python3 harness/validate_replay_v2.py    # VALIDATE_REPLAY_V2_PASS
python3 harness/build_checkpoint_dataset.py --strict   # 46 decisions / 176 samples / 0 errors
```
Server side (224) pending: SSH key not yet authorized (see open issues).

**T1.1–T1.3, T1.6 (local).** See CHANGELOG 0.1.0. Tests: `.venv/bin/python -m pytest -q tests` → 27 passed.

**Open issues**
1. **Server access blocked.** Password login is not used by the agent. A dedicated key
   `~/.ssh/id_ed25519_heurbridge` was created; the owner must authorize it once:
   `for p in 224 225 226 227 228 229 230 231 232 233 234; do ssh-copy-id -i ~/.ssh/id_ed25519_heurbridge.pub -p $p <user>@<host>; done`.
   Port 223 closed the connection during probing.
2. `lef_def.py` orientation handling (CHANGELOG findings) — verify with OpenROAD `odb` pin coordinates.
3. `DEEPSEEK_LAB_API_KEY` is not set locally; needed for T0.6 and T5.
