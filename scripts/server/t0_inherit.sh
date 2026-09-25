#!/usr/bin/env bash
# T0.1 on a server: the four HA-PR inheritance checks (HANDOFF_SESSION4_NEXT.md s.0).
# Expect SMOKE_TEST_PASS, v2=222 / control 46/46, VALIDATE_REPLAY_V2_PASS, 46 decisions / 176 samples / 0 errors.
set -u
EDA=${HB_EDA_DIR:-/data/dzy/heura_repr/eda}
cd "$EDA" || { echo "T0.1_FAIL no $EDA"; exit 1; }
export HEURA_EDA_BASE="$EDA"
echo "### smoke_test";              python3 harness/smoke_test.py 2>&1 | tail -3
echo "### session_status";          python3 harness/session_status.py 2>&1 | grep -E "replay labels|v2 gate_ok|control coverage"
echo "### validate_replay_v2";      python3 harness/validate_replay_v2.py 2>&1 | tail -1
echo "### build_checkpoint_dataset"; python3 harness/build_checkpoint_dataset.py --strict 2>&1 | python3 -c "
import json, sys
t = sys.stdin.read(); d = json.loads(t[t.find('{'):])
print('decisions=%s samples=%s errors=%s' % (d['n_decisions'], d['n_action_samples'], d['n_validation_errors']))"
