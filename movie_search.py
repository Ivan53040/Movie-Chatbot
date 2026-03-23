"""
Search movies by genre, mood, and year.
Data source: movies.json (same directory as this script).
"""
import json
import re
from pathlib import Path

from franchise_support import detect_franchise_from_text, movie_matches_franchise

# movies.json path — all searches use this file
MOVIES_PATH = Path(__file__).parent / "movies.json"

GENRE_ALIASES = {
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "science fiction": "science fiction",
    "animation": "animation",
    "anime": "animation",
    "動漫": "animation",
    "动漫": "animation",
    "romcom": "romance",
}

LANGUAGE_ALIASES = {
    "english": "en",
    "en": "en",
    "japanese": "ja",
    "ja": "ja",
    "korean": "ko",
    "ko": "ko",
    "french": "fr",
    "fr": "fr",
    "spanish": "es",
    "es": "es",
}


def _load_movies():
    """Load movies from JSON file."""
    with open(MOVIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize_text(value):
    return str(value).strip().lower() if value and str(value).strip() else None


def _normalize_name_for_match(value):
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _normalize_name_tokens(value):
    normalized = _normalize_text(value)
    if normalized is None:
        return []
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if token]


def _normalize_genre(value):
    value_lower = _normalize_text(value)
    if value_lower is None:
        return None
    return GENRE_ALIASES.get(value_lower, value_lower)


def _normalize_language(value):
    value_lower = _normalize_text(value)
    if value_lower is None:
        return None
    return LANGUAGE_ALIASES.get(value_lower, value_lower)


def _listify(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _name_matches(query_value, candidate_value):
    query_normalized = _normalize_name_for_match(query_value)
    candidate_normalized = _normalize_name_for_match(candidate_value)
    if query_normalized is None or candidate_normalized is None:
        return False
    return (
        query_normalized == candidate_normalized
        or query_normalized in candidate_normalized
        or candidate_normalized in query_normalized
    )


def _text_matches(query_value, candidate_value):
    query_text = _normalize_text(query_value)
    candidate_text = _normalize_text(candidate_value)
    if query_text is None or candidate_text is None:
        return False
    return (
        query_text == candidate_text
        or query_text in candidate_text
        or candidate_text in query_text
    )


def _normalize_keyword_value(value):
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    if any(token in normalized for token in ("dc universe", "dc extended universe", "(dcu)", "(dceu)", " dcu", " dceu")):
        return "dc universe"
    if any(token in normalized for token in ("marvel cinematic universe", "(mcu)", " mcu", "marvel")):
        return "marvel cinematic universe"
    if "star wars" in normalized or "starwars" in normalized:
        return "star wars"
    return normalized


def _normalize_franchise_value(value):
    return detect_franchise_from_text(value)


def _person_match_score(fragment, candidate_name, popularity=0.0):
    fragment_normalized = _normalize_name_for_match(fragment)
    candidate_normalized = _normalize_name_for_match(candidate_name)
    if fragment_normalized is None or candidate_normalized is None:
        return None

    score = None
    candidate_tokens = _normalize_name_tokens(candidate_name)
    if fragment_normalized == candidate_normalized:
        score = 120
    elif any(token == fragment_normalized for token in candidate_tokens):
        score = 110
    elif any(token.startswith(fragment_normalized) for token in candidate_tokens):
        score = 100
    elif fragment_normalized in candidate_normalized:
        score = 80
    elif candidate_normalized in fragment_normalized:
        score = 60

    if score is None:
        return None
    try:
        popularity_bonus = min(float(popularity or 0.0), 100.0) / 4.0
    except (TypeError, ValueError):
        popularity_bonus = 0.0
    return score + popularity_bonus


def find_person_candidates(fragment, limit=3):
    # This powers the frontend clarification step when a short fragment might
    # refer to either an actor or a director.
    movies = _load_movies()
    candidates = {"cast": {}, "director": {}}

    for movie in movies:
        popularity = movie.get("popularity", 0.0)
        for cast_name in _listify(movie.get("cast", [])):
            score = _person_match_score(fragment, cast_name, popularity=popularity)
            if score is None:
                continue
            entry = candidates["cast"].get(cast_name)
            if entry is None:
                candidates["cast"][cast_name] = {
                    "name": cast_name,
                    "score": score,
                    "total_popularity": float(popularity or 0.0),
                    "match_count": 1,
                }
            else:
                entry["score"] = max(entry["score"], score)
                entry["total_popularity"] += float(popularity or 0.0)
                entry["match_count"] += 1

        director_name = movie.get("director")
        score = _person_match_score(fragment, director_name, popularity=popularity)
        if score is not None:
            entry = candidates["director"].get(director_name)
            if entry is None:
                candidates["director"][director_name] = {
                    "name": director_name,
                    "score": score,
                    "total_popularity": float(popularity or 0.0),
                    "match_count": 1,
                }
            else:
                entry["score"] = max(entry["score"], score)
                entry["total_popularity"] += float(popularity or 0.0)
                entry["match_count"] += 1

    return {
        role: sorted(
            role_candidates.values(),
            key=lambda item: (
                -item["score"],
                -item["total_popularity"],
                -item["match_count"],
                item["name"],
            ),
        )[:limit]
        for role, role_candidates in candidates.items()
    }


def _matches_filters(
    movie,
    genre=None,
    mood=None,
    year_min=None,
    year_max=None,
    year=None,
    language=None,
    cast=None,
    director=None,
    keywords=None,
    franchise=None,
):
    # This function is the canonical definition of "hard match" in the app.
    genre_lower = _normalize_genre(genre)
    mood_lower = _normalize_text(mood)
    language_lower = _normalize_language(language)
    cast_lower = _normalize_text(cast)
    director_lower = _normalize_text(director)
    keywords_lower = _normalize_keyword_value(keywords)
    franchise_value = _normalize_franchise_value(franchise)

    if genre_lower is not None:
        movie_genres = [
            _normalize_genre(g)
            for g in _listify(movie.get("genres", movie.get("genre", [])))
            if _normalize_genre(g)
        ]

        if genre_lower not in movie_genres:
            return False

    if mood_lower is not None:
        keyword_tokens = [
            _normalize_text(k)
            for k in _listify(movie.get("keywords", []))
            if _normalize_text(k)
        ]
        mood_tokens = [
            _normalize_text(m)
            for m in _listify(movie.get("mood", []))
            if _normalize_text(m)
        ]
        overview_lower = _normalize_text(movie.get("overview", "")) or ""

        if (
            mood_lower not in mood_tokens
            and mood_lower not in keyword_tokens
            and mood_lower not in overview_lower
        ):
            return False

    raw_year = movie.get("year")
    try:
        movie_year = int(raw_year)
    except (TypeError, ValueError):
        movie_year = None

    if year is not None:
        if movie_year is None or movie_year != year:
            return False

    if year_min is not None:
        if movie_year is None or movie_year < year_min:
            return False

    if year_max is not None:
        if movie_year is None or movie_year > year_max:
            return False

    if language_lower is not None:
        movie_languages = [
            _normalize_language(l)
            for l in _listify(movie.get("language", []))
            if _normalize_language(l)
        ]

        if language_lower not in movie_languages:
            return False

    if cast_lower is not None:
        movie_cast = [
            _normalize_text(name)
            for name in _listify(movie.get("cast", []))
            if _normalize_text(name)
        ]
        if not any(_name_matches(cast_lower, name) for name in movie_cast):
            return False

    if director_lower is not None:
        movie_director = _normalize_text(movie.get("director"))
        if not _name_matches(director_lower, movie_director):
            return False

    if keywords_lower is not None:
        movie_keywords = [
            _normalize_keyword_value(keyword)
            for keyword in _listify(movie.get("keywords", []))
            if _normalize_keyword_value(keyword)
        ]
        overview_lower = _normalize_text(movie.get("overview", "")) or ""
        if not any(_text_matches(keywords_lower, keyword) for keyword in movie_keywords) and not _text_matches(keywords_lower, overview_lower):
            return False

    if franchise_value is not None and not movie_matches_franchise(movie, franchise_value):
        return False

    return True


def filter_movies(
    movies,
    genre=None,
    mood=None,
    year_min=None,
    year_max=None,
    year=None,
    language=None,
    cast=None,
    director=None,
    keywords=None,
    franchise=None,
):
    # Keep this as a thin wrapper so filtering can be reused on both the full
    # dataset and hybrid candidate lists.
    results = []
    for movie in movies:
        if _matches_filters(
            movie,
            genre=genre,
            mood=mood,
            year_min=year_min,
            year_max=year_max,
            year=year,
            language=language,
            cast=cast,
            director=director,
            keywords=keywords,
            franchise=franchise,
        ):
            results.append(movie)
    return results


def search_movies(
    genre=None,
    mood=None,
    year_min=None,
    year_max=None,
    year=None,
    language=None,
    cast=None,
    director=None,
    keywords=None,
    franchise=None,
):
    """
    Search movies by genre, mood, and/or year filters.
    All provided filters must match (AND logic).
    """
    movies = _load_movies()
    return filter_movies(
        movies,
        genre=genre,
        mood=mood,
        year_min=year_min,
        year_max=year_max,
        year=year,
        language=language,
        cast=cast,
        director=director,
        keywords=keywords,
        franchise=franchise,
    )


if __name__ == "__main__":
    print("Movies with genre Drama, mood emotional, from 2000 onward:")
    for m in search_movies(genre="Drama", mood="emotional", year_min=2000)[:5]:
        print(f"  {m['title']} ({m['year']}) - {m['genre']} | {m['mood']}")

    print("\nAll Romance movies:")
    romance = search_movies(genre="Romance")
    print(f"  Found {len(romance)} movies")

    print("\nEnglish movies:")
    english_movies = search_movies(language="English")
    print(f"  Found {len(english_movies)} movies")
