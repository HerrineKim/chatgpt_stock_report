import re

START = "<!-- latest-report:start -->"
END = "<!-- latest-report:end -->"


def update_latest(readme_text, today, folder_path):
    """README의 최신 리포트 구간만 오늘 리포트 링크로 바꾼다. 구간이 없으면 끝에 붙인다."""
    section = f"{START}\n최신 리포트: [{today} 리포트]({folder_path}/README.md)\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(readme_text):
        return pattern.sub(lambda _: section, readme_text, count=1)
    return f"{readme_text.rstrip()}\n\n{section}\n"
