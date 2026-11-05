import json
import gzip
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.database import connect,seed
from rift.sheets import validate_mapping
from scripts.check_patch import save_json
parser=argparse.ArgumentParser();parser.add_argument('--summary-only',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
if args.summary_only:
    report=json.loads((root/'reports/sheets_mapping_validation.json').read_text())
    assert report['valid'] and report['read_only'] and report['rows']==14468
    print(json.dumps({'mode':'saved_summary_only; not live Sheets verification','observed_at':report.get('observed_at'),'rows':report['rows'],'valid':report['valid']}))
    sys.exit(0)
lanes=json.loads((root/'data/lane_champions.json').read_text());db=connect(':memory:');seed(db,lanes)
report=validate_mapping(db,json.loads(gzip.decompress((root/'data/read_only/sheets_mapping.json.gz').read_bytes())),lanes)
for lane in report['lanes'].values(): lane.pop('row_map',None)
save_json(root/'reports/sheets_mapping_validation.json',report)
print(json.dumps({k:report[k] for k in ('rows','valid','read_only')},ensure_ascii=False))
if not report['valid']: sys.exit(1)
