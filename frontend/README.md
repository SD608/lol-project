# PICKOU frontend — stage 5

Minimal monochrome responsive UI using Next.js App Router. Designed from the approved black-and-white wireframe.

## Local run

From `frontend/`:

```bash
npm install
cp .env.example .env.local
npm run dev
```

On Windows PowerShell, copy with `Copy-Item .env.example .env.local`.

Run FastAPI locally at http://127.0.0.1:8000 with `CORS_ORIGINS=http://localhost:3000` and a **server-only** `DATABASE_URL`. Open http://localhost:3000.

Only `NEXT_PUBLIC_API_BASE_URL` (public backend URL) is available to browser code. Never put database credentials, Supabase service keys, or Riot API secrets into a `NEXT_PUBLIC_*` variable.

## Scope

- Responsive desktop sidebar + brand-only header; tablet compact top navigation; mobile hamburger drawer.
- Champion, opponent and lane selectors; matchup lookup with actual read-only FastAPI.
- Displays `검증 대기` for missing/unapproved matchup ratings, and distinguishes network errors from unknown data.
- Other navigation tabs are labeled **준비 중**, not falsely represented as implemented.
- This is a frontend feature branch. No production deployment or real Riot API statistics are implied.

## Tests / verification to complete

- `npm run build`; responsive browser checks at 390, 820, and 1440px.
- Local integration check against the real FastAPI /api/v1 endpoints.
- Accessibility keyboard testing and CORS checks.

Existing backend and PostgreSQL are not modified by this frontend branch.
