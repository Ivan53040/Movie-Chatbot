import json
import time

from config import get_env


def _get_float_env(name, default):
    try:
        return float(get_env(name, default))
    except (TypeError, ValueError):
        return float(default)


def _get_int_env(name, default):
    try:
        return int(get_env(name, default))
    except (TypeError, ValueError):
        return int(default)


def _build_groq_client():
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError(
            "The Groq Python package is not installed. "
            "Install it with: pip install groq"
        ) from exc

    api_key = get_env("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to .env before running the parser."
        )

    timeout_seconds = _get_float_env("GROQ_TIMEOUT_SECONDS", 12.0)
    max_retries = _get_int_env("GROQ_MAX_RETRIES", 0)
    return Groq(
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )


def chat_json(*, system_prompt, user_input):
    # Force JSON mode for parser/explanation tasks where downstream code expects
    # machine-readable output.
    client = _build_groq_client()
    model = get_env("GROQ_MODEL", "llama-3.1-8b-instant")
    response = _chat_with_retry(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Model returned empty content.")
    return json.loads(content)


def chat_text(*, system_prompt, user_input):
    client = _build_groq_client()
    model = get_env("GROQ_MODEL", "llama-3.1-8b-instant")
    response = _chat_with_retry(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Model returned empty content.")
    return content


def _chat_with_retry(
    *,
    client,
    model,
    messages,
    temperature,
    response_format=None,
    max_attempts=2,
):
    request_kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        request_kwargs["response_format"] = response_format

    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            # Retry only for rate limits; other failures should surface
            # immediately so the caller can fall back.
            if attempt == max_attempts or not _is_retryable_rate_limit(exc):
                raise
            sleep_seconds = min(3.0, 1.0 * attempt)
            time.sleep(sleep_seconds)


def _is_retryable_rate_limit(exc):
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    return exc.__class__.__name__ == "RateLimitError"
