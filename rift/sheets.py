"""Read-only Sheets mapping. No write API is exposed."""
import json
from rift.database import snapshot

HEADERS=['내 챔피언','상대 챔피언','기존 분류(참고용)','라인전 상성 등급(검증 후)','상성 평가 비율','게임 승률(%)','기대 대비 승률(%p)','표본 경기 수','패치','통계 출처','검증 상태','비고','라인전 지표(15분 CS·골드·경험치)','스킬 상성·판정 근거','유불리 변화 시점','근거 확인 상태','현재 패치 검증 상태']

def import_values(db, spreadsheet_id, lane, values, lanes):
    if not values or values[0]!=HEADERS: raise ValueError('unrecognized column mapping')
    if lane not in lanes: raise ValueError('unrecognized lane')
    seen=set()
    for row in values[1:]:
        if not row or not any(v is not None and v!='' for v in row): continue
        if len(row)<2 or row[0] not in lanes[lane] or row[1] not in lanes[lane] or row[0]==row[1]:
            raise ValueError('invalid champion pair')
        if tuple(row[:2]) in seen: raise ValueError('duplicate sheet pair')
        seen.add(tuple(row[:2]))
    # Preserve every original cell, including legacy labels; never promote it to verified.
    with db:
        digest=snapshot(db,f'google-sheets:{spreadsheet_id}:{lane}',values)
    expected=len(lanes[lane])*(len(lanes[lane])-1)
    return {'digest':digest,'rows':len(seen),'expected':expected,'complete':len(seen)==expected,'write_enabled':False}
