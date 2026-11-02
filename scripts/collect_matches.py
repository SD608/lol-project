#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.database import connect
from rift.matches import collect
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--db',default='data/rift.sqlite3'); p.add_argument('--region',default='KR'); p.add_argument('--tier',default='UNSPECIFIED'); p.add_argument('match_ids',nargs='+'); a=p.parse_args()
    db=connect(a.db)
    for match_id in a.match_ids:
        print(match_id, 'collected' if collect(db,match_id,a.region,a.tier) else 'duplicate')
