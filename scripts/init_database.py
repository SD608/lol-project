#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.database import connect,seed
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--db',default='data/rift.sqlite3'); a=p.parse_args()
    print(json.dumps(seed(connect(a.db),json.loads(Path('data/lane_champions.json').read_text())),ensure_ascii=False))
