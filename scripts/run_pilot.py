#!/usr/bin/env python3
"""Secrets-backed live pilot. A missing key produces an error report and exit 2."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.database import connect,seed
from rift.discovery import RiotClient
from rift.http import FetchError
from rift.pilot import empty_report,pilot,save_report,live_context

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--target',type=int,default=100);p.add_argument('--db',type=Path);a=p.parse_args()
    report=empty_report();report['patch_context']=live_context(a.root);client=None;db=None;code=0
    try:
        client=RiotClient()
        # Public champion names are fetched only when actual collection is authorized by a key.
        from scripts.check_patch import fetch_json,save_json,CDN
        version=json.loads((a.root/'data/patch_state.json').read_text())['ddragon_version']
        data=fetch_json(CDN.format(version=version,filename='champion.json'))
        save_json(a.root/'data/champion_ids.json',{str(c['key']):c['name'] for c in data['data'].values()})
        db=connect(a.db or a.root/'data/rift.sqlite3')
        seed(db,json.loads((a.root/'data/lane_champions.json').read_text()))
        report=pilot(db,a.root,client,target=a.target)
    except RuntimeError:
        report['status']='key_missing' if client is None else 'collection_error';report['errors']={report['status']:1};code=2
    except (ValueError,KeyError,TypeError,OSError):
        report['status']='invalid_configuration_or_response';report['errors']={report['status']:1};code=2
    finally:
        if client:
            report['api_events']=dict(client.events);report['actual_api_success']=client.events.get('responses_ok',0)>0
        if db: db.close()
        save_report(a.root,report)
    print(json.dumps({k:report[k] for k in ('status','actual_api_success','collected_matches','valid_matches','verified_matchups')}))
    return code
if __name__=='__main__': sys.exit(main())
