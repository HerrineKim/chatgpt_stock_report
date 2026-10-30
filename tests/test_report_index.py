import report_index


README = "# 프로젝트\n\n<!-- latest-report:start -->\n예전 링크\n<!-- latest-report:end -->\n\n## 설정\n"


def test_should_replace_only_the_latest_report_section():
    text = report_index.update_latest(README, "2026.10.30", "2026/10/30")

    assert "예전 링크" not in text
    assert "[2026.10.30 리포트](2026/10/30/README.md)" in text
    assert text.startswith("# 프로젝트\n\n<!-- latest-report:start -->")
    assert text.endswith("<!-- latest-report:end -->\n\n## 설정\n")


def test_should_append_the_section_when_markers_are_missing():
    text = report_index.update_latest("# 프로젝트\n", "2026.10.30", "2026/10/30")

    assert text.startswith("# 프로젝트\n")
    assert "<!-- latest-report:start -->" in text
    assert "[2026.10.30 리포트](2026/10/30/README.md)" in text
