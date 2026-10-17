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
        espn_codes = {
            "GS": "GSW",
            "NO": "NOP",
            "NY": "NYK",
            "SA": "SAS",
            "UTAH": "UTA",
        }
        for espn_code, alias in espn_codes.items():
            self.assertEqual(scrape_teams.NBA_TEAM_IDS[espn_code], scrape_teams.NBA_TEAM_IDS[alias])
        gs_count = scrape_teams.store_teams(conn, [{
            "team": {
                "abbreviation": "GS",
                "shortDisplayName": "Warriors",
                "displayName": "Golden State Warriors",
                "logos": [{"href": "http://gs"}],
            }
        }])
        self.assertEqual(gs_count, 1)
        gs = conn.execute("SELECT nba_team_id FROM teams WHERE code = 'GS'").fetchone()
        self.assertEqual(gs["nba_team_id"], 1610612744)


if __name__ == "__main__":
    unittest.main()
