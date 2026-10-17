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
