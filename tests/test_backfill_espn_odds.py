import unittest

from scripts.backfill_espn_odds import home_spread


class HomeSpreadTests(unittest.TestCase):
    def test_home_favorite_is_negative(self):
        self.assertEqual(home_spread("CLE -3.5", "CLE"), -3.5)

    def test_away_favorite_is_positive_for_home(self):
        self.assertEqual(home_spread("LAL -2.5", "CLE"), 2.5)

    def test_even_line_is_zero(self):
        self.assertEqual(home_spread("EVEN", "CLE"), 0.0)


if __name__ == "__main__":
    unittest.main()
