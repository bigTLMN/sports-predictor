import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import insight_writer as iw  # noqa: E402
import sqlite_store  # noqa: E402

REC, OPP = 1610612752, 1610612759


def _logs():
    rows = []
    for i in range(10):
        day = pd.Timestamp("2026-10-01") + pd.Timedelta(days=i)
        rows.append({"gameDateTimeEst": day, "teamId": REC, "opponentTeamId": OPP if i % 5 == 0 else 1,
                     "home": 1, "win": 1, "teamScore": 115, "opponentScore": 104,
                     "fieldGoalsPercentage": 0.49, "threePointersAttempted": 38, "threePointersPercentage": 0.39,
                     "freeThrowsPercentage": 0.75, "reboundsTotal": 46, "reboundsOffensive": 11, "assists": 28,
                     "steals": 8, "blocks": 5, "turnovers": 12, "plusMinusPoints": 11, "pointsInThePaint": 52,
                     "pointsFastBreak": 16, "pointsFromTurnovers": 18, "pointsSecondChance": 14, "benchPoints": 36})
        rows.append({"gameDateTimeEst": day, "teamId": OPP, "opponentTeamId": REC if i % 5 == 0 else 1,
                     "home": 0, "win": 0, "teamScore": 106, "opponentScore": 110,
                     "fieldGoalsPercentage": 0.44, "threePointersAttempted": 34, "threePointersPercentage": 0.34,
                     "freeThrowsPercentage": 0.81, "reboundsTotal": 42, "reboundsOffensive": 9, "assists": 24,
                     "steals": 7, "blocks": 4, "turnovers": 15, "plusMinusPoints": -4, "pointsInThePaint": 44,
                     "pointsFastBreak": 12, "pointsFromTurnovers": 14, "pointsSecondChance": 12, "benchPoints": 30})
    return pd.DataFrame(rows).sort_values(["teamId", "gameDateTimeEst"])


class InsightWriterTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite_store.connect(":memory:")
        self.rec = sqlite_store.upsert_team(self.conn, "NYK", "Knicks", "New York Knicks", None, REC)
        self.opp = sqlite_store.upsert_team(self.conn, "SAS", "Spurs", "San Antonio Spurs", None, OPP)
        other = sqlite_store.upsert_team(self.conn, "BOS", "Celtics", "Boston Celtics", None, 1610612738)
        for d, h, a, hs, as_, sp, tot in (
            ("2026-10-20", self.rec, other, 110, 104, -3.5, 221.5),
            ("2026-10-22", other, self.rec, 99, 108, 2.0, 219.0),
            ("2026-10-21", self.opp, other, 101, 115, 4.5, 228.0),
        ):
            sqlite_store.upsert_match(self.conn, {
                "date": d, "home_team_id": h, "away_team_id": a, "start_time": d, "status": "STATUS_FINAL",
                "home_score": hs, "away_score": as_, "period_scores": None, "vegas_spread": sp, "vegas_total": tot,
            })
        self.logs = _logs()

    def _ctx(self, **over):
        rec_form = iw.season_form(self.conn, self.rec, "2026-10-23")
        opp_form = iw.season_form(self.conn, self.opp, "2026-10-23")
        ctx = {
            "match_id": 9, "date": "2026-10-23", "rec_code": "NYK", "opp_code": "SAS", "rec_is_home": False,
            "home_code": "SAS", "vegas_spread": 6.5, "vegas_total": 226.5, "total_is_default": False,
            "pred_margin_rec": 2.3, "raw_margin_rec": 4.1, "pred_total": 229.8, "ou_pick": "OVER",
            "confidence": 71, "ou_confidence": 59, "withhold_spread": False,
            "rec_form": rec_form, "opp_form": opp_form,
            "rec_profile": iw.team_profile(self.logs, REC), "opp_profile": iw.team_profile(self.logs, OPP),
            "rec_rest": iw.rest_days(rec_form, "2026-10-23"), "opp_rest": iw.rest_days(opp_form, "2026-10-23"),
            "h2h": iw.head_to_head(self.logs, REC, OPP),
        }
        ctx.update(over)
        return ctx

    def test_season_form_counts_results_and_ats(self):
        form = iw.season_form(self.conn, self.rec, "2026-10-23")
        self.assertEqual((form["wins"], form["losses"]), (2, 0))
        self.assertEqual(form["ats"], (2, 0, 0))
        self.assertEqual(form["ou"], (0, 2, 0))
        self.assertEqual(form["streak"], "W2")
        self.assertEqual(iw.rest_days(form, "2026-10-23"), 1)

    def test_write_up_has_sections_numbers_and_separate_languages(self):
        en, zh, facts = iw.build_insight(self._ctx())
        for header in ("## The Call", "## Season So Far", "## Statistical Profile", "## Schedule & Rest", "## Total: OVER 226.5", "## What Could Go Wrong"):
            self.assertIn(header, en)
        for header in ("## 結論", "## 本季至今", "## 數據體質", "## 賽程與休息", "## 大小分：大分 226.5", "## 風險"):
            self.assertIn(header, zh)
        self.assertIn("NYK is 2-0", en)
        self.assertIn("-6.5", en)
        self.assertIn("229.8", en)
        self.assertIn("back-to-back", en)
        self.assertIn("背靠背", zh)
        self.assertNotIn("過盤", en)
        self.assertNotIn("OVER", zh.replace("## 大小分：大分 226.5", ""))
        self.assertNotIn("UNDER", zh)
        self.assertNotIn("•", en.split("## Statistical Profile")[0])
        self.assertEqual(facts["projection"]["edge"], round(2.3 - 6.5, 1))
        self.assertTrue(any(r["key"] == "fg" for r in facts["rows"]))
        self.assertEqual(facts["form"]["rec"]["wins"], 2)

    def test_withheld_pick_publishes_total_only(self):
        en, zh, _ = iw.build_insight(self._ctx(vegas_spread=-9.0, withhold_spread=True))
        self.assertIn("large-underdog rule", en)
        self.assertIn("大受讓規則", zh)
        self.assertNotIn("Confidence is", en)

    def test_different_games_do_not_share_an_opener(self):
        openers = set()
        for mid in range(12):
            en, _, _ = iw.build_insight(self._ctx(match_id=mid))
            openers.add(en.split("\n")[1])
        self.assertGreater(len(openers), 1)

    def test_missing_profiles_and_form_still_write(self):
        conn = sqlite_store.connect(":memory:")
        en, zh, facts = iw.build_insight(self._ctx(
            rec_form=iw.season_form(conn, 1, "2026-10-23"), opp_form=iw.season_form(conn, 2, "2026-10-23"),
            rec_profile=None, opp_profile=None, rec_rest=None, opp_rest=None, h2h=[],
        ))
        self.assertIn("Neither team has a completed game", en)
        self.assertIn("兩隊本季都還沒有完賽紀錄", zh)
        self.assertEqual(facts["rows"], [])

    def test_facts_round_trip_through_sqlite_snapshot(self):
        en, zh, facts = iw.build_insight(self._ctx())
        mid = sqlite_store.upsert_match(self.conn, {
            "date": "2026-10-23", "home_team_id": self.opp, "away_team_id": self.rec, "start_time": "x",
            "status": "STATUS_SCHEDULED", "home_score": None, "away_score": None, "period_scores": None,
            "vegas_spread": 6.5, "vegas_total": 226.5,
        })
        sqlite_store.upsert_pick(self.conn, {
            "match_id": mid, "recommended_team_id": self.rec, "confidence_score": 71, "spread_logic": "a",
            "spread_logic_zh": "b", "line_info": "6.5", "ou_pick": "OVER", "ou_line": 226.5, "ou_confidence": 59,
            "analysis_content": en, "analysis_content_zh": zh, "analysis_facts": facts,
            "predicted_margin": 2.3, "predicted_total": 229.8, "created_at": "t",
        })
        snap = sqlite_store.export_snapshot(self.conn)
        pick = snap["picks"][0]
        self.assertIsInstance(pick["analysis_facts"], dict)
        self.assertEqual(pick["analysis_facts"]["form"]["rec"]["streak"], "W2")

    def test_quantified_layer_probabilities_ranks_and_effects(self):
        league = {
            "profile": iw.league_context(self.logs),
            "effects": iw.historical_effects(self.logs),
            "season": iw.season_ranks(self.conn, "2026-10-23"),
            "sigmas": iw.line_sigmas(self.conn, "2026-10-23"),
            "record": {"spread": {"w": 6, "l": 3}, "total": {"w": 4, "l": 5}, "spread_at_conf": {"w": 3, "l": 1}},
        }
        en, zh, facts = iw.build_insight(self._ctx(league=league, rec_nba=REC, opp_nba=OPP,
                                                   rec_db_id=self.rec, opp_db_id=self.opp))
        p = facts["probability"]
        # edge = 2.3 - 6.5 = -4.2 -> cover probability below 50% with the default sigma
        self.assertAlmostEqual(p["cover"], iw.norm_cdf(-4.2 / iw.DEFAULT_SIGMA_SPREAD), places=3)
        self.assertLess(p["cover"], 0.5)
        self.assertAlmostEqual(p["win_market"], iw.norm_cdf(6.5 / iw.DEFAULT_SIGMA_SPREAD), places=3)
        self.assertAlmostEqual(p["total"], iw.norm_cdf(3.3 / iw.DEFAULT_SIGMA_TOTAL), places=3)
        self.assertIn("chance of covering", en)
        self.assertIn("過盤機率", zh)
        self.assertIn("break-even", en)
        # league ranks: two NBA teams in the synthetic logs, REC better on points
        self.assertEqual(league["profile"]["teams"], 2)
        fg_row = next(r for r in facts["rows"] if r["key"] == "ppg")
        self.assertEqual((fg_row["rec_rank"], fg_row["opp_rank"]), (1, 2))
        self.assertIsNotNone(fg_row["avg"])
        self.assertIn("1st vs SAS 2nd of 2", en)
        # season ranks from sqlite: NYK +7.5 margin ranks above SAS
        self.assertEqual(facts["form"]["rec"]["rank"]["margin"], 1)
        self.assertIn("(1st of 3)", en)
        # track record and effects reach the text
        self.assertIn("## Model Track Record", en)
        self.assertIn("6-3 (67%)", en)
        self.assertIn("## 模型本季戰績", zh)
        self.assertIn("Home teams have outscored visitors by", en)
        self.assertIn("back-to-back have been outscored", en)
        self.assertEqual(facts["record"]["spread"], [6, 3])
        self.assertIn("Consistency check", en)

    def test_line_sigmas_default_until_sample_is_large(self):
        s = iw.line_sigmas(self.conn, "2026-10-23")
        self.assertEqual((s["spread"], s["total"], s["measured"]), (iw.DEFAULT_SIGMA_SPREAD, iw.DEFAULT_SIGMA_TOTAL, False))

    def test_connect_adds_facts_column_to_old_database(self):
        import sqlite3
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        raw = sqlite3.connect(path)
        raw.executescript(sqlite_store.SCHEMA.replace("  analysis_facts TEXT,\n", ""))
        raw.close()
        conn = sqlite_store.connect(path)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(aggregated_picks)")}
        self.assertIn("analysis_facts", cols)


if __name__ == "__main__":
    unittest.main()
