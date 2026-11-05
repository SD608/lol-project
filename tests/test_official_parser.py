import unittest
from rift.official import parse_notes,resolve_notes,discover_urls
from rift.http import FetchError

URL='https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-22-notes/'
def document(extra='',change='50 ⇒ 60'):
    return f'''<html><nav>가렌 menu</nav><h1>리그 오브 레전드 26.22 패치 노트</h1><div id="patch-notes-container"><p>소개 {extra}</p><h2 id="patch-champions">챔피언</h2><div class="patch-change-block"><h3 class="change-title" id="patch-corki">코르키</h3><p>아지르와 오리아나처럼 상향합니다.</p><h4>R 미사일</h4><ul><li>피해량 {change}</li></ul></div><h2 id="patch-items">아이템</h2><div class="patch-change-block"><h3 class="change-title">도란의 활</h3><p>세트 언급</p><ul><li>공격력 10 ⇒ 9</li></ul></div><h2 id="patch-aram:-mayhem">아수라장</h2><div class="patch-change-block"><h3 class="change-title">가렌</h3><ul><li>피해량 200 ⇒ 300</li></ul></div><h2 id="patch-classic">클래식</h2></div><footer>{extra} 카르마</footer></html>'''

class OfficialParser(unittest.TestCase):
    def test_listing_discovery_and_patch_boundary(self):
        html=f'<a href="{URL}">26.22</a><a href="https://evil.example/26-22-notes">wrong</a><a href="/ko-kr/news/game-updates/patch-26-220-notes/">other</a>'
        self.assertEqual(discover_urls(html,'26.22'),[URL])
    def test_resolve_404_tries_other_official_link_once(self):
        old=URL.replace('league-of-legends-',''); calls=[]
        def fetch(url):
            calls.append(url)
            if url.endswith('/game-updates/'): return f'<a href="{old}">old</a><a href="{URL}">correct</a>'
            if url==old: raise FetchError('HTTP 404')
            return document()
        self.assertEqual(resolve_notes('26.22',fetch)[0],URL)
        self.assertEqual(calls.count(old),1)
    def test_article_only_modes_and_mentions(self):
        n=parse_notes(document(),'26.22',['가렌','코르키','아지르','세트'],strict=True)
        self.assertEqual(n['champions'],['코르키']);self.assertEqual(n['items'],['도란의 활']);self.assertEqual(n['runes'],[])
        self.assertNotIn('menu',n['text']);self.assertNotIn('카르마',n['text']);self.assertIn('aram_mayhem',n['other_modes'])
    def test_editorial_does_not_change_balance_digest(self):
        a=parse_notes(document(),'26.22',[],strict=True);b=parse_notes(document('편집 수정'),'26.22',[],strict=True)
        self.assertEqual(a['digest'],b['digest']);self.assertNotEqual(a['article_digest'],b['article_digest'])
        self.assertNotEqual(a['digest'],parse_notes(document(change='50 ⇒ 70'),'26.22',[],strict=True)['digest'])
    def test_changed_dom_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'structure_changed'):parse_notes('<html><h1>26.22</h1><p>챔피언 가렌</p></html>','26.22',[],strict=True)
        with self.assertRaisesRegex(ValueError,'missing change list'):parse_notes(document().replace('<li>피해량 50 ⇒ 60</li>',''),'26.22',[],strict=True)
    def test_wrong_document_patch_rejected(self):
        with self.assertRaises(ValueError):parse_notes(document().replace('26.22','26.21'),'26.22',[],strict=True)
    def test_two_targets_in_one_block(self):
        html=document().replace('<h2 id="patch-aram:-mayhem">','<div class="patch-change-block"><h3 class="change-title">지배자의 피갑옷</h3><ul><li>공격력 30 ⇒ 40</li></ul></div><h2 id="patch-aram:-mayhem">')
        html=html.replace('</ul></div><div class="patch-change-block"><h3 class="change-title">지배자의 피갑옷','</ul><h3 class="change-title">지배자의 피갑옷')
        self.assertEqual(parse_notes(html,'26.22',[],strict=True)['items'],['도란의 활','지배자의 피갑옷'])
    def test_hotfix_content_changes_digest(self):
        base=document();revision=base.replace('<h2 id="patch-champions">','<h2 id="patch-midpatch">추가 패치</h2><ul><li>가렌 피해량 10 ⇒ 12</li></ul><h2 id="patch-champions">')
        a=parse_notes(base,'26.22',[],strict=True);b=parse_notes(revision,'26.22',[],strict=True)
        self.assertNotEqual(a['digest'],b['digest']);self.assertTrue(b['hotfix_mentioned']);self.assertTrue(b['unmapped_changes'])
