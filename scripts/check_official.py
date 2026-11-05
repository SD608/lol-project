#!/usr/bin/env python3
"""Fetch even when DDragon is unchanged. No ratings are written."""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.official import fetch_text,parse_notes,live_evidence
from rift.patches import impact
from scripts.check_patch import save_json

def check(root, patch, fetch=fetch_text, live_url=None):
    lanes=json.loads((root/'data/lane_champions.json').read_text())
    url=f'https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-{patch.replace(".","-")}-notes/'
    notes=parse_notes(fetch(url),patch,{n for names in lanes.values() for n in names})
    live=False
    if live_url:
        from urllib.parse import urlparse
        u=urlparse(live_url)
        if u.scheme!='https' or u.hostname!='www.leagueoflegends.com' or not u.path.startswith('/ko-kr/news/'): raise ValueError('KR official evidence URL required')
        live=live_evidence(fetch(live_url),patch)
    state_path=root/'data/official_state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    previous=state.get(patch)
    changed=previous!=notes['digest']
    deps_path=root/'data/dependencies.json'
    deps=json.loads(deps_path.read_text()) if deps_path.exists() else {}
    unknown=notes['parse_status']=='unknown'
    queue=impact(lanes,notes['champions'],['official:unknown'] if notes['items_changed'] or unknown else [],['official:unknown'] if notes['runes_changed'] else [],deps) if changed else []
    for row in queue: row['패치']=patch
    report={'patch':patch,'notes_url':url,'live_url':live_url,'release_status':'confirmed' if live else 'pending','checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'content_digest':notes['digest'],'previous_digest':previous,'same_patch_revision':bool(previous and changed),'changed':changed,'ratings_changed':False,'notes':notes,'review_queue':queue}
    # All network and parsing work finishes before any existing state is changed.
    save_json(root/'reports/official_latest.json',report)
    save_json(root/'reports/official_history'/f'{patch}-{notes["digest"]}.json',report) if changed else None
    state[patch]=notes['digest']; save_json(state_path,state)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--patch');p.add_argument('--live-url');a=p.parse_args()
    patch=a.patch or json.loads((a.root/'data/patch_state.json').read_text())['public_patch']
    r=check(a.root,patch,live_url=a.live_url or os.environ.get('RIOT_KR_LIVE_EVIDENCE_URL'))
    print(json.dumps({k:r[k] for k in ('patch','release_status','changed','same_patch_revision','content_digest')}))
