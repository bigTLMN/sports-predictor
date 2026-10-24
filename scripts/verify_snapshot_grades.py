"""Verify public-snapshot spread/total outcomes match closing-line grading rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "web-app" / "data" / "public-snapshot.json"


def _float_line(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def grade_spread(pick, m, hs, aw):
    spread_line = _float_line(m.get("vegas_spread"))
    if spread_line is None:
        spread_line = _float_line(pick.get("line_info"))
    if spread_line is None or pick.get("recommended_team_id") is None:
        return None
    home_id = m.get("home_team_id")
    if home_id is None:
        return None
    margin = hs - aw
    covered = margin + spread_line
    if pick["recommended_team_id"] == home_id:
        return "WIN" if covered > 0 else "LOSS" if covered < 0 else "PUSH"
    return "LOSS" if covered > 0 else "WIN" if covered < 0 else "PUSH"


def grade_total(pick, m, hs, aw):
    total_line = _float_line(pick.get("ou_line"))
    if total_line is None:
        total_line = _float_line(m.get("vegas_total"))
    if not pick.get("ou_pick") or total_line is None:
        return None
    points = hs + aw
    if points == total_line:
        return "PUSH"
    if pick["ou_pick"] == "OVER":
        return "WIN" if points > total_line else "LOSS"
    return "WIN" if points < total_line else "LOSS"


def main() -> int:
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    mismatches = []
    for pick in data.get("picks", []):
        m = pick.get("matches") or {}
        if m.get("status") not in ("STATUS_FINAL", "STATUS_FINISHED", "Final"):
            continue
        hs, aw = m.get("home_score"), m.get("away_score")
        if hs is None or aw is None:
            continue
        hs, aw = float(hs), float(aw)
        exp_s = grade_spread(pick, m, hs, aw)
        if exp_s is not None and pick.get("spread_outcome") != exp_s:
            mismatches.append(("spread", pick.get("match_id"), pick.get("spread_outcome"), exp_s))
        exp_t = grade_total(pick, m, hs, aw)
        if exp_t is not None and pick.get("total_outcome") != exp_t:
            mismatches.append(("total", pick.get("match_id"), pick.get("total_outcome"), exp_t))
    if mismatches:
        for row in mismatches:
            print("MISMATCH", row)
        return 1
    print(f"OK: {len(data.get('picks', []))} picks checked, no outcome mismatches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
