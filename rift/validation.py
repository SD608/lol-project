"""Evidence gates do not convert win rates into matchup ratings."""
import math

def wilson(wins, total):
    if total<=0 or not 0<=wins<=total:
        raise ValueError('invalid sample')
    p=wins/total; z=1.959963984540054
    center=(p+z*z/(2*total))/(1+z*z/total)
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/(1+z*z/total)
    return center-half,center+half

def assess(evidence, minimum=100):
    required=('skill_interactions','power_spikes','sources','patch','region','tier')
    reasons=[f'missing:{k}' for k in required if not evidence.get(k)]
    n=evidence.get('sample_size',0)
    if not isinstance(n,int) or isinstance(n,bool) or n<minimum:
        reasons.append('insufficient_sample')
    metrics=evidence.get('metrics',{})
    for minute in (10,15):
        for metric in ('gold','cs','xp'):
            value=metrics.get(f'{metric}_diff_{minute}')
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value):
                reasons.append(f'missing:{metric}_{minute}')
    if evidence.get('conflicting_statistics'):
        reasons.append('conflicting_statistics')
    return {'status':'pending' if reasons else 'auto_checked','rating':None,'reasons':reasons}

def phase(seconds):
    if seconds<0: raise ValueError('negative duration')
    return 'early' if seconds<900 else 'mid' if seconds<1800 else 'late'

def composition(ally, enemy):
    if len(ally)!=5 or len(enemy)!=5 or len(set(ally+enemy))!=10:
        raise ValueError('ten unique champion picks required')
    return {'ally':ally,'enemy':enemy,'status':'unverified','phases':{p:{'score':None,'dimensions':['growth','frontline','damage_balance','cc','engage','poke','sustain','opponent_interactions']} for p in ('early','mid','late')}}
