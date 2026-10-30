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


class FakeAnthropic:
    def __init__(self, stop_reason="end_turn"):
        self.calls = []
        self.stop_reason = stop_reason
        self.messages = SimpleNamespace(create=self._create("messages"))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create("beta")))

    def _create(self, endpoint):
        def create(**kwargs):
            self.calls.append((endpoint, kwargs))
            content = [
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="claude "),
                SimpleNamespace(type="text", text="요약"),
            ]
            return SimpleNamespace(content=content, stop_reason=self.stop_reason, stop_details=None)

        return create


def test_should_call_claude_summary_model_with_system_prompt():
    client = FakeAnthropic()

    text = llm.generate("claude", "summary", "시스템", "리포트", client=client)

    assert text == "claude 요약"
    endpoint, kwargs = client.calls[0]
    assert endpoint == "messages"
    assert kwargs["model"] == "claude-haiku-5-5"
    assert kwargs["system"] == "시스템"
    assert kwargs["messages"] == [{"role": "user", "content": "리포트"}]


def test_should_call_claude_insight_model_with_refusal_fallback():
    client = FakeAnthropic()

    llm.generate("claude", "insight", "시스템", "요약들", client=client)

    endpoint, kwargs = client.calls[0]
    assert endpoint == "beta"
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]


def test_should_raise_when_claude_refuses():
    with pytest.raises(RuntimeError):
        llm.generate("claude", "summary", "s", "u", client=FakeAnthropic(stop_reason="refusal"))


def test_should_read_api_key_env_name_per_provider():
    assert llm.API_KEY_ENV == {"openai": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY"}
