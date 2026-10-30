import telegram_notify


REPORTS = [
    {"itemName": "삼성전자", "brokerName": "미래에셋증권", "opinionText": "매수", "goalPrice": "400000"},
    {"itemName": "아모레퍼시픽", "brokerName": "하나증권", "opinionText": "Buy", "goalPrice": "170000"},
]


def test_should_strip_markdown_marks_for_plain_text():
    md = "## 📊 오늘의 시장 인사이트\n\n### 🔍 주요 트렌드\n- **반도체** 강세\n---"

    assert telegram_notify.to_plain_text(md) == "📊 오늘의 시장 인사이트\n\n🔍 주요 트렌드\n- 반도체 강세"


def test_should_include_date_insight_report_list_and_link():
    messages = telegram_notify.build_messages(
        "2026.10.30", "## 인사이트\n시장 강세", REPORTS, "https://github.com/x/y/blob/main/2026/10/30/README.md"
    )
    text = "\n".join(messages)

    assert "2026.10.30" in text
    assert "시장 강세" in text
    assert "리포트 2건 · 2개 종목" in text
    assert "삼성전자 · 매수 · 목표 400,000원 (미래에셋증권)" in text
    assert "https://github.com/x/y/blob/main/2026/10/30/README.md" in text


def test_should_group_multiple_reports_on_same_company():
    reports = [
        {"itemName": "KB금융", "brokerName": "하나증권", "opinionText": "Buy", "goalPrice": "235000"},
        {"itemName": "KB금융", "brokerName": "SK증권", "opinionText": "매수", "goalPrice": "213000"},
        {"itemName": "KB금융", "brokerName": "키움증권", "opinionText": "Buy", "goalPrice": "0"},
    ]

    text = "\n".join(telegram_notify.build_messages("2026.10.30", "", reports, "https://link"))

    assert "리포트 3건 · 1개 종목" in text
    assert "KB금융 · 3건 · 목표 213,000~235,000원 (하나증권, SK증권, 키움증권)" in text


def test_should_say_so_when_there_are_no_reports():
    messages = telegram_notify.build_messages("2026.10.31", "", [], "https://link")

    assert "발행된 종목 리포트가 없습니다" in messages[0]


def test_should_split_long_text_under_telegram_limit():
    many = [{"itemName": f"회사{i}", "brokerName": "증권", "opinionText": "매수", "goalPrice": "1000"} for i in range(400)]

    messages = telegram_notify.build_messages("2026.10.30", "인사이트", many, "https://link")

    assert len(messages) > 1
    assert all(len(m) <= telegram_notify.MAX_MESSAGE_LENGTH for m in messages)
    joined = "\n".join(messages)
    assert "회사0 " in joined and "회사399 " in joined


def test_should_post_each_message_to_chat():
    sent = []

    class FakeSession:
        def post(self, url, json=None, timeout=None):
            sent.append((url, json))

            class R:
                def raise_for_status(self):
                    pass

            return R()

    telegram_notify.send_messages("TOKEN", "123", ["a", "b"], session=FakeSession())

    assert [s[0] for s in sent] == ["https://api.telegram.org/botTOKEN/sendMessage"] * 2
    assert [s[1]["text"] for s in sent] == ["a", "b"]
    assert sent[0][1]["chat_id"] == "123"


def test_should_show_which_ai_wrote_the_summary_in_header():
    messages = telegram_notify.build_messages("2026.10.30", "", REPORTS, "https://link", ai_label="Claude")

    assert messages[0].startswith("📈 2026.10.30 증권사 리포트 요약 (Claude)")
