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

push_main() {
  local gitcmd="$1"
  "$gitcmd" pull --ff-only origin main
  if "$gitcmd" diff --staged --quiet; then
    echo "No changes to commit."
    return 0
  fi
  "$gitcmd" commit -m "$2"
  if ! "$gitcmd" push origin main; then
    "$gitcmd" pull --rebase origin main
    "$gitcmd" push origin main
  fi
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

  mount_dir="${PI_UPDATE_MOUNT:-/mnt/sports-db}"
  mount_check="${PI_UPDATE_MOUNT_CHECK:-mountpoint}"
  if [ "$mount_check" != "skip" ]; then
    if ! mountpoint -q "$mount_dir" || [ ! -w "$mount_dir" ]; then
      echo "sqlite mount missing"
      exit 1
    fi
  fi

  echo "抓賽程"
  "$py" scrape_teams.py
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
  "$py" export_snapshot.py

  rm -f data/PlayerStatistics.csv
  "$gitcmd" add -f data/TeamStatistics.csv || true
  "$gitcmd" add .
  push_main "$gitcmd" "🤖 Auto-update: Schedule, Odds, Picks & CSV Data"
}

score_main() {
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

  mount_dir="${PI_UPDATE_MOUNT:-/mnt/sports-db}"
  mount_check="${PI_UPDATE_MOUNT_CHECK:-mountpoint}"
  if [ "$mount_check" != "skip" ]; then
    if ! mountpoint -q "$mount_dir" || [ ! -w "$mount_dir" ]; then
      echo "sqlite mount missing"
      exit 1
    fi
  fi

  echo "抓比分"
  "$py" scrape_schedule.py --scores-only
  echo "結算"
  "$py" grade_picks.py
  "$py" export_snapshot.py

  "$gitcmd" add -- web-app/data/public-snapshot.json
  push_main "$gitcmd" "🤖 Auto-update: Scores"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
