"""Official HTML evidence collector; editorial changes are review candidates."""
import hashlib
import re
import time
from urllib.error import HTTPError
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
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
    for attempt in range(4):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; RiftMatchupMonitor/0.3)'}),timeout=30) as response:
                if urlparse(response.url).hostname!='www.leagueoflegends.com': raise FetchError('unexpected redirect')
                return response.read(8_000_000).decode('utf-8')
        except HTTPError as exc:
            if exc.code!=429 and not 500<=exc.code<600:
                raise FetchError(f'official source HTTP {exc.code}') from None
        except (OSError,TimeoutError): pass
        if attempt<3: time.sleep(2**attempt)
    raise FetchError('official source retries exhausted') from None

def _fragment_notes(html, patch, champion_names):
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

class Node:
    def __init__(self, tag='', attrs=None): self.tag=tag; self.attrs=dict(attrs or []); self.children=[]
    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child,Node): yield from child.walk()
    def text(self):
        return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split()) if self.tag not in ('script','style','nav','footer') else ''

class DOM(HTMLParser):
    def __init__(self): super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,a); self.stack[-1].children.append(n)
        if t not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'): self.stack.append(n)
    def handle_startendtag(self,t,a): self.handle_starttag(t,a);self.handle_endtag(t)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t: self.stack=self.stack[:i];break
    def handle_data(self,s): self.stack[-1].children.append(s)

def discover_urls(html, patch, index_url='https://www.leagueoflegends.com/ko-kr/news/game-updates/'):
    dom=DOM();dom.feed(html);urls=[]
    pattern=r'(?<!\d)'+re.escape(patch.replace('.','-'))+r'(?!\d)'
    for node in dom.root.walk():
        if node.tag!='a': continue
        url=urljoin(index_url,node.attrs.get('href',''));u=urlparse(url)
        if u.scheme=='https' and u.hostname=='www.leagueoflegends.com' and u.path.startswith('/ko-kr/news/game-updates/') and re.search(pattern,u.path) and 'notes' in u.path:
            if url not in urls: urls.append(url)
    return urls

def resolve_notes(patch, fetch=fetch_text):
    index='https://www.leagueoflegends.com/ko-kr/news/game-updates/'
    listing=fetch(index)
    candidates=discover_urls(listing,patch)
    method='official_listing'
    if not candidates:
        # Known official naming convention only as fallback, always content-validated.
        candidates=[index+f'league-of-legends-patch-{patch.replace(".","-")}-notes/']
        method='validated_canonical_fallback'
    errors=[]
    for url in candidates:
        try:
            html=fetch(url)
            dom=DOM();dom.feed(html)
            titles=[n.text() for n in dom.root.walk() if n.tag=='h1']
            if not any(re.search(r'(?<!\d)'+re.escape(patch)+r'(?!\d)',t) for t in titles): raise ValueError('article title patch mismatch')
            return url,html,{'method':method,'index_url':index,'attempt_errors':errors}
        except (FetchError,ValueError) as exc: errors.append({'url':url,'error':str(exc)})
    raise FetchError('no validated official article: '+str(errors))

def parse_notes(html, patch, champion_names, strict=False):
    dom=DOM();dom.feed(html)
    containers=[n for n in dom.root.walk() if n.attrs.get('id')=='patch-notes-container']
    if not containers:
        if not strict and '<html' not in html.lower(): return _fragment_notes(html,patch,champion_names)
        raise ValueError('structure_changed: missing patch-notes-container')
    article=containers[0]
    titles=[n.text() for n in dom.root.walk() if n.tag=='h1']
    if not any(re.search(r'(?<!\d)'+re.escape(patch)+r'(?!\d)',t) for t in titles): raise ValueError('article patch mismatch')
    records=[];other={};category=None;mode='summoners_rift';section='';recognized=False;errors=[]
    sections={'patch-champions':'champions','patch-items':'items','patch-runes':'runes'}
    for node in article.walk():
        if node.tag=='h2':
            section=node.attrs.get('id','');category=sections.get(section)
            label=node.text()
            if re.search('aram|mayhem|아수라장|무작위 총력전',section+' '+label,re.I): mode='aram_mayhem'
            elif re.search('classic|클래식',section+' '+label,re.I): mode='classic'
            elif category: mode='summoners_rift';recognized=True
            elif section: mode='other'
            if mode!='summoners_rift': other.setdefault(mode,[]).append({'section':section,'heading':label})
        if 'patch-change-block' not in node.attrs.get('class','').split(): continue
        title=next((x for x in node.walk() if x.tag=='h3' and 'change-title' in x.attrs.get('class','').split()),None)
        if not title: continue
        details=[x.text() for x in node.walk() if x.tag=='li' and x.text()]
        if mode!='summoners_rift' or not category:
            other.setdefault(mode,[]).append({'name':title.text(),'changes':details});continue
        if not details:
            errors.append('missing change list: '+title.text());continue
        records.append({'mode':mode,'category':category,'name':title.text(),'anchor':title.attrs.get('id'),'changes':details})
    if not recognized or not records or errors: raise ValueError('structure_changed: '+('; '.join(errors) or 'no recognized balance blocks'))
    import json
    digest=hashlib.sha256(json.dumps(records,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    article_digest=hashlib.sha256(article.text().encode()).hexdigest()
    grouped={k:[r for r in records if r['category']==k] for k in ('champions','items','runes')}
    return {'digest':digest,'article_digest':article_digest,'text':article.text(),'sections':grouped,'changes':records,'champions':[r['name'] for r in grouped['champions']],'items':[r['name'] for r in grouped['items']],'runes':[r['name'] for r in grouped['runes']],'items_changed':bool(grouped['items']),'runes_changed':bool(grouped['runes']),'parse_status':'structured_candidates','other_modes':other,'hotfix_mentioned':bool(re.search(r'추가 패치|긴급 수정|hotfix|mid.?patch',' '.join(n.text() for n in article.walk() if n.tag in ('h2','h3')),re.I))}
