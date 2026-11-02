"""Compute paired lane metrics from sanitized official timelines."""
import json
import math
from collections import defaultdict
from rift.validation import wilson

LANES={'TOP':'탑','JUNGLE':'정글','MIDDLE':'미드','BOTTOM':'바텀','UTILITY':'서폿'}

def summarize(db, champion_names):
    groups=defaultdict(list)
    for match_id,patch,region,tier,raw in db.execute('SELECT * FROM matches'):
        payload=json.loads(raw)
        if tier=='UNSPECIFIED': continue
        for mine in payload['participants']:
            lane=LANES.get(mine.get('teamPosition'))
            enemies=[p for p in payload['participants'] if p.get('teamPosition')==mine.get('teamPosition') and p.get('teamId')!=mine.get('teamId')]
            if lane is None or len(enemies)!=1: continue
            opponent=enemies[0]
            a,b=champion_names.get(str(mine['championId'])),champion_names.get(str(opponent['championId']))
            if a is None or b is None: continue
            metrics={}
            for minute in (10,15):
                frame=payload['frames'].get(str(minute),{})
                left,right=frame.get(str(mine['participantId'])),frame.get(str(opponent['participantId']))
                if left is None or right is None: continue
                for label,field in (('gold','totalGold'),('xp','xp'),('level','level')):
                    if left.get(field) is not None and right.get(field) is not None: metrics[f'{label}_diff_{minute}']=left[field]-right[field]
                fields=('minionsKilled','jungleMinionsKilled')
                if all(p.get(k) is not None for p in (left,right) for k in fields): metrics[f'cs_diff_{minute}']=sum(left[k]-right[k] for k in fields)
            groups[(patch,lane,a,b,region,tier)].append((match_id,bool(mine.get('win')),metrics))
    result=[]
    for key,rows in groups.items():
        wins=sum(r[1] for r in rows)
        metrics={'game_win_rate':wins/len(rows),'game_win_rate_ci95':wilson(wins,len(rows)),'lane_rating':None}
        for name in {k for _,_,r in rows for k in r}:
            values=[r[name] for _,_,r in rows if name in r]
            mean=sum(values)/len(values)
            # Small samples expose no normal approximation CI.
            se=math.sqrt(sum((x-mean)**2 for x in values)/(len(values)-1)/len(values)) if len(values)>1 else None
            metrics[name]={'mean':mean,'sample_size':len(values),'ci95_normal': [mean-1.96*se,mean+1.96*se] if len(values)>=30 else None}
        result.append({'key':key,'sample_size':len(rows),'metrics':metrics,'sources':[r[0] for r in rows]})
    return result
