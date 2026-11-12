"""Compile the supplied workbook once; preserve source verdicts and explanations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.database import ALIASES,initials

ROOT=Path(__file__).resolve().parents[1]
FIELDS={'패치':'patch','포지션':'lane','내 챔피언':'champion','상대 챔피언':'opponent','상성 판정':'verdict','유리한 구간':'power_window','내가 활용할 조건':'advantage','상대에게 조심할 조건':'caution','판정 근거 구분':'basis','검증 메모':'verification_note','근거 URL':'source_url'}
GROUPS={'강한 유리':'hard','유리':'counter','반반':'even','불리':'unfavorable','강한 불리':'unfavorable'}

def compile_workbook(path,roster):
    import openpyxl
    workbook=openpyxl.load_workbook(path,read_only=True,data_only=True)
    rows=[];keys=set();measured=0
    try:
        for lane,names in roster.items():
            if lane not in workbook.sheetnames:raise ValueError('Missing sheet: '+lane)
            sheet=iter(workbook[lane].values);header=next(sheet);index={v:i for i,v in enumerate(header)}
            if not set(FIELDS)<=set(index):raise ValueError('Missing required workbook columns: '+lane)
            for number,values in enumerate(sheet,2):
                if not any(v is not None for v in values):continue
                item={field:values[index[column]] for column,field in FIELDS.items()}
                if any(not isinstance(item[k],str) or not item[k].strip() for k in ('champion','opponent','verdict','advantage','caution','basis')):raise ValueError('Missing source explanation')
                if item['lane']!=lane or item['patch']!='26.22' or item['champion'] not in names or item['opponent'] not in names or item['champion']==item['opponent']:raise ValueError('Invalid source matchup')
                key=(lane,item['champion'],item['opponent'])
                if key in keys:raise ValueError('Duplicate directed matchup')
                keys.add(key)
                grade=item['verdict'].split('(')[0]
                if grade not in GROUPS:raise ValueError('Unrecognized source verdict: '+item['verdict'])
                if item['basis'] not in ('승률·표본 확인','미검증 이론분석'):raise ValueError('Unrecognized evidence')
                item.update(group=GROUPS[grade],evidence='statistical' if item['basis']=='승률·표본 확인' else 'theoretical',source_sheet=lane,source_row=number)
                measured+=item['evidence']=='statistical';rows.append(item)
        expected={(lane,a,b) for lane,names in roster.items() for a in names for b in names if a!=b}
        if keys!=expected:raise ValueError('Incomplete directed coverage')
        names=sorted({n for group in roster.values() for n in group})
        if (len(names),sum(map(len,roster.values())),len(rows),measured)!=(173,266,14468,110):raise ValueError('Unexpected workbook totals')
        return {'schema_version':1,'patch':'26.22','ddragon_version':'16.22.1','source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'counts':{'champions':173,'registrations':266,'matchups':14468,'statistical':110,'theoretical':14358},'lanes':roster,'champions':[{'name':n,'aliases':ALIASES.get(n,[]),'initials':initials(n),'lanes':[l for l,v in roster.items() if n in v]} for n in names],'rows':rows}
    finally:workbook.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workbook',type=Path);p.add_argument('--output',type=Path,default=ROOT/'data/counter-guide-26.22.json');a=p.parse_args()
    data=compile_workbook(a.workbook,json.loads((ROOT/'data/lane_champions.json').read_text()))
    # Only replace the deployable file after the full workbook passes validation.
    temp=a.output.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')));temp.replace(a.output)
    print(json.dumps(data['counts']))
