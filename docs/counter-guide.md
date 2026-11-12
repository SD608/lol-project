# PICKOU 카운터 도감 · 26.22

포지션을 고르고 상대 챔피언을 선택하면, 해당 상대를 상대하기 좋은 챔피언과 엑셀에 적힌 이유가 즉시 나타납니다. 로그인, 분석 시작 버튼, 개인 전적 및 관리자 UI는 없습니다.

## 실행

저장소 루트에서 백엔드를 시작합니다. 새 카운터 API는 DATABASE_URL이나 Supabase 인증 없이 동작합니다. 기존 DB API를 사용할 때만 기존 읽기 전용 DATABASE_URL 설정이 필요합니다.

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

별도 터미널:

```bash
cd frontend
npm ci
npm run dev
# http://localhost:3000
```

프로덕션은 `npm run build && npm start`. Next.js 서버의 `PICKOU_API_ORIGIN`은 기본 `http://127.0.0.1:8000`이며 브라우저에는 이 값을 노출하지 않습니다. Next.js 서버에서 FastAPI로 연결 가능한 주소를 지정합니다. 같은 출처 `/api/counter-guide/*` 프록시를 사용하므로 별도의 CORS 완화가 필요 없습니다. Dockerfile도 정적 JSON을 포함합니다.

## 데이터와 조회 방향

- 제공 엑셀: `PICKOU_26_22_라인별_챔피언_상성표.xlsx`.
- 배포 데이터: `data/counter-guide-26.22.json`. 서버 시작 시 한 번 읽고 `(포지션, 상대 챔피언)`으로 메모리에 인덱싱합니다. 요청 시 Excel 파싱·DB 쿼리·외부 통계 호출을 하지 않습니다.
- 173명, 266개 등록, 14,468개 방향성 대진. 동일 챔피언 제외 및 라인별 전 조합 완전성을 검사합니다.
- `상대 챔피언=다리우스`인 행의 **내 챔피언**을 추천합니다. 원문 판정을 저장한 채 강한 유리→하드카운터, 유리→카운터, 반반→반반으로 분류합니다. 불리/강한 불리는 접힌 하단 영역에 모읍니다.
- 실측 110행은 제공 엑셀의 `승률·표본 확인`을 `통계 확인`으로 표시합니다. 독립적으로 Riot 통계를 재검증했다는 뜻이 아닙니다. 이론 14,358행은 `이론 참고`로 표시하고 승률·7:3 등 수치를 생성하지 않습니다.
- 유리한 이유와 주의 조건, 유리한 구간을 원문 그대로 전달합니다. 출처 시트·행 번호·파일 SHA-256을 보관합니다. 기존 승인 통계와 합치지 않습니다.
- 이미지: 기존 공식 Riot ID resolver와 캐시를 재사용하여 Data Dragon 명단을 한 번 읽고 공식 PNG를 표시합니다. 실패하면 로컬 SVG를 표시합니다. 외부 명단이나 이미지가 없어도 상성 조회는 계속 동작합니다.

엑셀 갱신 시에만 변환합니다. 워크북은 런타임 의존성이 아니며 저장소에 포함하지 않습니다.

```bash
python -m pip install -r scripts/requirements-import.txt
python scripts/build_counter_guide.py /path/to/PICKOU_26_22_라인별_챔피언_상성표.xlsx
```

누락 열·알 수 없는 판정·중복·누락 대진·불일치 라인·예상치 못한 합계는 실패 처리하고 기존 JSON을 교체하지 않습니다. 첨부 문서의 안내 문구는 데이터 참고용이며 개발 지시로 실행하지 않습니다.

## API

- `GET /api/counter-guide/metadata`
- `GET /api/counter-guide/champions?lane=탑&q=검색어`
- `GET /api/counter-guide/counters?lane=탑&opponent=다리우스`

라인 밖 챔피언은 검색에서 제외하며 잘못된 상대는 404, 라인은 422입니다. 기존 API 경로는 유지합니다. Supabase 테이블/데이터/권한은 변경하지 않았고 신규 테이블도 없습니다.

## 검증

- 전체 unittest 86개: 80개 통과, 실제 DATABASE_URL 미설정으로 기존 라이브 DB 테스트 6개 건너뜀.
- 기존 backend pytest: 13개 통과.
- 기존 Riot 이미지 resolver 테스트 및 Next.js TypeScript/production build 통과. 기존 Next.js 15·React 19 계열에서 보안 패치 버전을 고정하고 lockfile 추가.
- 첨부 엑셀 14,468행 × 사용 필드 11개 전수 비교: 불일치 0. `reports/counter_guide_validation.json` 참고.
- 실제 로컬 Next.js/FastAPI + Chromium: PC 1440×1080, 모바일 390×844에서 방향·원문 사유·근거 배지·즉시 조회·라인 초기화·별칭/초성·가로 넘침·JS 오류 검사 통과.
- 이미지 실패 경로는 CDN 요청을 강제로 실패시켜 검증했습니다. 실제 CDN 이미지 전체 173개의 정상 다운로드와 실제 모바일 기기, 운영 배포, 라이브 Supabase 정합성은 검증하지 않았습니다. 데이터베이스 쓰기 기능은 추가하지 않았습니다.

브라우저 검사는 서버 두 개를 시작한 뒤 Chromium과 Python playwright가 있는 환경에서:

```bash
PICKOU_TEST_URL=http://127.0.0.1:3000 python tests/browser_counter_guide.py
```

## 더블클릭으로 실행

- **Windows:** 루트의 `PICKOU 시작.cmd`를 더블클릭합니다.
- **macOS:** 루트의 `PICKOU 시작.command`를 더블클릭합니다.
- **Linux / 터미널:** 루트에서 `python3 start.py`를 실행합니다.

Python 3.10 이상과 Node.js LTS가 필요합니다. 첫 실행에는 인터넷으로 기존 고정 의존성을 `.venv`와 `frontend/node_modules`에 설치하고, 이후에는 의존성이 바뀔 때만 다시 설치합니다. 백엔드(8000)와 프런트엔드(3000)가 모두 준비되면 브라우저에서 **PICKOU 화면과 백엔드 API 문서** 두 탭을 자동으로 엽니다. 터미널에서 Ctrl+C를 누르면 두 서버를 함께 종료합니다. 사용 중인 포트가 있으면 기존 프로세스를 종료하지 않고 오류를 안내합니다. 로그는 `.pickou/logs/`에 저장합니다.

포트 변경: `python3 start.py --backend-port 8002 --frontend-port 3002`. 브라우저 자동 열기 제외: `--no-open`.

## 포지션별 즐겨찾기

선택 목록의 ☆를 누르면 ★가 되고 해당 포지션의 목록 위쪽에 표시됩니다. 별 버튼은 챔피언 선택 버튼과 분리되어 카운터 조회를 시작하지 않습니다. 별을 다시 누르면 해제됩니다. 검색창 아래의 `즐겨찾기만 보기`를 켜면 현재 포지션의 즐겨찾기와 검색 조건에 모두 맞는 챔피언만 표시합니다. 필터 표시 상태는 재접속 시 초기화하지만 즐겨찾기는 유지됩니다.

즐겨찾기는 브라우저 localStorage의 `pickou.favorites.v1`에 버전과 포지션별 이름 목록으로만 저장합니다. 로그인·백엔드·Supabase 요청이 없고 다른 브라우저/기기로 자동 동기화하지 않습니다. 손상된 저장 값은 안전한 빈 목록으로 처리합니다. 저장소 접근/용량 오류 시 현재 화면의 즐겨찾기와 카운터 조회는 유지하고 저장되지 않는다는 안내를 표시합니다.

별은 독립적인 네이티브 버튼이며 접근성 이름과 `aria-pressed`를 제공합니다. Tab으로 이동하고 Enter/Space로 등록·해제할 수 있습니다. 즐겨찾기 상태만 노란색 별로 강조합니다.

검증: 즐겨찾기 단위 테스트 4개, 기존 resolver 테스트 4개 및 프로덕션 빌드 통과. 실제 Next.js/FastAPI와 PC·모바일 화면폭 Chromium에서 등록·해제·정렬·필터·포지션 분리·검색 조합·새로고침·별 클릭/키보드 이벤트 분리·저장소 손상/차단을 검사했습니다. 같은 로컬 프로필로 Chromium 프로세스를 종료·재실행한 후 복원도 확인했습니다. 기존 카운터 브라우저 회귀 검사와 Python unittest 86개(80 통과, 기존 라이브 DB 6개 skip)도 유지했습니다.

```bash
cd frontend
npm run test:favorites
# 두 서버가 실행 중일 때 저장소 루트에서
PICKOU_TEST_URL=http://127.0.0.1:3000 python tests/browser_favorites.py
```
