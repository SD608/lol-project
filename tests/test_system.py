import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from rift.database import connect, seed, search, snapshot, enqueue
from rift.http import fetch_json, FetchError
from rift.validation import assess, wilson, composition, phase
from rift.patches import confirm_release, impact
from rift.matches import collect
from scripts.check_patch import main, changed_runes, patch_label

ROOT=Path(__file__).resolve().parents[1]
class SystemTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(':memory:')
        self.lanes=json.loads((ROOT/'data/lane_champions.json').read_text())
    def tearDown(self): self.db.close()
    def test_roster_and_idempotence(self):
        expected={'champions':173,'lane_champions':266,'matchups':14468}
        self.assertEqual(seed(self.db,self.lanes),expected)
        self.assertEqual(seed(self.db,self.lanes),expected)
        self.assertEqual({k:len(v) for k,v in self.lanes.items()},{'탑':65,'정글':56,'미드':62,'바텀':35,'서폿':48})
    def test_alias_and_initial_search(self):
        seed(self.db,self.lanes)
        self.assertIn('징크스',search(self.db,'징키'))
        self.assertIn('미스 포츈',search(self.db,'ㅁㅅㅍㅊ'))
    def test_immutable_source_and_decision(self):
        snapshot(self.db,'sheet',{'rating':'7:3'})
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute('DELETE FROM snapshots')
        self.db.execute("INSERT INTO decisions(patch,lane,champion,opponent,region,tier,rating,status,evidence,reviewer) VALUES('26.21','탑','가렌','잭스','KR','EMERALD','7:3','manual_approved','{}','reviewer')")
        enqueue(self.db,[{'패치':'26.22','라인':'탑','내 챔피언':'가렌','상대 챔피언':'잭스','재검증 이유':'patch'}])
        self.assertEqual(self.db.execute('SELECT rating,patch FROM decisions').fetchone(),('7:3','26.21'))
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("UPDATE decisions SET rating='5:5'")
    def test_evidence_gate(self):
        self.assertIsNone(assess({})['rating'])
        evidence=dict(skill_interactions=['source'],power_spikes=['level6'],sources=['official'],patch='26.21',region='KR',tier='EMERALD',sample_size=100,metrics={f'{m}_diff_{t}':0 for m in ('gold','cs','xp') for t in (10,15)})
        self.assertEqual(assess(evidence)['status'],'auto_checked')
        evidence['conflicting_statistics']=True
        self.assertEqual(assess(evidence)['status'],'pending')
    def test_intervals(self):
        lo,hi=wilson(50,100)
        self.assertLess(lo,.5); self.assertGreater(hi,.5)
        with self.assertRaises(ValueError): wilson(0,0)
    def test_composition_unverified(self):
        self.assertIsNone(composition(list('abcde'),list('fghij'))['phases']['early']['score'])
        self.assertEqual([phase(x) for x in (899,900,1799,1800)],['early','mid','mid','late'])
    def test_release_requires_both(self):
        notes={'patch':'26.22','url':'https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-22-notes/','checked_at':'now','content_digest':'digest'}
        live={**notes,'region':'KR','applied':True}
        self.assertEqual(confirm_release('26.22','KR',notes,live)['status'],'confirmed')
        self.assertEqual(confirm_release('26.22','NA',notes,live)['status'],'pending')
        self.assertEqual(confirm_release('26.22','KR',{},live)['status'],'pending')
    def test_item_rune_dependency_fallback(self):
        lanes={'탑':['A','B','C']}
        self.assertEqual(len(impact(lanes,[],['1'],[],{'items':{'1':['A']}})),4)
        self.assertEqual(len(impact(lanes,[],[],['2'])),6)
        self.assertEqual(len(changed_runes([], [{'slots':[{'runes':[{'id':1,'name':'r'}]}]}])),1)
    def test_retries_and_redacted_errors(self):
        calls=[]
        def opener(*args,**kwargs):
            calls.append(1)
            if len(calls)<3: raise HTTPError('secret',429,'secret',{'Retry-After':'3'},None)
            return io.StringIO('{"ok":true}')
        delays=[]
        self.assertEqual(fetch_json('https://example.com',opener=opener,sleep=delays.append),{'ok':True})
        self.assertTrue(all(d>=3 for d in delays))
        for code in (403,500):
            with self.assertRaises(FetchError) as ctx:
                fetch_json('https://example.com',opener=lambda *a,**k: (_ for _ in ()).throw(HTTPError('secret',code,'secret',{},None)),sleep=lambda _:None)
            self.assertNotIn('secret',str(ctx.exception))
    def test_match_duplicate_and_no_personal_fields(self):
        match={'metadata':{'matchId':'KR_1'},'info':{'queueId':420,'mapId':11,'gameVersion':'16.21.1','gameDuration':1200,'participants':[{'participantId':1,'puuid':'SECRET','summonerName':'SECRET','championId':1}]}}
        timeline={'metadata':{'matchId':'KR_1'},'info':{'frames':[]}}
        with patch.dict(os.environ,{'RIOT_API_KEY':'SECRET'}):
            fetch=lambda url,**k: timeline if url.endswith('/timeline') else match
            self.assertTrue(collect(self.db,'KR_1','KR','UNKNOWN',fetch))
            self.assertFalse(collect(self.db,'KR_1','KR','UNKNOWN',lambda *a,**k: self.fail('duplicate network request')))
        self.assertNotIn('SECRET',self.db.execute('SELECT payload FROM matches').fetchone()[0])
    def test_network_failure_preserves_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir()
            state=root/'data/patch_state.json'; state.write_text('{"ddragon_version":"16.21.1"}')
            old=state.read_bytes()
            with patch('sys.argv',['check_patch','--root',tmp]),patch('scripts.check_patch.fetch_json',side_effect=FetchError('network')):
                with self.assertRaises(FetchError): main()
            self.assertEqual(state.read_bytes(),old)
    def test_new_patch_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir()
            (root/'data/patch_state.json').write_text('{"ddragon_version":"16.21.1"}')
            (root/'data/lane_champions.json').write_text(json.dumps({'탑':['가렌','잭스']}))
            def fetch(url):
                if url.endswith('versions.json'): return ['16.22.1']
                if url.endswith('runesReforged.json'): return []
                if url.endswith('item.json'): return {'data':{}}
                return {'data':{'Garen':{'name':'가렌','stats':{'hp':2 if '16.22' in url else 1}}}}
            with patch('sys.argv',['check_patch','--root',tmp]),patch('scripts.check_patch.fetch_json',side_effect=fetch): main()
            report=json.loads((root/'reports/latest.json').read_text())
            self.assertEqual(report['affected_directed_matchups'],2)
            self.assertFalse(report['ratings_changed'])
            self.assertTrue((root/'reports/history/16.21.1-to-16.22.1.json').exists())
    def test_historic_patch_label(self): self.assertEqual(patch_label('14.24.1'),'14.24')

class IntegrationSafetyTests(unittest.TestCase):
    def test_sheet_mapping_preserves_original(self):
        from rift.sheets import HEADERS,import_values
        db=connect(':memory:')
        values=[HEADERS,['A','B','legacy','7:3'],['B','A','legacy']]
        result=import_values(db,'id','탑',values,{'탑':['A','B']})
        self.assertTrue(result['complete']); self.assertFalse(result['write_enabled'])
        self.assertEqual(json.loads(db.execute('SELECT payload FROM snapshots').fetchone()[0]),values)
        self.assertEqual(db.execute('SELECT count(*) FROM decisions').fetchone()[0],0)
        with self.assertRaises(ValueError): import_values(db,'id','탑',[['wrong']],{'탑':['A','B']})
        db.close()
    def test_pair_statistics(self):
        from rift.statistics import summarize
        db=connect(':memory:')
        ps=[{'participantId':1,'championId':1,'teamId':100,'teamPosition':'TOP','win':True},{'participantId':2,'championId':2,'teamId':200,'teamPosition':'TOP','win':False}]
        frames={str(t):{'1':{'totalGold':2000,'xp':1500,'level':5,'minionsKilled':60,'jungleMinionsKilled':2},'2':{'totalGold':1800,'xp':1400,'level':5,'minionsKilled':50,'jungleMinionsKilled':0}} for t in (10,15)}
        db.execute('INSERT INTO matches VALUES(?,?,?,?,?)',('KR_1','26.21','KR','UNKNOWN',json.dumps({'participants':ps,'frames':frames})))
        groups=summarize(db,{'1':'A','2':'B'})
        self.assertEqual(len(groups),2)
        self.assertEqual(groups[0]['metrics']['gold_diff_15']['mean'],200)
        self.assertEqual(groups[1]['metrics']['gold_diff_15']['mean'],-200)
        self.assertIsNone(groups[0]['metrics']['gold_diff_15']['ci95_normal'])
        self.assertIsNone(groups[0]['metrics']['lane_rating'])
        db.close()
    def test_approval_requires_persisted_sample(self):
        from rift.database import approve,record_statistics
        db=connect(':memory:')
        group={'key':('26.21','탑','A','B','KR','EMERALD'),'sample_size':100,'metrics':{f'{m}_diff_{t}':{'mean':0,'sample_size':100} for m in ('gold','cs','xp') for t in (10,15)},'sources':['KR_1']}
        ident=record_statistics(db,group)
        with self.assertRaises(ValueError): approve(db,ident,'5:5',{},'human')
        decision=approve(db,ident,'6:4',{'skill_interactions':['reviewed Q interaction'],'power_spikes':['level6']},'human')
        self.assertIsInstance(decision,int)
        self.assertEqual(db.execute('SELECT count(*) FROM validation_history').fetchone()[0],1)
        db.close()
    def test_unchanged_patch_has_audit_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir()
            state=root/'data/patch_state.json'; state.write_text('{"ddragon_version":"16.21.1"}')
            original=state.read_bytes()
            with patch('sys.argv',['check_patch','--root',tmp]),patch('scripts.check_patch.fetch_json',return_value=['16.21.1']): main()
            report=json.loads((root/'reports/check_status.json').read_text())
            self.assertFalse(report['ratings_changed'])
            self.assertEqual(state.read_bytes(),original)
