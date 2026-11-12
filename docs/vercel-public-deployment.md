# PICKOU 공개 배포 — Vercel

## 프로젝트 배포

PICKOU는 Vercel의 무료 Hobby 플랜(비상업 개인 프로젝트 기준)에서
Next.js 프런트엔드 하나로 배포할 수 있습니다. 공개 화면은 로그인 없이
라인/상대 챔피언 검색, 카운터와 이유 조회, 브라우저별 즐겨찾기를 제공합니다.

1. https://vercel.com/new 접속 후 GitHub 계정으로 로그인합니다.
2. `SD608/lol-project` 저장소를 Import 합니다.
3. **Framework Preset = Next.js**, **Root Directory = frontend** 로 설정합니다.
4. Build Command는 기본값인 `npm run build`, Install Command는 기본값을 사용합니다.
5. **PICKOU_API_ORIGIN을 설정하지 마세요.** (로컬 서버 주소를 사용하면 실패합니다.)
6. `Deploy`를 누르고 공개 `https://<project>.vercel.app` URL을 확인합니다.
7. 공개 페이지와 다음 API가 모두 열리는지 확인합니다:
   - `/api/counter-guide/metadata`
   - `/api/counter-guide/champions?lane=탑`
   - `/api/counter-guide/counters?lane=탑&opponent=다리우스`
8. 즐겨찾기 등록 후 새로고침하고, 모바일에서도 카운터를 조회해 봅니다.

GitHub의 main 브랜치와 연결하면 병합 후 Vercel에서 자동 재배포됩니다.

## 작동 구조

- `frontend/app/api/counter-guide`의 Next.js Route Handlers가 읽기 전용 API를 제공합니다.
- `frontend/data/counter-guide-26.22.json`은 배포 시 함께 포함되며 런타임에 메모리로 읽습니다.
- 원본은 `data/counter-guide-26.22.json`이며 두 파일은 해시로 일치 검증합니다.
- 기존 Windows `PICKOU 시작.cmd`와 FastAPI는 변경하지 않습니다.
- 데이터베이스 암호, Riot API 키, Supabase 연결이 필요하지 않습니다.
- 즐겨찾기는 사이트 주소별 브라우저 localStorage에 저장되므로 기존 localhost의
  즐겨찾기는 공개 도메인으로 자동 이동하지 않습니다.
- 데이터가 갱신되면 원본 `data/` 파일을 변환한 뒤 `frontend/data/`의 배포용 사본도 동기화합니다.

## 주의

- 14,358개 상성은 독립 검증을 마치지 않은 이론 참고 자료입니다.
- 공개 배포 시 '통계 확인' 110개 역시 제공 엑셀에서 확인했다는 의미이지
  별도의 독립적 통계 검증 완료를 뜻하지 않습니다.
- Riot Games의 공식 서비스가 아니며, 공식 게임 이미지 및 이름 권리와
  데이터 출처/이용약관을 점검해 비상업적으로 운영하세요.
- 서비스 URL은 Vercel에서 배포가 성공한 뒤 생성됩니다. 브라우저에서 localhost를
  다른 사람에게 공유해도 접근할 수 없습니다.
