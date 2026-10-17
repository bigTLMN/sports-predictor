# Pi Crontab Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the existing NBA schedule, grading, prediction, and 22:00 retrain pipeline from GitHub Actions onto a Pi crontab entry that runs every 30 minutes.

**Architecture:** `scripts/pi_update.sh` is the only scheduler entrypoint. It locks with `flock`, runs the existing Python scripts in the Actions order, retrains only at Taipei 22:00–22:29, then commits and pushes when git has staged changes. GitHub Actions keeps `workflow_dispatch` and loses its `schedule` and `push` triggers. A project-local virtualenv on the Pi runs the script.

**Tech Stack:** bash, flock, crontab, Python 3.14 (fallback 3.11), existing scripts (`scrape_schedule.py`, `grade_picks.py`, `fetch_kaggle_data.py`, `build_player_features.py`, `train_model.py`, `utils/export_impact_data.py`, `aggregate_picks.py`), GitHub Actions YAML.

## Global Constraints

- Do not change the model, features, `PREDICT_DAYS`, or add ATS backtesting.
- Taipei time is decided inside the script with `TZ=Asia/Taipei`, not the Pi system timezone.
- Retrain only when the Taipei hour is `22` and the minute is less than 30. Log `跳過重訓` at every other time, including 22:30.
- Python non-zero exit stops the script before any git commit.
- A held lock prints `already running` and exits 0. A Python failure must not be reported as `already running`.
- Commit message, when there is a staged diff, is exactly `🤖 Auto-update: Schedule, Odds, Picks & CSV Data`.
- Push with `git push origin main` only. Never force push.
- Do not commit `.env`, `.venv/`, `logs/`, or `data/*.csv` except force-added `data/TeamStatistics.csv`.
- Delete `data/PlayerStatistics.csv` after the Python steps and before `git add`.
- Do not restart other bots' systemd services.
- Do not use `/home/tedliu/.venv`.
- Tests need `bash` and `flock`. Run them on the Pi, not in Windows Git Bash.

## File structure

- Create `scripts/pi_update.sh`: lock, Taipei retrain decision, Python steps, git push. Sourced by tests; `main` runs only when executed.
- Create `scripts/test_pi_update.sh`: bash assertions for the retrain window, step order, failure, lock, and git push.
- Modify `.gitignore`: ignore `logs/`.
- Modify `.github/workflows/daily_update.yml`: trigger block only. Leave `jobs:` unchanged.
- Pi-only, not committed: `.venv/`, `.env`, crontab line, `origin` SSH URL.

---

### Task 1: Taipei retrain window

**Files:**
- Create: `scripts/pi_update.sh`
- Test: `scripts/test_pi_update.sh`

**Interfaces:**
- Consumes: nothing
- Produces: `should_retrain` — bash function, no arguments. Returns 0 when `PI_UPDATE_HOUR` (default `TZ=Asia/Taipei date +%H`) is `22` and `PI_UPDATE_MINUTE` (default `TZ=Asia/Taipei date +%M`) is numerically `< 30`. Returns 1 otherwise. Minute `08` must not be parsed as octal.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_pi_update.sh`:

```bash
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
echo "ALL PASS"
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
ssh tedliu@192.168.0.101 "mkdir -p /tmp/sports-predictor-tests"
scp "D:\sports-predictor\scripts\test_pi_update.sh" tedliu@192.168.0.101:/tmp/sports-predictor-tests/test_pi_update.sh
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /tmp/sports-predictor-tests/*.sh && bash /tmp/sports-predictor-tests/test_pi_update.sh"
```

Expected: FAIL because `scripts/pi_update.sh` does not exist yet (`No such file or directory`).

- [ ] **Step 3: Write the minimal implementation**

Create `scripts/pi_update.sh`:

```bash
#!/usr/bin/env bash

should_retrain() {
  local hour minute
  hour="${PI_UPDATE_HOUR:-$(TZ=Asia/Taipei date +%H)}"
  minute="${PI_UPDATE_MINUTE:-$(TZ=Asia/Taipei date +%M)}"
  if [ "$hour" = "22" ] && [ "$((10#$minute))" -lt 30 ]; then
    return 0
  fi
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
```

- [ ] **Step 4: Run the test to verify it passes**

```powershell
scp "D:\sports-predictor\scripts\pi_update.sh" "D:\sports-predictor\scripts\test_pi_update.sh" tedliu@192.168.0.101:/tmp/sports-predictor-tests/
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /tmp/sports-predictor-tests/*.sh && bash /tmp/sports-predictor-tests/test_pi_update.sh"
```

Expected: six `PASS retrain` lines and a final `ALL PASS`. Exit code 0.

- [ ] **Step 5: Commit**

```powershell
git -C "D:\sports-predictor" add -- scripts/pi_update.sh scripts/test_pi_update.sh
git -C "D:\sports-predictor" commit -m "test: decide the Taipei 22:00 retrain window"
```

Do not push yet.

---

### Task 2: Pipeline body, lock, and git push

**Files:**
- Modify: `scripts/pi_update.sh`
- Modify: `scripts/test_pi_update.sh`

**Interfaces:**
- Consumes: `should_retrain` from Task 1
- Produces: `main` — bash function, no arguments. Uses these environment overrides, each with the default in parentheses:
  - `PI_UPDATE_ROOT` (`/home/tedliu/sports-predictor`)
  - `PI_UPDATE_PYTHON` (`$PI_UPDATE_ROOT/.venv/bin/python`)
  - `PI_UPDATE_LOCK` (`/tmp/sports-predictor.lock`)
  - `PI_UPDATE_GIT` (`git`)
  - `cd` to `PI_UPDATE_ROOT`, acquire `PI_UPDATE_LOCK` with `flock -n` on fd 9
  - stdout labels, in order when not retraining: `抓賽程`, `結算`, `跳過重訓`, `預測`
  - when retraining, `開始重訓` replaces `跳過重訓`, then these commands before `預測`: `fetch_kaggle_data.py`, `build_player_features.py`, `train_model.py`, `utils/export_impact_data.py`
  - after Python steps: delete `data/PlayerStatistics.csv`, then `"$PI_UPDATE_GIT" add -f data/TeamStatistics.csv` (failure ignored), `"$PI_UPDATE_GIT" add .`, and if `diff --staged --quiet` is non-zero, commit the message `🤖 Auto-update: Schedule, Odds, Picks & CSV Data` and `push origin main`

- [ ] **Step 1: Extend the failing test**

Replace `scripts/test_pi_update.sh` with:

```bash
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
echo "$1" >> "$CALL_LOG"
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
grep -qx "scrape_schedule.py" "$CALL_LOG"
grep -qx "grade_picks.py" "$CALL_LOG"
grep -qx "aggregate_picks.py" "$CALL_LOG"
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
if [ "$python_order" != "scrape_schedule.py,grade_picks.py,fetch_kaggle_data.py,build_player_features.py,train_model.py,utils/export_impact_data.py,aggregate_picks.py" ]; then
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
echo "ALL PASS"
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
scp "D:\sports-predictor\scripts\pi_update.sh" "D:\sports-predictor\scripts\test_pi_update.sh" tedliu@192.168.0.101:/tmp/sports-predictor-tests/
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /tmp/sports-predictor-tests/*.sh && bash /tmp/sports-predictor-tests/test_pi_update.sh"
```

Expected: FAIL with `main: command not found` or a missing `抓賽程` line. The six retrain cases still pass.

- [ ] **Step 3: Write the pipeline**

Replace `scripts/pi_update.sh` with:

```bash
#!/usr/bin/env bash

should_retrain() {
  local hour minute
  hour="${PI_UPDATE_HOUR:-$(TZ=Asia/Taipei date +%H)}"
  minute="${PI_UPDATE_MINUTE:-$(TZ=Asia/Taipei date +%M)}"
  if [ "$hour" = "22" ] && [ "$((10#$minute))" -lt 30 ]; then
    return 0
  fi
  return 1
}

main() {
  set -euo pipefail
  local root py lock gitcmd
  root="${PI_UPDATE_ROOT:-/home/tedliu/sports-predictor}"
  py="${PI_UPDATE_PYTHON:-$root/.venv/bin/python}"
  lock="${PI_UPDATE_LOCK:-/tmp/sports-predictor.lock}"
  gitcmd="${PI_UPDATE_GIT:-git}"

  cd "$root"
  exec 9>"$lock"
  if ! flock -n 9; then
    echo "$(TZ=Asia/Taipei date '+%F %T') already running"
    exit 0
  fi

  echo "抓賽程"
  "$py" scrape_schedule.py
  echo "結算"
  "$py" grade_picks.py
  if should_retrain; then
    echo "開始重訓"
    "$py" fetch_kaggle_data.py
    "$py" build_player_features.py
    "$py" train_model.py
    "$py" utils/export_impact_data.py
  else
    echo "跳過重訓"
  fi
  echo "預測"
  "$py" aggregate_picks.py

  rm -f data/PlayerStatistics.csv
  "$gitcmd" add -f data/TeamStatistics.csv || true
  "$gitcmd" add .
  if "$gitcmd" diff --staged --quiet; then
    echo "No changes to commit."
  else
    "$gitcmd" commit -m "🤖 Auto-update: Schedule, Odds, Picks & CSV Data"
    "$gitcmd" push origin main
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
```

- [ ] **Step 4: Run the test to verify it passes**

```powershell
scp "D:\sports-predictor\scripts\pi_update.sh" "D:\sports-predictor\scripts\test_pi_update.sh" tedliu@192.168.0.101:/tmp/sports-predictor-tests/
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /tmp/sports-predictor-tests/*.sh && bash /tmp/sports-predictor-tests/test_pi_update.sh"
```

Expected: `PASS` lines for retrain cases, `PASS light run`, `PASS retrain order`, `PASS python failure stops before git`, `PASS dirty tree pushes main`, `PASS lock`, then `ALL PASS`. Exit code 0.

- [ ] **Step 5: Commit**

```powershell
git -C "D:\sports-predictor" add -- scripts/pi_update.sh scripts/test_pi_update.sh
git -C "D:\sports-predictor" update-index --chmod=+x scripts/pi_update.sh scripts/test_pi_update.sh
git -C "D:\sports-predictor" commit -m "feat: run the NBA update pipeline from one Pi script"
```

Do not push yet.

---

### Task 3: Ignore logs and stop Actions from auto-running

**Files:**
- Modify: `.gitignore`
- Modify: `.github/workflows/daily_update.yml` (the `on:` block only; `jobs:` stays as it is, including `git push` inside the commit step)
- Test: inline Python in the step below. No new test file.

**Interfaces:**
- Consumes: nothing from the shell script
- Produces: `.gitignore` contains a `logs/` line. The workflow trigger block is only `workflow_dispatch`.

- [ ] **Step 1: Write the failing check**

```powershell
python -c "from pathlib import Path; root=Path(r'D:\sports-predictor'); gi=root.joinpath('.gitignore').read_text(encoding='utf-8'); text=root.joinpath('.github/workflows/daily_update.yml').read_text(encoding='utf-8'); on,_,_=text.partition('permissions:'); assert 'logs/' in gi.splitlines(); assert 'workflow_dispatch:' in on; assert 'schedule:' not in on; assert 'cron:' not in on; assert '\n  push:' not in on; print('PASS actions disabled')"
```

Expected: FAIL. `logs/` is absent, and `schedule:` is still in the `on:` block.

- [ ] **Step 2: Update `.gitignore`**

Append this line to `.gitignore`:

```
logs/
```

The file already lists `.env`, `__pycache__/`, `.venv/`, and `data/*.csv`. Leave those lines in place.

- [ ] **Step 3: Replace the workflow trigger**

Replace the top of `.github/workflows/daily_update.yml` through the blank line before `permissions:` with:

```yaml
name: NBA Schedule & Odds Monitor

on:
  workflow_dispatch:
    inputs:
      force_predict:
        description: 'Force Run Prediction?'
        required: false
        default: 'true'

permissions:
```

Do not edit anything from `permissions:` downward. Manual dispatch still trains because the existing step treats `workflow_dispatch` as the heavy path. That behavior stays.

- [ ] **Step 4: Run the check to verify it passes**

```powershell
python -c "from pathlib import Path; root=Path(r'D:\sports-predictor'); gi=root.joinpath('.gitignore').read_text(encoding='utf-8'); text=root.joinpath('.github/workflows/daily_update.yml').read_text(encoding='utf-8'); on,_,_=text.partition('permissions:'); assert 'logs/' in gi.splitlines(); assert 'workflow_dispatch:' in on; assert 'schedule:' not in on; assert 'cron:' not in on; assert '\n  push:' not in on; assert 'git push' in text; print('PASS actions disabled')"
```

Expected: `PASS actions disabled`.

- [ ] **Step 5: Commit and push code tasks**

```powershell
git -C "D:\sports-predictor" add -- .gitignore .github/workflows/daily_update.yml
git -C "D:\sports-predictor" commit -m "chore: disable Actions schedule and ignore Pi logs"
git -C "D:\sports-predictor" push origin main
ssh tedliu@192.168.0.101 "git -C /home/tedliu/sports-predictor pull --ff-only origin main && git -C /home/tedliu/sports-predictor log -1 --format='%h %s'"
```

Expected: push updates `main`, and the Pi fast-forwards to that commit. Do not stage `doc/系統架構說明.md` or `web-app/app/components/TrendChart.tsx` if they only differ by line endings.

---

### Task 4: Install the venv, secret, SSH remote, and crontab

**Files:**
- No further repo files
- Pi: `/home/tedliu/sports-predictor/.venv`, `/home/tedliu/sports-predictor/.env`, `/home/tedliu/sports-predictor/logs/`, user crontab

**Interfaces:**
- Consumes: `scripts/pi_update.sh` from Task 2, now on the Pi via the Task 3 pull
- Produces: a crontab line exactly `*/30 * * * * /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1`

- [ ] **Step 1: Point origin at SSH and confirm the author**

```powershell
ssh tedliu@192.168.0.101 "git -C /home/tedliu/sports-predictor remote set-url origin git@github.com:bigTLMN/sports-predictor.git && git -C /home/tedliu/sports-predictor remote get-url origin && git -C /home/tedliu/sports-predictor config --get user.name && git -C /home/tedliu/sports-predictor config --get user.email && test -f /home/tedliu/sports-predictor/kaggle.json && echo PASS kaggle.json"
```

Expected:

```text
git@github.com:bigTLMN/sports-predictor.git
bigTLMN
tedliu851005@gmail.com
PASS kaggle.json
```

Do not change the user name or email if they already match.

- [ ] **Step 2: Create the virtualenv**

```powershell
ssh tedliu@192.168.0.101 "cd /home/tedliu/sports-predictor && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt && .venv/bin/python -c 'import xgboost, sklearn, pandas, supabase, dotenv; print(\"PASS imports\")'"
```

Expected: `PASS imports`.

If pip cannot install `xgboost` or `scikit-learn`, remove that `.venv` and use Python 3.11:

```powershell
ssh tedliu@192.168.0.101 "curl -LsSf https://astral.sh/uv/install.sh | sh && . ~/.local/bin/env && cd /home/tedliu/sports-predictor && rm -rf .venv && uv python install 3.11 && uv venv --python 3.11 .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -c 'import xgboost, sklearn, pandas, supabase, dotenv; print(\"PASS imports\")'"
```

Do not delete anything outside `/home/tedliu/sports-predictor/.venv`.

- [ ] **Step 3: Copy `.env` without printing it**

```powershell
scp "D:\sports-predictor\.env" tedliu@192.168.0.101:/home/tedliu/sports-predictor/.env
ssh tedliu@192.168.0.101 "chmod 600 /home/tedliu/sports-predictor/.env && test -s /home/tedliu/sports-predictor/.env && grep -q '^SUPABASE_URL=' /home/tedliu/sports-predictor/.env && grep -q '^SUPABASE_KEY=' /home/tedliu/sports-predictor/.env && echo PASS env"
```

Expected: `PASS env`. Do not echo the file.

- [ ] **Step 4: Install the crontab line once**

```powershell
ssh tedliu@192.168.0.101 "mkdir -p /home/tedliu/sports-predictor/logs; line='*/30 * * * * /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1'; crontab -l 2>/dev/null | grep -F 'scripts/pi_update.sh' >/dev/null || (crontab -l 2>/dev/null; echo \"`$line\") | crontab -; echo '---CRON---'; crontab -l"
```

Expected: the previous three entries are still present, and the new line appears once:

```text
0 4 * * * /home/tedliu/scripts/ssd-cleanup.sh
0 3 1 * * cd /home/tedliu/hsr_bot && /home/tedliu/.venv/bin/python scripts/fetch_student_schedule.py >> logs/schedule_fetch.log 2>&1 # hsr-student-schedule-fetch
30 4 * * 0 cd /home/tedliu/hsr_bot && /home/tedliu/.venv/bin/python scripts/fetch_student_schedule.py >> logs/schedule_fetch.log 2>&1 # hsr-student-schedule-fetch-weekly
*/30 * * * * /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1
```

- [ ] **Step 5: Manual run outside the retrain window**

If `TZ=Asia/Taipei date +%H:%M` is inside `22:00`–`22:29`, wait until `22:30` before this step. The first proof run must show `跳過重訓`.

```powershell
ssh tedliu@192.168.0.101 "TZ=Asia/Taipei date +%H:%M; /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1; echo EXIT:`$?; tail -n 40 /home/tedliu/sports-predictor/logs/pi_update.log"
```

Expected: `EXIT:0`. The log contains `抓賽程`, `結算`, `跳過重訓`, and `預測`. It does not contain `開始重訓`. A `git push origin main` from the script is acceptable only when it found a staged diff; that push must not be a force push. `git -C /home/tedliu/sports-predictor status --porcelain` must not list `logs/` or `.env`.

- [ ] **Step 6: Confirm the deployed script matches the tests**

```powershell
ssh tedliu@192.168.0.101 "sed -i 's/\r$//' /home/tedliu/sports-predictor/scripts/pi_update.sh /home/tedliu/sports-predictor/scripts/test_pi_update.sh && bash /home/tedliu/sports-predictor/scripts/test_pi_update.sh"
```

Expected: `ALL PASS`.
