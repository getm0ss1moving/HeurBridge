#!/usr/bin/env bash
# The cell-stage chat's C1 queue on 224 (reports/cell_stage_c1.md), run inside a vault job, so that the next C1 step
# starts when slots free up without anyone launching it:
#   bash scripts/server/cs_c1_queue.sh <this job's run name> <entry> [<entry> ...]
# Entries run on 2 workers each, when this chat has a free pair of slots (its share is 4, decision CS-D2 (a)): its
# other jobs (vault runs named cs_*) count one pair each, and so does each entry this queue is running.  The first
# ready s2 entry starts first; an s1 entry starts only when no s2 entry is still waiting.
#   s2:<design>:<candidate>   stage 2 (f2, the six shifts, --race 2, R0's rows from the Track-B test's ledger after
#                             one identical verification run).  The design's stage-1 job cs_c1_<design> runs
#                             elsewhere: while it runs, its ledger is copied from that job's workspace (the job
#                             deletes the workspace when it ends); the entry starts once the job has ended and the
#                             copy holds every f1 row (2 layouts x the recipes of configs/cellstage/c1_<design>.json),
#                             and is skipped, by name, if not.
#   s1:<design>:<candidate>   stage 1 (f1, unshifted) here.
# The job must restore seedB_orfs*_<design> (and for s2 tb_<design>) and mount cellpos_c1_<design> at
# cellpos_c1/<design>.  Make variables come from each campaign's meta.json (scripts/run_cell_stage.py).
# Tests (tests/test_cs_c1_queue.py) set HB_STATE_DIR, HB_QUEUE_POLL and HB_QUEUE_RUN (a command run instead of the
# runner, with the entry's kind, design and candidate).
set -u
ME=$1; shift
S=${HB_STATE_DIR:-/data/dzy/heura_repr/hb/state}
F=/data/dzy/heura_repr/third_party/ORFS-2024-12/flow
Y=/data/dzy/heura_repr/tools/yosys_048/bin/yosys
export HB_OPENROAD=$PWD/scripts/server/openroad_676.sh
log() { echo "HB_QUEUE $(date '+%m-%d %H:%M:%S') $*"; }
alive() { [ -e "$S/$1.pid" ] && kill -0 "$(cat "$S/$1.pid" 2>/dev/null)" 2>/dev/null; }
others() {
  local k=0 p n
  for p in "$S"/cs_*.pid; do
    [ -e "$p" ] || continue
    n=$(basename "$p" .pid)
    [ "$n" = "$ME" ] && continue
    if alive "$n"; then k=$((k + 1)); fi
  done
  echo "$k"
}
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
  local common="--flow $F --design nangate45/$2 --recipes configs/cellstage/c1_$2.json --layouts $3,M1 --tag c1 --workers 2 --check-drift --yosys $Y"
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
  running=0; pending=0
  for ((i = 0; i < n; i++)); do
    case "${state[i]}" in
      running) if kill -0 "${pid[i]}" 2>/dev/null; then running=$((running + 1)); else
                 wait "${pid[i]}"; log "${entries[i]} ended (rc $?)"; state[i]=done; fi ;;
      "") pending=$((pending + 1)) ;;
    esac
  done
  if [ "$pending" -eq 0 ] && [ "$running" -eq 0 ]; then log "all entries done"; break; fi
  s2wait=0
  for ((i = 0; i < n; i++)); do
    IFS=: read -r kind d cand <<< "${entries[i]}"
    if [ "$kind" = s2 ] && [ -z "${state[i]}" ]; then s2wait=$((s2wait + 1)); fi
  done
  for ((i = 0; i < n; i++)); do
    [ -z "${state[i]}" ] || continue
    e=${entries[i]}
    IFS=: read -r kind d cand <<< "$e"
    if [ "$kind" = s2 ]; then
      alive "cs_c1_$d" && continue                      # stage 1 still running: keep copying
      if [ "$(f1rows "$d")" != "$(want "$d")" ]; then
        log "$e skipped: the stage-1 ledger copy has $(f1rows "$d") of $(want "$d") f1 rows (launch it by hand)"
        state[i]=skipped; s2wait=$((s2wait - 1)); continue
      fi
    elif [ "$s2wait" -gt 0 ]; then
      continue                                           # stage 2 first
    fi
    if [ $(( $(others) + running )) -lt 2 ]; then
      log "$e starts (other jobs of this chat: $(others), entries running: $running)"
      run "$kind" "$d" "$cand" > "logs/cs_c1_queue_${kind}_$d.log" 2>&1 &
      pid[i]=$!; state[i]=running; running=$((running + 1))
      [ "$kind" = s2 ] && s2wait=$((s2wait - 1))
    fi
  done
  sleep "${HB_QUEUE_POLL:-5}"
done
