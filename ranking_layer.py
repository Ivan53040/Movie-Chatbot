import math


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalized_year_score(movie_year, current_year=2026):
    if movie_year <= 0:
        return 0.0
    age = max(0, current_year - movie_year)
    return max(0.0, 1.0 - min(age, 40) / 40.0)


def score_movie(movie, *, ranking_context=None):
    ranking_context = ranking_context or {}

    similarity = _safe_float(movie.get("similarity", 0.0))
    popularity = _safe_float(movie.get("popularity", 0.0))
    vote_average = _safe_float(movie.get("vote_average", 0.0))
    movie_year = _safe_int(movie.get("year"), 0)

    score = 0.0
    score += similarity * 0.60
    score += min(1.0, vote_average / 10.0) * 0.18
    score += min(1.0, math.log1p(max(popularity, 0.0)) / math.log1p(1000.0)) * 0.12

    if ranking_context.get("prefer_recent", True):
        score += _normalized_year_score(movie_year) * 0.10

    movie_genres = {str(genre).strip().lower() for genre in movie.get("genres", []) if str(genre).strip()}
    if ranking_context.get("genre"):
        genre_value = str(ranking_context["genre"]).strip().lower()
        genre_aliases = {genre_value, "science fiction" if genre_value in {"sci-fi", "scifi"} else genre_value}
        if movie_genres.intersection(genre_aliases):
            score += 0.05

    movie_language = str(movie.get("language", "")).strip().lower()
    if ranking_context.get("language") and movie_language == str(ranking_context["language"]).strip().lower():
        score += 0.04

    if ranking_context.get("year"):
        target_year = _safe_int(ranking_context["year"], 0)
        if movie_year == target_year:
            score += 0.08

    movie["ranking_score"] = score
    return score


def rank_movies(movies, *, ranking_context=None):
    ranked_movies = []
    for movie in movies:
        ranked_movie = movie.copy()
        score_movie(ranked_movie, ranking_context=ranking_context)
        ranked_movies.append(ranked_movie)

    return sorted(
        ranked_movies,
        key=lambda movie: (
            _safe_float(movie.get("ranking_score", 0.0)),
            _safe_float(movie.get("similarity", 0.0)),
            _safe_float(movie.get("vote_average", 0.0)),
            _safe_float(movie.get("popularity", 0.0)),
        ),
        reverse=True,
    )
