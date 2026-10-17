import json
import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import sqlite_store as store
import export_snapshot


class ExportSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(os.environ["NBA_SQLITE_PATH"])

    def test_write_snapshot_writes_public_json(self):
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
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
            path = tmp.name
        try:
            export_snapshot.write_snapshot(self.conn, path)
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(set(data), {"teams", "matches", "picks"})
            self.assertEqual(data["matches"][0]["home_team"]["code"], "LAL")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
