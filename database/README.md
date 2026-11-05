# PICKOU database v1 — review gate

This directory adds a **separate** PostgreSQL schema `pickou`. It does not change the existing SQLite database, Google Sheet, or Supabase projects. The SQL file is **not yet applied to a live database**.

## Why these tables
- `champions`, `champion_lanes`, `matchups`: canonical ordered matchup roster (expected 173 / 266 / 14,468).
- `patches`, `patch_events`, `source_snapshots`: patch-level official sources and immutable evidence.
- `matches`, `match_participants`: collected match/timeline records.
- `matchup_statistics`: aggregated observations by patch/region/tier/ordered pair.
- `matchup_decisions`, `validation_history`, `review_queue`: separate judgements, approvals, and required rechecks.
- `composition_evidence`: reserved data model, not a completed scoring engine.

## Before applying
1. Create an **independent PICKOU Supabase project**, not one of the existing SD projects. Confirm any quoted new-project cost first.
2. Review `pickou_postgres_v1.sql` in a development database. Confirm Supabase Data API does **not** expose this schema.
3. Test schema compilation and foreign keys in a disposable empty database.
4. Make a Python seed importer from `data/lane_champions.json` using the existing SQLite aliases/initials. Run in a single transaction, idempotently; assert 173/266/14,468 counts. Do **not** invent matchup grades.
5. Run database security advisors, verify `anon` and `authenticated` cannot access the schema, and check that privileged server-only access works.
6. Add deployment migrations and DB integration tests; do not put privileged database credentials in frontend variables.

## Design boundaries
- `patch` is a human-facing version, while `ddragon_version` is a separate field.
- User-facing matchups must not treat missing decisions as 5:5.
- Stats and approvals are intentionally **append-only**: new rows supersede earlier evidence, rather than rewriting history.
- `tier_provenance` distinguishes observed ranked tier from an unverified collector label.
- Browser clients should use a backend API; do not expose database credentials or Riot API keys.
- Supabase is PostgreSQL, not a replacement for rate-limited Riot data collection workers.

## Known follow-ups
- The PostgreSQL model needs a verified SQLite-to-Postgres importer, migration tool, detailed performance profiling, and real integration testing.
- `matches` uses a human patch label reference; live server patch confirmation remains an independent workflow.
- If the full timeline/participant volume grows significantly, design retention/partitioning before bulk import.
- Draft review PR is schema-only. No live database was created or altered.
