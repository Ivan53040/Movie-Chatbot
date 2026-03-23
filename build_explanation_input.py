def _listify(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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


def _reason_tags(movie, *, parsed_query, ranking_context):
    # Convert ranking/filter facts into short tags so the explanation prompt can
    # stay structured and constrained.
    tags = []

    genres = {
        str(item).strip().lower()
        for item in _listify(movie.get("genres"))
        if str(item).strip()
    }
    genre_query = str(parsed_query.get("genre") or "").strip().lower()
    if genre_query:
        normalized_genre_query = (
            "science fiction"
            if genre_query in {"sci-fi", "scifi", "science fiction"}
            else genre_query
        )
        if normalized_genre_query in genres:
            tags.append("matches requested genre")

    language_query = str(parsed_query.get("language") or "").strip().lower()
    movie_language = str(movie.get("language") or "").strip().lower()
    if language_query and movie_language == language_query:
        tags.append("matches requested language")

    movie_year = movie.get("year")
    if parsed_query.get("year") is not None and movie_year == parsed_query.get("year"):
        tags.append("matches requested year")
    elif parsed_query.get("year_min") is not None:
        try:
            if int(movie_year) >= int(parsed_query["year_min"]):
                tags.append("matches minimum year")
        except (TypeError, ValueError):
            pass
    elif parsed_query.get("year_max") is not None:
        try:
            if int(movie_year) <= int(parsed_query["year_max"]):
                tags.append("matches maximum year")
        except (TypeError, ValueError):
            pass

    if movie.get("similarity") is not None:
        tags.append("high semantic similarity")

    if float(movie.get("ranking_score", 0.0) or 0.0) > 0.5:
        tags.append("strong ranking score")

    cast_query = str(parsed_query.get("cast") or "").strip().lower()
    movie_cast = {
        str(name).strip().lower()
        for name in _listify(movie.get("cast"))
        if str(name).strip()
    }
    if cast_query and cast_query in movie_cast:
        tags.append(f"stars {parsed_query['cast']}")

    director_query = str(parsed_query.get("director") or "").strip().lower()
    movie_director = str(movie.get("director") or "").strip().lower()
    if director_query and director_query == movie_director:
        tags.append(f"directed by {parsed_query['director']}")

    keywords_query = str(parsed_query.get("keywords") or "").strip().lower()
    movie_keywords = {
        _normalize_keyword_value(keyword)
        for keyword in _listify(movie.get("keywords"))
        if str(keyword).strip()
    }
    normalized_keywords_query = _normalize_keyword_value(keywords_query)
    if normalized_keywords_query and normalized_keywords_query in movie_keywords:
        tags.append(f"matches keyword {parsed_query['keywords']}")

    franchise_value = str(ranking_context.get("franchise") or "").strip().lower()
    if franchise_value:
        from franchise_support import movie_matches_franchise

        if movie_matches_franchise(movie, franchise_value):
            tags.append(f"matches franchise {ranking_context['franchise']}")

    if ranking_context.get("similar_to"):
        tags.append(f"similar to {ranking_context['similar_to']}")
    elif ranking_context.get("semantic_query"):
        tags.append(f"fits {ranking_context['semantic_query']}")

    return tags


def _movie_payload(movie, *, parsed_query, ranking_context, rank_position):
    return {
        "title": movie.get("title"),
        "year": movie.get("year"),
        "genres": _listify(movie.get("genres")),
        "language": movie.get("language"),
        "overview": movie.get("overview", ""),
        "keywords": _listify(movie.get("keywords")),
        "director": movie.get("director"),
        "cast": _listify(movie.get("cast"))[:3],
        "similarity": movie.get("similarity"),
        "ranking_score": movie.get("ranking_score"),
        "rank_position": rank_position,
        "reason_tags": _reason_tags(
            movie,
            parsed_query=parsed_query,
            ranking_context=ranking_context,
        ),
    }


def build_explanation_input(movies, *, user_input, parsed_query, ranking_context):
    if not movies:
        return {"user_input": user_input, "movies": []}

    return {
        "user_input": user_input,
        "parsed_query": parsed_query,
        "movies": [
            _movie_payload(
                movie,
                parsed_query=parsed_query,
                ranking_context=ranking_context,
                rank_position=index + 1,
            )
            for index, movie in enumerate(movies[:5])
        ],
    }
