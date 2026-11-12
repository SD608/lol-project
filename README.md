# PICKOU(픽유) — 근거 기반 상성 데이터 시스템

현재 웹앱은 **라인별 챔피언 카운터 도감**입니다. 상대를 선택하면 제공 26.22 엑셀의 카운터·사유가 바로 표시됩니다. [실행·데이터·검증 안내](docs/counter-guide.md). 기존 통계/DB 모듈은 보존하되 현재 UI와 분리했습니다.


웹 화면 없이 패치 변경 감지, SQLite 데이터 보존, 재검증 큐와 경기 통계 검증 기반을 구현합니다. 첨부 키트의 원본 명단 및 기존 테스트를 유지합니다. `CODEX_PROMPT.md`는 첨부 참고문서이며 현재 사용자 요청이 우선합니다.

## 실행

Python 3.12, 외부 패키지 불필요.

```bash
python -m unittest discover -s tests -v
python scripts/init_database.py
python scripts/check_patch.py --db data/rift.sqlite3
# RIOT_API_KEY는 환경/Secrets에 주입. 키 값을 명령줄에 적지 않습니다.
python scripts/collect_matches.py --region KR --tier UNSPECIFIED KR_123456789
```

명단 기준 173명, 라인 등록 266개(탑 65/정글 56/미드 62/바텀 35/서폿 48), 방향성 대진 14,468개입니다. 이는 **첨부 명단 내부의 정합성**이며 최신 라이브 명단 검증을 뜻하지 않습니다. 데이터베이스는 로컬에 생성되며 Git에 업로드하지 않습니다.

## 구현한 기능

- Data Dragon 챔피언/아이템/룬 비교, 양방향 재검증 CSV 및 패치별 JSON 기록. 정적 파일의 변경은 실제 밸런스 변경 확정이 아닙니다.
- 기본 watcher는 아이템/룬 변경 시 전체 대진을 보수적으로 재검토합니다. `rift.patches.impact`는 의존성이 제공된 경우 영향 챔피언으로 좁히고, 누락되면 전체 대진으로 확대합니다.
- 원본 스냅샷, 정제 경기, 통계, 판정, 검증 이력, 패치 이벤트를 분리한 SQLite. 판정 조회 인덱스는 `(patch,lane,champion,opponent,region,tier)`입니다. 원본/통계/판정/경기/패치 이벤트/검증 이력은 UPDATE/DELETE 금지입니다.
- 명단 재입력과 경기 수집 중복 제거. 네트워크 실패 시 detector의 이전 패치 상태 유지. 상태 JSON은 임시 파일 후 교체합니다. 여러 보고서와 SQLite를 아우르는 분산 트랜잭션은 아닙니다.
- Match-V5와 timeline을 명시적 경기 ID로 수집. 랭크 솔로/협곡만 허용, PUUID·소환사 이름·API 키를 저장하지 않습니다. 10/15분 정확한 프레임의 골드/CS/XP/레벨 차이 및 방향별 경기 승률/신뢰구간 계산. 없는 프레임은 0으로 대체하지 않습니다.
- 표본별 평균과 30경기 이상인 지표에 정규근사 신뢰구간, 게임 승률에 Wilson 구간. 게임 승률을 상성 비율로 변환하지 않습니다. `record_statistics`는 통계를 별도 저장합니다.
- 기본 표본 정책 100경기와 10/15분 골드·CS·XP, 스킬 판정·강한 시점·출처·패치 정보를 검증합니다. 정책 통과는 `auto_checked`입니다. `approve`를 통한 수동 등급 승인은 별도 검증 및 이력 기록을 거칩니다. 근거가 모자라면 등급은 NULL입니다.
- 정식 이름, 약칭(미포/아우솔/트페/징키), 초성 검색.
- 5 대 5 픽과 초·중·후반 근거 저장 구조. 점수는 NULL이며 실제 밸류 분석기는 아직 없습니다. 구간은 0~14:59 / 15:00~29:59 / 30:00 이후입니다.
- Google Sheets A:Q 17개 실제 헤더와 일치 여부, 챔피언 대진 중복/명단 검증, 원본 셀 스냅샷 저장 함수. 읽기 전용이며 쓰기 API를 제공하지 않습니다.

## 패치와 CI

`16.21.1` 내부 버전과 `26.21` 사용자용 패치를 분리합니다. 2025년 이후 명명 규칙을 적용하며 2024년까지는 내부 major를 유지합니다. 이후 Riot 명명 정책이 바뀌면 재검토해야 합니다.

매일 KST 10:20에 `.github/workflows/patch-watch.yml`이 테스트 후 버전을 확인하고 보고서와 CSV를 커밋합니다. 동시 실행을 직렬화하고 아티팩트를 남깁니다. push/PR 시 `tests.yml`이 테스트와 명단 DB 초기화를 수행합니다. 자동 이슈 발송은 사용하지 않습니다.

Data Dragon watcher의 출시 상태와 공식 수집 상태는 분리합니다. 공식 노트는 목록 탐색과 본문 구조 검증 후 별도 파이프라인으로 수집하며 동일 버전의 관련 변경 목록도 비교합니다. KR 서버 적용 완료 근거가 없으면 pending입니다. 노트 수집이나 Data Dragon만으로 라이브 적용을 확정하지 않습니다.

## 외부 연결 상태와 제약

- Google Sheets 기준문서는 연결 도구로 메타데이터, 탑 A1:Q3 및 나머지 네 라인 A1:Q2를 읽어 5개 라인의 헤더 매핑을 확인했습니다. 전체 기존 데이터 가져오기는 하지 않았고 원본에 쓰지 않았습니다.
- 무인 Sheets 연동은 별도 OAuth/서비스 계정과 최소 권한 구성이 필요합니다. 키는 GitHub Secrets/Workload Identity로 관리하고 저장소에 넣지 않습니다. 정확한 행 매핑 및 변경 전 값 대조를 갖춘 쓰기 경로는 아직 없습니다.
- Riot API 키는 이 환경에 구성되지 않았습니다. 실제 경기 수집은 미실행입니다. 티어는 호출자 제공값이며 경기 당시 티어를 증명하지 않으므로 분석 전 출처를 검증해야 합니다.
- HTTP 429/5xx/네트워크 오류는 지수 백오프와 숫자형 Retry-After를 적용합니다. Riot의 앱/메서드별 전역 요청 버킷 및 성공 응답 rate-limit 헤더 기반 분산 조절은 후속 작업입니다. 운영 대량 수집에 사용하기 전 완료해야 합니다.
- LoLalytics/SeeMeta 크롤러는 없습니다. 이용 조건/라이선스를 확인하기 전 해당 데이터를 수집하지 않습니다.

실제 테스트·원격 CI 상태 및 다음 단계는 [개발 로드맵](ROADMAP.md)을 참조하십시오.

## 2단계 (2026-11-05)

`python scripts/check_official.py`는 현재 운영 패치의 한국어 Riot 공식 노트를 매번 가져옵니다. 기사의 협곡 변경 목록 SHA-256으로 같은 패치 내 수정 후보를 감지하고 기사 편집 digest는 별도로 저장합니다. 수정은 핫픽스 **후보**이며 편집 수정과 실제 밸런스 변경을 자동 확정하지 않습니다. 원문 텍스트, 카테고리별 변경 문장, 출처 URL, digest, 패치별 이력과 큐를 보관합니다. 구조 인식 실패 및 아이템/룬 의존성 불명 시 전체 대진을 재검토합니다. 현재 공식 문장의 아이템/룬 ID 매핑은 미완료이므로 보수적 전체 검토를 사용합니다.

KR 적용은 `RIOT_KR_LIVE_EVIDENCE_URL` 저장소 변수로 지정한 실제 한국 공식 공지의 패치 번호·한국 서버·완료 문장을 확인합니다. 노트 게시 자체나 Data Dragon 갱신은 적용 근거가 아닙니다. 근거가 없으면 pending입니다. 공식 공지 자동 탐색 및 의미 판독의 완전성은 보장하지 않으며 수동 근거 검토가 필요합니다.

`rift.limiter`는 단일 프로세스/단일 API 키 워커에서 직렬 호출, 1.3초 최소 간격, 120초당 90회 제한 및 앱/메서드 응답 헤더 소진 시 대기를 적용합니다. 여러 프로세스에서 동일 키를 공유하는 운영은 지원하지 않습니다. API 키는 수동 수집 workflow의 GitHub Secrets로만 주입합니다. 키 미설정은 실패이며 수집 성공으로 표시하지 않습니다. 누락 프레임은 통계에서 제외하고 기존 자료를 수정하지 않습니다.

### 2단계 초기 검증 기록 — 수정 전

28개 테스트 로컬/Actions 통과: https://github.com/SD608/lol-project/actions/runs/41942136649 . 공식 수집 실실행은 현재 `26.22`의 예상 Riot URL에서 HTTP 404로 실패: https://github.com/SD608/lol-project/actions/runs/41942136686 . 따라서 실제 공식 노트 수집 완료·KR 적용 확인·실제 핫픽스 발견을 주장하지 않습니다. URL 발견/공식 게시 여부 확인이 다음 작업이며, 404에서 우회 수집하거나 라이브 적용을 추정하지 않습니다. 해당 실행은 원격 패치 상태/공식 이력을 커밋하지 않았습니다. 공식 노트 구조화/핫픽스 후보/완료 근거는 모의 HTML 테스트 검증입니다. 실제 Match-V5는 키가 없어 실행하지 않았습니다.


## PICKOU 공식 수집 오류 수정

공식 게임 업데이트 목록의 실제 링크를 탐색하고 공식 호스트·경로·정확한 패치 경계·문서 h1을 검증합니다. 목록에 없을 때만 알려진 공식 canonical 후보를 검증하며, 404 링크는 재시도하지 않습니다. 기사 본문의 `patch-notes-container`와 `patch-change-block`의 실제 변경 목록을 읽습니다. 소개/개발자 해설의 단순 이름 언급은 변경 챔피언으로 분류하지 않습니다. 아수라장·클래식과 기타 섹션은 협곡 변경 목록에서 분리합니다. 인식 불가 구조는 명시적인 pending 오류 보고서를 남기고 기존 공식 상태를 보존합니다.

밸런스 digest는 협곡의 실제 변경 블록만 포함하며 기사 편집 digest와 분리합니다. 본문 편집만으로 재검증 큐를 만들지 않습니다. 변경 목록의 문구 수정은 의미적 동등성을 자동 판별할 수 없으므로 밸런스/핫픽스 **후보**로만 표시합니다. 공식 노트의 추가 패치 언급도 한국 적용 완료를 증명하지 않습니다. 자동 확정 핫픽스는 없습니다.

`python scripts/verify_official_2622.py`는 네트워크 통합 검사로 실제 공식 목록과 26.22 기사를 수집합니다. 오프라인 unittest와 구분하며 `reports/official_26.22_integration.json`을 생성합니다. 기존 28개를 포함한 36개 오프라인 테스트 통과. 실제 Actions 결과는 ROADMAP에 기록합니다. 경로/DB 명칭은 유지하며 상성 등급은 생성·복사하지 않습니다.


### PICKOU 수정 후 실제 검증 결과

- 실제 공식 목록에서 탐색한 URL: https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-22-notes
- 실제 수집·본문 분석·26.22 통합 검사·보고서 커밋 성공: https://github.com/SD608/lol-project/actions/runs/41943529719
- 기존 28개 + 신규 8개 = 36개 오프라인 테스트 Actions 성공: https://github.com/SD608/lol-project/actions/runs/41943529723
- 실제 수집 결과: `reports/official_26.22_integration.json`. 상세 변경 목록/출처/digest/모드별 내용은 `reports/official_latest.json`, 이력은 `reports/official_history/`.
- 협곡 챔피언: 아우렐리온 솔, 코르키, 케일, 로크, 마오카이, 멜, 나피리, 럼블, 쉔, 스몰더, 쓰레쉬, 빅토르, 야스오, 자헨.
- 협곡 아이템: 도란의 활, 지배자의 피갑옷. 룬 변경 블록 없음. 아수라장/클래식 변경은 협곡 대상에서 제외.
- KR 적용 완료 pending, 실제 핫픽스 확인 없음. 핫픽스/편집/404/구조 변경 경로는 모의 테스트로 검증했으며 실제 핫픽스 발생을 주장하지 않음. DB/상성 등급/Sheets 변경 없음.

## PICKOU 3단계 — KR 경기 실증 파이프라인

기존 36개 테스트를 유지하고 경기 ID 탐색/역할 검증/패치 분리/타임라인 누락/비밀값 미기록/보고서/Sheets 계획 테스트를 추가했습니다.

```bash
# RIOT_API_KEY를 환경에 안전하게 주입한 경우만 실제 실행
python scripts/run_pilot.py --target 100
python scripts/validate_sheets_mapping.py
```

- League-V4의 KR 에메랄드 I·다이아몬드 I 첫 페이지에서 최대 10명의 현재 랭크 시드를 확인하고 Asia Match-V5에서 솔로랭크 경기 ID를 탐색합니다. 시드당 최대 40개 기록, 총 후보 최대 300개, 유효 경기 최대 100개로 제한합니다. 현재 높은 티어의 시드를 선정한 편향된 표본이며 경기 당시의 참가자 티어를 증명하지 않습니다. PUUID와 소환사명은 메모리에서만 사용합니다.
- 통계 티어 키 `UNKNOWN_AT_MATCH__SEED_CURRENT_...`는 경기 티어 미확인과 현재 시드 티어 관찰을 명시합니다. 지역·패치·역할·챔피언·상대·티어 코호트별로 분리하며 미확인 티어도 누락하지 않습니다.
- 최신 공식 KR 적용 근거가 저장되어 있고 48시간 이내이며 Data Dragon 후보 패치와 일치할 때만 해당 패치를 목표로 제한합니다. 그렇지 않으면 `pending` 상태에서 경기 gameVersion별로 나누어 보관하고 최신 라이브 표본이라고 주장하지 않습니다. 이 제한 시간은 운영 정책이며 패치 적용 자체를 증명하지 않습니다.
- 10명/양 팀 역할 유일성, Riot teamPosition과 individualPosition 불일치를 검사합니다. 불명확한 역할 경기는 보존하되 기본 통계에서 제외합니다. 실제 위치 기반의 모든 인게임 라인 스왑을 탐지하지는 못합니다. 정글 지표는 동선·맵 영향, 서포터 지표는 공유 라인·로밍 영향으로 해석합니다.
- 10/15분 정확한 프레임의 골드·전체 CS(라인+중립)·라인 CS·중립 CS·경험치·레벨 차이를 계산합니다. 없는 프레임/지표는 대체하지 않습니다. 지표별 표본 수를 따로 저장하고 표본 30개 이상에서 평균의 정규근사 95% 구간을 제공합니다. 작은 표본의 평균 구간은 NULL이고 승률은 Wilson 구간을 사용합니다. 게임 승률을 라인전 등급으로 변환하지 않습니다.
- 같은 경기의 A→B/B→A는 별도 방향성 관찰이며 각 방향에서 경기 ID당 한 번 집계합니다. 경기 원본은 기존 append-only 테이블에 저장하고 통계는 별도 스냅샷입니다. 여러 통계 스냅샷의 표본 수를 합산하면 안 됩니다.
- 상태: 최소 지표별 100경기 미만 `insufficient_sample`, 통계 충족/스킬 근거 부족 `evidence_pending`, 근거 게이트 통과 `auto_checked`, 같은 표본·지표에 대한 기존 수동 승인이 있을 때만 `approved`. DB의 기존 `manual_approved` 상태는 유지하며 보고서에서 `approved`로 표현합니다. 자동 승인이나 등급 생성은 없습니다.
- `.github/workflows/riot-pilot.yml`은 GitHub Secrets의 RIOT_API_KEY만 사용합니다. 키가 없으면 exit 2와 `key_missing` 보고서를 남기며 수집 성공으로 처리하지 않습니다. 별도의 기존 명시적 ID workflow와 같은 concurrency 그룹으로 키를 공유하는 작업을 직렬화합니다. 다른 저장소/프로세스가 같은 키를 사용하는 분산 운영은 지원하지 않습니다.
- 결과는 `reports/collection/`의 JSON·Markdown에 보관하고 실제 확보된 경우에만 최대 5개 통계 예시를 출력합니다. 원본 DB는 Git에 올리지 않고 Actions artifact로 7일 보관합니다. 다음 수집 실행에 자동 복원하는 영구 DB 운영은 후속 작업이며 지속하려면 기존 DB를 `--db`로 제공해야 합니다.

### 3단계 Sheets 읽기 전용 검증

연결 도구로 5개 라인의 모든 A/B 대진 열과 A:Q 헤더를 실제 읽었습니다. 173명·266개 라인 등록·14,468개 대진이 명단과 DB의 행·챔피언·라인 기준으로 일치했습니다. 압축 스냅샷 `data/read_only/sheets_mapping.json.gz`는 로컬에서만 보관하고 GitHub에 게시하지 않습니다. GitHub에는 원본 행이 없는 검증 요약만 저장합니다. Actions의 `--summary-only`는 저장된 요약을 확인하며 실제 시트를 재조회한 검증이 아닙니다. 기존 상성 셀은 읽어 가져오거나 변경하지 않았습니다.

실제 통계가 생기면 원본 행 키·source digest·기존 패치 재조회·별도 지역/티어 목적지 매핑을 요구하는 검토 계획만 생성합니다. 상성 등급 열 D/E는 계획에서도 제외하고 원본 쓰기 API는 없습니다. Google 쓰기는 별도 승인 및 정확한 목적지 매핑 전까지 비활성화합니다.


### 3단계 실제 실행 결과

- 기존 36개 포함 54개 테스트 통과: https://github.com/SD608/lol-project/actions/runs/41946190060
- 실증 workflow: https://github.com/SD608/lol-project/actions/runs/41946190139 — RIOT_API_KEY GitHub Secret 미설정으로 key_missing(exit 2). 실패를 성공으로 처리하지 않으며 JSON·Markdown 아티팩트 업로드는 성공했습니다.
- 실제 API 요청 0 / 실제 경기 0 / 승인된 매치업 0 / 실제 통계 예시 0. 테스트용 모의 데이터를 실제 수집 자료로 보고하지 않았습니다.
- 지속 기록: `reports/stage3_execution.json`, `reports/stage3_execution.md`. 실제 표본 100건과 통계 예시 최대 5건은 키 설정 후 실증해야 합니다.
- 다음 단계: 저장소 Settings → Secrets and variables → Actions에 RIOT_API_KEY를 설정하고 PICKOU KR Riot pilot을 수동 실행합니다. 키 값을 채팅·코드에 붙여넣지 않습니다.


## PICKOU Supabase PostgreSQL — applied 2026-11-05

- **Target only:** Supabase project `PICKOU` (`yspqfkcexibucnwvxdmw`, Tokyo). Existing SD Supabase projects, SQLite, Google Sheets: **not modified**.
- Database schema: private `pickou` (14 tables), 21 foreign-key constraints; `anon` and `authenticated` have no schema USAGE, no table grants. All 14 tables have RLS enabled (no browser-facing policies). FastAPI must use separately authorized server-side DB access; never expose service keys in Next.js.
- Applied migration records: `20261105013751_pickou_foundation_v1_with_immutable_import_ledger` and `pickou_enable_rls_and_fk_indexes`. SQL copies in `database/migrations/`; an exact-value roster seed SQL archive is also saved there (seed executed through SQL, not registered as DDL migration).
- Input: `data/lane_champions.json` Git blob `4c0e31de879718a42e4a676914dcb7996a8f1f3f`. The source snapshot and import ledger preserve origin/revision and are append-only.
- **Verified by actual PostgreSQL SQL:** 173 champions / 266 champion-lane registrations / 14,468 directional matchups; missing foreign keys 0, duplicate pairs 0, self-matchups 0, missing reverse pairs 0. Five lane counts: top 65, jungle 56, mid 62, bot 35, support 48.
- Patch/event evidence, matchup statistics, decisions and validation history are separate append-only models; the **actual match statistics and matchup ratings have not been collected or asserted**. Missing ratings are not 5:5.
- Not yet done: real FastAPI/PostgreSQL integration, privileged backend authorization integration tests, Next.js responsive UI, deployment, and API security/production load tests. Schema-only and seed validation must not be confused with end-to-end deployment.


## PICKOU 4.1 — 라이브 최소권한 DB 역할 적용 (2026-11-05)

- 적용 대상: PICKOU `yspqfkcexibucnwvxdmw` 한정. SQL migration: `20261105020903_pickou_api_reader_select_only_rls`.
- `pickou_api_reader` LOGIN 역할 생성, 슈퍼유저/BYPASSRLS/CREATE 권한 없음. 인증 비밀번호는 **NULL** (미설정). 필요한 7개 테이블에 SELECT만, 각 테이블에 역할 전용 SELECT RLS 정책. 7개 나머지 테이블 접근 없음. 브라우저 `anon`/`authenticated` 사용 권한 없음.
- 실제 Supabase SQL 카탈로그 검증: 14 tables, 173/266/14,468, 7개 역할 전용 정책, INSERT/UPDATE/DELETE 0개. 이력/기존 데이터 변경 없음.
- 실제 역할 전환 SQL (FastAPI 아님)에서 173/266/14,468, 탑 우르곳 상대 64, 페이지 10개, 패치 0개 SELECT 검증. INSERT/UPDATE/DELETE는 실제 실행 없이 EXPLAIN 권한 거부 확인. 재현용 `database/tests/verify_pickou_reader_permissions.sql`.
- 테스트 중 권한 변경은 ROLLBACK. 관리자의 기존 역할 생성자 멤버십은 SET=false/INHERIT=false, 추가 SET 권한 유지되지 않음.
- **실제 FastAPI 로그인/연결은 미완료**: 비밀번호와 backend-only 비밀 저장소가 없으며 공개 저장소에 비밀값을 기록하지 않음. PR #2는 Draft 유지.
