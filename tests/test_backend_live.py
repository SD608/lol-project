"""Live PostgreSQL read-only integration gate.

Only runs when DATABASE_URL is supplied securely; otherwise skipped, never faked.
"""
import os
import unittest

try:
    from fastapi.testclient import TestClient
    from backend.main import app
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient is not None and bool(os.environ.get("DATABASE_URL")), "Live DATABASE_URL not configured")
class LivePickouReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = TestClient(app)
        cls.client = cls.session.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.session.__exit__(None, None, None)

    def test_health_real_postgres_counts(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"], {"champions": 173, "lanes": 266, "matchups": 14468})

    def test_real_champion_search(self):
        for query, expected in [("미포", "미스 포츈"), ("ㅁㅅㅍㅊ", "미스 포츈"), ("아우솔", "아우렐리온 솔")]:
            response = self.client.get("/api/v1/champions", params={"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertIn(expected, [item["name"] for item in response.json()["items"]])

    def test_real_lane_totals(self):
        response = self.client.get("/api/v1/lanes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({r["lane"]: r["champion_count"] for r in response.json()["items"]},
                         {"탑": 65, "정글": 56, "미드": 62, "바텀": 35, "서폿": 48})

    def test_real_filtered_matchups_and_detail(self):
        response = self.client.get("/api/v1/matchups", params={"lane": "탑", "champion": "우르곳", "limit": 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 64)
        self.assertEqual(len(response.json()["items"]), 10)
        item = response.json()["items"][0]
        detail = self.client.get("/api/v1/matchups/" + item["id"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["champion"], "우르곳")
        self.assertIn(detail.json()["status"], ("unknown", "verified"))
        if detail.json()["status"] == "unknown":
            self.assertIsNone(detail.json()["rating"])

    def test_no_database_write_privileges(self):
        import asyncio
        import asyncpg

        async def check():
            conn = await asyncpg.connect(os.environ["DATABASE_URL"])
            try:
                return await conn.fetchrow("""SELECT current_user AS username,
                    has_table_privilege(current_user, 'pickou.champions', 'INSERT') AS can_insert,
                    has_table_privilege(current_user, 'pickou.champions', 'UPDATE') AS can_update,
                    has_table_privilege(current_user, 'pickou.champions', 'DELETE') AS can_delete,
                    has_schema_privilege('anon','pickou','USAGE') AS anon_usage,
                    has_schema_privilege('authenticated','pickou','USAGE') AS auth_usage""")
            finally:
                await conn.close()

        role = asyncio.run(check())
        self.assertNotIn(role["username"], ("postgres", "supabase_admin"))
        for col in ("can_insert", "can_update", "can_delete", "anon_usage", "auth_usage"):
            self.assertFalse(role[col], col)


if __name__ == "__main__":
    unittest.main()
