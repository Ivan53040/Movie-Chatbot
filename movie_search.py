"""
Search movies by genre, mood, and year.
Data source: movies.json (same directory as this script).
"""
import json
from pathlib import Path

# movies.json path — all searches use this file
MOVIES_PATH = Path(__file__).parent / "movies.json"

GENRE_ALIASES = {
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "science fiction": "science fiction",
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


def _matches_filters(movie, genre=None, mood=None, year_min=None, year_max=None, year=None, language=None):
    genre_lower = _normalize_genre(genre)
    mood_lower = _normalize_text(mood)
    language_lower = _normalize_language(language)

    if genre_lower is not None:
        movie_genres = [
            _normalize_genre(g) for g in _listify(movie.get("genres", movie.get("genre", []))) if _normalize_genre(g)
        ]

        if genre_lower not in movie_genres:
            return False

    if mood_lower is not None:
        keyword_tokens = [_normalize_text(k) for k in _listify(movie.get("keywords", [])) if _normalize_text(k)]
        mood_tokens = [_normalize_text(m) for m in _listify(movie.get("mood", [])) if _normalize_text(m)]
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
            _normalize_language(l) for l in _listify(movie.get("language", [])) if _normalize_language(l)
        ]

        if language_lower not in movie_languages:
            return False

    return True


def filter_movies(movies, genre=None, mood=None, year_min=None, year_max=None, year=None, language=None):
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
        ):
            results.append(movie)
    return results


def search_movies(genre=None, mood=None, year_min=None, year_max=None, year=None, language=None):
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
