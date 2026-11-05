"""Official HTML evidence collector; editorial changes are review candidates."""
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from rift.http import FetchError

class Article(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('h1','h2','h3','h4','p','li','div'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('h1','h2','h3','h4','p','li'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)

def fetch_text(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='www.leagueoflegends.com': raise ValueError('official host required')
    try:
        with urlopen(Request(url,headers={'User-Agent':'RiftMatchupMonitor/0.3'}),timeout=30) as response:
            if urlparse(response.url).hostname!='www.leagueoflegends.com': raise FetchError('unexpected redirect')
            return response.read(8_000_000).decode('utf-8')
    except (OSError,TimeoutError): raise FetchError('official source unavailable') from None

def parse_notes(html, patch, champion_names):
    parser=Article(); parser.feed(html)
    text='\n'.join(x.strip() for x in ''.join(parser.parts).splitlines() if x.strip())
    if not re.search(r'(?<!\d)'+re.escape(patch)+r'(?!\d)',text): raise ValueError('patch identity missing')
    lines=text.splitlines(); sections={'champions':[], 'items':[], 'runes':[]}; category=None
    headings={'챔피언':'champions','아이템':'items','룬':'runes','Champions':'champions','Items':'items','Runes':'runes'}
    for line in lines:
        if line in headings: category=headings[line]
        if category: sections[category].append(line)
    changed=sorted(n for n in champion_names if any(n in line for line in sections['champions']))
    return {'digest':hashlib.sha256(text.encode()).hexdigest(),'text':text,'sections':sections,'champions':changed,'items_changed':bool(sections['items']),'runes_changed':bool(sections['runes']),'parse_status':'structured_candidates' if any(sections.values()) else 'unknown','hotfix_mentioned':bool(re.search(r'추가 패치|긴급 수정|hotfix|mid.?patch',text,re.I))}

def live_evidence(html, patch):
    parser=Article(); parser.feed(html); text=' '.join(''.join(parser.parts).split())
    # A KR localized notes page or future maintenance schedule is not deployment proof.
    patch_ok=bool(re.search(r'(?<!\d)'+re.escape(patch)+r'(?!\d)',text))
    applied=bool(re.search(r'(점검|패치|업데이트)[^.!?\n]{0,100}(완료되었습니다|적용되었습니다|완료되었습니다\.)',text))
    return patch_ok and applied and ('한국' in text or 'KR 서버' in text)
