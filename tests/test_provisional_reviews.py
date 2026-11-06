"""Guard provisional matchup reviews against unsourced or fabricated grades."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH = Path(__file__).resolve().parents[1] / "frontend" / "data" / "provisional-matchup-reviews.json"
LANES = {"탑", "정글", "미드", "바텀", "서폿"}
FORBIDDEN = {"rating", "win_rate", "winRate", "win_probability", "score", "confidence"}

class ProvisionalMatchupReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def test_unique_directional_keys_and_valid_sources(self):
        keys = set()
        self.assertEqual(self.data["scope"], "mechanic_based_provisional")
        for row in self.data["entries"]:
            key = (row["lane"], row["champion"], row["opponent"])
            self.assertNotIn(key, keys)
            keys.add(key)
            self.assertIn(row["lane"], LANES)
            self.assertNotEqual(row["champion"], row["opponent"])
            self.assertEqual(row["status"], "provisional")
            self.assertTrue(row["assessment"])
            self.assertTrue(row["phase"])
            self.assertGreaterEqual(len(row["mechanisms"]), 2)
            self.assertTrue(all(isinstance(x, str) and x.strip() for x in row["mechanisms"]))
            self.assertTrue(row["counterplay"])
            self.assertTrue(row["limitations"])
            self.assertFalse(FORBIDDEN.intersection(row))
            self.assertGreaterEqual(len(row["sources"]), 2)
            self.assertTrue(any("leagueoflegends.com" in s["url"] for s in row["sources"]))
            for source in row["sources"]:
                url = urlparse(source["url"])
                self.assertEqual(url.scheme, "https")
                self.assertTrue(url.netloc)
                self.assertTrue(source["label"])

    def test_five_lanes_present_and_no_unreviewed_mass_generation(self):
        rows = self.data["entries"]
        self.assertEqual(len(rows), 26)
        self.assertTrue(any(r["lane"] == "탑" and r["champion"] == "케이틀린" and r["opponent"] == "트린다미어" for r in rows))
        self.assertEqual({r["lane"] for r in rows}, LANES)
        self.assertTrue(all(r["status"] == "provisional" for r in rows))

    def test_reverse_direction_exists_and_does_not_claim_approval(self):
        keys = {(row["lane"], row["champion"], row["opponent"]) for row in self.data["entries"]}
        for lane, champ, opp in keys:
            self.assertIn((lane, opp, champ), keys)


if __name__ == "__main__":
    unittest.main()
