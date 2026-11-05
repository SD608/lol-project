# PICKOU 3단계 실행 결과

기존 36개 포함 54개 테스트 통과. [테스트 실행](https://github.com/SD608/lol-project/actions/runs/41946190060).

[실증 실행](https://github.com/SD608/lol-project/actions/runs/41946190139)은 GitHub Secret RIOT_API_KEY 미설정으로 key_missing(exit 2) 실패. 실제 API 호출 0, 수집 경기 0, 승인된 매치업 0, 실제 통계 예시 없음. 임의의 5개 예시를 생성하지 않았습니다. 오류 결과 JSON·Markdown과 검증 요약은 pickou-kr-pilot 아티팩트로 저장됐습니다.

KR League-V4/Asia Match-V5 경기 ID 탐색, 제한기/재시도 이벤트, 패치별 분리, 역할 불명확 경기 표시 및 기본 통계 제외, 지표별 표본·신뢰구간, 동일 표본 재집계 방지, 읽기 전용 Sheets 업데이트 계획을 구현했습니다. 실제 데이터 기능은 모의 응답으로 검증됐으며 아직 Riot 실데이터 검증이 아닙니다.

Sheets 14,468개 대진은 연결 도구로 실제 읽어 DB와 대조했습니다. 원본 스냅샷은 로컬 전용이며 CI는 저장된 검증 요약만 확인합니다. 자동 승인 검토가 비공개 원본의 GitHub 업로드를 거부해 원본을 게시하지 않았습니다. 상성 등급 및 원본 시트 변경 없음.

다음 단계: 저장소 Settings → Secrets and variables → Actions에 RIOT_API_KEY를 설정한 후 PICKOU KR Riot pilot을 재실행합니다. 채팅이나 코드에 키 값을 넣지 않습니다. 최신 KR 공식 적용 근거, 경기 당시 티어 증명, 위치 기반 라인 스왑 판정, 영구 DB 복원·분산 제한기 등은 별도 검증이 필요합니다.
