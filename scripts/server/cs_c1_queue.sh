#!/usr/bin/env bash
# The cell-stage chat's C1 queue on 224 (reports/cell_stage_c1.md), run inside a vault job: each C1 step starts when it
# is ready, and every evaluation takes a slot from the gate shared with the macro chat (heurbridge/cellstage/slots.py:
# at most 8 OpenROAD runs on the server, the macro chat's registered jobs first), so C1 uses whatever slots are free:
#   bash scripts/server/cs_c1_queue.sh <entry> [<entry> ...]
#   s2:<design>:<candidate>   stage 2 (f2, the six shifts, --race 2, R0's rows from the Track-B test's ledger after
#                             one identical verification run).  If the design's stage-1 job cs_c1_<design> runs
#                             elsewhere, its ledger is copied from that job's workspace while it runs (the job deletes
#                             the workspace when it ends); a restored ledger serves as it is.  The entry starts once no
#                             stage-1 job runs and the ledger holds every f1 row (2 layouts x the recipes of
#                             configs/cellstage/c1_<design>.json); it is skipped, by name, if not.  Slot priority 0.
#   s1:<design>:<candidate>   stage 1 (f1, unshifted).  Slot priority 1: stage 2 goes first.
# The job must restore seedB_orfs*_<design> (and for s2 tb_<design>, and the stage-1 job's final when it has ended)
# and mount cellpos_c1_<design> at cellpos_c1/<design>.  Make variables come from each campaign's meta.json.
# Tests (tests/test_cs_c1_queue.py) set HB_STATE_DIR, HB_SLOT_DIR, HB_QUEUE_POLL and HB_QUEUE_RUN (a command run
# instead of the runner, with the entry's kind, design and candidate).
set -u
S=${HB_STATE_DIR:-/data/dzy/heura_repr/hb/state}
SLOTS=${HB_SLOT_DIR:-/data/dzy/heura_repr/hb/slots}
F=/data/dzy/heura_repr/third_party/ORFS-2024-12/flow
Y=/data/dzy/heura_repr/tools/yosys_048/bin/yosys
export HB_OPENROAD=$PWD/scripts/server/openroad_676.sh HB_STATE_DIR=$S
log() { echo "HB_QUEUE $(date '+%m-%d %H:%M:%S') $*"; }
alive() { [ -e "$S/$1.pid" ] && kill -0 "$(cat "$S/$1.pid" 2>/dev/null)" 2>/dev/null; }
grab() {   # the newest copy of a running stage-1 job's ledger
  local d=$1 w f t
  w=$(cat "$S/cs_c1_$d.wd" 2>/dev/null) || return 0
  f="$w/repo/runs/seed_orfs/$d/evals_cs_c1.jsonl"; t="runs/seed_orfs/$d/evals_cs_c1.jsonl"
  [ -s "$f" ] || return 0
  if [ ! -e "$t" ] || [ "$(wc -c < "$f")" -gt "$(wc -c < "$t")" ]; then
    cp "$f" "$t.tmp" && mv "$t.tmp" "$t"
  fi
}
f1rows() { grep -c '"fidelity": 1,' "runs/seed_orfs/$1/evals_cs_c1.jsonl" 2>/dev/null || true; }
want() { echo $((2 * $(grep -c '"id":' "configs/cellstage/c1_$1.json"))); }
run() {    # kind design candidate
  if [ -n "${HB_QUEUE_RUN:-}" ]; then $HB_QUEUE_RUN "$1" "$2" "$3"; return; fi
  local prio=1
  [ "$1" = s2 ] && prio=0
  local common="--flow $F --design nangate45/$2 --recipes configs/cellstage/c1_$2.json --layouts $3,M1 --tag c1 --workers 4 --check-drift --yosys $Y --slot-gate $SLOTS --slot-priority $prio"
  if [ "$1" = s2 ]; then
    bash scripts/server/trackb.sh python scripts/run_cell_stage.py $common --fidelity 2 --shifts tb --race 2 \
      --default-rows "runs/seed_orfs/$2/evals_tb.jsonl" --verify-default 1
  else
    bash scripts/server/trackb.sh python scripts/run_cell_stage.py $common --fidelity 1
  fi
}
entries=("$@")
n=${#entries[@]}
state=(); pid=()
for ((i = 0; i < n; i++)); do state[i]=""; pid[i]=""; done
log "start: ${entries[*]}"
while :; do
  for ((i = 0; i < n; i++)); do
    IFS=: read -r kind d cand <<< "${entries[i]}"
    if [ "$kind" = s2 ] && [ -z "${state[i]}" ] && alive "cs_c1_$d"; then grab "$d"; fi
  done
  open=0
  for ((i = 0; i < n; i++)); do
    e=${entries[i]}
    IFS=: read -r kind d cand <<< "$e"
    case "${state[i]}" in
      running)
        if kill -0 "${pid[i]}" 2>/dev/null; then open=$((open + 1)); else
          wait "${pid[i]}"; log "$e ended (rc $?)"; state[i]=done; fi ;;
      "")
        open=$((open + 1))
        if [ "$kind" = s2 ]; then
          alive "cs_c1_$d" && continue                    # stage 1 still running: keep copying
          if [ "$(f1rows "$d")" != "$(want "$d")" ]; then
            log "$e skipped: the stage-1 ledger has $(f1rows "$d") of $(want "$d") f1 rows (launch it by hand)"
            state[i]=skipped; open=$((open - 1)); continue
          fi
        fi
        log "$e starts"
        run "$kind" "$d" "$cand" > "logs/cs_c1_queue_${kind}_$d.log" 2>&1 &
        pid[i]=$!; state[i]=running ;;
    esac
  done
  if [ "$open" -eq 0 ]; then log "all entries done"; break; fi
  sleep "${HB_QUEUE_POLL:-5}"
done
