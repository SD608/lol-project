"""Explicit Match-V5 IDs; PUUIDs and participant names are never persisted."""
import json
import os
import re
from rift.http import fetch_json
from scripts.check_patch import patch_label

ROUTES={'KR':'asia','JP':'asia','NA':'americas','BR':'americas','EUW':'europe','EUNE':'europe','OCE':'sea'}

def collect(db, match_id, region, tier, fetch=fetch_json):
    if region not in ROUTES or not re.fullmatch(r'[A-Z0-9]+_\d+',match_id):
        raise ValueError('invalid routing or match id')
    if db.execute('SELECT 1 FROM matches WHERE match_id=?',(match_id,)).fetchone(): return False
    key=os.environ.get('RIOT_API_KEY')
    if not key: raise RuntimeError('RIOT_API_KEY required')
    base=f'https://{ROUTES[region]}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers={'X-Riot-Token':key}
    match=fetch(base,headers=headers); timeline=fetch(base+'/timeline',headers=headers)
    if match['metadata']['matchId']!=match_id or timeline['metadata']['matchId']!=match_id:
        raise ValueError('mismatched response identity')
    info=match['info']
    if info.get('queueId')!=420 or info.get('mapId')!=11: raise ValueError('ranked solo Summoners Rift required')
    frames={}
    for minute in (10,15):
        frame=next((f for f in timeline['info']['frames'] if f['timestamp']==minute*60000),None)
        if frame:
            frames[str(minute)]={pid:{k:v.get(k) for k in ('totalGold','minionsKilled','jungleMinionsKilled','xp','level')} for pid,v in frame['participantFrames'].items()}
    participants=[{k:p.get(k) for k in ('participantId','championId','teamId','teamPosition','win')} for p in info['participants']]
    safe={'participants':participants,'frames':frames,'game_duration':info['gameDuration'],'queue':420,'rank_provenance':'caller_supplied_not_verified'}
    with db:
        db.execute('INSERT OR IGNORE INTO matches VALUES(?,?,?,?,?)',(match_id,patch_label(info['gameVersion']),region,tier,json.dumps(safe)))
    return True
