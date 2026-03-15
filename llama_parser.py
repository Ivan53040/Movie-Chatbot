import re

from pydantic import BaseModel
from api_parser_client import chat_json


VALID_MOODS = [
    "light",
    "funny",
    "emotional",
    "dark",
    "exciting",
    "uplifting",
    "romantic",
]

MOOD_HINTS = {
    "light": ["light", "輕鬆", "轻松"],
    "funny": ["funny", "comedy", "搞笑", "好笑"],
    "emotional": ["emotional", "sad", "touching", "催淚", "催泪", "感人"],
    "dark": ["dark", "grim", "黑暗", "陰暗", "阴暗"],
    "exciting": ["exciting", "thrilling", "刺激", "熱血", "热血"],
    "uplifting": ["uplifting", "inspiring", "勵志", "励志", "振奮", "振奋"],
    "romantic": ["romantic", "浪漫"],
}


class MovieQuery(BaseModel):
    genre: str | None = None
    mood: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    year: int | None = None
    language: str | None = None
    similar_to: str | None = None
    semantic_query: str | None = None


def _to_int_or_none(value):
    try:
        if value is None:
            return None
        parsed = int(value)
        if parsed <= 1800:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _to_str_or_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def _extract_year_overrides(user_input: str) -> dict:
    text = user_input.lower()
    overrides = {"year": None, "year_min": None, "year_max": None}

    match = re.search(r"\bafter\s+(19\d{2}|20\d{2}|21\d{2})\b", text)
    if match:
        overrides["year_min"] = int(match.group(1)) + 1
        return overrides

    match = re.search(r"\b(before|earlier than)\s+(19\d{2}|20\d{2}|21\d{2})\b", text)
    if match:
        overrides["year_max"] = int(match.group(2)) - 1
        return overrides

    match = re.search(r"\b(since|from)\s+(19\d{2}|20\d{2}|21\d{2})\b", text)
    if match:
        overrides["year_min"] = int(match.group(2))
        return overrides

    match = re.search(r"\b(in|from)\s+(19\d{2}|20\d{2}|21\d{2})\b", text)
    if match:
        overrides["year"] = int(match.group(2))
        return overrides

    match = re.search(r"(19\d{2}|20\d{2}|21\d{2})\s*年(?:\s*[的之])?(?:\s*(後|后))?", user_input)
    if match:
        year_value = int(match.group(1))
        if match.group(2):
            overrides["year_min"] = year_value + 1
        else:
            overrides["year"] = year_value
        return overrides

    match = re.search(r"(19\d{2}|20\d{2}|21\d{2})", user_input)
    if match:
        overrides["year"] = int(match.group(1))

    return overrides


def _is_mood_explicit(user_input: str, mood: str | None) -> bool:
    if not mood:
        return False
    normalized_input = user_input.lower()
    for token in MOOD_HINTS.get(mood.lower(), [mood.lower()]):
        if token.lower() in normalized_input:
            return True
    return False


def _normalize_parsed_query(user_input: str, query: dict) -> dict:
    year_overrides = _extract_year_overrides(user_input)
    if year_overrides["year"] is not None:
        query["year"] = year_overrides["year"]
        query["year_min"] = None
        query["year_max"] = None
    else:
        if year_overrides["year_min"] is not None:
            query["year_min"] = year_overrides["year_min"]
        if year_overrides["year_max"] is not None:
            query["year_max"] = year_overrides["year_max"]

    if query.get("mood") and not _is_mood_explicit(user_input, query["mood"]):
        query["mood"] = None

    return query


def parse_user_query(user_input: str) -> dict:
    system_prompt = (
        "You are a movie preference parser.\n"
        "Extract movie search filters from the user's message.\n\n"
        "Return a JSON object with these keys only:\n"
        "genre, mood, year_min, year_max, year, language, similar_to, semantic_query\n\n"
        "Rules:\n"
        "- genre should be a movie genre (Romance, Comedy, Sci-Fi, Drama, etc)\n"
        "- mood should be a simple word (light, emotional, dark, funny, exciting)\n"
        "- Only set mood when the user explicitly states a mood or feeling\n"
        "- Do not infer mood from genre, plot, or semantic_query\n"
        "- year_min means movies after that year\n"
        "- year_max means movies before that year\n"
        "- year means exactly that year\n"
        "- If the user does not mention a year, year/year_min/year_max must be null, never 0\n"
        "- language means movie language\n"
        "- similar_to must only be used when the user explicitly mentions a specific movie title\n"
        "- Never use similar_to for generic concepts, topics, themes, or categories\n"
        "- Phrases like robot movies, space movies, sad movies, war movies, or action movies are not movie titles\n"
        "- semantic_query is a free-text taste query about themes, vibe, or story style\n"
        "- If the user says 'like Interstellar', set similar_to to 'Interstellar'\n"
        "- If the user says they want robot-related movies, set semantic_query to 'robot movies'\n"
        "- If the user asks in Chinese for machine, robot, AI, or space related movies, use semantic_query, not similar_to\n"
        "- Example: 'I want movies like Interstellar' -> similar_to='Interstellar'\n"
        "- Example: 'Recommend robot movies' -> semantic_query='robot movies'\n"
        "- Example: '我想看機器人相關的電影' -> semantic_query='robot movies'\n"
        "- Example: '推薦像星際效應的電影' -> similar_to='Interstellar'\n"
        "- If the user describes a vibe or concept, copy that into semantic_query\n"
        "- If information is missing return null\n"
        "- Return ONLY valid JSON"
    )
    data = chat_json(system_prompt=system_prompt, user_input=user_input)
    parsed_query = {
        "genre": _to_str_or_none(data.get("genre")),
        "mood": _to_str_or_none(data.get("mood")),
        "year_min": _to_int_or_none(data.get("year_min")),
        "year_max": _to_int_or_none(data.get("year_max")),
        "year": _to_int_or_none(data.get("year")),
        "language": _to_str_or_none(data.get("language")),
        "similar_to": _to_str_or_none(data.get("similar_to")),
        "semantic_query": _to_str_or_none(data.get("semantic_query")),
    }
    return _normalize_parsed_query(user_input, parsed_query)


if __name__ == "__main__":
    from router import main

    main()
