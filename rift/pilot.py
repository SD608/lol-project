"""KR pilot orchestration. Reports contain aggregates, never account identifiers."""
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from rift.database import record_statistics
from rift.discovery import discover
from rift.http import FetchError
from rift.matches import collect,TimelineUnavailable
from rift.quality import quality,status
from rift.statistics import summarize


def empty_report():
    return {'project':'PICKOU','observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'not_started','data_origin':'riot_api','actual_api_success':False,'collected_matches':0,'duplicate_matches':0,'valid_matches':0,'usable_timeline_matches':0,'timeline_missing_matches':0,'timeline_fetch_failures':0,'role_flagged_matches':0,'patch_counts':{},'lane_matchup_counts':{},'errors':{},'api_events':{},'matchups':[],'examples':[],'verified_matchups':0,'ratings_changed':False,'sheet_write_enabled':False,'sheet_update_plan':{'write_enabled':False,'proposals':[],'reason':'no actual statistics'},'limitations':['Current seed tier does not prove participant tiers at match time.','Riot reported roles cannot detect all physical lane swaps.','Observational statistics do not establish causal skill counters.']}

def live_context(root):
    path=root/'reports/official_latest.json'
    state_path=root/'data/patch_state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    report=json.loads(path.read_text()) if path.exists() else {}
    recent=False
    try: recent=0<=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(report['checked_at'])).total_seconds()<48*3600
    except (KeyError,ValueError,TypeError): pass
    confirmed=report.get('release_status')=='confirmed' and bool(report.get('live_url')) and report.get('patch')==state.get('public_patch') and recent
    return {'candidate_patch':state.get('public_patch'),'official_latest_live_patch':report.get('patch') if confirmed else None,'live_status':'confirmed' if confirmed else 'pending','basis':'official_regional_evidence' if confirmed else 'match_gameVersion_partition_only; latest live not confirmed'}

def pilot(db,root,client,target=100,origin='riot_api'):
    if not 1<=target<=100: raise ValueError('target must be 1..100')
    r=empty_report();r['data_origin']=origin;r['patch_context']=live_context(root);errors=Counter();patches=Counter();selected=set();flags=Counter()
    ids,contexts,discovery=discover(client,candidate_limit=min(500,max(100,target*3)))
    r['discovery']=discovery;r['duplicate_matches']=discovery.get('duplicate_ids',0)
    # Champion ID/name mapping comes from official static metadata, independently of API keys.
    mapping_path=root/'data/champion_ids.json'
    mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
    r['champion_mapping_status']='available' if mapping else 'missing; no named matchup statistics'
    for match_id in ids:
        if r['valid_matches']>=target: break
        cohort='UNKNOWN_AT_MATCH__SEED_CURRENT_'+'_'.join(contexts.get(match_id,[]))
        exists=db.execute('SELECT 1 FROM matches WHERE match_id=?',(match_id,)).fetchone()
        try:
            if exists: r['duplicate_matches']+=1
            elif collect(db,match_id,'KR',cohort,fetch=client,rank_context={'seed_current_tiers':contexts.get(match_id,[]),'observed_at':r['observed_at'],'match_tier_status':'unknown'}): r['collected_matches']+=1
            row=db.execute('SELECT patch,payload FROM matches WHERE match_id=?',(match_id,)).fetchone()
            if not row: continue
            patch,payload=row[0],json.loads(row[1]);patches[patch]+=1
            q=quality(payload)
            if q['missing_timeline_minutes']: r['timeline_missing_matches']+=1
            if q['role_flags']: r['role_flagged_matches']+=1;flags.update(q['role_flags'])
            if not q['valid']: errors['invalid_match_quality']+=1;continue
            official=r['patch_context']['official_latest_live_patch']
            if official and patch!=official: errors['other_patch_preserved_excluded_from_target']+=1;continue
            r['valid_matches']+=1;selected.add(match_id)
            if not q['missing_timeline_minutes']: r['usable_timeline_matches']+=1
        except TimelineUnavailable:
            r['timeline_fetch_failures']+=1;errors['timeline_unavailable']+=1
        except FetchError:
            errors['api_request_failed']+=1
        except (ValueError,KeyError,TypeError):
            errors['invalid_response']+=1
        if errors['api_request_failed']>=5: errors['circuit_breaker']+=1;break
    groups=summarize(db,mapping,selected)
    for group in groups:
        group['status']=status(group)
        # An existing manual decision counts only when tied to the same source sample.
        approved=db.execute("SELECT s.sources,s.metrics FROM decisions d JOIN statistics s ON d.statistic_id=s.id WHERE d.status='manual_approved' AND d.patch=? AND d.lane=? AND d.champion=? AND d.opponent=? AND d.region=? AND d.tier=?",group['key']).fetchall()
        if any(set(json.loads(v[0]))==set(group['sources']) and json.loads(v[1])==group['metrics'] for v in approved): group['status']='approved'
        record_statistics(db,group)
        if group['status']=='approved': r['verified_matchups']+=1
        r['lane_matchup_counts'][group['key'][1]]=r['lane_matchup_counts'].get(group['key'][1],0)+1
    groups.sort(key=lambda x:(-x['sample_size'],x['key']))
    r.update({'status':'completed' if r['valid_matches']>=target else 'partial' if r['valid_matches'] else 'no_usable_samples','patch_counts':dict(patches),'errors':dict(errors),'role_flags':dict(flags),'matchups':groups,'api_events':dict(getattr(client,'events',{}))})
    r['actual_api_success']=origin=='riot_api' and r['api_events'].get('responses_ok',0)>0
    r['examples']=groups[:5] if origin=='riot_api' and r['valid_matches'] else []
    sheet_path=root/'data/read_only/sheets_mapping.json.gz'
    if origin=='riot_api' and groups and sheet_path.exists():
        from rift.sheets import validate_mapping,update_plan
        import gzip
        mapping=validate_mapping(db,json.loads(gzip.decompress(sheet_path.read_bytes())),json.loads((root/'data/lane_champions.json').read_text()))
        r['sheet_update_plan']=update_plan(groups,mapping)
    return r


def save_report(root,report):
    from scripts.check_patch import save_json
    import uuid
    directory=root/'reports/collection';run_id=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    # Atomic JSON replacement and immutable per-run names; no source records are overwritten.
    save_json(directory/(run_id+'.json'),report);save_json(directory/'latest.json',report)
    lines=['# PICKOU 경기 수집 보고서','',f"상태: {report['status']}",f"실제 Riot API 응답 성공: {report['actual_api_success']}",f"새 경기 수집: {report['collected_matches']}",f"중복 제거: {report['duplicate_matches']}",f"유효 경기: {report['valid_matches']}",f"타임라인 누락: {report['timeline_missing_matches']} / 요청 실패: {report['timeline_fetch_failures']}",f"승인된 매치업: {report['verified_matchups']}",'', '승률을 상성 비율로 변환하지 않으며 미검증 등급은 NULL입니다.','', '## 실제 통계 예시']
    if not report['examples']: lines.append('실제 확보된 통계 예시 없음. 임의의 수치를 생성하지 않았습니다.')
    for group in report['examples']:
        lines.extend(['',f"### {' / '.join(group['key'])}",f"표본: {group['sample_size']}, 상태: {group['status']}", '```json',json.dumps(group['metrics'],ensure_ascii=False,indent=2),'```'])
    lines.extend(['','## 제한 및 오류',json.dumps({'errors':report['errors'],'patch_counts':report['patch_counts'],'lane_matchup_counts':report['lane_matchup_counts'],'api_events':report['api_events'],'limitations':report['limitations']},ensure_ascii=False,indent=2)])
    text='\n'.join(lines)+'\n';(directory/(run_id+'.md')).write_text(text);(directory/'latest.md').write_text(text)
