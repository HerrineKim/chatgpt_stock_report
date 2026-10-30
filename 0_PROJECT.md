# 25/12/26
- 그 동안 방치했는데 클로드 코드와 함께 오류 수정 및 고도화 작업 시작했습니다.

# 26/10/30
- 2025년 말 네이버 증권 리서치가 `finance.naver.com` → `stock.naver.com`(Next.js)으로 이전되며 HTML 크롤링이 0건을 반환하던 문제를 JSON API(`/api/stockSecurity/researches/v2/company`)로 교체했습니다.
- 워크플로 파일이 `.yml` 확장자 없이 `python-app`으로 바뀌어 Actions가 돌지 않던 문제를 고쳤습니다.
- 매일 요약을 텔레그램으로 보냅니다(시장 인사이트 + 종목별 리포트 목록 + 상세 링크). 작업이 실패하면 실패 알림이 갑니다.

## 설정
GitHub 저장소 Settings → Secrets and variables → Actions에 아래 3개를 등록합니다.

| 이름 | 값 |
| --- | --- |
| `OPEN_API_KEY` | OpenAI API 키 (ChatGPT로 요약할 때) |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude로 요약할 때) |
| `TELEGRAM_BOT_TOKEN` | @BotFather에서 만든 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 봇에게 메시지를 보낸 뒤 `https://api.telegram.org/bot<토큰>/getUpdates`에서 확인한 `chat.id` |

## 요약 AI 선택
| 설정 | 요약(리포트별) | 인사이트(하루 1번) |
| --- | --- | --- |
| `openai` (기본) | gpt-5-mini | gpt-5 |
| `claude` | claude-haiku-5-5 | claude-opus-5-5 |

- 매일 자동 실행: Settings → Secrets and variables → Actions → Variables에 `AI_PROVIDER`를 `openai` 또는 `claude`로 둡니다. 없으면 `openai`.
- 한 번만 바꿔 실행: Actions → Scraper & Summary → Run workflow에서 provider를 고릅니다.
- 고른 쪽의 키만 있으면 됩니다. 키가 없으면 수집 전에 바로 실패합니다.
- 모델은 `llm.py`의 `MODELS`에서 바꿉니다.

포크 저장소는 Actions 탭에서 워크플로를 한 번 활성화해야 스케줄이 돕니다.

## 로컬 실행
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
OPENAI_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... .venv/bin/python scrap_and_summary.py
AI_PROVIDER=claude ANTHROPIC_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... .venv/bin/python scrap_and_summary.py
```
