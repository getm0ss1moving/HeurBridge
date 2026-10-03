# Defect: the tool never placed ISPD2005's macros (found 3 Oct 2026)

| Field | Value |
|---|---|
| Report | defect_ispd_tool_runs |
| Date | 2026-10-03 |
| Status | confirmed; fixed in code (commit 157bf21); consequences below; the owner's decision on a re-test is D10 (reports/next_phase_decisions.md) |
| Affects | every DREAMPlace mixed-size run (the tool, "M1") on ISPD2005 since the ISPD2005 seeding campaign (28 Sep), and everything that calls those runs "the tool's" |
| Does not affect | IBM; f1 (the macros are fixed in every f1 run by design); every heuristic, local-search or bridge layout (placed by HeurBridge's code) |

## 1 What happened

- HeurBridge loads ISPD2005 in the mixed-size (MMS) convention: every macro movable, set in memory
  (scripts/tool_refine_eval.py:42-53; scripts/train_bridge.py:40-44 for the seeding and E0 bundles).
- The tool's input file is written by `write_oriented_bookshelf` (heurbridge/eval/dreamplace.py). Until the fix it
  copied each node's terminal tag from the source .nodes and wrote /FIXED for every terminal, whatever the design in
  memory said. ISPD2005's source lists its macros as terminals (fixed blocks), so DREAMPlace saw them as fixed in every
  tool run and left them where the benchmark puts them; P_M then legalized them under HeurBridge's spacing rule. The
  "tool's layout" on ISPD2005 was therefore the benchmark's own macro placement after P_M.
- bigblue3 is the exception: its source has movable macros besides its fixed blocks, and the tool placed those.

## 2 Evidence

- The macro layouts of the 8 tool seeds at target density 0.9 (RL#1's runs) and at 0.6 (RL#2's runs) are identical
  on adaptec1-4, bigblue1, bigblue2 and bigblue4 (largest coordinate difference 0 across seeds and across densities);
  on bigblue3, 2,538 of its 3,778 macros differ across seeds (run files `runs/remote/rlc_*`, `runs/remote/rtd_*`,
  local).
- Writing the tool's input for adaptec1 marked all 543 of its macros terminal and /FIXED (checked 3 Oct).
- In the three confirmatory tests on ISPD2005, 56 of 64 units tie exactly in RL#2 and RL#3 and 57 in RL#1; the other
  units are bigblue3's (reports/relink_confirmatory.md, reports/density_confirmatory.md,
  reports/portfolio_confirmatory.md).

## 3 Consequences

1. **J's reference on ISPD2005.** J = 0.45 on ISPD2005 is the benchmark's macro placement after P_M, not DREAMPlace's
   macro placement (bigblue3 excepted). J's normalization stays valid as a fixed reference layout; every statement
   that calls it the tool's on ISPD2005 is wrong: reports/T2_trackA_ispd_dreamplace.md (Notes),
   reports/E0_partner_ablation.md and reports/E0_partner_ablation_eq.md (Caveat), reports/PROGRESS.md (Section 8), the
   HANDOFF entries of 28 Sep. E0's comparisons among HeurBridge's partners (the G0' decision) do not involve the
   tool and are unaffected.
2. **RL#1-RL#3.** Their procedure assumed that the tool places every ISPD2005 macro. On 7 of 8 designs it placed none,
   so every arm is the same layout there. As recorded: RL#1 FAILED (p = 0.88); RL#2 and RL#3 passed their alpha, on
   bigblue3's 8 units alone. **None of the three is evidence for its registered claim.** The alpha-ledger keeps the
   results as recorded, with a note.
3. **The fix:** in the tool's input (fix_macros=False) a macro that the design keeps movable is written as a movable
   node; f1's input is unchanged (heurbridge/eval/dreamplace.py:50-56; tests/test_dreamplace_io.py).

## 4 Open

- A test of the tool's configuration on ISPD2005 needs new tool runs that place the macros. ISPD2005 is partly
  seen: on bigblue3, one run at 0.6 beat the best of four at 0.9 in all 8 units (the RL#2 and RL#3 data).
- With the fix, the tool's own macro placement may be worse than the benchmark's given one on ISPD2005 (J above
  0.45): the benchmark's macro positions come with the contest benchmarks.
- How it was missed: the loader test checks the in-memory flags (tests/test_beat_tool.py,
  test_raw_loader_applies_the_ispd_convention), not the file the tool reads; and on ISPD2005 the seeding campaign
  ran one tool seed per design, so identical layouts across seeds could not show.
