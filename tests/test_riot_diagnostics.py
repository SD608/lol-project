"""Riot auth diagnostic must never disclose secrets or need real network."""
import contextlib
import io
import unittest
from urllib.error import HTTPError, URLError

from scripts.diagnose_riot_api import (
    PUBLIC_STATUS, LEAGUE_ENTRIES, CHALLENGER, interpret, run, probe,
)


class FakeResponse:
    def __init__(self, code):
        self.status = code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class RiotDiagnosticsTests(unittest.TestCase):
    def test_no_key_never_calls_network(self):
        def fail(*args, **kwargs):
            raise AssertionError("network called")
        result, code = run("", opener=fail)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "key_not_configured")

    def test_403_is_distinguished_from_public_status(self):
        seen = []
        def fake(request, timeout=None):
            seen.append((request.full_url, request.headers))
            if request.full_url == PUBLIC_STATUS:
                return FakeResponse(200)
            raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

        result, code = run("RGAPI-test-secret-DO-NOT-PRINT", opener=fake)
        self.assertEqual(code, 0)
        self.assertEqual(result["public_kr_status_http"], 200)
        self.assertEqual(result["league_entries_http"], 403)
        self.assertEqual(result["challenger_league_http"], 403)
        self.assertIn("forbidden", result["status"])
        self.assertEqual(len(seen), 3)
        self.assertFalse(any("X-riot-token" in headers or "X-Riot-Token" in headers for url, headers in seen[:1]))
        self.assertTrue(result["secrets_logged"] is False)
        self.assertNotIn("RGAPI-test-secret", str(result))

    def test_one_authenticated_endpoint_success_proves_token_usable(self):
        self.assertEqual(interpret(200, 200, 403), "authenticated_access_confirmed")
        self.assertEqual(interpret(200, 403, 200), "authenticated_access_confirmed")

    def test_rate_limited_and_network(self):
        self.assertIn("rate_limited", interpret(200, 429, 429))
        self.assertEqual(interpret(None, None, None), "network_or_transport_problem")
        self.assertIsNone(probe(CHALLENGER, "dummy", opener=lambda *args, **kwargs: (_ for _ in ()).throw(URLError("offline"))))


if __name__ == "__main__":
    unittest.main()
