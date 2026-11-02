import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_patch import patch_label, changed_champions, changed_items, make_review_queue

class PatchWatchTests(unittest.TestCase):
    def test_patch_label(self):
        self.assertEqual(patch_label('16.21.1'), '26.21')
        self.assertEqual(patch_label('16.22.2'), '26.22')

    def test_only_changed_stats_are_reported(self):
        old = {'data': {'A': {'name':'가렌','stats':{'hp': 1}}, 'B': {'name':'다리우스','stats':{'hp': 2}}}}
        new = {'data': {'A': {'name':'가렌','stats':{'hp': 3}}, 'B': {'name':'다리우스','stats':{'hp': 2}}}}
        self.assertEqual(changed_champions(old, new), [{'id':'A', 'name':'가렌', 'fields':['stats']}])

    def test_item_changes_trigger_system_review(self):
        old = {'data':{'1':{'name':'아이템','gold':{'total':1000}}}}
        new = {'data':{'1':{'name':'아이템','gold':{'total':1100}}}}
        self.assertEqual(len(changed_items(old, new)), 1)

    def test_directed_pair_coverage(self):
        lanes={'탑':['가렌','다리우스','잭스'], '정글':['리 신','비에고']}
        partial=make_review_queue(lanes, {'가렌'}, False, '26.22')
        self.assertEqual(len(partial), 4)
        all_rows=make_review_queue(lanes, set(), True, '26.22')
        self.assertEqual(len(all_rows), 8)
        self.assertTrue(all(x['상성 등급']=='' for x in all_rows))

if __name__ == '__main__':
    unittest.main()
