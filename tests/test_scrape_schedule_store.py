import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import scrape_schedule
import sqlite_store


class ScheduleStoreTests(unittest.TestCase):
    def test_save_match_updates_same_pairing(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        home = sqlite_store.upsert_team(conn, "LAL", "Lakers", "Los Angeles Lakers", None, 1)
        away = sqlite_store.upsert_team(conn, "BOS", "Celtics", "Boston Celtics", None, 2)
        team_map = {"LAL": home, "BOS": away}
        payload = {
            "date": "2026-10-18", "start_time": "2026-10-18T23:00:00Z",
            "home_abbr": "LAL", "away_abbr": "BOS", "status": "STATUS_SCHEDULED",
            "home_score": 0, "away_score": 0, "period_scores": None,
            "vegas_spread": -2.5, "vegas_total": 215.0,
        }
        first = scrape_schedule.save_match(conn, team_map, payload)
        payload["status"] = "STATUS_FINISHED"
        payload["home_score"] = 101
        second = scrape_schedule.save_match(conn, team_map, payload)
        self.assertEqual(first, second)
        status = conn.execute("SELECT status, home_score FROM matches WHERE id=?", (first,)).fetchone()
        self.assertEqual(status["status"], "STATUS_FINISHED")
        self.assertEqual(status["home_score"], 101)


if __name__ == "__main__":
    unittest.main()
