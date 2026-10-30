from types import SimpleNamespace

import pytest

import llm


class FakeOpenAI:
    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content="openai 요약")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_should_call_openai_summary_model_and_return_text():
    client = FakeOpenAI()

    text = llm.generate("openai", "summary", "시스템", "리포트", client=client)

    assert text == "openai 요약"
    assert client.calls[0]["model"] == "gpt-5-mini"
    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "시스템"},
        {"role": "user", "content": "리포트"},
    ]


def test_should_use_larger_openai_model_for_insight():
    client = FakeOpenAI()

    llm.generate("openai", "insight", "시스템", "요약들", client=client)

    assert client.calls[0]["model"] == "gpt-5"


def test_should_reject_unknown_provider():
    with pytest.raises(ValueError):
        llm.generate("gemini", "summary", "s", "u", client=object())
