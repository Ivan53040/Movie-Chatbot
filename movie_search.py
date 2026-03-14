"""
Search movies by genre, mood, and year.
Data source: movies.json (same directory as this script).
"""
import json
from pathlib import Path

# movies.json path — all searches use this file
MOVIES_PATH = Path(__file__).parent / "movies.json"


def _load_movies():
    """Load movies from JSON file."""
    with open(MOVIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _matches_filters(movie, genre=None, mood=None, year_min=None, year_max=None, year=None, language=None):
    genre_lower = genre.strip().lower() if genre and str(genre).strip() else None
    mood_lower = mood.strip().lower() if mood and str(mood).strip() else None
    language_lower = language.strip().lower() if language and str(language).strip() else None

    if genre_lower is not None:
        movie_genre_data = movie.get("genre", [])
        if isinstance(movie_genre_data, str):
            movie_genres = [movie_genre_data.strip().lower()]
        else:
            movie_genres = [g.strip().lower() for g in movie_genre_data if str(g).strip()]

        if genre_lower not in movie_genres:
            return False

    if mood_lower is not None:
        movie_mood_data = movie.get("mood", [])
        if isinstance(movie_mood_data, str):
            movie_moods = [movie_mood_data.strip().lower()]
        else:
            movie_moods = [m.strip().lower() for m in movie_mood_data if str(m).strip()]

        if mood_lower not in movie_moods:
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
        movie_language_data = movie.get("language", [])

        if isinstance(movie_language_data, str):
            movie_languages = [movie_language_data.strip().lower()]
        else:
            movie_languages = [l.strip().lower() for l in movie_language_data if str(l).strip()]

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
