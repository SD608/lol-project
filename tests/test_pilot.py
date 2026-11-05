import copy
import io
import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from rift.database import connect,seed
from rift.discovery import discover,RiotClient
from rift.http import fetch_json,FetchError
from rift.matches import collect,TimelineUnavailable
from rift.pilot import pilot,save_report,empty_report,live_context
from rift.quality import quality,status
from rift.statistics import LANES,summarize
from rift.sheets import HEADERS,validate_mapping,update_plan

SECRET='TEST_ONLY_CREDENTIAL_SENTINEL'
ROLES=list(LANES)
def fixture(match_id='KR_1',version='16.22.1'):
    players=[{'participantId':i+1,'championId':i+1,'teamId':100 if i<5 else 200,'teamPosition':ROLES[i%5],'individualPosition':ROLES[i%5],'win':i<5,'puuid':'PRIVATE_PLAYER','summonerName':'PRIVATE_NAME'} for i in range(10)]
    info={'queueId':420,'mapId':11,'gameMode':'CLASSIC','gameVersion':version,'gameDuration':1200,'participants':players}
    frames=[{'timestamp':minute*60000,'participantFrames':{str(i):{'totalGold':1000+i*10,'minionsKilled':50+i,'jungleMinionsKilled':i,'xp':1500+i*10,'level':6} for i in range(1,11)}} for minute in (10,15)]
    return {'metadata':{'matchId':match_id},'info':info},{'metadata':{'matchId':match_id},'info':{'frames':frames}}
class FakeClient:
    def __init__(self,versions=None): self.events=Counter();self.urls=[];self.versions=versions or ['16.22.1','16.22.1']
    def __call__(self,url,headers=None):
        self.urls.append(url);self.events['responses_ok']+=1
        if '/entries/' in url:return [{'puuid':'PRIVATE_SEED'}]
        if '/by-puuid/' in url:return ['KR_1','KR_1','KR_2']
        match_id=url.split('/matches/')[1].split('/')[0]; index=int(match_id.split('_')[1])-1
        match,timeline=fixture(match_id,self.versions[index])
        return timeline if url.endswith('/timeline') else match

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'data').mkdir();self.db=connect(':memory:')
        self.lanes={lane:['C'+str(i+1),'C'+str(i+6)] for i,lane in enumerate(LANES.values())}
        (self.root/'data/lane_champions.json').write_text(json.dumps(self.lanes));seed(self.db,self.lanes)
        (self.root/'data/champion_ids.json').write_text(json.dumps({str(i):'C'+str(i) for i in range(1,11)}))
        self.env=patch.dict(os.environ,{'RIOT_API_KEY':SECRET});self.env.start()
    def tearDown(self): self.env.stop();self.db.close();self.tmp.cleanup()
    def test_discovery_routes_bounds_and_duplicate_ids(self):
        client=FakeClient();ids,context,report=discover(client)
        self.assertEqual(ids,['KR_1','KR_2']);self.assertEqual(report['duplicate_ids'],1)
        self.assertEqual(context['KR_1'],['EMERALD_I'])
        self.assertTrue(any('kr.api.riotgames.com/lol/league/' in u for u in client.urls))
        self.assertTrue(any('asia.api.riotgames.com/lol/match/' in u and 'queue=420' in u for u in client.urls))
        with self.assertRaises(ValueError): discover(client,max_seeds=100)
        self.assertNotIn('PRIVATE_SEED',json.dumps(report))
    def test_match_extraction_directional_and_no_duplicate_aggregation(self):
        client=FakeClient();self.assertTrue(collect(self.db,'KR_1','KR','UNSPECIFIED',fetch=client))
        self.assertFalse(collect(self.db,'KR_1','KR','UNSPECIFIED',fetch=client))
        groups=summarize(self.db,{str(i):'C'+str(i) for i in range(1,11)})
        self.assertEqual(len(groups),10);self.assertTrue(all(g['sample_size']==1 for g in groups))
        a=next(g for g in groups if g['key'][2]=='C1');b=next(g for g in groups if g['key'][2]=='C6')
        self.assertEqual(a['metrics']['gold_diff_15']['mean'],-b['metrics']['gold_diff_15']['mean'])
        self.assertEqual(a['metrics']['cs_diff_10']['mean'],-10)
        self.assertIsNone(a['metrics']['lane_rating']);self.assertEqual(status(a),'insufficient_sample')
    def test_role_disagreement_and_duplicate_team_role_excluded(self):
        client=FakeClient();collect(self.db,'KR_1','KR','UNKNOWN',fetch=client)
        payload=json.loads(self.db.execute('SELECT payload FROM matches').fetchone()[0]);self.assertTrue(quality(payload)['valid'])
        payload['participants'][0]['individualPosition']='MIDDLE';self.assertIn('role_disagreement_or_swap',quality(payload)['role_flags'])
        payload['participants'][0]['teamPosition']='MIDDLE';self.assertIn('ambiguous_roles',quality(payload)['role_flags'])
    def test_missing_frames_not_zero_imputed(self):
        match,timeline=fixture();timeline['info']['frames']=timeline['info']['frames'][:1]
        collect(self.db,'KR_1','KR','UNKNOWN',fetch=lambda u,**kw:timeline if u.endswith('/timeline') else match)
        payload=json.loads(self.db.execute('SELECT payload FROM matches').fetchone()[0]);self.assertEqual(quality(payload)['missing_timeline_minutes'],[15])
        groups=summarize(self.db,{str(i):'C'+str(i) for i in range(1,11)})
        self.assertNotIn('gold_diff_15',groups[0]['metrics'])
    def test_timeline_request_failure_preserves_existing_database(self):
        collect(self.db,'KR_1','KR','UNKNOWN',fetch=FakeClient())
        before=self.db.execute('SELECT * FROM matches').fetchall();match,timeline=fixture('KR_2')
        def fetch(u,**k):
            if u.endswith('/timeline'):raise FetchError(SECRET)
            return match
        with self.assertRaises(TimelineUnavailable) as error:collect(self.db,'KR_2','KR','UNKNOWN',fetch=fetch)
        self.assertNotIn(SECRET,str(error.exception));self.assertEqual(before,self.db.execute('SELECT * FROM matches').fetchall())
    def test_pilot_partition_and_simulation_not_live_success(self):
        report=pilot(self.db,self.root,FakeClient(['16.21.1','16.22.1']),target=2,origin='test_fixture')
        self.assertEqual(report['valid_matches'],2);self.assertEqual(report['patch_counts'],{'26.21':1,'26.22':1})
        self.assertEqual(len(report['matchups']),20);self.assertEqual(report['verified_matchups'],0)
        self.assertFalse(report['actual_api_success']);self.assertEqual(report['examples'],[])
        self.assertTrue(all('UNKNOWN_AT_MATCH' in g['key'][5] for g in report['matchups']))
        save_report(self.root,report)
        raw=(self.root/'reports/collection/latest.json').read_text()
        for value in (SECRET,'PRIVATE_SEED','PRIVATE_PLAYER','PRIVATE_NAME'):self.assertNotIn(value,raw)
        self.assertIn('통계 예시 없음',(self.root/'reports/collection/latest.md').read_text())
        dbraw=str(self.db.execute('SELECT * FROM matches').fetchall());self.assertNotIn('PRIVATE_PLAYER',dbraw)
    def test_status_lifecycle_never_assigns_grade(self):
        g={'key':('26.22','탑','A','B','KR','UNKNOWN_AT_MATCH'),'sample_size':100,'sources':['KR_1'],'metrics':{f'{m}_diff_{t}':{'mean':0,'sample_size':100} for m in ('gold','cs','xp') for t in (10,15)}}
        self.assertEqual(status(g),'evidence_pending')
        self.assertEqual(status(g,{'skill_interactions':['verified source'],'power_spikes':['level6']}),'auto_checked')
        g['metrics']['xp_diff_15']['sample_size']=99;self.assertEqual(status(g),'insufficient_sample')
    def test_riot_client_key_missing_and_host_guard(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'RIOT_API_KEY missing'):RiotClient()
        with self.assertRaises(ValueError):RiotClient()('https://attacker.example')
    def test_http_retry_observation_redaction(self):
        from urllib.error import HTTPError
        attempts=[];events=Counter()
        def opener(*a,**k):
            attempts.append(1)
            if len(attempts)==1:raise HTTPError('url',429,SECRET,{'Retry-After':'2'},None)
            return io.StringIO('{}')
        self.assertEqual(fetch_json('https://example.org',opener=opener,sleep=lambda n:None,observer=lambda e:events.update([e])),{})
        self.assertEqual(events['requests'],2);self.assertEqual(events['http_429'],1)
        self.assertNotIn(SECRET,str(events))
    def test_sheet_mapping_and_safe_plan(self):
        payload={'spreadsheet_id':'id','sheets':{lane:{'header':HEADERS,'sheetId':i,'rows':[[a,b] for a in names for b in names if a!=b]} for i,(lane,names) in enumerate(self.lanes.items())}}
        mapping=validate_mapping(self.db,payload,self.lanes);self.assertTrue(mapping['valid'])
        group={'key':('26.22','탑','C1','C6','KR','UNKNOWN'),'sample_size':1,'metrics':{'game_win_rate':1}}
        plan=update_plan([group],mapping);self.assertFalse(plan['write_enabled']);self.assertEqual(len(plan['proposals']),1)
        self.assertTrue(plan['proposals'][0]['separate_patch_destination_required'])
        self.assertTrue(all('!D' not in c and '!E' not in c for c in plan['proposals'][0]['cells']))
        payload['sheets']['탑']['rows'].append(['C1','C6']);self.assertFalse(validate_mapping(self.db,payload,self.lanes)['valid'])
    def test_missing_key_cli_writes_truthful_report_without_database_change(self):
        from scripts.run_pilot import main
        path=self.root/'data/patch_state.json';path.write_text('{"public_patch":"26.22"}');before=path.read_bytes()
        with patch.dict(os.environ,{},clear=True),patch('sys.argv',['run_pilot','--root',str(self.root)]):self.assertEqual(main(),2)
        report=json.loads((self.root/'reports/collection/latest.json').read_text())
        self.assertEqual(report['status'],'key_missing');self.assertFalse(report['actual_api_success']);self.assertEqual(report['examples'],[])
        self.assertEqual(path.read_bytes(),before);self.assertFalse((self.root/'data/rift.sqlite3').exists())
    def test_live_target_requires_fresh_official_regional_evidence(self):
        (self.root/'data/patch_state.json').write_text('{"public_patch":"26.22"}')
        (self.root/'reports').mkdir();report={'patch':'26.22','release_status':'pending','live_url':None}
        (self.root/'reports/official_latest.json').write_text(json.dumps(report))
        self.assertIsNone(live_context(self.root)['official_latest_live_patch'])
    def test_invalid_roles_are_preserved_but_pilot_excludes_them(self):
        class RoleClient(FakeClient):
            def __call__(self,url,headers=None):
                obj=super().__call__(url,headers)
                if isinstance(obj,dict) and 'participants' in obj.get('info',{}):obj['info']['participants'][0]['teamPosition']='MIDDLE'
                return obj
        report=pilot(self.db,self.root,RoleClient(),target=2,origin='test_fixture')
        self.assertEqual(report['role_flagged_matches'],2);self.assertEqual(report['valid_matches'],0)
        self.assertEqual(report['matchups'],[]);self.assertEqual(self.db.execute('SELECT count(*) FROM matches').fetchone()[0],2)
    def test_repeat_pilot_does_not_duplicate_statistic_samples(self):
        first=pilot(self.db,self.root,FakeClient(),target=2,origin='test_fixture')
        count=self.db.execute('SELECT count(*) FROM statistics').fetchone()[0]
        second=pilot(self.db,self.root,FakeClient(),target=2,origin='test_fixture')
        self.assertEqual(second['collected_matches'],0);self.assertGreaterEqual(second['duplicate_matches'],2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM statistics').fetchone()[0],count)
        self.assertTrue(all(g['sample_size']==2 for g in second['matchups']))
    def test_confirmed_patch_excludes_old_games_without_deletion(self):
        import datetime as dt
        (self.root/'data/patch_state.json').write_text('{"public_patch":"26.22"}')
        (self.root/'reports').mkdir()
        report={'patch':'26.22','release_status':'confirmed','live_url':'https://www.leagueoflegends.com/ko-kr/news/notices/complete/','checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
        path=self.root/'reports/official_latest.json';path.write_text(json.dumps(report));before=path.read_bytes()
        r=pilot(self.db,self.root,FakeClient(['16.21.1','16.22.1']),target=2,origin='test_fixture')
        self.assertEqual(r['valid_matches'],1);self.assertEqual(r['errors']['other_patch_preserved_excluded_from_target'],1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM matches').fetchone()[0],2)
        self.assertTrue(all(g['key'][0]=='26.22' for g in r['matchups']));self.assertEqual(path.read_bytes(),before)
        report['live_url']='https://attacker.example';path.write_text(json.dumps(report))
        self.assertIsNone(live_context(self.root)['official_latest_live_patch'])
    def test_invalid_numeric_timeline_values_stay_missing(self):
        match,timeline=fixture();timeline['info']['frames'][1]['participantFrames']['1']['totalGold']='bad'
        collect(self.db,'KR_1','KR','UNKNOWN',fetch=lambda u,**k:timeline if u.endswith('/timeline') else match)
        groups=summarize(self.db,{str(i):'C'+str(i) for i in range(1,11)})
        group=next(g for g in groups if g['key'][2]=='C1');self.assertNotIn('gold_diff_15',group['metrics'])
    def test_riot_503_and_date_retry_after_with_no_secret_logging(self):
        import datetime as dt
        from email.utils import format_datetime
        from urllib.error import HTTPError
        events=Counter();waits=[]
        retry=format_datetime(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=20),usegmt=True)
        def opener(*a,**k):raise HTTPError('private-url',503,SECRET,{'Retry-After':retry},None)
        with self.assertRaises(FetchError) as ctx:fetch_json('https://example.org',opener=opener,attempts=2,sleep=waits.append,observer=lambda e:events.update([e]))
        self.assertGreater(waits[0],10);self.assertEqual(events['http_503'],2);self.assertNotIn(SECRET,str(ctx.exception))
    def test_report_has_explicit_zero_api_counters(self):
        report=empty_report();report['status']='key_missing';save_report(self.root,report)
        stored=json.loads((self.root/'reports/collection/latest.json').read_text())
        self.assertEqual(stored['api_requests'],0);self.assertEqual(stored['api_error_count'],0);self.assertEqual(stored['api_limit_events'],0)
        self.assertEqual(stored['unverified_reasons'],['no_actual_samples'])
