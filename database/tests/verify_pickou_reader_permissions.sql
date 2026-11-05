-- SQL-only live authorization check, PICKOU project yspqfkcexibucnwvxdmw.
-- Run as postgres with permission to grant this role. Does not retain membership or mutate rows.
-- The elevated SET option below is transactional and rolled back.\n-- Supabase may retain a pre-existing ADMIN-only creator membership (SET FALSE / INHERIT FALSE).
BEGIN;
GRANT pickou_api_reader TO postgres WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;
SET LOCAL ROLE pickou_api_reader;
DO $verify$
DECLARE n bigint;
BEGIN
 IF current_user <> 'pickou_api_reader' THEN RAISE EXCEPTION 'Role did not switch'; END IF;
 SELECT count(*) INTO n FROM pickou.champions;
 IF n<>173 THEN RAISE EXCEPTION 'Champion count mismatch %',n; END IF;
 SELECT count(*) INTO n FROM pickou.champion_lanes;
 IF n<>266 THEN RAISE EXCEPTION 'Lane count mismatch %',n; END IF;
 SELECT count(*) INTO n FROM pickou.matchups;
 IF n<>14468 THEN RAISE EXCEPTION 'Matchup count mismatch %',n; END IF;
 SELECT count(*) INTO n FROM pickou.matchups WHERE lane='탑' AND champion='우르곳';
 IF n<>64 THEN RAISE EXCEPTION 'Top Urgot matchup count mismatch %',n; END IF;
 SELECT count(*) INTO n FROM (SELECT opponent FROM pickou.matchups WHERE lane='탑' AND champion='우르곳' ORDER BY opponent LIMIT 10) page;
 IF n<>10 THEN RAISE EXCEPTION 'Page length mismatch'; END IF;
 SELECT count(*) INTO n FROM pickou.patches;
 IF n<>0 THEN RAISE EXCEPTION 'Patches should be empty'; END IF;
 IF has_table_privilege(current_user,'pickou.import_runs','SELECT') THEN RAISE EXCEPTION 'Import runs exposed'; END IF;
 IF has_table_privilege(current_user,'pickou.champions','INSERT') OR has_table_privilege(current_user,'pickou.champions','UPDATE') OR has_table_privilege(current_user,'pickou.champions','DELETE') THEN RAISE EXCEPTION 'Writable reader'; END IF;
 -- Planning forbidden DML with EXPLAIN does not execute/mutate it.
 BEGIN
  EXECUTE 'EXPLAIN INSERT INTO pickou.champions(name) VALUES (''__pickou_security_probe__'')';
  RAISE EXCEPTION 'INSERT was allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
 BEGIN
  EXECUTE 'EXPLAIN UPDATE pickou.champions SET initials = ''X'' WHERE name = ''__pickou_security_probe__''';
  RAISE EXCEPTION 'UPDATE was allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
 BEGIN
  EXECUTE 'EXPLAIN DELETE FROM pickou.champions WHERE name = ''__pickou_security_probe__''';
  RAISE EXCEPTION 'DELETE was allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $verify$;
RESET ROLE;
ROLLBACK;
