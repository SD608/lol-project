import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.counter_guide import CounterGuide
from backend.main import app

ROOT=Path(__file__).resolve().parents[1]
class CounterGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.guide=CounterGuide();cls.data=cls.guide.data
    def test_complete_roster_and_directed_coverage(self):
        d=self.data
        self.assertEqual(len(d['champions']),173);self.assertEqual(sum(map(len,d['lanes'].values())),266)
        keys={(r['lane'],r['champion'],r['opponent']) for r in d['rows']}
        self.assertEqual(len(keys),14468)
        self.assertEqual(keys,{(l,a,b) for l,names in d['lanes'].items() for a in names for b in names if a!=b})
    def test_evidence_preserved_and_reasons_present(self):
        self.assertEqual(sum(r['evidence']=='statistical' for r in self.data['rows']),110)
        self.assertEqual(sum(r['evidence']=='theoretical' for r in self.data['rows']),14358)
        for r in self.data['rows']:
            self.assertTrue(r['advantage']);self.assertTrue(r['caution'])
            self.assertEqual(r['source_sheet'],r['lane']);self.assertGreater(r['source_row'],1)
            self.assertEqual(r['group'],{'강한 유리':'hard','유리':'counter','반반':'even','불리':'unfavorable','강한 불리':'unfavorable'}[r['verdict'].split('(')[0]])
    def test_direction_is_recommendation_perspective(self):
        result=self.guide.counters('탑','다리우스')
        actual=[r for group in result['groups'].values() for r in group]
        expected=[r for r in self.data['rows'] if r['lane']=='탑' and r['opponent']=='다리우스']
        self.assertEqual({r['champion'] for r in actual},{r['champion'] for r in expected})
        self.assertEqual(len(actual),64)
        for r in actual:self.assertIn(r,expected);self.assertEqual(r['opponent'],'다리우스');self.assertNotEqual(r['champion'],'다리우스')
    def test_korean_alias_initials_and_lane_filter(self):
        for q,name,lane in [('미포','미스 포츈','바텀'),('트페','트위스티드 페이트','미드'),('아우솔','아우렐리온 솔','미드'),('징키','징크스','바텀'),('ㅈㅋㅅ','징크스','바텀')]:
            self.assertIn(name,[c['name'] for c in self.guide.champions(lane,q)])
        self.assertEqual(self.guide.champions('탑','징키'),[])
    def test_endpoints_independent_of_database(self):
        with patch.dict(os.environ,{'DATABASE_URL':''}),patch('backend.main.fetch',side_effect=AssertionError('DB must not be queried')):
            with TestClient(app) as client:
                self.assertEqual(client.get('/api/counter-guide/metadata').json()['counts']['matchups'],14468)
                self.assertEqual(len(client.get('/api/counter-guide/champions',params={'lane':'탑'}).json()['items']),65)
                response=client.get('/api/counter-guide/counters',params={'lane':'탑','opponent':'다리우스'})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json()['groups']['counter'])
                self.assertEqual(client.get('/api/counter-guide/counters',params={'lane':'탑','opponent':'징크스'}).status_code,404)
                self.assertEqual(client.get('/api/counter-guide/champions',params={'lane':'unknown'}).status_code,422)
    def test_memory_index_uses_no_runtime_file_or_network(self):
        with patch('pathlib.Path.read_text',side_effect=AssertionError('read per request')):
            for lane,names in self.data['lanes'].items():self.assertTrue(self.guide.counters(lane,names[0])['groups'])
