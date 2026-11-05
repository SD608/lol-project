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
                      "/api/v1/lanes", "/api/v1/matchups", "/api/v1/matchups/{id}", "/api/v1/patches"):
            self.assertIn(route, paths)

    def test_database_unavailable_returns_503(self):
        app.state.pool = None
        for path in ("/api/v1/health", "/api/v1/champions", "/api/v1/lanes", "/api/v1/patches", "/api/v1/matchups"):
            self.assertEqual(self.client.get(path).status_code, 503)

    def test_query_bounds(self):
        self.assertEqual(self.client.get("/api/v1/matchups?limit=201").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/champions?offset=-1").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/matchups?lane=INVALID").status_code, 422)

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

    def test_cors_closed_by_default(self):
        response = self.client.options("/api/v1/health", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"})
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")


if __name__ == "__main__":
    unittest.main()
