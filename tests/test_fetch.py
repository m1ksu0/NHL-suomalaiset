import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_html
import fetch_data as fd


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


class TimeWindowTests(unittest.TestCase):
    def test_winter_time_inside(self):
        # Talviaika (UTC+2): 17:30 UTC = 19:30 Suomessa
        self.assertTrue(fd.in_time_window(utc("2026-11-10T17:30:00")))

    def test_boundaries_inclusive(self):
        self.assertTrue(fd.in_time_window(utc("2026-11-10T16:00:00")))   # 18:00
        self.assertTrue(fd.in_time_window(utc("2026-11-10T21:00:00")))   # 23:00
        self.assertFalse(fd.in_time_window(utc("2026-11-10T15:59:00")))  # 17:59
        self.assertFalse(fd.in_time_window(utc("2026-11-10T21:01:00")))  # 23:01

    def test_summer_time(self):
        # Kesäaika (UTC+3): 15:00 UTC = 18:00 Suomessa
        self.assertTrue(fd.in_time_window(utc("2026-07-10T15:00:00")))
        self.assertFalse(fd.in_time_window(utc("2026-07-10T14:59:00")))

    def test_night_game_outside(self):
        self.assertFalse(fd.in_time_window(utc("2026-11-11T00:00:00")))  # 02:00


class SeasonTests(unittest.TestCase):
    def test_season_id(self):
        self.assertEqual(fd.season_id(date(2026, 11, 6)), 20262027)
        self.assertEqual(fd.season_id(date(2027, 3, 1)), 20262027)
        self.assertEqual(fd.season_id(date(2027, 9, 20)), 20272028)

    def test_outcome_label(self):
        self.assertEqual(fd.outcome_label("REG"), "")
        self.assertEqual(fd.outcome_label("OT"), "JA")
        self.assertEqual(fd.outcome_label("SO"), "VL")


class FinnishLinesTests(unittest.TestCase):
    def setUp(self):
        self.box = {
            "awayTeam": {"abbrev": "OTT"},
            "homeTeam": {"abbrev": "BUF"},
            "playerByGameStats": {
                "awayTeam": {
                    "forwards": [
                        {"playerId": 1, "name": {"default": "A. Suomi"}, "position": "C",
                         "goals": 1, "assists": 1, "points": 2, "plusMinus": 1, "toi": "20:00"},
                        {"playerId": 2, "name": {"default": "B. Muu"}, "position": "L",
                         "goals": 3, "assists": 0, "points": 3, "plusMinus": 2, "toi": "18:00"},
                    ],
                    "defense": [],
                    "goalies": [],
                },
                "homeTeam": {
                    "forwards": [],
                    "defense": [],
                    "goalies": [
                        {"playerId": 3, "name": {"default": "K. Maalari"}, "toi": "59:12", "saves": 24,
                         "shotsAgainst": 25, "goalsAgainst": 1, "savePctg": 0.96, "decision": "W"},
                        {"playerId": 4, "name": {"default": "V. Varalla"}, "toi": "00:00"},
                    ],
                },
            },
        }

    def test_filters_only_finns(self):
        res = fd.finnish_lines(self.box, {1, 3, 4}, {1: "Aku Suomi", 3: "Kalle Maalari"})
        self.assertEqual([s["name"] for s in res["skaters"]], ["Aku Suomi"])
        self.assertEqual(res["skaters"][0]["p"], 2)
        # Maalivahti, joka ei pelannut (toi 00:00), jätetään pois
        self.assertEqual([g["name"] for g in res["goalies"]], ["Kalle Maalari"])
        self.assertEqual(res["goalies"][0]["saves"], 24)


class HtmlTests(unittest.TestCase):
    def test_builds_with_minimal_data(self):
        data = {
            "generated_at": "2026-11-06T07:00:00+00:00", "season": 20262027,
            "skaters": [], "goalies": [], "results": [], "upcoming": [],
        }
        html = build_html.build(data)
        self.assertIn("Suomalaiset NHL:ssä", html)
        self.assertIn("2026&ndash;27", html)
        self.assertIn("Ei otteluita tällä aikavälillä.", html)

    def test_has_three_tabs_with_matching_panels(self):
        data = {
            "generated_at": "2026-11-06T07:00:00+00:00", "season": 20262027,
            "skaters": [], "goalies": [], "results": [], "upcoming": [],
        }
        html = build_html.build(data)
        for name in ("tulokset", "tulossa", "tilastot"):
            self.assertIn(f'aria-controls="{name}"', html)
            self.assertIn(f'id="{name}"', html)
        # Ilman JavaScriptia kaikki osiot pysyvät näkyvissä (ei kovakoodattua hidden-attribuuttia)
        self.assertNotIn(" hidden>", html)


if __name__ == "__main__":
    unittest.main()
