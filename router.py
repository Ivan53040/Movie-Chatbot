from hybrid_search import hybrid_recommend_similar_movies, hybrid_search
from item_based_cf import score_movies_for_user
from llama_parser import parse_user_query
from llm_explanation import generate_recommendation_explanation
from movie_search import filter_movies, search_movies
from ranking_layer import rank_movies
from semantic_search import cosine_search
from similar_search import recommend_similar_movies
from top_k_movies import (
    DEFAULT_TOP_K,
    MAX_TOP_K,
    candidate_k_for_top_k,
    normalize_top_k,
    parse_more_command,
)


# Build one shared scoring context so the ranking layer does not need to know
# about the original parser output shape.
def build_ranking_context(query):
    return {
        "genre": query.get("genre"),
        "mood": query.get("mood"),
        "year": query.get("year"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "language": query.get("language"),
        "cast": query.get("cast"),
        "director": query.get("director"),
        "keywords": query.get("keywords"),
        "franchise": query.get("franchise"),
        "similar_to": query.get("similar_to"),
        "semantic_query": query.get("semantic_query"),
        "prefer_latest": query.get("prefer_latest", False),
        "prefer_recent": query.get("year") is None and query.get("year_min") is None,
    }


def _requests_latest(user_input):
    lowered = str(user_input or "").lower()
    return any(
        token in lowered
        for token in ("latest", "lastest", "lastes", "newest", "most recent", "recent")
    )


# These are the filters we treat as strict constraints during retrieval.
def _strict_filter_kwargs(query):
    keyword_value = str(query.get("keywords") or "").strip().lower()
    return {
        "genre": query.get("genre"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "year": query.get("year"),
        "language": query.get("language"),
        "keywords": query.get("keywords")
        if keyword_value in {
            "dc extended universe",
            "dc universe",
            "marvel cinematic universe",
            "star wars",
        }
        else None,
        "franchise": query.get("franchise"),
    }


# Print each stage of the hybrid pipeline so retrieval, filtering, and ranking
# can be debugged separately.
def print_hybrid_debug(hybrid_result, top_k):
    print("\nHybrid debug:")
    print(f"semantic candidates: {len(hybrid_result['semantic_candidates'])}")
    print(f"filtered candidates: {len(hybrid_result['filtered_candidates'])}")

    filtered_ids = {
        movie.get("id", movie.get("title"))
        for movie in hybrid_result["filtered_candidates"]
    }
    dropped_candidates = [
        movie
        for movie in hybrid_result["semantic_candidates"][:10]
        if movie.get("id", movie.get("title")) not in filtered_ids
    ]

    if dropped_candidates:
        print("dropped from top 10 semantic candidates:")
        for movie in dropped_candidates:
            score = float(movie.get("similarity", 0.0) or 0.0)
            print(f"  - {movie['title']} ({movie.get('year', 'N/A')}) score={score:.4f}")

    print(f"final top {top_k}:")
    for movie in hybrid_result["final_results"]:
        similarity = float(movie.get("similarity", 0.0) or 0.0)
        ranking_score = float(movie.get("ranking_score", 0.0) or 0.0)
        print(
            f"  - {movie['title']} ({movie.get('year', 'N/A')}) "
            f"sim={similarity:.4f} rank={ranking_score:.4f}"
        )


def _run_similar_hybrid(query, *, candidate_k, top_k, ranking_context):
    strict_filters = _strict_filter_kwargs(query)
    return hybrid_recommend_similar_movies(
        query["similar_to"],
        genre=strict_filters["genre"],
        year_min=strict_filters["year_min"],
        year_max=strict_filters["year_max"],
        year=strict_filters["year"],
        language=strict_filters["language"],
        keywords=strict_filters["keywords"],
        franchise=strict_filters["franchise"],
        candidate_k=candidate_k,
        top_k=top_k,
        ranking_context=ranking_context,
    )


def _run_semantic_hybrid(query, *, candidate_k, top_k, ranking_context):
    strict_filters = _strict_filter_kwargs(query)
    return hybrid_search(
        query["semantic_query"],
        genre=strict_filters["genre"],
        year_min=strict_filters["year_min"],
        year_max=strict_filters["year_max"],
        year=strict_filters["year"],
        language=strict_filters["language"],
        keywords=strict_filters["keywords"],
        franchise=strict_filters["franchise"],
        candidate_k=candidate_k,
        top_k=top_k,
        ranking_context=ranking_context,
    )


def _relaxed_query_variants(query):
    variants = []
    seen = set()

    def add_variant(**updates):
        variant = query.copy()
        variant.update(updates)
        key = tuple(
            (field, variant.get(field))
            for field in (
                "genre",
                "mood",
                "year_min",
                "year_max",
                "year",
                "language",
                "cast",
                "director",
                "keywords",
                "franchise",
            )
        )
        if key not in seen:
            seen.add(key)
            variants.append(variant)

    # Soft preferences are not used as hard filters anymore, so the only
    # fallback we keep here is dropping genre when hybrid retrieval is too narrow.
    if query.get("genre") is not None:
        add_variant(genre=None)
    return variants


# Cast/director checks are applied after retrieval so we can keep hybrid search
# broad and only enforce identity filters on the returned candidates.
def _enforce_identity_filters(movies, query):
    if not movies:
        return movies
    if query.get("cast") is None and query.get("director") is None:
        return movies
    return filter_movies(
        movies,
        cast=query.get("cast"),
        director=query.get("director"),
    )


def _exclude_seen_movies(movies, exclude_ids):
    if not movies or not exclude_ids:
        return movies
    excluded = {str(value) for value in exclude_ids}
    return [
        movie
        for movie in movies
        if str(movie.get("id", movie.get("title", ""))) not in excluded
    ]


def _apply_cf_personalization(movies, *, user_id, top_k):
    if not movies or not user_id:
        return movies[:top_k]

    try:
        cf_scores = score_movies_for_user(user_id, movies)
    except Exception:
        return movies[:top_k]

    if not cf_scores:
        return movies[:top_k]

    personalized = []
    for movie in movies:
        enriched_movie = movie.copy()
        movie_id = str(movie.get("id", movie.get("movie_id", "")))
        cf_bundle = cf_scores.get(movie_id)
        if cf_bundle:
            cf_score = float(cf_bundle.get("cf_score", 0.0) or 0.0)
            enriched_movie["cf_score"] = cf_score
            enriched_movie["cf_contributors"] = cf_bundle.get("contributors", [])
            enriched_movie["ranking_score"] = float(enriched_movie.get("ranking_score", 0.0) or 0.0) + (cf_score * 0.18)
        personalized.append(enriched_movie)

    return sorted(
        personalized,
        key=lambda movie: (
            float(movie.get("ranking_score", 0.0) or 0.0),
            float(movie.get("cf_score", 0.0) or 0.0),
            float(movie.get("similarity", 0.0) or 0.0),
            float(movie.get("vote_average", 0.0) or 0.0),
            float(movie.get("popularity", 0.0) or 0.0),
        ),
        reverse=True,
    )[:top_k]


# Retry a narrower hybrid route with relaxed filters before giving up entirely.
def _try_relaxed_hybrid(query, *, strategy, candidate_k, top_k, user_input, explain):
    for relaxed_query in _relaxed_query_variants(query):
        ranking_context = build_ranking_context(relaxed_query)
        hybrid_result = strategy(
            relaxed_query,
            candidate_k=candidate_k,
            top_k=top_k,
            ranking_context=ranking_context,
        )
        movies = hybrid_result["final_results"]
        if movies:
            return _with_explanations(
                movies,
                user_input=user_input,
                parsed_query=relaxed_query,
                ranking_context=ranking_context,
                explain=explain,
            )
    return []


def recommend_from_query(
    query,
    *,
    user_input="",
    top_k=DEFAULT_TOP_K,
    exclude_ids=None,
    user_id="",
    debug=True,
    explain=True,
):
    query = dict(query)
    if _requests_latest(user_input):
        query["prefer_latest"] = True

    top_k = normalize_top_k(top_k)
    candidate_k = candidate_k_for_top_k(top_k)
    exclude_ids = exclude_ids or []
    expanded_top_k = normalize_top_k(min(MAX_TOP_K, top_k + len(exclude_ids)))
    expanded_candidate_k = candidate_k_for_top_k(expanded_top_k)
    mood_genre_map = {
        "funny": "Comedy",
        "romantic": "Romance",
        "emotional": "Drama",
        "exciting": "Action",
        "uplifting": "Drama",
        "light": "Comedy",
    }

    # Mood-only requests get a light genre hint so pure filter search has a
    # better starting point.
    if not query.get("genre") and query.get("mood") in mood_genre_map:
        query["genre"] = mood_genre_map[query["mood"]]

    ranking_context = build_ranking_context(query)
    has_hard_filters = any(
        query.get(key) is not None
        for key in ("genre", "year_min", "year_max", "year", "language", "cast", "director", "franchise")
    )

    # Route 1: title-based similarity search, then strict filtering and ranking.
    if query.get("similar_to"):
        try:
            hybrid_result = _run_similar_hybrid(
                query,
                candidate_k=expanded_candidate_k,
                top_k=expanded_top_k,
                ranking_context=ranking_context,
            )
            movies = _enforce_identity_filters(hybrid_result["final_results"], query)
            movies = _exclude_seen_movies(movies, exclude_ids)
            movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
            if movies:
                if debug:
                    print_hybrid_debug(hybrid_result, top_k)
                return _with_explanations(
                    movies,
                    user_input=user_input,
                    parsed_query=query,
                    ranking_context=ranking_context,
                    explain=explain,
                )
            if has_hard_filters:
                relaxed_movies = _try_relaxed_hybrid(
                    query,
                    strategy=_run_similar_hybrid,
                    candidate_k=expanded_candidate_k,
                    top_k=expanded_top_k,
                    user_input=user_input,
                    explain=explain,
                )
                if relaxed_movies:
                    relaxed_movies = _enforce_identity_filters(relaxed_movies, query)
                    relaxed_movies = _exclude_seen_movies(relaxed_movies, exclude_ids)
                    relaxed_movies = _apply_cf_personalization(relaxed_movies, user_id=user_id, top_k=top_k)
                    if relaxed_movies:
                        return relaxed_movies
                if debug:
                    print_hybrid_debug(hybrid_result, top_k)
                return []
            movies = _enforce_identity_filters(
                recommend_similar_movies(query["similar_to"], top_k=expanded_top_k),
                query,
            )
            movies = _exclude_seen_movies(movies, exclude_ids)
            movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
            return movies[:top_k]
        except FileNotFoundError:
            pass

    # Route 2: semantic text search for theme/vibe/style requests.
    if query.get("semantic_query"):
        try:
            hybrid_result = _run_semantic_hybrid(
                query,
                candidate_k=expanded_candidate_k,
                top_k=expanded_top_k,
                ranking_context=ranking_context,
            )
            movies = _enforce_identity_filters(hybrid_result["final_results"], query)
            movies = _exclude_seen_movies(movies, exclude_ids)
            movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
            if movies:
                if debug:
                    print_hybrid_debug(hybrid_result, top_k)
                return _with_explanations(
                    movies,
                    user_input=user_input,
                    parsed_query=query,
                    ranking_context=ranking_context,
                    explain=explain,
                )
            if has_hard_filters:
                relaxed_movies = _try_relaxed_hybrid(
                    query,
                    strategy=_run_semantic_hybrid,
                    candidate_k=expanded_candidate_k,
                    top_k=expanded_top_k,
                    user_input=user_input,
                    explain=explain,
                )
                if relaxed_movies:
                    relaxed_movies = _enforce_identity_filters(relaxed_movies, query)
                    relaxed_movies = _exclude_seen_movies(relaxed_movies, exclude_ids)
                    relaxed_movies = _apply_cf_personalization(relaxed_movies, user_id=user_id, top_k=top_k)
                    if relaxed_movies:
                        return relaxed_movies
                if debug:
                    print_hybrid_debug(hybrid_result, top_k)
                return []
            movies = _enforce_identity_filters(
                cosine_search(query["semantic_query"], top_k=expanded_top_k),
                query,
            )
            movies = _exclude_seen_movies(movies, exclude_ids)
            movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
            return movies[:top_k]
        except FileNotFoundError:
            pass

    # Route 3: pure metadata filtering when the query is already structured.
    movies = search_movies(
        **_strict_filter_kwargs(query),
    )

    if movies:
        movies = rank_movies(movies, ranking_context=ranking_context)
        movies = _enforce_identity_filters(movies, query)
        movies = _exclude_seen_movies(movies, exclude_ids)
        movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
        movies = movies[:top_k]

    # Final fallback: if the query was too vague for filters, try embedding
    # search on the raw user text.
    if not movies and not has_hard_filters:
        try:
            movies = cosine_search(user_input, top_k=top_k)
            movies = _enforce_identity_filters(movies, query)
            movies = _exclude_seen_movies(movies, exclude_ids)
            movies = _apply_cf_personalization(movies, user_id=user_id, top_k=top_k)
            movies = movies[:top_k]
        except FileNotFoundError:
            pass

    return _with_explanations(
        movies,
        user_input=user_input,
        parsed_query=query,
        ranking_context=ranking_context,
        explain=explain,
    )


def recommend_movies(
    user_input: str,
    top_k=DEFAULT_TOP_K,
    *,
    exclude_ids=None,
    user_id="",
    query_override=None,
    debug=True,
    explain=True,
):
    # The frontend can pass a query override after a clarification step.
    query = (
        dict(query_override)
        if query_override is not None
        else parse_user_query(user_input)
    )

    if debug:
        print("\nParsed query:")
        print(query)

    return recommend_from_query(
        query,
        user_input=user_input,
        top_k=top_k,
        exclude_ids=exclude_ids,
        user_id=user_id,
        debug=debug,
        explain=explain,
    )


def _route_name_from_query(query: dict) -> str:
    if query.get("similar_to"):
        return "hybrid_similar"
    if query.get("semantic_query"):
        return "hybrid_semantic"
    return "filter_search"


def recommend_movies_with_metadata(
    user_input: str,
    top_k=DEFAULT_TOP_K,
    *,
    exclude_ids=None,
    user_id="",
    query_override=None,
    debug=True,
    explain=True,
):
    # Same recommendation flow as recommend_movies(), but with extra metadata
    # for the frontend to render route and parsed-query chips.
    query = (
        dict(query_override)
        if query_override is not None
        else parse_user_query(user_input)
    )

    if debug:
        print("\nParsed query:")
        print(query)

    results = recommend_from_query(
        query,
        user_input=user_input,
        top_k=top_k,
        exclude_ids=exclude_ids,
        user_id=user_id,
        debug=debug,
        explain=explain,
    )
    return {
        "parsed_query": query,
        "route": _route_name_from_query(query),
        "results": results,
    }


def _with_explanations(movies, *, user_input, parsed_query, ranking_context, explain):
    if not movies:
        return movies
    if not explain:
        return [movie.copy() for movie in movies]
    try:
        # Explanation failure should not block recommendations, so this stays
        # best-effort.
        explanation_bundle = generate_recommendation_explanation(
            movies,
            user_input=user_input,
            parsed_query=parsed_query,
            ranking_context=ranking_context,
        )
        enriched_movies = [movie.copy() for movie in movies]
        explanation_by_title = {
            str(item.get("title", "")).strip(): str(item.get("text", "")).strip()
            for item in explanation_bundle.get("movie_texts", [])
            if str(item.get("title", "")).strip() and str(item.get("text", "")).strip()
        }
        for index, movie in enumerate(enriched_movies):
            explanation_text = explanation_by_title.get(str(movie.get("title", "")).strip(), "")
            if explanation_text:
                movie["match_reason_text"] = explanation_text
                if index == 0:
                    movie["top_pick_text"] = explanation_text
        if enriched_movies and not enriched_movies[0].get("top_pick_text"):
            enriched_movies[0]["top_pick_text"] = explanation_bundle.get("top_pick_text", "")
        return enriched_movies
    except Exception:
        return movies


def main():
    last_query = None

    while True:
        user_input = input("\nWhat movie do you want to watch? (type 'exit' to quit)\n> ")

        if user_input.lower() == "exit":
            break

        # "more" reuses the previous natural-language query but increases how
        # many results we ask the pipeline to return.
        more_top_k = parse_more_command(user_input)
        if more_top_k is not None:
            if last_query is None:
                print("\nNo previous query found. Ask for a movie first.\n")
                continue
            query_text = last_query
            requested_top_k = more_top_k
        else:
            query_text = user_input
            requested_top_k = DEFAULT_TOP_K
            last_query = user_input

        results = recommend_movies(query_text, top_k=requested_top_k)

        print("\nRecommended Movies:\n")

        if not results:
            print("No movies found matching your request.\n")
        else:
            top_movie = results[0]
            similarity = top_movie.get("similarity")
            ranking_score = float(top_movie.get("ranking_score", 0.0) or 0.0)
            if similarity is None:
                print(f"{top_movie['title']} ({top_movie['year']}) - rank={ranking_score:.4f}")
            else:
                print(
                    f"{top_movie['title']} ({top_movie['year']}) "
                    f"- sim={similarity:.4f} rank={ranking_score:.4f}"
                )
            if top_movie.get("top_pick_text"):
                print(top_movie["top_pick_text"])

            if len(results) > 1:
                print("\nMore recommendations:")
                for movie in results[1:requested_top_k]:
                    print(f"- {movie['title']} ({movie['year']})")


if __name__ == "__main__":
    main()
