"""PICKOU v1 read-only API. The API never creates, updates or deletes DB rows."""
import asyncio
import binascii
import base64
import json
import os
import re
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from rift.database import ALIASES, initials

LANES = ("탑", "정글", "미드", "바텀", "서폿")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,600}$")
PATCH_RE = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}(?:\.[0-9]{1,3})?$")
NAME_MAX = 100


def matchup_id(lane: str, champion: str, opponent: str) -> str:
    raw = json.dumps([lane, champion, opponent], ensure_ascii=False, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def parse_matchup_id(value: str) -> tuple[str, str, str]:
    if not ID_RE.fullmatch(value):
        raise HTTPException(422, "Invalid matchup ID")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        obj = json.loads(raw)
        if not isinstance(obj, list) or len(obj) != 3 or not all(isinstance(v, str) for v in obj):
            raise ValueError("expected three strings")
        lane, champ, opp = obj
        if lane not in LANES or not champ or not opp or champ == opp or max(len(champ), len(opp)) > NAME_MAX:
            raise ValueError("invalid pair")
        if matchup_id(*obj) != value:
            raise ValueError("noncanonical encoding")
        return lane, champ, opp
    except (ValueError, UnicodeError, TypeError, binascii.Error):
        raise HTTPException(422, "Invalid matchup ID") from None


def normalize(value: str) -> str:
    return "".join(value.casefold().split())


def champion_view(row):
    obj = dict(row)
    name = obj["name"]
    aliases = list(dict.fromkeys([*(obj.get("aliases") or []), *ALIASES.get(name, [])]))
    obj["aliases"] = aliases
    obj["initials"] = obj.get("initials") or initials(name)
    return obj


def match_search(champion, q):
    q = normalize(q)
    return any(q in normalize(text) for text in [champion["name"], champion["initials"], *champion["aliases"]])


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = os.environ.get("DATABASE_URL")
    app.state.pool = None
    if url:
        # Do not log credentials; fail closed if DB connection is unavailable.
        pool = await asyncpg.create_pool(
            dsn=url, min_size=int(os.getenv("DB_POOL_MIN", "1")),
            max_size=int(os.getenv("DB_POOL_MAX", "5")),
            timeout=float(os.getenv("DB_TIMEOUT_SECONDS", "5")),
            server_settings={"default_transaction_read_only": "on", "statement_timeout": "5000"},
        )
        try:
            async with pool.acquire() as conn:
                # Fail closed if a high-privilege or unexpected credential is configured.
                role = await conn.fetchrow("""
                    SELECT current_user AS username,
                      has_schema_privilege(current_user,'pickou','USAGE') AS schema_usage,
                      has_table_privilege(current_user,'pickou.champions','SELECT') AS can_read,
                      has_table_privilege(current_user,'pickou.champions','INSERT') AS can_insert,
                      has_table_privilege(current_user,'pickou.champions','UPDATE') AS can_update,
                      has_table_privilege(current_user,'pickou.champions','DELETE') AS can_delete
                """)
                if (role["username"] != "pickou_api_reader"
                    or not role["schema_usage"] or not role["can_read"]
                    or role["can_insert"] or role["can_update"] or role["can_delete"]):
                    raise RuntimeError("Unsafe database role; expected read-only pickou_api_reader")
            app.state.pool = pool
        except BaseException:
            await pool.close()
            raise
    try:
        yield
    finally:
        if app.state.pool is not None:
            await app.state.pool.close()


app = FastAPI(title="PICKOU Read API", version="1.0.0", lifespan=lifespan)
origins = [u.strip() for u in os.getenv("CORS_ORIGINS", "").split(",") if u.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["Accept", "Content-Type"])


async def fetch(request, query, *args):
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(503, "Database unavailable")
    try:
        async with pool.acquire(timeout=5) as conn:
            return await conn.fetch(query, *args)
    except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError, asyncio.TimeoutError):
        raise HTTPException(503, "Database unavailable") from None


async def one(request, query, *args):
    rows = await fetch(request, query, *args)
    return dict(rows[0]) if rows else None


@app.get("/api/v1/health")
async def health(request: Request):
    row = await one(request, "SELECT current_database() AS name, (SELECT count(*) FROM pickou.champions) AS champions, (SELECT count(*) FROM pickou.champion_lanes) AS lanes, (SELECT count(*) FROM pickou.matchups) AS matchups")
    return {"status": "ok", "database": "ok", "counts": {"champions": row["champions"], "lanes": row["lanes"], "matchups": row["matchups"]}}


@app.get("/api/v1/champions")
async def champions(request: Request, q: str | None = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    # Aliases/initials from existing code are merged in memory; SQL remains read-only.
    rows = await fetch(request, "SELECT name,riot_id,aliases,initials,image_url FROM pickou.champions ORDER BY name")
    items = [champion_view(r) for r in rows]
    if q:
        items = [item for item in items if match_search(item, q)]
    return {"total": len(items), "limit": limit, "offset": offset, "items": items[offset:offset+limit]}


@app.get("/api/v1/champions/{id}")
async def champion_detail(id: str, request: Request):
    if not id or len(id) > NAME_MAX:
        raise HTTPException(422, "Invalid champion ID")
    row = await one(request, "SELECT name,riot_id,aliases,initials,image_url FROM pickou.champions WHERE name=$1", id)
    if row is None:
        raise HTTPException(404, "Champion not found")
    lanes = await fetch(request, "SELECT lane FROM pickou.champion_lanes WHERE champion=$1 ORDER BY lane", id)
    return {**champion_view(row), "lanes": [r["lane"] for r in lanes]}


@app.get("/api/v1/lanes")
async def lanes(request: Request):
    rows = await fetch(request, "SELECT lane,count(*)::int AS champion_count FROM pickou.champion_lanes GROUP BY lane")
    counts = {r["lane"]: r["champion_count"] for r in rows}
    return {"items": [{"lane": lane, "champion_count": counts.get(lane, 0)} for lane in LANES]}


@app.get("/api/v1/patches")
async def patches(request: Request, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0)):
    rows = await fetch(request, "SELECT patch,ddragon_version,region,release_status,official_notes_url,confirmed_at FROM pickou.patches ORDER BY created_at DESC,patch DESC LIMIT $1 OFFSET $2", limit, offset)
    total = await one(request, "SELECT count(*)::int AS n FROM pickou.patches")
    return {"total": total["n"], "limit": limit, "offset": offset, "items": [dict(r) for r in rows]}


def validate_pair(lane, champion, patch):
    if lane is not None and lane not in LANES:
        raise HTTPException(422, "Invalid lane")
    if champion is not None and (not champion or len(champion) > NAME_MAX):
        raise HTTPException(422, "Invalid champion")
    if patch is not None and not PATCH_RE.fullmatch(patch):
        raise HTTPException(422, "Invalid patch")


@app.get("/api/v1/matchups")
async def matchups(request: Request, lane: str | None = None, champion: str | None = None, patch: str | None = None,
                   region: str = Query("KR", min_length=2, max_length=16),
                   tier: str = Query("UNSPECIFIED", min_length=1, max_length=40),
                   limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    validate_pair(lane, champion, patch)
    clauses = ["($1::text IS NULL OR lane=$1)", "($2::text IS NULL OR champion=$2)"]
    where = " AND ".join(clauses)
    total = await one(request, f"SELECT count(*)::int AS n FROM pickou.matchups WHERE {where}", lane, champion)
    rows = await fetch(request, f"SELECT lane,champion,opponent FROM pickou.matchups WHERE {where} ORDER BY lane,champion,opponent LIMIT $3 OFFSET $4", lane, champion, limit, offset)
    return {"total": total["n"], "limit": limit, "offset": offset, "items": [
        {"id": matchup_id(r["lane"], r["champion"], r["opponent"]), **dict(r), "rating": None, "status": "unknown"} for r in rows
    ], "note": "List entries never inherit old-patch decisions; fetch detail with an explicit confirmed patch."}


@app.get("/api/v1/matchups/{id}")
async def matchup_detail(id: str, request: Request, patch: str | None = None,
                         region: str = Query("KR", min_length=2, max_length=16),
                         tier: str = Query("UNSPECIFIED", min_length=1, max_length=40)):
    lane, champion, opponent = parse_matchup_id(id)
    validate_pair(lane, champion, patch)
    row = await one(request, "SELECT lane,champion,opponent FROM pickou.matchups WHERE lane=$1 AND champion=$2 AND opponent=$3", lane, champion, opponent)
    if row is None:
        raise HTTPException(404, "Matchup not found")
    # Explicit patch must be confirmed in region. Without it, no historical grade is promoted.
    selected = await one(request, "SELECT patch FROM pickou.patches WHERE release_status='confirmed' AND region=$1 AND ($2::text IS NULL OR patch=$2) ORDER BY confirmed_at DESC NULLS LAST,created_at DESC LIMIT 1", region, patch)
    result = {"id": id, **dict(row), "patch": selected["patch"] if selected else None,
              "rating": None, "status": "unknown", "statistics": None, "decision": None, "validation_history": []}
    if not selected:
        return result
    key = (selected["patch"], lane, champion, opponent, region, tier)
    stat = await one(request, """SELECT id,patch,region,tier,sample_size,metrics,confidence_intervals,sources,calculated_at
          FROM pickou.matchup_statistics WHERE patch=$1 AND lane=$2 AND champion=$3 AND opponent=$4 AND region=$5 AND tier=$6
          ORDER BY calculated_at DESC,id DESC LIMIT 1""", *key)
    result["statistics"] = stat
    decision = await one(request, """SELECT id,patch,region,tier,rating,status,evidence,statistic_id,reviewer,created_at
          FROM pickou.matchup_decisions WHERE patch=$1 AND lane=$2 AND champion=$3 AND opponent=$4 AND region=$5 AND tier=$6
          ORDER BY created_at DESC,id DESC LIMIT 1""", *key)
    if decision:
        result["decision"] = {**decision, "rating": decision["rating"] if decision["status"] == "manual_approved" else None}
        history = await fetch(request, "SELECT event,evidence,created_at FROM pickou.validation_history WHERE decision_id=$1 ORDER BY created_at,id", decision["id"])
        result["validation_history"] = [dict(r) for r in history]
        if decision["status"] == "manual_approved" and decision["rating"] is not None:
            result["rating"] = decision["rating"]
            result["status"] = "verified"
    return result


@app.get("/api/v1/counters")
async def counters(request: Request, lane: str = Query(...), opponent: str = Query(..., min_length=1, max_length=NAME_MAX),
                   region: str = Query("KR", min_length=2, max_length=16),
                   tier: str = Query("UNSPECIFIED", min_length=1, max_length=40)):
    """Counter suggestions, including off-meta opponents without inventing matchups or grades."""
    validate_pair(lane, opponent, None)

    # Existence in the global champion roster is independent of lane registration.
    champion = await one(request,
        "SELECT name FROM pickou.champions WHERE name=$1", opponent)
    if champion is None:
        raise HTTPException(404, "Champion not found")

    registered = await one(request,
        "SELECT champion FROM pickou.champion_lanes WHERE lane=$1 AND champion=$2", lane, opponent)
    is_off_meta = registered is None

    patch = await one(request, """
        SELECT patch FROM pickou.patches
        WHERE release_status='confirmed' AND region=$1
        ORDER BY confirmed_at DESC NULLS LAST, created_at DESC
        LIMIT 1
    """, region)
    patch_name = patch["patch"] if patch else None

    # Use the selected lane's possible counter picks, excluding the opponent. For a
    # non-registered opponent there are NO stored matchup rows: return eligible
    # candidates as unverified only, never borrow ratings from another lane.
    rows = await fetch(request, """
        SELECT cl.champion,
               CASE WHEN d.status='manual_approved' AND d.rating IS NOT NULL
                    THEN d.rating ELSE NULL END AS rating
        FROM pickou.champion_lanes AS cl
        LEFT JOIN pickou.matchups AS m
          ON m.lane=cl.lane AND m.champion=cl.champion AND m.opponent=$2
        LEFT JOIN LATERAL (
            SELECT status, rating FROM pickou.matchup_decisions
            WHERE patch=$3 AND region=$4 AND tier=$5
              AND lane=m.lane AND champion=m.champion AND opponent=m.opponent
            ORDER BY created_at DESC,id DESC LIMIT 1
        ) AS d ON m.champion IS NOT NULL AND $3::text IS NOT NULL
        WHERE cl.lane=$1 AND cl.champion<>$2
        ORDER BY cl.champion
    """, lane, opponent, patch_name, region, tier)

    hard, counter, even = [], [], []
    unknown_count = 0
    for row in rows:
        rating = row["rating"]
        pick = {"champion": row["champion"], "rating": rating}
        if rating in ("9:1", "8:2"):
            hard.append(pick)
        elif rating in ("7:3", "6:4"):
            counter.append(pick)
        elif rating == "5:5":
            even.append(pick)
        elif rating is None:
            unknown_count += 1
        # Ratings that favor the opponent are not recommended.

    return {
        "lane": lane, "opponent": opponent,
        "lane_registered": not is_off_meta,
        "coverage_status": "off_meta_unregistered" if is_off_meta else "registered",
        "data_status": "no_verified_matchups" if not (hard or counter or even) else "partially_verified",
        "patch": patch_name,
        "region": region, "tier": tier,
        "hard_counters": hard, "counters": counter, "even": even,
        "unknown_count": unknown_count, "total": len(rows),
        "note": ("Opponent has no registered lane matchup evidence. Candidate lane picks "
                 "are not counter recommendations." if is_off_meta else
                 "Only manually approved current-patch matchup ratings can be recommended.")
    }
