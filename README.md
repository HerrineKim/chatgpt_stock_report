# 증권사 리포트 요약 봇

네이버 증권에 올라온 그날의 종목 리포트를 AI로 요약해 텔레그램으로 보내고, 요약본을 날짜별 폴더에 저장합니다.

<!-- latest-report:start -->
최신 리포트: [2026.11.11 리포트](2026/11/11/README.md)
<!-- latest-report:end -->

## 하는 일
평일 오후 1시(KST)에 GitHub Actions가 아래 순서로 돌립니다.

1. 네이버 증권 리서치 API에서 그날 발행된 종목 리포트 목록을 받습니다.
2. 리포트마다 네이버가 붙인 짧은 요약과 PDF에서 뽑은 글자를 함께 AI에게 넘겨 요약을 받습니다. PDF가 이미지라 글자가 거의 나오지 않으면 AI는 사실상 네이버 요약만 보고 씁니다.
3. 요약 전체를 다시 AI에게 넘겨 그날의 시장 인사이트를 받습니다.
4. `연/월/일/README.md`에 인사이트와 종목별 요약을 저장하고 커밋합니다.
5. 텔레그램으로 인사이트, 종목별 한 줄 목록(투자의견·목표주가·증권사), 상세 요약 링크를 보냅니다.

작업이 실패하면 텔레그램으로 실패 알림과 실행 로그 링크가 갑니다. 텔레그램 발송만 실패해도 요약본은 커밋됩니다.

## 설정
저장소 Settings → Secrets and variables → Actions에서 등록합니다.

| 종류 | 이름 | 값 |
| --- | --- | --- |
| Secret | `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude로 요약할 때) |
| Secret | `OPEN_API_KEY` | OpenAI API 키 (ChatGPT로 요약할 때) |
| Secret | `TELEGRAM_BOT_TOKEN` | @BotFather에서 만든 봇 토큰 |
| Secret | `TELEGRAM_CHAT_ID` | 봇에게 아무 메시지나 보낸 뒤 `https://api.telegram.org/bot<토큰>/getUpdates`에서 확인한 `chat.id` |
| Variable | `AI_PROVIDER` | `claude` 또는 `openai`. 없으면 `openai` |

고른 AI의 키만 있으면 됩니다. 포크한 저장소라면 Actions 탭에서 워크플로를 한 번 켜야 스케줄이 돕니다.

## 요약 AI
| `AI_PROVIDER` | 리포트별 요약 | 시장 인사이트 |
| --- | --- | --- |
| `claude` | claude-haiku-5-5 | claude-haiku-5-5 |
| `openai` | gpt-5-mini | gpt-5 |

- 한 번만 다른 AI로 돌리려면 Actions → Scraper & Summary → Run workflow에서 provider를 고릅니다.
- 모델은 `llm.py`의 `MODELS`에서 바꿉니다.
- 2026-10-30 실행 기준으로 리포트 121건을 처리하는 데 약 27분 걸렸습니다.

## 로컬 실행
```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
AI_PROVIDER=claude ANTHROPIC_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... .venv/bin/python scrap_and_summary.py
```
텔레그램 값을 빼면 발송 없이 요약 파일만 만듭니다.

## 파일
| 파일 | 역할 |
| --- | --- |
| `scrap_and_summary.py` | 수집, 요약, 저장, 발송을 잇는 진입점 |
| `naver_research.py` | 네이버 증권 리서치 API 호출 |
| `llm.py` | Claude·OpenAI 호출 |
| `telegram_notify.py` | 텔레그램 메시지 만들기와 발송 |
| `report_index.py` | 이 README의 최신 리포트 링크 갱신 |
| `prompt.txt`, `insight_prompt.txt` | 요약·인사이트 프롬프트 |

변경 이력은 [0_PROJECT.md](0_PROJECT.md)에 있습니다.
