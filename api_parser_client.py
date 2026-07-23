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


def build_chat_model(*, temperature):
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise RuntimeError(
            "LangChain Groq dependencies are not installed. "
            "Install them with: pip install langchain langchain-groq"
        ) from exc

    api_key = get_env("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to .env before running the chatbot."
        )

    return ChatGroq(
        api_key=api_key,
        model=get_env("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=temperature,
        timeout=_get_float_env("GROQ_TIMEOUT_SECONDS", 12.0),
        max_retries=_get_int_env("GROQ_MAX_RETRIES", 0),
    )


def invoke_messages(*, messages, temperature, response_format=None, max_attempts=2):
    for attempt in range(1, max_attempts + 1):
        try:
            model = build_chat_model(temperature=temperature)
            if response_format is not None:
                model = model.bind(response_format=response_format)
            return model.invoke(messages)
        except Exception as exc:
            if attempt == max_attempts or not _is_retryable_rate_limit(exc):
                raise
            sleep_seconds = min(3.0, 1.0 * attempt)
            time.sleep(sleep_seconds)


def invoke_json_messages(*, messages, temperature=0):
    response = invoke_messages(
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = coerce_content_to_text(response.content)
    if not content:
        raise RuntimeError("Model returned empty content.")
    return json.loads(content)


def invoke_text_messages(*, messages, temperature=0.2):
    response = invoke_messages(messages=messages, temperature=temperature)
    content = coerce_content_to_text(response.content)
    if not content:
        raise RuntimeError("Model returned empty content.")
    return content


def chat_json(*, system_prompt, user_input):
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:
        raise RuntimeError(
            "LangChain core is not installed. Install it with: pip install langchain"
        ) from exc

    return invoke_json_messages(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
    )


def chat_text(*, system_prompt, user_input):
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:
        raise RuntimeError(
            "LangChain core is not installed. Install it with: pip install langchain"
        ) from exc

    return invoke_text_messages(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
    )


def coerce_content_to_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def _is_retryable_rate_limit(exc):
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    return exc.__class__.__name__ == "RateLimitError"
