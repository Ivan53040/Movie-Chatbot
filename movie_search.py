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


def search_movies(genre=None, mood=None, year_min=None, year_max=None, year=None):
    """
    Search movies by genre, mood, and/or minimum and maximum year.
    All provided filters must match (AND logic).

    Args:
        genre: Filter by genre (e.g. "Drama", "Comedy"). Case-insensitive.
        mood: Filter by mood (e.g. "emotional", "stylish"). Case-insensitive.
        year_min: Only include movies from this year or later.
        year_max: Only include movies from this year or earlier.
        year: Only include movies from this year.

    Returns:
        List of matching movie dicts (title, genre, year, mood, language).
    """
    movies = _load_movies()
    results = []

    genre_lower = genre.strip().lower() if (genre and genre.strip()) else None
    mood_lower = mood.strip().lower() if (mood and mood.strip()) else None

    for movie in movies:
        if genre_lower is not None:
            movie_genres = [g.lower() for g in movie.get("genre", [])]
            if genre_lower not in movie_genres:
                continue
        if mood_lower is not None:
            movie_moods = [m.lower() for m in movie.get("mood", [])]
            if mood_lower not in movie_moods:
                continue
        if year_min is not None:
            if movie.get("year", 0) < year_min:
                continue
        if year_max is not None:
            if movie.get("year", 0) > year_max:
                continue
        if year is not None:
            if movie.get("year", 0) != year:
                continue
        results.append(movie)
        
    return results


if __name__ == "__main__":
    # Example usage
    print("Movies with genre Drama, mood emotional, from 2000 onward:")
    for m in search_movies(genre="Drama", mood="emotional", year_min=2000)[:5]:
        print(f"  {m['title']} ({m['year']}) - {m['genre']} | {m['mood']}")

    print("\nAll Romance movies:")
    romance = search_movies(genre="Romance")
    print(f"  Found {len(romance)} movies")
