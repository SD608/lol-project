"""Bounded KR League-V4 seed discovery and Asia Match-V5 history search.

PUUIDs live in memory only. A seed's current rank is not the match's rank.
"""
import os
import re
from collections import Counter
from urllib.parse import quote, urlencode
from rift.http import fetch_json, FetchError

class RiotClient:
    def __init__(self, fetch=fetch_json):
        self.key=os.environ.get('RIOT_API_KEY')
        if not self.key: raise RuntimeError('RIOT_API_KEY missing; no Riot collection performed')
        self.fetch=fetch; self.events=Counter()
    def observe(self,event): self.events[event]+=1
    def __call__(self,url,headers=None):
        from urllib.parse import urlparse
        u=urlparse(url)
        if u.scheme!='https' or u.hostname not in ('kr.api.riotgames.com','asia.api.riotgames.com'): raise ValueError('KR pilot routing only')
        # Do not retain URLs, request objects, exception text or response bodies.
        return self.fetch(url,headers={'X-Riot-Token':self.key},observer=self.observe)

def discover(client, max_seeds=10, history_pages=2, candidate_limit=300):
    if not 1<=max_seeds<=20 or not 1<=history_pages<=3 or not 1<=candidate_limit<=500: raise ValueError('discovery bounds exceeded')
    seeds=[]; seen=set(); counts=Counter(); contexts={}; ids=[]
    for tier in ('EMERALD','DIAMOND'):
        rows=client(f'https://kr.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/I?page=1')
        if not isinstance(rows,list): raise ValueError('invalid league response')
        for row in rows:
            puuid=row.get('puuid')
            if not puuid and row.get('summonerId'):
                try:
                    record=client('https://kr.api.riotgames.com/lol/summoner/v4/summoners/'+quote(row['summonerId'],safe=''))
                    puuid=record.get('puuid')
                except FetchError:
                    counts['seed_lookup_errors']+=1;continue
            if not isinstance(puuid,str) or not puuid: counts['seeds_without_puuid']+=1;continue
            if puuid not in seen:
                seeds.append((puuid,tier+'_I')); seen.add(puuid)
            if len(seeds)>=max_seeds: break
        if len(seeds)>=max_seeds: break
    seen_ids=set()
    for puuid,tier in seeds:
        for page in range(history_pages):
            query=urlencode({'queue':420,'type':'ranked','start':page*20,'count':20})
            try:
                matches=client('https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/'+quote(puuid,safe='')+'/ids?'+query)
            except FetchError:
                counts['history_errors']+=1;break
            if not isinstance(matches,list): raise ValueError('invalid match history')
            for match_id in matches:
                if not isinstance(match_id,str) or not re.fullmatch(r'KR_\d+',match_id): counts['invalid_ids']+=1;continue
                contexts.setdefault(match_id,set()).add(tier)
                if match_id in seen_ids: counts['duplicate_ids']+=1;continue
                seen_ids.add(match_id);ids.append(match_id)
                if len(ids)>=candidate_limit: break
            if len(ids)>=candidate_limit or len(matches)<20: break
        if len(ids)>=candidate_limit: break
    return ids,{k:sorted(v) for k,v in contexts.items()},{'seed_count':len(seeds),**counts,'rank_provenance':'seed_current_rank_only; match_participant_ranks_unknown','sampling_bias':'bounded first-page high-rank seeds; not representative'}
