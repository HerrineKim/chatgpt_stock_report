import time

import anthropic
from openai import OpenAI

# task별 모델: summary는 리포트마다(하루 100건 안팎) 부르고, insight는 하루 한 번 부른다.
MODELS = {
    "openai": {"summary": "gpt-5-mini", "insight": "gpt-5"},
    "claude": {"summary": "claude-haiku-5-5", "insight": "claude-opus-5-5"},
}
API_KEY_ENV = {"openai": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY"}
# 거절(refusal) 시 서버가 다른 모델로 이어 받게 한다. Haiku는 지원하지 않는다.
CLAUDE_FALLBACK_MODELS = {"claude-opus-5-5"}


def generate(provider, task, system_prompt, user_prompt, api_key=None, client=None):
    """provider의 task 모델로 system/user 프롬프트를 보내고 응답 텍스트를 돌려준다."""
    if provider not in MODELS:
        raise ValueError(f"Unknown provider: {provider} (choose one of {', '.join(MODELS)})")
    model = MODELS[provider][task]
    if provider == "claude":
        return _claude(model, system_prompt, user_prompt, client or anthropic.Anthropic(api_key=api_key))
    return _openai(model, system_prompt, user_prompt, client or OpenAI(api_key=api_key))


def _claude(model, system_prompt, user_prompt, client):
    # 재시도(429, 5xx, 연결 오류)는 SDK가 기본으로 처리한다.
    params = {
        "model": model,
        "max_tokens": 16000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if model in CLAUDE_FALLBACK_MODELS:
        response = client.beta.messages.create(
            **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
        )
    else:
        response = client.messages.create(**params)
    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None)
        raise RuntimeError(f"{model} refused the request (category: {category})")
    return "".join(block.text for block in response.content if block.type == "text")


def _openai(model, system_prompt, user_prompt, client):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    retries = 3
    retry_cnt = 0
    backoff_time = 10
    while True:
        try:
            response = client.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            if retry_cnt >= retries:
                raise
            print(f"{type(e).__name__}: {e}. Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)
            backoff_time *= 1.5
            retry_cnt += 1
