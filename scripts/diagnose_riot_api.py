#!/usr/bin/env python3
"""Bounded Riot API auth/path diagnostic. No secrets, response bodies, or player IDs in reports.

Only 3 GETs: public KR platform status, and two documented KR LEAGUE-V4
endpoints. It never collects matches, touches databases, or prints headers.
"""
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PUBLIC_STATUS = "https://kr.api.riotgames.com/lol/status/v4/platform-data"
LEAGUE_ENTRIES = "https://kr.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/EMERALD/I?page=1"
CHALLENGER = "https://kr.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"


def probe(url, key=None, opener=urlopen):
    headers = {"User-Agent": "PICKOU-diagnostics/1.0"}
    if key:
        headers["X-Riot-Token"] = key
    try:
        # Never print the URL, response headers, exception details or contents.
        with opener(Request(url, headers=headers), timeout=10) as response:
            code = response.status
            return code if 100 <= code <= 599 else None
    except HTTPError as exc:
        return exc.code if 100 <= exc.code <= 599 else None
    except (URLError, TimeoutError, OSError, ValueError):
        return None


def interpret(status, entries, challenger):
    if status is None and entries is None and challenger is None:
        return "network_or_transport_problem"
    if entries in (200, 204) or challenger in (200, 204):
        return "authenticated_access_confirmed"
    if entries == 403 and challenger == 403:
        return "both_authenticated_endpoints_forbidden_check_key_status_and_permissions"
    if entries == 401 and challenger == 401:
        return "both_authenticated_endpoints_unauthorized_check_key"
    if entries == 429 or challenger == 429:
        return "rate_limited_do_not_retry_immediately"
    if entries == 403 or challenger == 403:
        return "at_least_one_authenticated_endpoint_forbidden_review_path_and_key"
    return "inconclusive_review_http_codes"


def run(key, opener=urlopen):
    if not key:
        return {"status": "key_not_configured", "requests": 0}, 2
    # Don't inspect or print key contents beyond existence.
    result = {
        "public_kr_status_http": probe(PUBLIC_STATUS, opener=opener),
        "league_entries_http": probe(LEAGUE_ENTRIES, key=key, opener=opener),
        "challenger_league_http": probe(CHALLENGER, key=key, opener=opener),
        "requests": 3,
        "secrets_logged": False,
        "data_collected": False,
    }
    result["status"] = interpret(
        result["public_kr_status_http"], result["league_entries_http"], result["challenger_league_http"]
    )
    return result, 0


if __name__ == "__main__":
    result, code = run(os.getenv("RIOT_API_KEY", ""))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    sys.exit(code)
