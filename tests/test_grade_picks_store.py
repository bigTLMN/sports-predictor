import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import grade_picks
import sqlite_store


class GradeTests(unittest.TestCase):
    def test_home_cover_and_under_total(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        home = sqlite_store.upsert_team(conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = sqlite_store.upsert_team(conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        match_id = sqlite_store.upsert_match(conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_FINISHED",
            "home_score": 110, "away_score": 100, "period_scores": None,
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        sqlite_store.upsert_pick(conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 230.0, "created_at": "2026-10-17T00:00:00",
        })
        updated = grade_picks.settle(conn)
        row = conn.execute("SELECT spread_outcome, total_outcome FROM aggregated_picks").fetchone()
        self.assertEqual(updated, 1)
        self.assertEqual(row["spread_outcome"], "WIN")
        self.assertEqual(row["total_outcome"], "LOSS")

    def test_total_uses_saved_line_after_market_total_is_cleared(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        home = sqlite_store.upsert_team(conn, "DET", "Pistons", "Detroit Pistons", None, 3)
        away = sqlite_store.upsert_team(conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        match_id = sqlite_store.upsert_match(conn, {
            "date": "2026-10-20", "start_time": "2026-10-20T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_FINISHED",
            "home_score": 121, "away_score": 113, "period_scores": None,
            "vegas_spread": 1.5, "vegas_total": None,
        })
        sqlite_store.upsert_pick(conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "1.5",
            "ou_pick": "UNDER", "ou_line": 222.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 210.0, "created_at": "2026-10-20T00:00:00",
        })
        grade_picks.settle(conn)
        row = conn.execute(
            "SELECT total_outcome FROM aggregated_picks WHERE match_id=?",
            (match_id,),
        ).fetchone()
        self.assertEqual(row["total_outcome"], "LOSS")


if __name__ == "__main__":
    unittest.main()
