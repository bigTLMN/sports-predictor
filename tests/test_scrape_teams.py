import os
import tempfile
import unittest

os.environ["NBA_SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "nba.sqlite")

import scrape_teams
import sqlite_store


class TeamSeedTests(unittest.TestCase):
    def test_store_teams_uses_espn_abbreviation_and_nba_id(self):
        conn = sqlite_store.connect(os.environ["NBA_SQLITE_PATH"])
        count = scrape_teams.store_teams(conn, [{
            "team": {
                "abbreviation": "LAL",
                "shortDisplayName": "Lakers",
                "displayName": "Los Angeles Lakers",
                "logos": [{"href": "http://logo"}],
            }
        }])
        self.assertEqual(count, 1)
        row = conn.execute("SELECT code, nba_team_id, full_name FROM teams").fetchone()
        self.assertEqual(row["code"], "LAL")
        self.assertEqual(row["nba_team_id"], 1610612747)
        self.assertEqual(row["full_name"], "Los Angeles Lakers")


if __name__ == "__main__":
    unittest.main()
