# 25/12/26
- 그 동안 방치했는데 클로드 코드와 함께 오류 수정 및 고도화 작업 시작했습니다.

# 26/10/30
- 2025년 말 네이버 증권 리서치가 `finance.naver.com` → `stock.naver.com`(Next.js)으로 옮겨 가면서 HTML 크롤링이 0건을 반환했습니다. 수집 방식을 JSON API(`/api/stockSecurity/researches/v2/company`)로 바꿨습니다.
- 워크플로 파일이 `.yml` 확장자 없이 `python-app`으로 바뀌어 Actions가 돌지 않던 문제를 고쳤습니다.
- 매일 요약을 텔레그램으로 보냅니다(시장 인사이트, 종목별 리포트 목록, 상세 링크). 작업이 실패하면 실패 알림이 갑니다.
- Claude(Haiku)와 ChatGPT 중 골라 요약할 수 있게 했습니다. 기본은 저장소 변수 `AI_PROVIDER`로 정합니다.
- 루트 README는 프로젝트 소개로 두고, 매일 최신 리포트 링크만 바꿉니다.

설정과 실행 방법은 [README.md](README.md)에 있습니다.
