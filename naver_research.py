import requests
from bs4 import BeautifulSoup

# finance.naver.com/research 는 stock.naver.com 으로 이전되어 HTML 대신 JSON API를 쓴다.
API_BASE = "https://stock.naver.com/api/stockSecurity/researches/v2"
PAGE_SIZE = 50  # API 최대값
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_company_reports(day, session=requests):
    """day(YYYY-MM-DD)에 발행된 종목분석 리포트 목록을 모든 페이지에서 가져온다."""
    reports = []
    index = 0
    while True:
        params = {"index": index, "size": PAGE_SIZE, "startDate": day, "endDate": day}
        response = session.get(f"{API_BASE}/company", params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        page = response.json()
        reports.extend(page["items"])
        if not page.get("hasNext") or not page["items"]:
            return reports
        index += 1


def fetch_attach_url(nid, session=requests):
    """리포트 상세에서 PDF 첨부 URL을 가져온다. 없으면 None."""
    response = session.get(f"{API_BASE}/company/{nid}", headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("attachUrl")


def content_text(item):
    """목록 API의 HTML 요약(content)을 줄 단위 텍스트로 바꾼다."""
    soup = BeautifulSoup(item.get("content") or "", "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    lines = soup.get_text("\n").splitlines()
    return "\n".join(line.strip() for line in lines if line.strip())


def format_price(value):
    if not value or not str(value).isdigit() or int(value) == 0:
        return "없음"
    return f"{int(value):,}원"


def build_report_input(item, pdf_text=None, max_chars=15000):
    """LLM에 넘길 리포트 본문: 메타데이터 + 애널리스트 요약 + PDF 본문(길이 제한)."""
    parts = [
        f"회사명: {item.get('itemName', '')}",
        f"증권사: {item.get('brokerName', '')}",
        f"제목: {item.get('title', '')}",
        f"투자의견: {item.get('opinionText') or '없음'}",
        f"목표주가: {format_price(item.get('goalPrice'))}",
        "",
        "[요약]",
        content_text(item),
    ]
    if pdf_text:
        parts += ["", "[PDF 본문]", pdf_text[:max_chars]]
    return "\n".join(parts)
