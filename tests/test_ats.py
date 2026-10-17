import unittest

from ats import apply_shrink, grade_spread, grade_total, summarize


class AtsTests(unittest.TestCase):
    def test_home_favorite_covers_when_margin_beats_the_line(self):
        self.assertEqual(grade_spread(4, 6, -3.5), "WIN")

    def test_home_favorite_misses_when_margin_is_short(self):
        self.assertEqual(grade_spread(3, 6, -3.5), "LOSS")

    def test_exact_line_is_a_push(self):
        self.assertEqual(grade_spread(3.5, 6, -3.5), "PUSH")

    def test_tied_prediction_follows_the_live_picker_and_takes_the_away_side(self):
        self.assertEqual(grade_spread(4, 3.5, -3.5), "LOSS")

    def test_shrink_moves_the_margin_toward_the_market(self):
        self.assertAlmostEqual(apply_shrink(10, -4, 0.5), 7.0)

    def test_total_grades_over_and_under(self):
        self.assertEqual(grade_total(230, 226, 220.5), "WIN")
        self.assertEqual(grade_total(210, 226, 220.5), "LOSS")

    def test_summary_ignores_pushes(self):
        stats = summarize(["WIN", "LOSS", "PUSH"])
        self.assertEqual(stats["rate"], 0.5)
        self.assertEqual(stats["pushes"], 1)

    def test_time_split_keeps_the_cut_date_out_of_training(self):
        import pandas as pd
        from ats import time_split
        frame = pd.DataFrame({
            "game_date": ["2026-04-01", "2026-04-01", "2026-04-02", "2026-04-03"],
            "gameId": ["a", "b", "c", "d"],
        })
        train, test = time_split(frame, 0.5)
        self.assertTrue((train["game_date"] < test["game_date"].min()).all())
        self.assertEqual(set(train["gameId"]) & set(test["gameId"]), set())


if __name__ == "__main__":
    unittest.main()
