import argparse
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests
from tqdm import tqdm
import fitz  # PyMuPDF

import llm
import naver_research
import report_index
import telegram_notify

KST = timezone(timedelta(hours=9))
AI_LABELS = {"openai": "ChatGPT", "claude": "Claude"}


def extract_text_from_pdf(pdf_url, session=requests):
    """PDF를 내려받아 본문 텍스트를 돌려준다. 실패하면 None."""
    try:
        response = session.get(pdf_url, headers=naver_research.HEADERS, timeout=30)
        response.raise_for_status()
        with fitz.open(stream=response.content, filetype="pdf") as doc:
            return "".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return None


def extract_company_name(summary_text):
    """'## [회사명]' 제목에서 회사명을 꺼낸다. 없으면 'Unknown'."""
    match = re.search(r"##\s*\[?([^\]]+?)\]?(?:\s*\n|$)", summary_text)
    if match:
        return match.group(1).strip()

    match = re.search(r"##\s+(.+?)(?:\s*\n|$)", summary_text)
    if match:
        return match.group(1).strip()

    return "Unknown"


def normalize_heading(summary):
    """첫 ## 제목을 '## 회사명'으로 맞춘다. 대괄호와 종목코드 괄호('(112610)')는 뗀다."""
    def clean(match):
        name = re.sub(r"\s*\([^)]*\d{6}[^)]*\)", "", match.group(1)).strip()
        return f"## {name}"

    return re.sub(r"^##\s*\[?(.+?)\]?[ \t]*$", clean, summary, count=1, flags=re.M)


def process_and_sort_summaries(summaries):
    """제목을 정리하고 회사명순으로 정렬한다. 같은 회사가 여러 건이면 제목에 (1), (2)… 번호를 붙인다."""
    items = sorted(
        ((extract_company_name(summary), summary) for summary in map(normalize_heading, summaries)),
        key=lambda item: item[0],
    )
    totals = Counter(company for company, _ in items)
    seen = Counter()

    processed = []
    for company, content in items:
        seen[company] += 1
        if totals[company] > 1:
            content = re.sub(
                r"(##\s*\[?)(" + re.escape(company) + r")(\]?)",
                rf"\1\2 ({seen[company]})\3",
                content,
                count=1,
            )
        processed.append(content)
    return processed


def collect_reports(day):
    """day(YYYY-MM-DD)의 종목 리포트를 모아 (메타데이터, LLM 입력 본문) 목록으로 돌려준다."""
    items = naver_research.fetch_company_reports(day)
    print(f"Found {len(items)} reports for {day}")

    reports = []
    for item in tqdm(items):
        pdf_text = None
        try:
            pdf_url = naver_research.fetch_attach_url(item["nid"])
            if pdf_url:
                pdf_text = extract_text_from_pdf(pdf_url)
        except requests.RequestException as e:
            print(f"✗ Failed to fetch detail {item['nid']}: {e}")
        reports.append((item, naver_research.build_report_input(item, pdf_text)))
    return reports


def load_prompt(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding="utf-8") as f:
        return f.read()


def summarize_reports(reports, provider, api_key):
    """리포트마다 요약을 만든다. 일부 실패는 건너뛰지만 전부 실패하면 예외를 낸다."""
    prompt = load_prompt("prompt.txt")
    summaries = []
    for item, report in tqdm(reports):
        try:
            summaries.append(llm.generate(provider, "summary", prompt, report, api_key=api_key))
        except Exception as e:
            print(f"✗ Summary failed for {item.get('itemName')}: {e}")

    if reports and not summaries:
        raise RuntimeError(f"All summaries failed. Check the {provider} API key and model access.")
    return summaries


def generate_insight(summaries, provider, api_key):
    """전체 요약을 바탕으로 시장 인사이트를 만든다. 실패하면 빈 문자열."""
    if not summaries:
        return ""
    try:
        return llm.generate(
            provider, "insight", load_prompt("insight_prompt.txt"), "\n\n---\n\n".join(summaries), api_key=api_key
        )
    except Exception as e:
        print(f"Failed to generate market insight: {e}")
        return ""


def build_report_markdown(today, provider, insight, summaries):
    """일일 리포트 README: 제목, 요약 모델, (있으면) 시장 인사이트, 종목별 요약."""
    models = ", ".join(dict.fromkeys(llm.MODELS[provider].values()))
    sections = [f"# {today} stock report", f"> 요약: {AI_LABELS[provider]} ({models})"]
    if insight:
        sections += [insight, "---\n\n## 📋 개별 종목 리포트"]
    sections += summaries
    return "\n\n".join(sections)


def write_outputs(today, folder_path, report_markdown):
    with open(os.path.join(folder_path, "README.md"), "w") as file:
        file.write(report_markdown)

    # 루트 README는 프로젝트 소개라서 최신 리포트 링크 구간만 바꾼다
    with open("README.md", encoding="utf-8") as file:
        readme = file.read()
    with open("README.md", "w", encoding="utf-8") as file:
        file.write(report_index.update_latest(readme, today, folder_path))


def main(args):
    now_kst = datetime.now(KST)
    today = now_kst.strftime("%Y.%m.%d")
    folder_path = today.replace(".", "/")
    os.makedirs(folder_path, exist_ok=True)

    reports = collect_reports(now_kst.strftime("%Y-%m-%d"))

    print(f"\n{'='*80}")
    print(f"Total reports collected for {today}: {len(reports)}")
    print(f"{'='*80}\n")

    summaries = process_and_sort_summaries(summarize_reports(reports, args.provider, args.api_key))
    insight = generate_insight(summaries, args.provider, args.api_key)
    write_outputs(today, folder_path, build_report_markdown(today, args.provider, insight, summaries))

    if args.telegram_token and args.telegram_chat_id:
        page_url = f"https://github.com/{args.github_repo}/blob/main/{folder_path}/README.md"
        messages = telegram_notify.build_messages(
            today, insight, [item for item, _ in reports], page_url, ai_label=AI_LABELS[args.provider]
        )
        telegram_notify.send_messages(args.telegram_token, args.telegram_chat_id, messages)
        print(f"Sent {len(messages)} Telegram message(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", choices=sorted(llm.MODELS), default=os.environ.get("AI_PROVIDER") or "openai"
    )
    parser.add_argument("--api_key", type=str, default="", help="기본값: provider에 맞는 환경 변수")
    parser.add_argument("--telegram_token", type=str, default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--telegram_chat_id", type=str, default=os.environ.get("TELEGRAM_CHAT_ID", ""))
    parser.add_argument(
        "--github_repo", type=str, default=os.environ.get("GITHUB_REPOSITORY", "HerrineKim/chatgpt_stock_report")
    )
    args = parser.parse_args()
    args.api_key = args.api_key or os.environ.get(llm.API_KEY_ENV[args.provider], "")
    if not args.api_key:
        parser.error(f"{llm.API_KEY_ENV[args.provider]} is not set for provider '{args.provider}'")

    main(args)
