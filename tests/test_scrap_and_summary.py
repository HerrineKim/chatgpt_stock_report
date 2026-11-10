import scrap_and_summary


def test_should_number_same_company_even_when_heading_has_ticker_code():
    summaries = [
        "## 씨에스윈드 (112610)\n\n본문 A",
        "## 씨에스윈드\n\n본문 B",
    ]

    processed = scrap_and_summary.process_and_sort_summaries(summaries)

    assert [s.splitlines()[0] for s in processed] == ["## 씨에스윈드 (1)", "## 씨에스윈드 (2)"]


def test_should_drop_ticker_code_from_single_company_heading():
    processed = scrap_and_summary.process_and_sort_summaries(["## [해성디에스 (195870)]\n\n본문"])

    assert processed[0].splitlines()[0] == "## 해성디에스"


def test_should_put_insight_before_company_summaries():
    markdown = scrap_and_summary.build_report_markdown("2026.11.10", "claude", "인사이트", ["## A", "## B"])

    assert markdown.split("\n\n") == [
        "# 2026.11.10 stock report",
        "> 요약: Claude (claude-haiku-5-5)",
        "인사이트",
        "---",
        "## 📋 개별 종목 리포트",
        "## A",
        "## B",
    ]


def test_should_omit_insight_section_when_insight_is_empty():
    markdown = scrap_and_summary.build_report_markdown("2026.11.10", "openai", "", ["## A"])

    assert markdown == "# 2026.11.10 stock report\n\n> 요약: ChatGPT (gpt-5-mini, gpt-5)\n\n## A"


def test_should_extract_text_from_downloaded_pdf():
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello report")
    pdf_bytes = doc.tobytes()

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            class R:
                content = pdf_bytes

                def raise_for_status(self):
                    pass

            return R()

    assert "hello report" in scrap_and_summary.extract_text_from_pdf("https://pdf", session=FakeSession())


def test_should_return_none_when_pdf_download_fails():
    class FailingSession:
        def get(self, url, headers=None, timeout=None):
            raise OSError("down")

    assert scrap_and_summary.extract_text_from_pdf("https://pdf", session=FailingSession()) is None


def test_should_stop_when_every_summary_fails(monkeypatch):
    import pytest

    def fail(*args, **kwargs):
        raise RuntimeError("no access")

    monkeypatch.setattr(scrap_and_summary.llm, "generate", fail)

    with pytest.raises(RuntimeError, match="All summaries failed"):
        scrap_and_summary.summarize_reports([({"itemName": "A"}, "본문")], "claude", "key")
