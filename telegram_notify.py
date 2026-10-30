import re

import requests

from naver_research import format_price

MAX_MESSAGE_LENGTH = 4000  # 텔레그램 한도 4096자에서 여유를 둔다


def to_plain_text(markdown):
    """parse_mode 없이 보내므로 마크다운 기호(#, **, ---)를 걷어 낸다."""
    lines = []
    for line in markdown.splitlines():
        if re.fullmatch(r"\s*-{3,}\s*", line):
            continue
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        lines.append(line.replace("**", ""))
    return "\n".join(lines).strip()


def report_line(item):
    goal = format_price(item.get("goalPrice"))
    goal_text = f"목표 {goal}" if goal != "없음" else "목표가 없음"
    opinion = item.get("opinionText") or "의견 없음"
    return f"• {item.get('itemName', '')} · {opinion} · {goal_text} ({item.get('brokerName', '')})"


def company_line(items):
    """같은 종목 리포트 여러 건은 한 줄로 묶어 목표주가 범위를 보여 준다."""
    if len(items) == 1:
        return report_line(items[0])
    goals = [int(i["goalPrice"]) for i in items if str(i.get("goalPrice", "")).isdigit() and int(i["goalPrice"]) > 0]
    if not goals:
        goal_text = "목표가 없음"
    elif min(goals) == max(goals):
        goal_text = f"목표 {min(goals):,}원"
    else:
        goal_text = f"목표 {min(goals):,}~{max(goals):,}원"
    brokers = ", ".join(i.get("brokerName", "") for i in items)
    return f"• {items[0].get('itemName', '')} · {len(items)}건 · {goal_text} ({brokers})"


def group_by_company(reports):
    groups = {}
    for item in reports:
        groups.setdefault(item.get("itemName", ""), []).append(item)
    return [groups[name] for name in sorted(groups)]


def split_text(text, limit=MAX_MESSAGE_LENGTH):
    """줄 경계를 지키며 limit 이하 조각으로 나눈다."""
    chunks, current = [], ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def build_messages(today, insight_markdown, reports, page_url, ai_label=None):
    header = f"📈 {today} 증권사 리포트 요약" + (f" ({ai_label})" if ai_label else "")
    if not reports:
        return [f"{header}\n\n오늘 발행된 종목 리포트가 없습니다."]

    sections = [header]
    if insight_markdown:
        sections.append(to_plain_text(insight_markdown))
    groups = group_by_company(reports)
    report_lines = "\n".join(company_line(items) for items in groups)
    sections.append(f"📋 리포트 {len(reports)}건 · {len(groups)}개 종목\n{report_lines}")
    sections.append(f"🔗 종목별 상세 요약\n{page_url}")
    return split_text("\n\n".join(sections))


def send_messages(token, chat_id, messages, session=requests):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for message in messages:
        response = session.post(
            url,
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=30,
        )
        response.raise_for_status()
