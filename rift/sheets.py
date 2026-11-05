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


def validate_mapping(db, payload, lanes):
    """Validate every visible source pair against the DB; preserve row coordinates."""
    import hashlib
    result={'spreadsheet_id':payload['spreadsheet_id'],'read_only':True,'observed_at':payload.get('observed_at'),'lanes':{},'rows':0,'valid':True}
    for lane,names in lanes.items():
        sheet=payload.get('sheets',{}).get(lane,{})
        rows=sheet.get('rows',[]);seen=set();issues=[];row_map={}
        if sheet.get('header')!=HEADERS: issues.append('header_mismatch')
        expected={(a,b) for a in names for b in names if a!=b}
        for number,row in enumerate(rows,2):
            if not row or not any(row): continue
            pair=tuple(row[:2])
            if len(pair)!=2 or pair not in expected: issues.append('invalid_pair_at_row_'+str(number));continue
            if pair in seen: issues.append('duplicate_pair_at_row_'+str(number))
            seen.add(pair);row_map['\t'.join(pair)]=number
        db_pairs=set(db.execute('SELECT champion,opponent FROM matchups WHERE lane=?',(lane,)))
        missing=len(expected-seen);extra=len(seen-expected)
        if missing or extra or db_pairs!=expected: issues.append('coverage_or_database_mismatch')
        digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest()
        result['lanes'][lane]={'sheetId':sheet.get('sheetId'),'rows':len(seen),'expected':len(expected),'missing':missing,'extra':extra,'issues':issues,'source_rows_digest':digest,'row_map':row_map}
        result['rows']+=len(seen)
        if issues: result['valid']=False
    return result


def update_plan(groups,mapping):
    """Review-only proposal. No API credentials or write calls exist here."""
    proposals=[];skipped=[]
    for g in groups:
        patch,lane,a,b,region,tier=g['key']
        item=mapping.get('lanes',{}).get(lane,{})
        row=item.get('row_map',{}).get(a+'\t'+b)
        if not mapping.get('valid') or not row:
            skipped.append({'key':g['key'],'reason':'mapping_not_verified'});continue
        metrics=g['metrics']; sample=min([g['sample_size']]+[v['sample_size'] for v in metrics.values() if isinstance(v,dict) and 'sample_size' in v])
        # Columns D/E (grade) remain absent. Region/tier have no verified destination column.
        proposals.append({'key':g['key'],'requires_approval':True,'write_enabled':False,'source_rows_digest':item['source_rows_digest'],'preconditions':{'A':a,'B':b,'I':'must re-read existing patch; do not replace another patch or region/tier cohort'},'separate_patch_destination_required':True,'cells':{f"'{lane}'!F{row}":metrics.get('game_win_rate')*100 if metrics.get('game_win_rate') is not None else None,f"'{lane}'!H{row}":sample,f"'{lane}'!I{row}":patch,f"'{lane}'!M{row}":{k:v for k,v in metrics.items() if '_diff_' in k}},'reason':'human review plus fresh cell read and cohort destination mapping required'})
    return {'write_enabled':False,'approval_required':True,'proposals':proposals,'skipped':skipped}
