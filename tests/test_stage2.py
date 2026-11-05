import json
import tempfile
import unittest
from pathlib import Path
from rift.official import parse_notes,live_evidence
from rift.limiter import Limiter
from scripts.check_official import check

class Stage2(unittest.TestCase):
    def test_sections(self):
        n=parse_notes('<h1>26.22 패치</h1><h2>챔피언</h2><h3>가렌</h3><p>Q 피해량 증가</p><h2>아이템</h2><p>검</p><h2>룬</h2><p>정복자</p>','26.22',{'가렌'})
        self.assertEqual(n['champions'],['가렌']);self.assertTrue(n['items_changed']);self.assertTrue(n['runes_changed'])
    def test_no_false_live(self):
        for text in ('26.22 한국 서버 점검 예정','26.22 패치 노트','26.21 한국 패치 적용되었습니다'):
            self.assertFalse(live_evidence(text,'26.22'))
        self.assertTrue(live_evidence('26.22 한국 서버 패치가 적용되었습니다','26.22'))
    def test_revision_and_failure_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir();(root/'data/lane_champions.json').write_text(json.dumps({'탑':['가렌','잭스']}))
            original='<h1>26.22</h1><h2>챔피언</h2><h3>가렌</h3><p>Q 변경</p>'
            a=check(root,'26.22',lambda _:original)
            self.assertEqual(a['release_status'],'pending');self.assertEqual(len(a['review_queue']),2)
            self.assertFalse(check(root,'26.22',lambda _:original)['changed'])
            b=check(root,'26.22',lambda _:original+'<p>추가 패치 Q 변경</p>')
            self.assertTrue(b['same_patch_revision']);self.assertEqual(len(list((root/'reports/official_history').glob('*.json'))),2)
            state=(root/'data/official_state.json').read_bytes()
            with self.assertRaises(OSError): check(root,'26.22',lambda _: (_ for _ in ()).throw(OSError('failure')))
            self.assertEqual((root/'data/official_state.json').read_bytes(),state)
    def test_unknown_structure_reviews_all(self):
        n=parse_notes('<p>26.22 unknown structure</p>','26.22',[])
        self.assertEqual(n['parse_status'],'unknown')
        with self.assertRaises(ValueError): parse_notes('<p>26.21</p>','26.22',[])
    def test_limiter(self):
        now=[0.0]; sleeps=[]
        def sleep(n): sleeps.append(n);now[0]+=n
        limiter=Limiter(clock=lambda:now[0],sleep=sleep)
        limiter.wait();limiter.wait();self.assertGreaterEqual(sleeps[0],1.3)
        limiter.observe({'X-App-Rate-Limit':'2:10','X-App-Rate-Limit-Count':'2:10'})
        limiter.wait();self.assertGreaterEqual(sleeps[-1],10)
