BEGIN;
DO $block$
DECLARE t record;
BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'pickou' LOOP
  EXECUTE format('ALTER TABLE pickou.%I ENABLE ROW LEVEL SECURITY',t.tablename);
 END LOOP;
END $block$;
REVOKE ALL ON FUNCTION pickou.reject_evidence_mutation() FROM PUBLIC, anon, authenticated;
CREATE INDEX IF NOT EXISTS champion_lanes_champion_idx ON pickou.champion_lanes(champion);
CREATE INDEX IF NOT EXISTS matchups_opponent_lookup_idx ON pickou.matchups(lane,opponent);
CREATE INDEX IF NOT EXISTS source_snapshots_patch_idx ON pickou.source_snapshots(patch);
CREATE INDEX IF NOT EXISTS patch_events_source_digest_idx ON pickou.patch_events(source_digest);
CREATE INDEX IF NOT EXISTS matches_source_digest_idx ON pickou.matches(source_digest);
CREATE INDEX IF NOT EXISTS matchup_statistics_pair_idx ON pickou.matchup_statistics(lane,champion,opponent);
CREATE INDEX IF NOT EXISTS matchup_decisions_pair_idx ON pickou.matchup_decisions(lane,champion,opponent);
CREATE INDEX IF NOT EXISTS matchup_decisions_stat_idx ON pickou.matchup_decisions(statistic_id);
CREATE INDEX IF NOT EXISTS review_queue_pair_idx ON pickou.review_queue(lane,champion,opponent);
CREATE INDEX IF NOT EXISTS validation_history_decision_idx ON pickou.validation_history(decision_id);
CREATE INDEX IF NOT EXISTS composition_evidence_champion_idx ON pickou.composition_evidence(champion);
CREATE INDEX IF NOT EXISTS composition_evidence_patch_idx ON pickou.composition_evidence(patch);
CREATE INDEX IF NOT EXISTS import_runs_source_digest_idx ON pickou.import_runs(source_digest);
COMMIT;
