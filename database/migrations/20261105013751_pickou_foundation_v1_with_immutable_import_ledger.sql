-- PICKOU PostgreSQL foundation (review before applying).
-- Isolated, non-exposed schema. No DROP, TRUNCATE, or changes to existing public tables.
BEGIN;
CREATE SCHEMA IF NOT EXISTS pickou;
REVOKE ALL ON SCHEMA pickou FROM PUBLIC, anon, authenticated;
CREATE TABLE IF NOT EXISTS pickou.champions (
  name text PRIMARY KEY,
  riot_id text UNIQUE,
  aliases text[] NOT NULL DEFAULT '{}',
  initials text NOT NULL DEFAULT '',
  image_url text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pickou.champion_lanes (
  lane text NOT NULL CHECK (lane IN ('탑','정글','미드','바텀','서폿')),
  champion text NOT NULL REFERENCES pickou.champions(name),
  PRIMARY KEY (lane, champion)
);
CREATE TABLE IF NOT EXISTS pickou.matchups (
  lane text NOT NULL,
  champion text NOT NULL,
  opponent text NOT NULL,
  PRIMARY KEY (lane, champion, opponent),
  FOREIGN KEY (lane, champion) REFERENCES pickou.champion_lanes(lane, champion),
  FOREIGN KEY (lane, opponent) REFERENCES pickou.champion_lanes(lane, champion),
  CHECK (champion <> opponent)
);
CREATE TABLE IF NOT EXISTS pickou.patches (
  patch text PRIMARY KEY,
  ddragon_version text,
  region text NOT NULL DEFAULT 'KR',
  release_status text NOT NULL DEFAULT 'pending'
    CHECK (release_status IN ('pending','confirmed','superseded')),
  official_notes_url text,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pickou.source_snapshots (
  digest text PRIMARY KEY,
  source_uri text NOT NULL,
  source_type text NOT NULL,
  patch text REFERENCES pickou.patches(patch),
  payload jsonb NOT NULL,
  captured_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pickou.patch_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patch text REFERENCES pickou.patches(patch),
  ddragon_version text,
  category text NOT NULL CHECK (category IN ('champion','item','rune','system','article','release')),
  target_id text,
  change_detail jsonb NOT NULL DEFAULT '{}',
  source_digest text REFERENCES pickou.source_snapshots(digest),
  verification_status text NOT NULL DEFAULT 'pending',
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS patch_events_patch_idx ON pickou.patch_events(patch,category);
CREATE TABLE IF NOT EXISTS pickou.matches (
  match_id text PRIMARY KEY,
  patch text NOT NULL REFERENCES pickou.patches(patch),
  region text NOT NULL,
  queue_id integer,
  tier_label text NOT NULL DEFAULT 'UNSPECIFIED',
  tier_provenance text NOT NULL DEFAULT 'unknown',
  duration_seconds integer CHECK (duration_seconds >= 0),
  started_at timestamptz,
  source_digest text REFERENCES pickou.source_snapshots(digest),
  ingested_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS matches_patch_region_idx ON pickou.matches(patch,region);
CREATE TABLE IF NOT EXISTS pickou.match_participants (
  match_id text NOT NULL REFERENCES pickou.matches(match_id),
  participant_id smallint NOT NULL CHECK (participant_id BETWEEN 1 AND 10),
  champion text NOT NULL REFERENCES pickou.champions(name),
  lane text CHECK (lane IN ('탑','정글','미드','바텀','서폿')),
  team_id smallint NOT NULL,
  win boolean NOT NULL,
  timeline_10 jsonb,
  timeline_15 jsonb,
  lane_verified boolean NOT NULL DEFAULT false,
  PRIMARY KEY(match_id,participant_id)
);
CREATE INDEX IF NOT EXISTS participants_champion_idx ON pickou.match_participants(champion,lane);
CREATE TABLE IF NOT EXISTS pickou.matchup_statistics (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patch text NOT NULL REFERENCES pickou.patches(patch),
  lane text NOT NULL,
  champion text NOT NULL,
  opponent text NOT NULL,
  region text NOT NULL,
  tier text NOT NULL,
  sample_size integer NOT NULL CHECK (sample_size >= 0),
  metrics jsonb NOT NULL DEFAULT '{}',
  confidence_intervals jsonb NOT NULL DEFAULT '{}',
  sources jsonb NOT NULL DEFAULT '[]',
  calculated_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (lane,champion,opponent) REFERENCES pickou.matchups(lane,champion,opponent)
);
CREATE INDEX IF NOT EXISTS matchup_stats_lookup_idx ON pickou.matchup_statistics(patch,lane,champion,opponent,region,tier,calculated_at DESC);
CREATE TABLE IF NOT EXISTS pickou.matchup_decisions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patch text NOT NULL REFERENCES pickou.patches(patch),
  lane text NOT NULL,
  champion text NOT NULL,
  opponent text NOT NULL,
  region text NOT NULL,
  tier text NOT NULL,
  rating text CHECK(rating IN ('9:1','8:2','7:3','6:4','5:5','4:6','3:7','2:8','1:9')),
  status text NOT NULL DEFAULT 'unverified'
    CHECK(status IN ('unverified','pending','auto_checked','manual_approved','rejected')),
  evidence jsonb NOT NULL DEFAULT '{}',
  statistic_id bigint REFERENCES pickou.matchup_statistics(id),
  reviewer text,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (lane,champion,opponent) REFERENCES pickou.matchups(lane,champion,opponent),
  CHECK(status <> 'manual_approved' OR (rating IS NOT NULL AND nullif(trim(reviewer),'') IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS matchup_decisions_lookup_idx ON pickou.matchup_decisions(patch,lane,champion,opponent,region,tier,created_at DESC);
CREATE TABLE IF NOT EXISTS pickou.validation_history (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  decision_id bigint NOT NULL REFERENCES pickou.matchup_decisions(id),
  event text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pickou.review_queue (
  patch text NOT NULL REFERENCES pickou.patches(patch),
  lane text NOT NULL,
  champion text NOT NULL,
  opponent text NOT NULL,
  region text NOT NULL DEFAULT 'KR',
  tier text NOT NULL DEFAULT 'UNSPECIFIED',
  reason text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(patch,lane,champion,opponent,region,tier),
  FOREIGN KEY (lane,champion,opponent) REFERENCES pickou.matchups(lane,champion,opponent)
);
CREATE TABLE IF NOT EXISTS pickou.composition_evidence (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  patch text NOT NULL REFERENCES pickou.patches(patch),
  champion text NOT NULL REFERENCES pickou.champions(name),
  phase text NOT NULL CHECK(phase IN ('early','mid','late')),
  dimensions jsonb NOT NULL DEFAULT '{}',
  source_uri text,
  status text NOT NULL DEFAULT 'unverified',
  created_at timestamptz NOT NULL DEFAULT now()
);
-- Source evidence and decisions are immutable; new observations are inserted as new rows.
CREATE OR REPLACE FUNCTION pickou.reject_evidence_mutation()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN RAISE EXCEPTION 'PICKOU evidence is append-only: %', TG_TABLE_NAME; END
$$;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['source_snapshots','patch_events','matches','match_participants','matchup_statistics','matchup_decisions','validation_history','composition_evidence']
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS prevent_evidence_mutation ON pickou.%I',t);
    EXECUTE format('CREATE TRIGGER prevent_evidence_mutation BEFORE UPDATE OR DELETE ON pickou.%I FOR EACH ROW EXECUTE FUNCTION pickou.reject_evidence_mutation()',t);
  END LOOP;
END $$;
-- Explicitly deny frontend roles; backend uses a separately privileged connection.
REVOKE ALL ON ALL TABLES IN SCHEMA pickou FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA pickou FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA pickou REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA pickou REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
-- Immutable import ledger for provenance and repeatability.
CREATE TABLE IF NOT EXISTS pickou.import_runs (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_uri text NOT NULL,
 source_revision text NOT NULL,
 source_digest text NOT NULL REFERENCES pickou.source_snapshots(digest),
 champions_count integer NOT NULL CHECK(champions_count>=0),
 lanes_count integer NOT NULL CHECK(lanes_count>=0),
 matchups_count integer NOT NULL CHECK(matchups_count>=0),
 validation jsonb NOT NULL DEFAULT '{}'::jsonb,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(source_uri,source_revision)
);
CREATE TRIGGER prevent_evidence_mutation BEFORE UPDATE OR DELETE ON pickou.import_runs
 FOR EACH ROW EXECUTE FUNCTION pickou.reject_evidence_mutation();
REVOKE ALL ON pickou.import_runs FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE pickou.import_runs_id_seq FROM PUBLIC, anon, authenticated;
-- Guard against future accidental API role grants; keep server access only.
REVOKE USAGE ON SCHEMA pickou FROM PUBLIC, anon, authenticated;
COMMIT;
