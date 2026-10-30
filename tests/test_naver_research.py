import naver_research


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, pages, details=None):
        self.pages = pages
        self.details = details or {}
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        if url.endswith("/company"):
            return FakeResponse(self.pages[params["index"]])
        nid = url.rsplit("/", 1)[1]
        return FakeResponse(self.details[nid])


def test_should_collect_reports_across_all_pages_for_the_date():
    session = FakeSession(
        pages=[
            {"hasNext": True, "items": [{"nid": "1"}, {"nid": "2"}]},
            {"hasNext": False, "items": [{"nid": "3"}]},
        ]
    )

    reports = naver_research.fetch_company_reports("2026-10-30", session=session)

    assert [r["nid"] for r in reports] == ["1", "2", "3"]
    first_params = session.calls[0][1]
    assert first_params["startDate"] == "2026-10-30"
    assert first_params["endDate"] == "2026-10-30"


def test_should_strip_html_from_report_content():
    item = {"content": "<p><strong>제목</strong></p><p><br>본문 1<br>본문 2</p>"}

    assert naver_research.content_text(item) == "제목\n본문 1\n본문 2"


def test_should_build_llm_input_with_metadata_and_pdf_text():
    item = {
        "itemName": "삼성전자",
        "brokerName": "미래에셋증권",
        "title": "초우량 고성장",
        "opinionText": "매수",
        "goalPrice": "400000",
        "content": "<p>요약</p>",
    }

    text = naver_research.build_report_input(item, pdf_text="PDF 본문", max_chars=100)

    assert "회사명: 삼성전자" in text
    assert "증권사: 미래에셋증권" in text
    assert "목표주가: 400,000원" in text
    assert "요약" in text
    assert "PDF 본문" in text


def test_should_truncate_pdf_text_to_max_chars():
    item = {"itemName": "A", "content": ""}

    text = naver_research.build_report_input(item, pdf_text="x" * 500, max_chars=50)

    assert "x" * 50 in text
    assert "x" * 51 not in text


def test_should_read_attach_url_from_detail():
    session = FakeSession(pages=[], details={"97383": {"attachUrl": "https://x/a.pdf"}})

    assert naver_research.fetch_attach_url("97383", session=session) == "https://x/a.pdf"
