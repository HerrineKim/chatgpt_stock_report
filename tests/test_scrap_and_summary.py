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
