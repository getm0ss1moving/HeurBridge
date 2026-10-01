#!/usr/bin/env bash
# T5 demo jobs on 225 inside the encrypted workspace (repo root = cwd); protocol: reports/t5_demo_preregistration.md.
#   bash scripts/server/t5_demo.sh smoke | preflight | hb | ctrl | eval_V | eval_T
# hbv inputs: --after seedA_dp_s1 seedA_dp_s2 (+ t5demo_hb t5demo_ctrl for eval_*) --data eda_harness:eda
#   bridge_v1_e0_frozen:checkpoints/algR_trackA_final; preflight and hb also need --api-key-file (the LLM client reads
#   the key from that file; the path is never written in the repo).  Commands: HANDOFF.md, "T5 demo runbook".
set -euo pipefail
MODE=${1:?usage: t5_demo.sh smoke|preflight|hb|ctrl|eval_V|eval_T}
ln -sfn /tmp/.hbdata/benchmarks benchmarks
export HB_EDA_DIR=$PWD/eda HB_DREAMPLACE=/tmp/.hbtools/dreamplace OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
P=/tmp/.hbenv/hb/bin/python
B=checkpoints/algR_trackA_final/best.pt
echo "f95bdde8485316349a1a47b8b1e8115018085f518419f46c903c65f773a525a5  $B" | sha256sum -c -
[ -d archive_A0_trackA ] || $P scripts/merge_archives.py --out archive_A0_trackA --inputs archive_A0_trackA_s1 archive_A0_trackA_s2
$P -c "from heurbridge.archive.store import Archive; s = Archive('archive_A0_trackA', min_fidelity=1).snapshot('check'); assert s.endswith('2ebe74fadcf0'), s"
COMMON="--suite ibm --runs runs/seed_trackA_dp --archive archive_A0_trackA --bridge $B --guard dp --fitness refinability --proposer heurbridge"
DEMO="$COMMON --evo ibm01,ibm03 --seeds 2 --generations 4 --parents 4 --children 2 --islands 4 --split t5demo --budget 100"
case "$MODE" in
  smoke)      # no LLM: the whole loop and the endpoint on the smallest setting
    $P -m pytest -q -x tests/test_engine.py tests/test_t5_endpoint.py tests/test_sandbox.py
    $P scripts/run_evolution.py $COMMON --evo ibm01 --seeds 1 --programs M6.v0,M2.v0 --generations 1 --parents 1 \
        --children 1 --islands 1 --llm mock --split smoke --out runs/evo/t5_smoke_mock
    $P scripts/eval_t5_portfolio.py --arms runs/evo/t5_smoke_mock --designs ibm04 --seeds 1 --q 2 --runs runs/seed_trackA_dp \
        --bridge $B --out runs/evo/t5_smoke_eval ;;
  preflight)  # the real LLM once: key, parsing, ledger (at most 2 calls)
    $P scripts/run_evolution.py $COMMON --evo ibm01 --seeds 1 --programs M6.v0,M2.v0 --generations 1 --parents 1 \
        --children 1 --islands 1 --llm deepseek --budget 4 --split t5preflight --out runs/evo/t5_preflight ;;
  hb)   $P scripts/run_evolution.py $DEMO --llm deepseek --out runs/evo/t5demo_hb ;;
  ctrl) $P scripts/run_evolution.py $DEMO --llm perturb --out runs/evo/t5demo_ctrl ;;
  eval_V|eval_T)
    D=$([ "$MODE" = eval_V ] && echo ibm04,ibm06 || echo ibm08,ibm12)
    $P scripts/eval_t5_portfolio.py --arms runs/evo/t5demo_hb,runs/evo/t5demo_ctrl --control t5demo_ctrl --designs $D \
        --seeds 3 --runs runs/seed_trackA_dp --bridge $B --out runs/evo/t5demo_${MODE#eval_} ;;
  *) echo "unknown mode $MODE" >&2; exit 2 ;;
esac
