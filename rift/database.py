"""SQLite storage. Source records and decisions are append-only."""
import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS champions(name TEXT PRIMARY KEY, aliases TEXT NOT NULL, initials TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lane_champions(lane TEXT, champion TEXT REFERENCES champions(name), PRIMARY KEY(lane,champion));
CREATE TABLE IF NOT EXISTS matchups(lane TEXT, champion TEXT, opponent TEXT, PRIMARY KEY(lane,champion,opponent), CHECK(champion<>opponent));
CREATE TABLE IF NOT EXISTS snapshots(digest TEXT PRIMARY KEY, source TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS matches(match_id TEXT PRIMARY KEY, patch TEXT NOT NULL, region TEXT NOT NULL, tier TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS statistics(id INTEGER PRIMARY KEY, patch TEXT NOT NULL, lane TEXT NOT NULL, champion TEXT NOT NULL, opponent TEXT NOT NULL, region TEXT NOT NULL, tier TEXT NOT NULL, sample_size INTEGER NOT NULL CHECK(sample_size>=0), metrics TEXT NOT NULL, sources TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, patch TEXT NOT NULL, lane TEXT NOT NULL, champion TEXT NOT NULL, opponent TEXT NOT NULL, region TEXT NOT NULL, tier TEXT NOT NULL, rating TEXT CHECK(rating IN ('9:1','8:2','7:3','6:4','5:5','4:6','3:7','2:8','1:9')), status TEXT NOT NULL CHECK(status IN ('unverified','pending','auto_checked','manual_approved','rejected')), evidence TEXT NOT NULL, statistic_id INTEGER REFERENCES statistics(id), reviewer TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, CHECK(status<>'manual_approved' OR (rating IS NOT NULL AND reviewer IS NOT NULL)));
CREATE INDEX IF NOT EXISTS decision_lookup ON decisions(patch,lane,champion,opponent,region,tier);
CREATE TABLE IF NOT EXISTS patch_events(id INTEGER PRIMARY KEY, ddragon_version TEXT NOT NULL, public_patch TEXT NOT NULL, region TEXT NOT NULL, status TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS review_queue(patch TEXT,lane TEXT,champion TEXT,opponent TEXT,region TEXT,tier TEXT,reason TEXT,status TEXT DEFAULT 'pending',PRIMARY KEY(patch,lane,champion,opponent,region,tier));
CREATE TABLE IF NOT EXISTS validation_history(id INTEGER PRIMARY KEY, decision_id INTEGER REFERENCES decisions(id), event TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS composition_evidence(id INTEGER PRIMARY KEY, patch TEXT NOT NULL, champion TEXT NOT NULL, phase TEXT CHECK(phase IN ('early','mid','late')), dimensions TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unverified');
'''
INITIALS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
ALIASES = {'미스 포츈':['미포'], '아우렐리온 솔':['아우솔'], '트위스티드 페이트':['트페'], '징크스':['징키'], '케이틀린':['케틀','케틀린']}

def initials(name):
    return ''.join(INITIALS[(ord(c)-0xAC00)//588] if 0xAC00<=ord(c)<=0xD7A3 else c for c in name).replace(' ','')

def connect(path):
    db=sqlite3.connect(path)
    db.executescript(SCHEMA)
    for table in ('snapshots','statistics','decisions','patch_events','validation_history','matches','composition_evidence'):
        for operation in ('UPDATE','DELETE'):
            db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'append-only record'); END")
    return db

def snapshot(db, source, payload):
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True)
    digest=hashlib.sha256(raw.encode()).hexdigest()
    db.execute('INSERT OR IGNORE INTO snapshots(digest,source,payload) VALUES(?,?,?)',(digest,source,raw))
    return digest

def seed(db, lanes):
    names=set(n for group in lanes.values() for n in group)
    if any(len(v)!=len(set(v)) for v in lanes.values()):
        raise ValueError('duplicate champion in lane')
    with db:
        snapshot(db,'patch-kit/lane_champions.json',lanes)
        db.executemany('INSERT OR IGNORE INTO champions VALUES(?,?,?)',[(n,json.dumps(ALIASES.get(n,[]),ensure_ascii=False),initials(n)) for n in sorted(names)])
        db.executemany('INSERT OR IGNORE INTO lane_champions VALUES(?,?)',[(l,n) for l,v in lanes.items() for n in v])
        db.executemany('INSERT OR IGNORE INTO matchups VALUES(?,?,?)',[(l,a,b) for l,v in lanes.items() for a in v for b in v if a!=b])
    return {t:db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('champions','lane_champions','matchups')}

def search(db, query):
    q=query.replace(' ','').casefold()
    return [name for name,aliases,initial in db.execute('SELECT * FROM champions') if any(q in x.replace(' ','').casefold() for x in [name,initial,*json.loads(aliases)])]

def enqueue(db, rows, region='KR', tier='UNSPECIFIED'):
    with db:
        db.executemany('INSERT OR IGNORE INTO review_queue(patch,lane,champion,opponent,region,tier,reason) VALUES(?,?,?,?,?,?,?)',[(r['패치'],r['라인'],r['내 챔피언'],r['상대 챔피언'],region,tier,r['재검증 이유']) for r in rows])

def record_statistics(db, group):
    with db:
        cursor=db.execute('INSERT INTO statistics(patch,lane,champion,opponent,region,tier,sample_size,metrics,sources) VALUES(?,?,?,?,?,?,?,?,?)',(*group['key'],group['sample_size'],json.dumps(group['metrics']),json.dumps(group['sources'])))
    return cursor.lastrowid

def approve(db, statistic_id, rating, evidence, reviewer):
    from rift.validation import assess
    if not reviewer or not reviewer.strip(): raise ValueError('reviewer required')
    record=db.execute('SELECT patch,lane,champion,opponent,region,tier,sample_size,metrics,sources FROM statistics WHERE id=?',(statistic_id,)).fetchone()
    if record is None: raise ValueError('missing statistics')
    metrics=json.loads(record[7]); samples=[]; flat={}
    for minute in (10,15):
        for metric in ('gold','cs','xp'):
            name=f'{metric}_diff_{minute}'; entry=metrics.get(name,{})
            flat[name]=entry.get('mean'); samples.append(entry.get('sample_size',0))
    verified={**evidence,'patch':record[0],'region':record[4],'tier':record[5],'sample_size':min(samples),'metrics':flat,'sources':json.loads(record[8])}
    if assess(verified)['status']!='auto_checked': raise ValueError('evidence gate failed')
    with db:
        cursor=db.execute('INSERT INTO decisions(patch,lane,champion,opponent,region,tier,rating,status,evidence,statistic_id,reviewer) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(*record[:6],rating,'manual_approved',json.dumps(verified),statistic_id,reviewer))
        db.execute('INSERT INTO validation_history(decision_id,event,evidence) VALUES(?,?,?)',(cursor.lastrowid,'manual_approved',json.dumps({'reviewer':reviewer})))
    return cursor.lastrowid
