# PICKOU FastAPI — stage 4

Seven **read-only** endpoints are mounted under `/api/v1`. OpenAPI: `/openapi.json`, interactive docs: `/docs`. Uses asyncpg connection pool managed by FastAPI lifespan. The existing SQLite collector, Google Sheets and PostgreSQL rows are not modified. Named champion IDs use URL-encoded Korean canonical names. Matchup IDs are unpadded URL-safe base64 of a JSON array `[lane, champion, opponent]`; get them from `/matchups`, do not construct them manually.

## Local development

From repository root, Python 3.12:

```bash
python -m pip install -r backend/requirements.txt
# Copy backend/.env.example to a private environment manager, then provide DATABASE_URL
export DATABASE_URL='postgresql://pickou_api_reader:...@POOLER_HOST:5432/postgres?ssl=require'
export CORS_ORIGINS='https://your-frontend.example'
uvicorn backend.main:app --reload
python -m pytest -q tests/test_backend.py
python -m unittest discover -s tests -v
```

Run the backend inside a locked-down environment. Docker from repository root: `docker build -f backend/Dockerfile -t pickou-api .` then `docker run --env-file ./private.env -p 8000:8000 pickou-api`.

A deliberately **absent** `DATABASE_URL` allows OpenAPI-only boot; real data endpoints return 503. Startup fails if an explicitly configured database is unreachable (fail closed). The health endpoint performs a real DB query; it is not a fabricated healthy status.

## Access / security contract

- Use a separate PostgreSQL login with `CONNECT`, `USAGE ON SCHEMA pickou`, and `SELECT` only on needed read tables. Provision credentials out of band through Supabase dashboard/secure secrets. Do not use `postgres` owner or service-role tokens as a browser credential.
- On the PostgreSQL side, enabled RLS with no policies blocks ordinary non-bypass roles, including a new reader. Have an administrator review and install **narrow SELECT-only policies TO pickou_api_reader** as a separately reviewed migration, or use a controlled server-only role with explicit justified bypass RLS. **Do not grant anon or authenticated schema usage.** Current reader provisioning and real credential connectivity are NOT complete.
- Parameterized `$1` SQL, query limits 1–200, validated IDs and patch input. CORS from `CORS_ORIGINS` only, no wildcard. No write routes.
- `unknown` is never coerced into `5:5`; list ratings always unknown. Detail only uses the same confirmed patch, region and tier; only manually approved decision ratings are surfaced as verified. Stats, decisions and evidence remain separate. A patch with no confirmed entry yields unknown.

## Caveats / next gates

The PostgreSQL roster currently has empty stored aliases/initials. GET /champions merges existing `rift.database.ALIASES` and `initials` at read time, without database mutation. No real backend DB credentials are configured by this repository; integration requiring the actual database must be run with a read-only credential in a secure runner. GitHub Actions offline tests do **not** substitute for real PostgreSQL integration. Do not add secrets to Actions logs or repository files.
