"""Offline API contract tests. No SQLite or live PostgreSQL mutation."""
import unittest

try:
    from fastapi.testclient import TestClient
    from backend.main import app, matchup_id, parse_matchup_id, champion_view, match_search
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient is not None, "Install backend/requirements.txt")
class BackendContractTests(unittest.TestCase):
    def setUp(self):
        # TestClient without lifespan intentionally omits a configured database.
        self.client = TestClient(app)

    def test_openapi_has_all_routes(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for route in ("/api/v1/health", "/api/v1/champions", "/api/v1/champions/{id}",
                      "/api/v1/lanes", "/api/v1/matchups", "/api/v1/matchups/{id}", "/api/v1/patches", "/api/v1/counters"):
            self.assertIn(route, paths)

    def test_database_unavailable_returns_503(self):
        app.state.pool = None
        for path in ("/api/v1/health", "/api/v1/champions", "/api/v1/lanes", "/api/v1/patches", "/api/v1/matchups", "/api/v1/counters?lane=탑&opponent=우르곳"):
            self.assertEqual(self.client.get(path).status_code, 503)

    def test_query_bounds(self):
        self.assertEqual(self.client.get("/api/v1/matchups?limit=201").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/champions?offset=-1").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/matchups?lane=INVALID").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/counters?lane=INVALID&opponent=우르곳").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/counters?lane=탑").status_code, 422)

    def test_matchup_id_roundtrip(self):
        key = ("탑", "우르곳", "가렌")
        self.assertEqual(parse_matchup_id(matchup_id(*key)), key)

    def test_invalid_matchup_id(self):
        from fastapi import HTTPException
        for value in ("../etc/passwd", "a", matchup_id("탑", "가렌", "가렌")):
            with self.assertRaises(HTTPException):
                parse_matchup_id(value)

    def test_alias_and_initials(self):
        miss = champion_view({"name": "미스 포츈", "aliases": [], "initials": "", "riot_id": None, "image_url": None})
        self.assertTrue(match_search(miss, "미포"))
        self.assertTrue(match_search(miss, "ㅁㅅㅍㅊ"))
        self.assertTrue(match_search(miss, "미스 포츈"))

    def test_off_meta_enemy_returns_unregistered_coverage_not_404(self):
        from unittest.mock import AsyncMock, patch
        from backend import main as backend_main

        # First query: champion exists in global roster; second: not in the lane;
        # third: no confirmed live patch. No fabricated matchup rows or grades.
        with patch.object(backend_main, "one", new_callable=AsyncMock) as one_mock, \
             patch.object(backend_main, "fetch", new_callable=AsyncMock) as fetch_mock:
            one_mock.side_effect = [{"name": "케이틀린"}, None, None]
            fetch_mock.return_value = [{"champion": "가렌", "rating": None},
                                       {"champion": "우르곳", "rating": None}]
            response = self.client.get("/api/v1/counters", params={"lane": "탑", "opponent": "케이틀린"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["lane_registered"])
        self.assertEqual(data["coverage_status"], "off_meta_unregistered")
        self.assertEqual(data["data_status"], "no_verified_matchups")
        self.assertEqual(data["unknown_count"], 2)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["hard_counters"], [])
        self.assertEqual(data["counters"], [])
        self.assertEqual(data["even"], [])
        self.assertEqual(data["patch"], None)

    def test_registered_enemy_keeps_normal_coverage(self):
        from unittest.mock import AsyncMock, patch
        from backend import main as backend_main
        with patch.object(backend_main, "one", new_callable=AsyncMock) as one_mock, \
             patch.object(backend_main, "fetch", new_callable=AsyncMock) as fetch_mock:
            one_mock.side_effect = [{"name": "가렌"}, {"champion": "가렌"}, {"patch": "26.22"}]
            fetch_mock.return_value = [{"champion": "우르곳", "rating": "7:3"},
                                       {"champion": "케일", "rating": None}]
            response = self.client.get("/api/v1/counters", params={"lane": "탑", "opponent": "가렌"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["lane_registered"])
        self.assertEqual(data["coverage_status"], "registered")
        self.assertEqual(data["counters"], [{"champion": "우르곳", "rating": "7:3"}])
        self.assertEqual(data["unknown_count"], 1)

    def test_unknown_champion_returns_404(self):
        from unittest.mock import AsyncMock, patch
        from backend import main as backend_main
        with patch.object(backend_main, "one", new_callable=AsyncMock, return_value=None):
            response = self.client.get("/api/v1/counters", params={"lane": "탑", "opponent": "존재하지않는챔피언"})
        self.assertEqual(response.status_code, 404)

    def test_cors_closed_by_default(self):
        response = self.client.options("/api/v1/health", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"})
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")


if __name__ == "__main__":
    unittest.main()
