import argparse
import os
import re
from datetime import datetime, timedelta, timezone
import tempfile

import requests
from tqdm import tqdm
import fitz  # PyMuPDF

import llm
import naver_research
import telegram_notify

KST = timezone(timedelta(hours=9))
AI_LABELS = {"openai": "ChatGPT", "claude": "Claude"}


def extract_text_from_pdf(pdf_url):
    """
    Download and extract text from PDF
    Returns: extracted text or None on failure
    """
    temp_pdf_path = None
    try:
        # Download PDF to temp file with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            temp_pdf_path = tmp.name

        # Extract text using PyMuPDF
        text = ""
        doc = fitz.open(temp_pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()

        return text

    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return None
    finally:
        # Cleanup temp file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def extract_company_name(summary_text):
    """
    Extract company name from summary text
    Returns: company name or None
    """
    # Look for ## [회사명] pattern
    match = re.search(r"##\s*\[?([^\]]+?)\]?(?:\s*\n|$)", summary_text)
    if match:
        return match.group(1).strip()

    # Fallback: look for ## followed by text
    match = re.search(r"##\s+(.+?)(?:\s*\n|$)", summary_text)
    if match:
        return match.group(1).strip()

    return "Unknown"


def process_and_sort_summaries(summaries):
    """
    Process summaries: add numbering for duplicates and sort by company name
    Returns: list of processed summaries
    """
    # Extract company names and pair with summaries
    summary_data = []
    for summary in summaries:
        company_name = extract_company_name(summary)
        summary_data.append({"company": company_name, "content": summary})

    # Sort by company name
    summary_data.sort(key=lambda x: x["company"])

    # First pass: count total occurrences of each company
    company_totals = {}
    for item in summary_data:
        company = item["company"]
        company_totals[company] = company_totals.get(company, 0) + 1

    # Second pass: add numbering to all items of companies with duplicates
    company_current_counts = {}
    processed_summaries = []

    for item in summary_data:
        company = item["company"]
        content = item["content"]

        # Track current count for this company
        if company not in company_current_counts:
            company_current_counts[company] = 0
        company_current_counts[company] += 1

        # Add number if company appears more than once
        if company_totals[company] > 1:
            # Replace company name with numbered version
            content = re.sub(
                r"(##\s*\[?)(" + re.escape(company) + r")(\]?)",
                r"\1\2 (" + str(company_current_counts[company]) + r")\3",
                content,
                count=1,
            )

        processed_summaries.append(content)

    return processed_summaries


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


def main(args):
    now_kst = datetime.now(KST)
    today = now_kst.strftime("%Y.%m.%d")
    folder_path = today.replace(".", "/")
    os.makedirs(folder_path, exist_ok=True)

    reports = collect_reports(now_kst.strftime("%Y-%m-%d"))

    print(f"\n{'='*80}")
    print(f"Total reports collected for {today}: {len(reports)}")
    print(f"{'='*80}\n")

    ############################################################################
    # Load prompt from file
    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    # Generate summaries
    raw_summaries = []
    for item, report in tqdm(reports):
        try:
            raw_summaries.append(llm.generate(args.provider, "summary", base_prompt, report, api_key=args.api_key))
        except Exception as e:
            print(f"✗ Summary failed for {item.get('itemName')}: {e}")

    if reports and not raw_summaries:
        raise RuntimeError(f"All summaries failed. Check the {args.provider} API key and model access.")

    # Process summaries: sort by company name and add numbering for duplicates
    processed_summaries = process_and_sort_summaries(raw_summaries)

    # Generate market insight from all summaries
    market_insight = ""
    if processed_summaries:
        try:
            # Load insight prompt
            insight_prompt_path = os.path.join(os.path.dirname(__file__), "insight_prompt.txt")
            with open(insight_prompt_path, "r", encoding="utf-8") as f:
                insight_system_prompt = f.read()

            # Combine all summaries for analysis
            all_summaries_text = "\n\n---\n\n".join(processed_summaries)

            # Request market insight
            market_insight = llm.generate(
                args.provider, "insight", insight_system_prompt, all_summaries_text, api_key=args.api_key
            )
        except Exception as e:
            print(f"Failed to generate market insight: {e}")
            market_insight = ""

    # Build final summary with insight at the top
    ai_label = AI_LABELS[args.provider]
    final_summary = [f"# {today} stock report", f"> 요약: {ai_label} ({', '.join(dict.fromkeys(llm.MODELS[args.provider].values()))})"]

    if market_insight:
        final_summary.append(market_insight)
        final_summary.append("---\n\n## 📋 개별 종목 리포트")

    final_summary.extend(processed_summaries)

    with open(os.path.join(folder_path, "README.md"), "w") as file:
        file.write("\n\n".join(final_summary))

    with open("README.md", "w") as file:
        file.write("\n\n".join(final_summary))

    if args.telegram_token and args.telegram_chat_id:
        page_url = f"https://github.com/{args.github_repo}/blob/main/{folder_path}/README.md"
        messages = telegram_notify.build_messages(
            today, market_insight, [item for item, _ in reports], page_url, ai_label=ai_label
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
