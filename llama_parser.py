import re

from pydantic import BaseModel

from api_parser_client import chat_json
from franchise_support import (
    detect_franchise_from_text,
    franchise_keyword,
    franchise_semantic_query,
)


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
    "light": ["light", "è¼•é¬†", "è½»æ¾"],
    "funny": ["funny", "comedy", "æžç¬‘", "å¥½ç¬‘"],
    "emotional": ["emotional", "sad", "touching", "å‚¬æ·š", "å‚¬æ³ª", "æ„Ÿäºº"],
    "dark": ["dark", "grim", "é»‘æš—", "é™°æš—", "é˜´æš—"],
    "exciting": ["exciting", "thrilling", "åˆºæ¿€", "ç†±è¡€", "çƒ­è¡€"],
    "uplifting": ["uplifting", "inspiring", "å‹µå¿—", "åŠ±å¿—", "æŒ¯å¥®", "æŒ¯å¥‹"],
    "romantic": ["romantic", "æµªæ¼«"],
}

NON_PERSON_TERMS = {
    "action",
    "animated",
    "animation",
    "anime",
    "comedy",
    "crime",
    "dark",
    "director",
    "drama",
    "emotional",
    "exciting",
    "fantasy",
    "film",
    "funny",
    "hero",
    "horror",
    "light",
    "movie",
    "mystery",
    "romance",
    "romantic",
    "sci-fi",
    "scifi",
    "science fiction",
    "sport",
    "sports",
    "thriller",
    "uplifting",
    "war",
}

DIRECTOR_NAME_ALIASES = {
    "chris nolan": "Christopher Nolan",
    "christopher nolan": "Christopher Nolan",
    "nolan": "Christopher Nolan",
    "david fincher": "David Fincher",
    "fincher": "David Fincher",
}

CAST_NAME_ALIASES = {
    "rdj": "Robert Downey Jr.",
    "robert downey jr": "Robert Downey Jr.",
    "robert downey jr.": "Robert Downey Jr.",
    "leo": "Leonardo DiCaprio",
    "leo dicaprio": "Leonardo DiCaprio",
    "leonardo dicaprio": "Leonardo DiCaprio",
}

PERSON_NAME_ALIASES = {}
PERSON_NAME_ALIASES.update(DIRECTOR_NAME_ALIASES)
PERSON_NAME_ALIASES.update(CAST_NAME_ALIASES)

class MovieQuery(BaseModel):
    genre: str | None = None
    mood: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    year: int | None = None
    language: str | None = None
    cast: str | None = None
    director: str | None = None
    keywords: str | None = None
    similar_to: str | None = None
    semantic_query: str | None = None


# Normalize model output aggressively because parser mistakes should degrade
# into "missing field" rather than leaking bad values deeper into the pipeline.
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

    # Regex year rules run after the LLM so explicit phrases like "after 2010"
    # always win over a fuzzy parse.
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

    match = re.search(
        r"(19\d{2}|20\d{2}|21\d{2})\s*å¹´(?:\s*[çš„ä¹‹])?(?:\s*(å¾Œ|åŽ))?",
        user_input,
    )
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
    if mood.lower() == "exciting" and "excited" in normalized_input:
        return True
    for token in MOOD_HINTS.get(mood.lower(), [mood.lower()]):
        if token.lower() in normalized_input:
            return True
    return False


def _extract_language_hint(user_input: str) -> str | None:
    match = re.search(
        r"\b(?:in|an|a)\s+(en|ja|ko|fr|es|de|it|tl|ta|sv|cs)\s+[a-z][a-z\- ]*\s+movie\b",
        user_input.lower(),
    )
    if match:
        return match.group(1)
    return None


def _extract_keyword_hint(user_input: str) -> str | None:
    lower_input = user_input.lower()
    match = re.search(
        r"\bmovie(?:s)?\s+about\s+(.+?)(?:\s+after\s+\d{4}|\s+before\s+\d{4}|\s+in\s+\d{4}|$)",
        lower_input,
    )
    if match:
        return match.group(1).strip(" .,!?:;\"'")

    match = re.search(
        r"\babout\s+(.+?)(?:\s+movie(?:s)?|\s+after\s+\d{4}|\s+before\s+\d{4}|\s+in\s+\d{4}|$)",
        lower_input,
    )
    if match:
        return match.group(1).strip(" .,!?:;\"'")

    return None


def _extract_cast_hint(user_input: str) -> str | None:
    patterns = [
        r"\bstarring\s+([a-z][a-z\s\.'\-]+?)(?:\s+movie|\s+after|\s+before|$)",
        r"\bcast by\s+([a-z][a-z\s\.'\-]+?)(?:\s+movie|\s+after|\s+before|$)",
        r"\bwith\s+([a-z][a-z\s\.'\-]+?)\s+in it\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input, flags=re.IGNORECASE)
        if match:
            value = _clean_person_hint(match.group(1))
            if _looks_like_person_name(value):
                return value
    return None


def _extract_loose_cast_hint(user_input: str) -> str | None:
    patterns = [
        r"\b([A-Z][a-zA-Z\.'\-]+\s+[A-Z][a-zA-Z\.'\-]+)\s+movie\b",
        r"\b([A-Z][a-zA-Z\.'\-]+\s+[A-Z][a-zA-Z\.'\-]+)\s+film\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            value = _clean_person_hint(match.group(1))
            if _looks_like_person_name(value):
                return value
    return None


def _extract_director_hint(user_input: str) -> str | None:
    patterns = [
        r"\bdirected by\s+([a-z][a-z\s\.'\-]+?)(?:\s+movie|\s+after|\s+before|$)",
        r"\bfrom director\s+([a-z][a-z\s\.'\-]+?)(?:\s+movie|\s+after|\s+before|$)",
        r"\bdirector is\s+([a-z][a-z\s\.'\-]+?)(?:\s+movie|\s+after|\s+before|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input, flags=re.IGNORECASE)
        if match:
            value = _clean_person_hint(match.group(1))
            if _looks_like_person_name(value):
                return value
    return None


def _extract_loose_director_hint(user_input: str) -> str | None:
    patterns = [
        r"\b(?:a|an)\s+([A-Z][a-zA-Z\.'\-]+)\s+movie\b",
        r"\b([A-Z][a-zA-Z\.'\-]+)\s+movie\b",
        r"\b(?:a|an)\s+([A-Z][a-zA-Z\.'\-]+)\s+film\b",
        r"\b([A-Z][a-zA-Z\.'\-]+)\s+film\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            value = _clean_person_hint(match.group(1))
            if _looks_like_person_name(value):
                return value
    return None


def _has_explicit_director_phrase(user_input: str) -> bool:
    lowered = str(user_input).lower()
    return (
        "directed by" in lowered
        or "from director" in lowered
        or "director is" in lowered
    )


def _has_explicit_cast_phrase(user_input: str) -> bool:
    lowered = str(user_input).lower()
    return "starring" in lowered or "cast by" in lowered or "with " in lowered


def _clean_person_hint(value: str) -> str:
    return (
        str(value)
        .strip(" .,!?:;\"'")
        .removeprefix("a ")
        .removeprefix("an ")
        .removeprefix("the ")
        .strip()
    )


def _normalize_person_alias(value: str | None, role: str | None = None) -> str | None:
    cleaned = _to_str_or_none(value)
    if cleaned is None:
        return None
    alias_key = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
    if role == "cast":
        return CAST_NAME_ALIASES.get(alias_key, cleaned)
    if role == "director":
        return DIRECTOR_NAME_ALIASES.get(alias_key, cleaned)
    return PERSON_NAME_ALIASES.get(alias_key, cleaned)


def _looks_like_person_name(value: str | None) -> bool:
    cleaned = _to_str_or_none(value)
    if cleaned is None:
        return False
    lowered = cleaned.lower()
    if lowered in NON_PERSON_TERMS:
        return False
    if any(token in NON_PERSON_TERMS for token in lowered.split()):
        return False
    return True


def _normalize_parsed_query(user_input: str, query: dict) -> dict:
    # Post-processing is where the parser becomes reliable: we repair years,
    # remove unsupported inference, and prefer explicit user phrasing.
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
    if not query.get("mood"):
        for mood in VALID_MOODS:
            if _is_mood_explicit(user_input, mood):
                query["mood"] = mood
                break

    language_hint = _extract_language_hint(user_input)
    if language_hint and not query.get("language"):
        query["language"] = language_hint

    keyword_hint = _extract_keyword_hint(user_input)
    if keyword_hint and not query.get("keywords") and not query.get("similar_to"):
        query["keywords"] = keyword_hint

    query["cast"] = _normalize_person_alias(query.get("cast"), role="cast")
    query["director"] = _normalize_person_alias(query.get("director"), role="director")

    # Name extraction is handled outside the LLM as well so actor/director
    # queries work even when the model is vague.
    explicit_cast_hint = _extract_cast_hint(user_input)
    loose_cast_hint = None
    if explicit_cast_hint is None:
        loose_cast_hint = _extract_loose_cast_hint(user_input)

    cast_hint = explicit_cast_hint or loose_cast_hint
    cast_hint = _normalize_person_alias(cast_hint, role="cast")

    if cast_hint:
        query["cast"] = cast_hint
        query["similar_to"] = None
        query["semantic_query"] = None

    director_hint = _extract_director_hint(user_input)
    loose_director_hint = None
    if director_hint is None and not explicit_cast_hint:
        loose_director_hint = _extract_loose_director_hint(user_input)
        director_hint = loose_director_hint
    director_hint = _normalize_person_alias(director_hint, role="director")
    loose_director_alias_hit = bool(
        loose_director_hint
        and director_hint
        and director_hint != loose_director_hint
    )

    if (
        loose_cast_hint
        and not explicit_cast_hint
        and not director_hint
        and not _has_explicit_cast_phrase(user_input)
    ):
        loose_director_alias = _normalize_person_alias(loose_cast_hint, role="director")
        if loose_director_alias and loose_director_alias != loose_cast_hint:
            director_hint = loose_director_alias
            cast_hint = None
            query["cast"] = None

    if director_hint:
        query["director"] = director_hint
        query["similar_to"] = None
        query["semantic_query"] = None

    if cast_hint and not _has_explicit_director_phrase(user_input):
        if loose_director_alias_hit and not explicit_cast_hint:
            query["cast"] = None
            cast_hint = None
        else:
            query["director"] = None

    genre_value = str(query.get("genre") or "").strip().lower()
    # Broad concepts like "superhero" are better represented as topics than as
    # hard genres in this dataset.
    if genre_value in {"superhero", "super hero"}:
        query["keywords"] = query.get("keywords") or "superhero"
        query["semantic_query"] = query.get("semantic_query") or "superhero movie"
        query["genre"] = None

    if genre_value in {"anime", "animation", "animated", "å‹•æ¼«", "åŠ¨æ¼«"}:
        query["genre"] = "Animation"
        if (
            not query.get("keywords")
            or query.get("keywords", "").strip().lower()
            in {"animation", "animated"}
        ):
            query["keywords"] = "anime"
        query["semantic_query"] = query.get("semantic_query") or "anime animated movie"

    lowered_input = str(user_input or "").lower()
    franchise = detect_franchise_from_text(user_input) or detect_franchise_from_text(query.get("keywords"))
    if franchise:
        query["franchise"] = franchise
        franchise_keyword_value = franchise_keyword(franchise)
        if franchise_keyword_value:
            query["keywords"] = franchise_keyword_value
        franchise_semantic = franchise_semantic_query(franchise)
        if franchise_semantic:
            query["semantic_query"] = query.get("semantic_query") or franchise_semantic
        if query.get("similar_to") and "like " not in lowered_input and "something like " not in lowered_input:
            query["similar_to"] = None

    if query.get("similar_to") == "Star Wars" and ("star wars" in lowered_input or "starwars" in lowered_input):
        if "like star wars" not in lowered_input and "something like star wars" not in lowered_input:
            query["similar_to"] = None
            query["keywords"] = "star wars"
            query["semantic_query"] = query.get("semantic_query") or franchise_semantic_query("star wars")
            query["franchise"] = "star wars"

    return query


def _extract_similar_to_hint(user_input: str) -> str | None:
    patterns = [
        r"\blike\s+([a-z0-9][a-z0-9\s:'&\-\.\!,]+?)(?:\s+but|\s+with|\s+after|\s+before|\s+from|$)",
        r"\bsomething like\s+([a-z0-9][a-z0-9\s:'&\-\.\!,]+?)(?:\s+but|\s+with|\s+after|\s+before|\s+from|$)",
    ]
    text = str(user_input).strip()
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,!?:;\"'")
    return None


def _keyword_in_text(user_input: str, options: list[str]) -> bool:
    lowered = user_input.lower()
    return any(option in lowered for option in options)


def _fallback_parse_user_query(user_input: str) -> dict:
    # The fallback parser is intentionally simple, but it preserves the same
    # query shape so the rest of the system does not need a separate path.
    text = str(user_input).strip()
    lowered = text.lower()

    query = {
        "genre": None,
        "mood": None,
        "year_min": None,
        "year_max": None,
        "year": None,
        "language": None,
        "cast": None,
        "director": None,
        "keywords": None,
        "similar_to": None,
        "semantic_query": None,
    }

    genre_keywords = {
        "Comedy": ["comedy", "funny", "romcom", "rom-com"],
        "Drama": ["drama", "emotional", "touching"],
        "Science Fiction": ["sci-fi", "scifi", "science fiction", "space", "alien"],
        "Romance": ["romance", "romantic", "love story"],
        "Thriller": ["thriller", "suspense", "tense"],
        "Action": ["action", "exciting"],
        "Animation": ["animation", "animated", "anime"],
        "Horror": ["horror", "scary"],
        "Crime": ["crime", "detective"],
        "Mystery": ["mystery"],
        "Fantasy": ["fantasy", "magical"],
    }
    for genre, keywords in genre_keywords.items():
        if _keyword_in_text(lowered, keywords):
            query["genre"] = genre
            break

    for mood in VALID_MOODS:
        if _is_mood_explicit(text, mood):
            query["mood"] = mood
            break

    language_map = {
        "english": "en",
        "japanese": "ja",
        "korean": "ko",
        "french": "fr",
        "spanish": "es",
    }
    for label, code in language_map.items():
        if label in lowered:
            query["language"] = code
            break

    if "robot" in lowered or "ai" in lowered or "artificial intelligence" in lowered:
        query["keywords"] = "robot"
        query["semantic_query"] = "robot movies"
    elif (
        "sport" in lowered
        or "sports" in lowered
        or "é‹å‹•" in text
        or "è¿åŠ¨" in text
        or "é«”è‚²" in text
        or "ä½“è‚²" in text
    ):
        query["keywords"] = "sports"
        query["semantic_query"] = "sports movies"
    elif "time travel" in lowered:
        query["keywords"] = "time travel"
        query["semantic_query"] = "time travel movies"
    elif "space" in lowered:
        query["keywords"] = "space"
        query["semantic_query"] = "space movies"
    elif "alien" in lowered:
        query["keywords"] = "alien"
        query["semantic_query"] = "alien movies"

    similar_to = _extract_similar_to_hint(text)
    if similar_to:
        query["similar_to"] = similar_to

    has_structured_signal = any(
        query.get(key) is not None
        for key in (
            "genre",
            "mood",
            "year_min",
            "year_max",
            "year",
            "language",
            "cast",
            "director",
            "keywords",
        )
    )
    if not query["similar_to"] and not has_structured_signal:
        query["semantic_query"] = query["semantic_query"] or text

    return _normalize_parsed_query(user_input, query)


def parse_user_query(user_input: str) -> dict:
    # The LLM is used only for structured extraction. Deterministic cleanup
    # below still owns the final query object.
    system_prompt = (
        "You are a movie preference parser.\n"
        "Extract movie search filters from the user's message.\n\n"
        "Return a JSON object with these keys only:\n"
        "genre, mood, year_min, year_max, year, language, cast, director, keywords, similar_to, semantic_query\n\n"
        "Rules:\n"
        "- genre should be a movie genre (Romance, Comedy, Sci-Fi, Drama, etc)\n"
        "- mood should be a simple word (light, emotional, dark, funny, exciting)\n"
        "- Only set mood when the user explicitly states a mood or feeling\n"
        "- Do not infer mood from genre, plot, or semantic_query\n"
        "- year_min means movies after that year\n"
        "- year_max means movies before that year\n"
        "- year means exactly that year\n"
        "- If the user asks for movies after a year, set year_min to one year after that year\n"
        "- If the user asks for movies before or earlier than a year, set year_max to one year before that year\n"
        "- If the user asks for movies since a year, set year_min to that year\n"
        "- If the user asks for movies from a year and it clearly means a lower bound, set year_min to that year\n"
        "- If the user asks for movies in a specific year, set year to that exact year\n"
        "- If the user gives one exact year, prefer year over year_min or year_max\n"
        "- Never set both year and year_min/year_max unless the user clearly gives a range\n"
        "- If the user does not mention a year, year/year_min/year_max must be null, never 0\n"
        "- language means movie language\n"
        "- language can also be a short code like en, ja, ko, tl, ta, sv, or cs\n"
        "- cast is a person or actor name the user wants in the movie\n"
        "- director is a director name the user wants in the movie\n"
        "- If the user asks for movies starring an actor, put the name in cast\n"
        "- If the user asks for movies with an actor in it, put the name in cast\n"
        "- If the user asks for a movie cast by someone, put the name in cast\n"
        "- If the user asks for movies directed by someone, put the name in director\n"
        "- If the user asks for movies from a director or says director is someone, put the name in director\n"
        "- If the user clearly wants cast or director, do not put that person into semantic_query\n"
        "- keywords is a short topic like robot, superhero, anime, time travel, or space survival\n"
        "- If the user asks for movies about a short concrete topic, put that topic in keywords\n"
        "- similar_to must only be used when the user explicitly mentions a specific movie title\n"
        "- Never use similar_to for generic concepts, topics, themes, or categories\n"
        "- Phrases like robot movies, space movies, sad movies, war movies, or action movies are not movie titles\n"
        "- semantic_query is a free-text taste query about themes, vibe, or story style\n"
        "- If the user describes a broad vibe, story idea, or concept, copy that into semantic_query\n"
        "- If the user asks for a broad topic like superhero or anime movies, use keywords or semantic_query, not similar_to\n"
        "- If the user says 'like Interstellar', set similar_to to 'Interstellar'\n"
        "- If the user says 'something like' a specific movie title, set similar_to to that movie title\n"
        "- If the user says they want robot-related movies, set semantic_query to 'robot movies'\n"
        "- Do not use similar_to for superhero, anime, robot, sports, space, alien, romance, thriller, or other generic categories unless they are clearly movie titles\n"
        "- For superhero or super hero requests, prefer keywords='superhero'\n"
        "- For anime, animated, or animation movie requests, prefer genre='Animation' and keywords='anime'\n"
        "- For robot, AI, artificial intelligence, space, alien, sports, war, crime, horror, thriller, or similar topic requests, semantic_query is often appropriate\n"
        "- If the user asks in Chinese for machine, robot, AI, sports, anime, space, war, thriller, romance, horror, Korean movies, or Japanese movies, map that to keywords, genre, language, or semantic_query instead of similar_to unless a real movie title is named\n"
        "- Example: 'I want a movie cast by Keanu Reeves' -> cast='Keanu Reeves'\n"
        "- Example: 'I want a movie directed by Christopher Nolan' -> director='Christopher Nolan'\n"
        "- Example: 'I want a superhero movie' -> keywords='superhero'\n"
        "- Example: 'I want a tl Thriller movie' -> language='tl', genre='Thriller'\n"
        "- Example: 'I want a movie about alien life-form after 1930' -> keywords='alien life-form', year_min=1931\n"
        "- Example: 'movies after 2010' -> year_min=2011\n"
        "- Example: 'movies before 2000' -> year_max=1999\n"
        "- Example: 'movies from 1999' -> year=1999\n"
        "- Example: 'movies since 2015' -> year_min=2015\n"
        "- Example: 'movies with Leonardo DiCaprio in it' -> cast='Leonardo DiCaprio'\n"
        "- Example: 'movies from director Nolan' -> director='Christopher Nolan'\n"
        "- Example: 'something like Interstellar but after 2010' -> similar_to='Interstellar', year_min=2011\n"
        "- Example: 'æœ€è¿‘æœ‰ä»€éº¼å¥½çœ‹çš„å‹•æ¼«é›»å½±' -> genre='Animation', keywords='anime'\n"
        "- If the user asks in Chinese for machine, robot, AI, or space related movies, use semantic_query, not similar_to\n"
        "- Example: 'I want movies like Interstellar' -> similar_to='Interstellar'\n"
        "- Example: 'Recommend robot movies' -> semantic_query='robot movies'\n"
        "- Example: 'æˆ‘æƒ³çœ‹æ©Ÿå™¨äººç›¸é—œçš„é›»å½±' -> semantic_query='robot movies'\n"
        "- Example: 'æŽ¨è–¦åƒæ˜Ÿéš›æ•ˆæ‡‰çš„é›»å½±' -> similar_to='Interstellar'\n"
        "- If information is missing return null\n"
        "- Return ONLY valid JSON"
    )
    try:
        data = chat_json(system_prompt=system_prompt, user_input=user_input)
    except Exception:
        return _fallback_parse_user_query(user_input)
    parsed_query = {
        "genre": _to_str_or_none(data.get("genre")),
        "mood": _to_str_or_none(data.get("mood")),
        "year_min": _to_int_or_none(data.get("year_min")),
        "year_max": _to_int_or_none(data.get("year_max")),
        "year": _to_int_or_none(data.get("year")),
        "language": _to_str_or_none(data.get("language")),
        "cast": _to_str_or_none(data.get("cast")),
        "director": _to_str_or_none(data.get("director")),
        "keywords": _to_str_or_none(data.get("keywords")),
        "similar_to": _to_str_or_none(data.get("similar_to")),
        "semantic_query": _to_str_or_none(data.get("semantic_query")),
    }
    return _normalize_parsed_query(user_input, parsed_query)


if __name__ == "__main__":
    from router import main

    main()
