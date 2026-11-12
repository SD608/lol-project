"""Memory-only workbook reference; no SQL, API keys, or runtime workbook reads."""
import json
from pathlib import Path
from fastapi import APIRouter,HTTPException,Query
from rift.database import ALIASES,initials

DEFAULT=Path(__file__).resolve().parents[1]/'data/counter-guide-26.22.json'
class CounterGuide:
    def __init__(self,path=DEFAULT):
        self.data=json.loads(Path(path).read_text());self.index={}
        if self.data['patch']!='26.22' or len(self.data['rows'])!=14468:raise ValueError('Invalid counter guide dataset')
        for row in self.data['rows']:
            self.index.setdefault((row['lane'],row['opponent']),[]).append(row)
    def champions(self,lane,q=''):
        if lane not in self.data['lanes']:raise HTTPException(422,'Unknown lane')
        query=''.join(q.casefold().split())
        return [c for c in self.data['champions'] if lane in c['lanes'] and any(query in ''.join(v.casefold().split()) for v in [c['name'],c['initials'],*c['aliases']])]
    def counters(self,lane,opponent):
        if lane not in self.data['lanes']:raise HTTPException(422,'Unknown lane')
        if opponent not in self.data['lanes'][lane]:raise HTTPException(404,'Opponent not registered in lane')
        groups={k:[] for k in ('hard','counter','even','unfavorable')}
        for row in self.index[(lane,opponent)]:groups[row['group']].append(row)
        for group in groups.values():group.sort(key=lambda r:(r['evidence']!='statistical',r['champion']))
        return {'patch':self.data['patch'],'lane':lane,'opponent':opponent,'groups':groups,'note':'통계 확인은 제공 엑셀의 승률·표본 확인 분류입니다. 이론 참고는 검증 전 가설이며 실제 승률이 아닙니다.'}

router=APIRouter(prefix='/api/counter-guide',tags=['Workbook counter guide'])
# Once per server process, independent of the existing PostgreSQL API lifecycle.
_GUIDE=None
def guide():
    global _GUIDE
    if _GUIDE is None:raise HTTPException(503,'Counter guide data unavailable')
    return _GUIDE

def load_guide():
    global _GUIDE
    _GUIDE=CounterGuide()

@router.get('/metadata')
def metadata():
    d=guide().data
    return {k:d[k] for k in ('patch','ddragon_version','counts')}|{'lanes':list(d['lanes'])}

@router.get('/champions')
def champions(lane:str=Query(...,max_length=10),q:str=Query('',max_length=100)):
    return {'items':guide().champions(lane,q)}

@router.get('/counters')
def counters(lane:str=Query(...,max_length=10),opponent:str=Query(...,max_length=100)):
    return guide().counters(lane,opponent)
