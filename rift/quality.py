"""Conservative validity flags. Never impute missing timeline values."""
from collections import Counter
from rift.statistics import LANES

def quality(payload):
    players=payload.get('participants',[]); reasons=[]
    if payload.get('game_mode')!='CLASSIC': reasons.append('non_classic_or_unknown_mode')
    if len(players)!=10 or len({p.get('participantId') for p in players})!=10: reasons.append('invalid_participant_count')
    for team in (100,200):
        members=[p for p in players if p.get('teamId')==team]
        if len(members)!=5 or Counter(p.get('teamPosition') for p in members)!=Counter(LANES.keys()): reasons.append('ambiguous_roles')
    if any(p.get('individualPosition') not in (None,'',p.get('teamPosition')) for p in players): reasons.append('role_disagreement_or_swap')
    if any(not isinstance(p.get('win'),bool) or not p.get('championId') for p in players): reasons.append('missing_participant_fields')
    missing=[]
    for minute in (10,15):
        frame=payload.get('frames',{}).get(str(minute),{})
        if any(not frame.get(str(p.get('participantId'))) or any(frame[str(p.get('participantId'))].get(k) is None for k in ('totalGold','minionsKilled','jungleMinionsKilled','xp','level')) for p in players): missing.append(minute)
    return {'valid':not reasons,'role_flags':sorted(set(reasons)),'missing_timeline_minutes':missing,'role_assignment':'Riot reported roles; unreported in-game lane swaps cannot be ruled out'}

def status(group, evidence=None):
    from rift.validation import assess
    required=[f'{m}_diff_{minute}' for m in ('gold','cs','xp') for minute in (10,15)]
    metrics=group['metrics']
    if group['sample_size']<100 or any(metrics.get(k,{}).get('sample_size',0)<100 for k in required): return 'insufficient_sample'
    if not evidence: return 'evidence_pending'
    record={**evidence,'patch':group['key'][0],'region':group['key'][4],'tier':group['key'][5],'sample_size':group['sample_size'],'sources':group['sources'],'metrics':{k:metrics[k]['mean'] for k in required}}
    return 'auto_checked' if assess(record)['status']=='auto_checked' else 'evidence_pending'
