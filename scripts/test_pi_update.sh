#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/pi_update.sh"

expect_retrain() {
  local hour="$1" minute="$2" want="$3" rc
  set +e
  PI_UPDATE_HOUR="$hour" PI_UPDATE_MINUTE="$minute" should_retrain
  rc=$?
  set -e
  if [ "$want" = "yes" ] && [ "$rc" -ne 0 ]; then
    echo "FAIL retrain ${hour}:${minute} expected yes got ${rc}"
    exit 1
  fi
  if [ "$want" = "no" ] && [ "$rc" -eq 0 ]; then
    echo "FAIL retrain ${hour}:${minute} expected no got ${rc}"
    exit 1
  fi
  echo "PASS retrain ${hour}:${minute} ${want}"
}

expect_retrain 22 00 yes
expect_retrain 22 08 yes
expect_retrain 22 29 yes
expect_retrain 22 30 no
expect_retrain 21 00 no
expect_retrain 23 15 no

make_sandbox() {
  SANDBOX=$(mktemp -d)
  mkdir -p "$SANDBOX/bin" "$SANDBOX/root/data"
  export CALL_LOG="$SANDBOX/calls.txt"
  export GIT_LOG="$SANDBOX/git.txt"
  export FAIL_ON=""
  export SLOW=""
  export DIFF_DIRTY=""
  : > "$CALL_LOG"
  : > "$GIT_LOG"
  cat > "$SANDBOX/bin/python" << 'EOF'
#!/usr/bin/env bash
echo "$*" >> "$CALL_LOG"
if [ -n "${FAIL_ON:-}" ] && [ "$1" = "$FAIL_ON" ]; then
  exit 1
fi
if [ "${SLOW:-}" = "1" ]; then
  sleep 2
fi
exit 0
EOF
  cat > "$SANDBOX/bin/git" << 'EOF'
#!/usr/bin/env bash
if [ "$1" = "diff" ]; then
  if [ "${DIFF_DIRTY:-}" = "1" ]; then
    exit 1
  fi
  exit 0
fi
echo "$*" >> "$GIT_LOG"
exit 0
EOF
  chmod +x "$SANDBOX/bin/python" "$SANDBOX/bin/git"
  echo x > "$SANDBOX/root/data/PlayerStatistics.csv"
  export PI_UPDATE_ROOT="$SANDBOX/root"
  export PI_UPDATE_PYTHON="$SANDBOX/bin/python"
  export PI_UPDATE_GIT="$SANDBOX/bin/git"
  export PI_UPDATE_LOCK="$SANDBOX/lock"
  export PI_UPDATE_HOUR=10
  export PI_UPDATE_MINUTE=00
  export PI_UPDATE_MOUNT_CHECK=skip
}

make_sandbox
set +e
( main > "$SANDBOX/out.txt" )
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "FAIL light run exit ${rc}"
  exit 1
fi
grep -qx "抓賽程" "$SANDBOX/out.txt"
grep -qx "結算" "$SANDBOX/out.txt"
grep -qx "跳過重訓" "$SANDBOX/out.txt"
grep -qx "預測" "$SANDBOX/out.txt"
grep -qx "scrape_teams.py" "$CALL_LOG"
grep -qx "scrape_schedule.py" "$CALL_LOG"
grep -qx "grade_picks.py" "$CALL_LOG"
grep -qx "aggregate_picks.py" "$CALL_LOG"
grep -qx "export_snapshot.py" "$CALL_LOG"
if grep -q "fetch_kaggle_data.py" "$CALL_LOG"; then
  echo "FAIL light run retrained"
  exit 1
fi
if [ -f "$SANDBOX/root/data/PlayerStatistics.csv" ]; then
  echo "FAIL PlayerStatistics.csv still present"
  exit 1
fi
if grep -q "commit" "$GIT_LOG"; then
  echo "FAIL light run committed a clean tree"
  exit 1
fi
echo "PASS light run"

make_sandbox
export PI_UPDATE_HOUR=22
export PI_UPDATE_MINUTE=10
( main > "$SANDBOX/out.txt" )
grep -qx "開始重訓" "$SANDBOX/out.txt"
python_order=$(paste -sd, "$CALL_LOG")
if [ "$python_order" != "scrape_teams.py,scrape_schedule.py,grade_picks.py,fetch_kaggle_data.py,build_player_features.py,train_model.py,utils/export_impact_data.py,aggregate_picks.py,export_snapshot.py" ]; then
  echo "FAIL retrain order: $python_order"
  exit 1
fi
echo "PASS retrain order"

make_sandbox
export FAIL_ON="grade_picks.py"
set +e
( main > "$SANDBOX/out.txt" )
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
  echo "FAIL expected non-zero after grade_picks.py"
  exit 1
fi
if grep -q "already running" "$SANDBOX/out.txt"; then
  echo "FAIL python error reported as already running"
  exit 1
fi
if grep -q "aggregate_picks.py" "$CALL_LOG"; then
  echo "FAIL continued after python error"
  exit 1
fi
if grep -q "commit" "$GIT_LOG"; then
  echo "FAIL committed after python error"
  exit 1
fi
echo "PASS python failure stops before git"

make_sandbox
export DIFF_DIRTY=1
( main > "$SANDBOX/out.txt" )
grep -F "commit -m 🤖 Auto-update: Schedule, Odds, Picks & CSV Data" "$GIT_LOG"
grep -qx "push origin main" "$GIT_LOG"
if grep -q -- "--force" "$GIT_LOG"; then
  echo "FAIL force push"
  exit 1
fi
echo "PASS dirty tree pushes main"

make_sandbox
export SLOW=1
main > "$SANDBOX/slow-out.txt" &
slow_pid=$!
sleep 1
second=$(main)
kill "$slow_pid" 2>/dev/null || true
wait "$slow_pid" 2>/dev/null || true
if ! printf "%s\n" "$second" | grep -q "already running"; then
  echo "FAIL lock did not report already running"
  printf "%s\n" "$second"
  exit 1
fi
echo "PASS lock"

SANDBOX=$(mktemp -d)
export PI_UPDATE_ROOT="$SANDBOX"
export PI_UPDATE_PYTHON="$SANDBOX/bin/python"
export PI_UPDATE_LOCK="$SANDBOX/lock"
export PI_UPDATE_MOUNT_CHECK=mountpoint
export PI_UPDATE_MOUNT="$SANDBOX/not-a-mount"
mkdir -p "$PI_UPDATE_MOUNT"
set +e
( main > "$SANDBOX/mount-out.txt" )
rc=$?
set -e
if [ "$rc" -eq 0 ] || ! grep -qx "sqlite mount missing" "$SANDBOX/mount-out.txt"; then
  echo "FAIL mount check"
  exit 1
fi
echo "PASS mount check"

make_sandbox
export DIFF_DIRTY=1
( score_main > "$SANDBOX/out.txt" )
grep -qx "抓比分" "$SANDBOX/out.txt"
grep -qx "scrape_schedule.py --scores-only" "$CALL_LOG"
grep -qx "grade_picks.py" "$CALL_LOG"
grep -qx "export_snapshot.py" "$CALL_LOG"
if grep -q "aggregate_picks.py" "$CALL_LOG" || grep -q "train_model.py" "$CALL_LOG"; then
  echo "FAIL score run changed predictions or retrained"
  exit 1
fi
grep -F "add -- web-app/data/public-snapshot.json" "$GIT_LOG"
grep -F "commit -m 🤖 Auto-update: Scores" "$GIT_LOG"
if grep -q "add \." "$GIT_LOG"; then
  echo "FAIL score run staged the whole tree"
  exit 1
fi
echo "PASS score run pushes snapshot only"

make_sandbox
( score_main > "$SANDBOX/out.txt" )
grep -qx "No changes to commit." "$SANDBOX/out.txt"
if grep -q "commit" "$GIT_LOG"; then
  echo "FAIL clean score run committed"
  exit 1
fi
echo "PASS clean score run does not commit"
echo "ALL PASS"
