#!/usr/bin/env python3
"""Detect Data Dragon changes; preserve patch history; prepare manual matchup review.

No Riot API key required for this watcher. It does NOT infer counter ratings.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rift.http import fetch_json as resilient_fetch
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = 'https://ddragon.leagueoflegends.com/api/versions.json'
CDN = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/{filename}'


def fetch_json(url: str):
    return resilient_fetch(url, headers={'User-Agent':'RiftMatchupPatchMonitor/0.2'})


def patch_label(version: str) -> str:
    """Data Dragon 16.21.1 -> Riot's 2026 public label 26.21."""
    major, minor, *_ = version.split('.')
    return f'{int(major) + 10 if int(major) >= 15 else int(major)}.{int(minor):02d}'


def changed_champions(previous: dict, current: dict) -> list[dict]:
    left, right = previous.get('data', {}), current.get('data', {})
    keys = set(left) | set(right)
    output = []
    fields = ['stats', 'spells', 'passive', 'info', 'partype', 'tags']
    for champion_id in sorted(keys):
        before, after = left.get(champion_id), right.get(champion_id)
        if before is None or after is None:
            changes = ['added_or_removed']
        else:
            changes = [field for field in fields if before.get(field) != after.get(field)]
        if changes:
            output.append({
                'id': champion_id,
                'name': (after or before).get('name', champion_id),
                'fields': changes,
            })
    return output


def changed_items(previous: dict, current: dict) -> list[dict]:
    l, r = previous.get('data', {}), current.get('data', {})
    fields = ['stats', 'gold', 'description', 'inStore', 'maps', 'requiredAlly', 'specialRecipe']
    output = []
    for item_id in sorted(set(l) | set(r)):
        b, a = l.get(item_id), r.get(item_id)
        changes = ['added_or_removed'] if b is None or a is None else [f for f in fields if b.get(f) != a.get(f)]
        if changes:
            output.append({'id': item_id, 'name': (a or b).get('name', item_id), 'fields': changes})
    return output


def flatten_runes(data: list) -> dict:
    return {str(slot['id']): slot for tree in data for group in tree.get('slots', []) for slot in group.get('runes', [])}


def changed_runes(previous: list, current: list) -> list[dict]:
    old, new = flatten_runes(previous), flatten_runes(current)
    answer = []
    for rune_id in sorted(set(old) | set(new)):
        b, a = old.get(rune_id), new.get(rune_id)
        fields = ['added_or_removed'] if b is None or a is None else [f for f in ['name', 'shortDesc', 'longDesc'] if b.get(f) != a.get(f)]
        if fields:
            answer.append({'id': rune_id, 'name': (a or b).get('name', rune_id), 'fields': fields})
    return answer


def make_review_queue(lanes: dict[str, list[str]], champions: set[str], system_changed: bool, label: str):
    """Make DIRECTED matchups: A->B and B->A. No fabricated ratings."""
    queue = []
    for lane, names in lanes.items():
        for mine in names:
            for opponent in names:
                if mine == opponent:
                    continue
                if not (system_changed or mine in champions or opponent in champions):
                    continue
                why = '아이템·룬 체계 변경 검토' if system_changed else '한쪽 챔피언의 패치 변경'
                queue.append({'패치': label, '라인': lane, '내 챔피언': mine,
                              '상대 챔피언': opponent, '재검증 이유': why,
                              '상성 등급': '', '상태': '검증 대기'})
    return queue


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as fp:
        json.dump(obj, fp, ensure_ascii=False, indent=2)
        fp.write('\n')
        temporary = fp.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--db', type=Path, help='Optional persistent review database')
    args = parser.parse_args()
    root = args.root
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as fp:
            fp.write('changed=false\n')
    state_file = root / 'data/patch_state.json'
    state = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
    versions = fetch_json(VERSIONS)
    latest = versions[0]
    previous = state.get('ddragon_version')
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    if not previous:
        state = {'ddragon_version': latest, 'public_patch': patch_label(latest), 'initialized_at_utc': now}
        save_json(state_file, state)
        print(f'Initial baseline set: {latest}. No old-patch comparisons yet.')
        return
    if previous == latest:
        save_json(root / 'reports/check_status.json', {
            'checked_at_utc': now, 'ddragon_version': latest,
            'public_patch': patch_label(latest), 'static_version_changed': False,
            'release_confirmation': 'pending_official_notes_and_regional_live_evidence',
            'ratings_changed': False, 'source': VERSIONS})
        print(f'No Data Dragon release change: {latest}')
        return

    def asset(version: str, filename: str):
        return fetch_json(CDN.format(version=version, filename=filename))

    champion_changes = changed_champions(asset(previous, 'championFull.json'), asset(latest, 'championFull.json'))
    item_changes = changed_items(asset(previous, 'item.json'), asset(latest, 'item.json'))
    rune_changes = changed_runes(asset(previous, 'runesReforged.json'), asset(latest, 'runesReforged.json'))

    label = patch_label(latest)
    lane_map = json.loads((root / 'data/lane_champions.json').read_text(encoding='utf-8'))
    changed_names = {rec['name'] for rec in champion_changes}
    roster_names = {name for champions in lane_map.values() for name in champions}
    unmatched_names = sorted(changed_names - roster_names)
    queue = make_review_queue(lane_map, changed_names, bool(item_changes or rune_changes), label)
    report = {
        'checked_at_utc': now,
        'detected_ddragon_version': latest,
        'previous_ddragon_version': previous,
        'public_patch_label': label,
        'source': VERSIONS,
        'review_status': '자동감지·인간검증필요',
        'release_confirmation': 'pending_official_notes_and_regional_live_evidence',
        'official_notes_url': None,
        'live_region': 'KR',
        'ratings_changed': False,
        'warning': 'Data Dragon 반영은 패치 출시와 시차가 날 수 있음. 정적 데이터의 문자열 변화만으로 게임 내 상성 7:3 등을 판정할 수 없음.',
        'changed_champions': champion_changes,
        'unmatched_changed_champion_names': unmatched_names,
        'changed_items': item_changes,
        'changed_runes': rune_changes,
        'affected_directed_matchups': len(queue),
    }
    save_json(root / 'reports/latest.json', report)
    save_json(root / 'reports/history' / f'{previous}-to-{latest}.json', report)
    (root / 'reports').mkdir(parents=True, exist_ok=True)
    with (root / 'reports/latest_review_queue.csv').open('w', newline='', encoding='utf-8-sig') as fp:
        columns = ['패치', '라인', '내 챔피언', '상대 챔피언', '재검증 이유', '상성 등급', '상태']
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(queue)
    if args.db:
        from rift.database import connect, seed, enqueue
        db = connect(args.db)
        seed(db, lane_map)
        enqueue(db, queue)
        with db:
            db.execute('INSERT INTO patch_events(ddragon_version,public_patch,region,status,evidence) VALUES(?,?,?,?,?)',
                       (latest,label,'KR','pending',json.dumps(report,ensure_ascii=False)))
        db.close()
    state.update({'ddragon_version': latest, 'public_patch': label, 'last_detection_at_utc': now})
    save_json(state_file, state)
    print(json.dumps({'new_version': latest, 'label': label, 'champions': len(champion_changes),
                      'items': len(item_changes), 'runes': len(rune_changes), 'review_rows': len(queue)}, ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as fp:
            fp.write(f'changed=true\npatch_label={label}\nddragon_version={latest}\nchampion_count={len(champion_changes)}\nreview_count={len(queue)}\n')


if __name__ == '__main__':
    main()
