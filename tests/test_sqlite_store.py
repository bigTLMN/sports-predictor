import json
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import sqlite_store as store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(os.environ["NBA_SQLITE_PATH"])

    def test_upsert_team_by_code(self):
        first = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "http://logo", 1610612747)
        second = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "http://logo2", 1610612747)
        self.assertEqual(first, second)
        row = self.conn.execute("SELECT logo_url, nba_team_id FROM teams WHERE code='LAL'").fetchone()
        self.assertEqual(row["logo_url"], "http://logo2")
        self.assertEqual(row["nba_team_id"], 1610612747)

    def test_upsert_match_keeps_one_row_and_json_periods(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1610612747)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", None, 1610612738)
        row = {
            "date": "2026-10-18",
            "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home,
            "away_team_id": away,
            "status": "STATUS_SCHEDULED",
            "home_score": 0,
            "away_score": 0,
            "period_scores": {"home": [1], "away": [2]},
            "vegas_spread": -3.5,
            "vegas_total": 220.5,
        }
        match_id = store.upsert_match(self.conn, row)
        row["home_score"] = 110
        row["status"] = "STATUS_FINISHED"
        again = store.upsert_match(self.conn, row)
        self.assertEqual(match_id, again)
        saved = self.conn.execute("SELECT home_score, period_scores FROM matches WHERE id=?", (match_id,)).fetchone()
        self.assertEqual(saved["home_score"], 110)
        self.assertEqual(json.loads(saved["period_scores"])["home"], [1])

    def test_upsert_pick_does_not_wipe_grades(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        match_id = store.upsert_match(self.conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_FINISHED",
            "home_score": 110, "away_score": 100, "period_scores": None,
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        pick_id = store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 225.0, "created_at": "2026-10-17T00:00:00",
        })
        store.grade_pick(self.conn, pick_id, "WIN", "LOSS")
        store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 61,
            "spread_logic": "en2", "spread_logic_zh": "zh2", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "b", "analysis_content_zh": "乙",
            "predicted_margin": 5.0, "predicted_total": 226.0, "created_at": "2026-10-17T01:00:00",
        })
        graded = self.conn.execute(
            "SELECT spread_outcome, total_outcome, confidence_score FROM aggregated_picks WHERE id=?",
            (pick_id,),
        ).fetchone()
        self.assertEqual(graded["spread_outcome"], "WIN")
        self.assertEqual(graded["total_outcome"], "LOSS")
        self.assertEqual(graded["confidence_score"], 61)

    def test_export_snapshot_nests_teams(self):
        home = store.upsert_team(self.conn, "LAL", "Lakers", "Los Angeles Lakers", "h", 1)
        away = store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", "a", 2)
        match_id = store.upsert_match(self.conn, {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_team_id": home, "away_team_id": away, "status": "STATUS_SCHEDULED",
            "home_score": 0, "away_score": 0, "period_scores": {"home": [], "away": []},
            "vegas_spread": -3.5, "vegas_total": 220.5,
        })
        store.upsert_pick(self.conn, {
            "match_id": match_id, "recommended_team_id": home, "confidence_score": 60,
            "spread_logic": "en", "spread_logic_zh": "zh", "line_info": "-3.5",
            "ou_pick": "OVER", "ou_line": 220.5, "ou_confidence": 55,
            "analysis_content": "a", "analysis_content_zh": "甲",
            "predicted_margin": 4.0, "predicted_total": 225.0, "created_at": "2026-10-17T00:00:00",
        })
        snap = store.export_snapshot(self.conn)
        self.assertEqual(set(snap), {"teams", "matches", "picks"})
        self.assertEqual(snap["matches"][0]["home_team"]["code"], "LAL")
        self.assertEqual(snap["matches"][0]["away_team"]["full_name"], "Boston Celtics")
        self.assertEqual(snap["picks"][0]["matches"]["home_team"]["logo_url"], "h")
        self.assertEqual(snap["picks"][0]["recommended_team"]["code"], "LAL")
        self.assertIsInstance(snap["matches"][0]["period_scores"], dict)


if __name__ == "__main__":
    unittest.main()
