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
