import time

from openai import OpenAI

# task별 모델: summary는 리포트마다(하루 100건 안팎) 부르고, insight는 하루 한 번 부른다.
MODELS = {
    "openai": {"summary": "gpt-5-mini", "insight": "gpt-5"},
}


def generate(provider, task, system_prompt, user_prompt, api_key=None, client=None):
    """provider의 task 모델로 system/user 프롬프트를 보내고 응답 텍스트를 돌려준다."""
    if provider not in MODELS:
        raise ValueError(f"Unknown provider: {provider} (choose one of {', '.join(MODELS)})")
    model = MODELS[provider][task]
    return _openai(model, system_prompt, user_prompt, client or OpenAI(api_key=api_key))


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
