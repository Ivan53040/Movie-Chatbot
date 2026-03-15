import json

from config import get_env


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

    return Groq(api_key=api_key)


def chat_json(*, system_prompt, user_input):
    client = _build_groq_client()
    model = get_env("GROQ_MODEL", "llama-3.1-8b-instant")

    response = client.chat.completions.create(
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
