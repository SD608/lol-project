"""Network integration check, explicitly separate from offline unittest fixtures."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rift.official import resolve_notes,parse_notes
from scripts.check_patch import save_json
url,html,discovery=resolve_notes('26.22')
notes=parse_notes(html,'26.22',[],strict=True)
expected={'아우렐리온 솔','코르키','케일','로크','마오카이','멜','나피리','럼블','쉔','스몰더','쓰레쉬','빅토르','야스오','자헨'}
assert expected <= set(notes['champions']),notes['champions']
assert {'도란의 활','지배자의 피갑옷'} <= set(notes['items']),notes['items']
assert '아지르' not in notes['champions'] and '세트' not in notes['champions'], 'commentary mention leaked'
assert 'aram_mayhem' in notes['other_modes'] and 'classic' in notes['other_modes']
report={'official_url':url,'discovery':discovery,'live_collection':True,'champions':notes['champions'],'items':notes['items'],'runes':notes['runes'],'digest':notes['digest'],'KR_live_status':'pending','hotfix_status':'not_confirmed'}
save_json(Path('reports/official_26.22_integration.json'),report)
print(json.dumps(report,ensure_ascii=False))
