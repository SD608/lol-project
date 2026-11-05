"""Explicit Match-V5 IDs; PUUIDs and participant names are never persisted."""
import json
import os
import re
import math
from rift.http import fetch_json, FetchError

class TimelineUnavailable(FetchError):
    pass

from scripts.check_patch import patch_label

ROUTES={'KR':'asia','JP':'asia','NA':'americas','BR':'americas','EUW':'europe','EUNE':'europe','OCE':'sea'}

def collect(db, match_id, region, tier, fetch=fetch_json, rank_context=None):
    prefixes={'KR':'KR','JP':'JP1','NA':'NA1','BR':'BR1','EUW':'EUW1','EUNE':'EUN1','OCE':'OC1'}
    if region not in ROUTES or not re.fullmatch(prefixes.get(region,'INVALID')+r'_\d+',match_id):
        raise ValueError('invalid routing or match id')
    if db.execute('SELECT 1 FROM matches WHERE match_id=?',(match_id,)).fetchone(): return False
    key=os.environ.get('RIOT_API_KEY')
    if not key: raise RuntimeError('RIOT_API_KEY required')
    base=f'https://{ROUTES[region]}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers={'X-Riot-Token':key}
    match=fetch(base,headers=headers)
    try:
        timeline=fetch(base+'/timeline',headers=headers)
    except FetchError:
        raise TimelineUnavailable('timeline_unavailable; match not inserted') from None
    if match['metadata']['matchId']!=match_id or timeline['metadata']['matchId']!=match_id:
        raise ValueError('mismatched response identity')
    if not isinstance(timeline.get('info',{}).get('frames'),list): raise ValueError('missing timeline frames')
    info=match['info']
    if not isinstance(info.get('gameVersion'),str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)*',info['gameVersion']): raise ValueError('invalid game version')
    if not isinstance(info.get('participants'),list) or any(not isinstance(p,dict) for p in info['participants']): raise ValueError('invalid participants')
    if not isinstance(info.get('gameDuration'),(int,float)) or info['gameDuration']<0: raise ValueError('invalid duration')
    if any(not isinstance(f,dict) for f in timeline['info']['frames']): raise ValueError('invalid frames')
    if info.get('queueId')!=420 or info.get('mapId')!=11: raise ValueError('ranked solo Summoners Rift required')
    frames={}
    for minute in (10,15):
        frame=next((f for f in timeline['info']['frames'] if f.get('timestamp')==minute*60000),None)
        if frame:
            if not isinstance(frame.get('participantFrames'),dict) or any(not isinstance(v,dict) for v in frame['participantFrames'].values()): raise ValueError('invalid participant frames')
            frames[str(minute)]={pid:{k:v.get(k) if isinstance(v.get(k),(int,float)) and not isinstance(v.get(k),bool) and math.isfinite(v[k]) and v[k]>=0 else None for k in ('totalGold','minionsKilled','jungleMinionsKilled','xp','level')} for pid,v in frame['participantFrames'].items()}
    participants=[{k:p.get(k) for k in ('participantId','championId','teamId','teamPosition','individualPosition','win')} for p in info['participants']]
    safe={'game_version':info['gameVersion'],'map_id':info['mapId'],'game_mode':info.get('gameMode'),'game_creation':info.get('gameCreation'),'rank_context':{k:v for k,v in (rank_context or {}).items() if k in ('seed_current_tiers','observed_at','match_tier_status')},'participants':participants,'frames':frames,'game_duration':info['gameDuration'],'queue':420,'rank_provenance':'caller_supplied_not_verified'}
    with db:
        db.execute('INSERT OR IGNORE INTO matches VALUES(?,?,?,?,?)',(match_id,patch_label(info['gameVersion']),region,tier,json.dumps(safe)))
    return True
