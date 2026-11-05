from urllib.request import urlopen
from html.parser import HTMLParser
import re
class Inspect(HTMLParser):
    def handle_starttag(self,t,a):
        d=dict(a)
        if t in ('h1','h2','h3','h4','article') or any('patch' in str(v) or 'article' in str(v) for k,v in a if k in ('class','id','data-testid')): print(t,d)
    def handle_data(self,s):
        if s.strip() and len(s)<250: print('TEXT',s.strip())
url='https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-22-notes/'
s=urlopen(url).read().decode();print('ARTICLE',len(s));Inspect().feed(s)
index=urlopen('https://www.leagueoflegends.com/ko-kr/news/game-updates/').read().decode()
print('LINKS',re.findall(r'href="([^"]*26-22[^"]*)"',index))
