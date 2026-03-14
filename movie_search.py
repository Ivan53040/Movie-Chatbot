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


def search_movies(genre=None, mood=None, year_min=None, year_max=None, year=None, language=None):
    """
    Search movies by genre, mood, and/or year filters.
    All provided filters must match (AND logic).

    Args:
        genre: Filter by genre (e.g. "Drama", "Comedy"). Case-insensitive.
        mood: Filter by mood (e.g. "emotional", "stylish"). Case-insensitive.
        year_min: Only include movies from this year or later.
        year_max: Only include movies from this year or earlier.
        year: Only include movies from this exact year.
        language: Only include movies from this language. Case-insensitive.

    Returns:
        List of matching movie dicts.
    """
    movies = _load_movies()
    results = []

    genre_lower = genre.strip().lower() if genre and genre.strip() else None
    mood_lower = mood.strip().lower() if mood and mood.strip() else None
    language_lower = language.strip().lower() if language and language.strip() else None

    for movie in movies:
        # Genre filter
        if genre_lower is not None:
            movie_genres = [g.strip().lower() for g in movie.get("genre", [])]
            if genre_lower not in movie_genres:
                continue

        # Mood filter
        if mood_lower is not None:
            movie_moods = [m.strip().lower() for m in movie.get("mood", [])]
            if mood_lower not in movie_moods:
                continue

        # Year range filter
        movie_year = movie.get("year", 0)

        if year is not None and movie_year != year:
            continue
        if year_min is not None and movie_year < year_min:
            continue
        if year_max is not None and movie_year > year_max:
            continue

        # Language filter
        if language_lower is not None:
            movie_language_data = movie.get("language", [])

            if isinstance(movie_language_data, str):
                movie_languages = [movie_language_data.strip().lower()]
            else:
                movie_languages = [l.strip().lower() for l in movie_language_data]

            if language_lower not in movie_languages:
                continue

        results.append(movie)

    return results


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