-- PICKOU project yspqfkcexibucnwvxdmw ONLY.
-- Applied live via Supabase migration 20261105020903.
-- The LOGIN role deliberately has PASSWORD NULL: provision a unique password only
-- through a secure deployment/secret-management path, not through Git history.
-- Does not alter existing rows, public schema, or other projects.
BEGIN;
DO $create$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='pickou_api_reader') THEN
   RAISE EXCEPTION 'pickou_api_reader already exists; manual review required';
 END IF;
 CREATE ROLE pickou_api_reader WITH LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD NULL CONNECTION LIMIT 5;
END $create$;
GRANT CONNECT ON DATABASE postgres TO pickou_api_reader;
GRANT USAGE ON SCHEMA pickou TO pickou_api_reader;
GRANT SELECT ON pickou.champions,pickou.champion_lanes,pickou.matchups,pickou.patches,pickou.matchup_statistics,pickou.matchup_decisions,pickou.validation_history TO pickou_api_reader;
CREATE POLICY pickou_api_reader_select ON pickou.champions FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.champion_lanes FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.matchups FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.patches FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.matchup_statistics FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.matchup_decisions FOR SELECT TO pickou_api_reader USING (true);
CREATE POLICY pickou_api_reader_select ON pickou.validation_history FOR SELECT TO pickou_api_reader USING (true);
REVOKE ALL ON SCHEMA pickou FROM PUBLIC,anon,authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA pickou FROM PUBLIC,anon,authenticated;
COMMIT;
