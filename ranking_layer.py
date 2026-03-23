import math

from franchise_support import movie_matches_franchise


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


def _text_matches(query, candidate):
    query_text = str(query or "").strip().lower()
    candidate_text = str(candidate or "").strip().lower()
    if not query_text or not candidate_text:
        return False
    return (
        query_text == candidate_text
        or query_text in candidate_text
        or candidate_text in query_text
    )


def _normalize_keyword_value(value):
    normalized = str(value or "").strip().lower()
    if not normalized:
        return ""
    if any(token in normalized for token in ("dc universe", "dc extended universe", "(dcu)", "(dceu)", " dcu", " dceu")):
        return "dc universe"
    if any(token in normalized for token in ("marvel cinematic universe", "(mcu)", " mcu", "marvel")):
        return "marvel cinematic universe"
    if "star wars" in normalized or "starwars" in normalized:
        return "star wars"
    return normalized


def _normalized_year_score(movie_year, current_year=2026):
    if movie_year <= 0:
        return 0.0
    age = max(0, current_year - movie_year)
    return max(0.0, 1.0 - min(age, 40) / 40.0)


def score_movie(movie, *, ranking_context=None):
    # Ranking is intentionally handcrafted so each factor is easy to inspect and
    # retune.
    ranking_context = ranking_context or {}

    similarity = _safe_float(movie.get("similarity", 0.0))
    popularity = _safe_float(movie.get("popularity", 0.0))
    vote_average = _safe_float(movie.get("vote_average", 0.0))
    movie_year = _safe_int(movie.get("year"), 0)

    score = 0.0
    score += similarity * 0.52
    score += min(1.0, vote_average / 10.0) * 0.22
    score += min(1.0, math.log1p(max(popularity, 0.0)) / math.log1p(1000.0)) * 0.16

    # Recency matters unless the user already asked for a specific year or
    # explicit minimum year.
    if ranking_context.get("prefer_recent", True):
        score += _normalized_year_score(movie_year) * 0.10
    if ranking_context.get("prefer_latest"):
        score += _normalized_year_score(movie_year) * 0.35

    movie_genres = {
        str(genre).strip().lower()
        for genre in movie.get("genres", [])
        if str(genre).strip()
    }
    if ranking_context.get("genre"):
        genre_value = str(ranking_context["genre"]).strip().lower()
        genre_aliases = {
            genre_value,
            "science fiction"
            if genre_value in {"sci-fi", "scifi"}
            else genre_value,
        }
        if movie_genres.intersection(genre_aliases):
            score += 0.05

    movie_language = str(movie.get("language", "")).strip().lower()
    if (
        ranking_context.get("language")
        and movie_language == str(ranking_context["language"]).strip().lower()
    ):
        score += 0.04

    movie_cast = {
        str(name).strip().lower()
        for name in movie.get("cast", [])
        if str(name).strip()
    }
    if ranking_context.get("cast"):
        cast_value = str(ranking_context["cast"]).strip().lower()
        if cast_value in movie_cast:
            score += 0.20

    movie_director = str(movie.get("director", "")).strip().lower()
    if ranking_context.get("director"):
        director_value = str(ranking_context["director"]).strip().lower()
        if director_value and director_value == movie_director:
            score += 0.16

    movie_keywords = {
        _normalize_keyword_value(keyword)
        for keyword in movie.get("keywords", [])
        if str(keyword).strip()
    }
    movie_mood = {
        str(item).strip().lower()
        for item in movie.get("mood", [])
        if str(item).strip()
    }
    overview_text = str(movie.get("overview", "")).strip().lower()

    if ranking_context.get("mood"):
        mood_value = str(ranking_context["mood"]).strip().lower()
        if (
            mood_value in movie_mood
            or mood_value in movie_keywords
            or mood_value in overview_text
        ):
            score += 0.08

    if ranking_context.get("keywords"):
        keyword_value = _normalize_keyword_value(ranking_context["keywords"])
        if (
            any(_text_matches(keyword_value, keyword) for keyword in movie_keywords)
            or _text_matches(keyword_value, overview_text)
        ):
            score += 0.10

    if ranking_context.get("franchise") and movie_matches_franchise(movie, ranking_context["franchise"]):
        score += 0.18

    if ranking_context.get("year"):
        target_year = _safe_int(ranking_context["year"], 0)
        if movie_year == target_year:
            score += 0.08

    movie["ranking_score"] = score
    return score


def rank_movies(movies, *, ranking_context=None):
    # Copy each movie before scoring so callers can still inspect the original
    # candidate objects if needed.
    ranked_movies = []
    for movie in movies:
        ranked_movie = movie.copy()
        score_movie(ranked_movie, ranking_context=ranking_context)
        ranked_movies.append(ranked_movie)

    prefer_latest = bool((ranking_context or {}).get("prefer_latest"))
    return sorted(
        ranked_movies,
        key=lambda movie: (
            _safe_int(movie.get("year"), 0) if prefer_latest else 0,
            _safe_float(movie.get("ranking_score", 0.0)),
            _safe_float(movie.get("similarity", 0.0)),
            _safe_float(movie.get("vote_average", 0.0)),
            _safe_float(movie.get("popularity", 0.0)),
        ),
        reverse=True,
    )
