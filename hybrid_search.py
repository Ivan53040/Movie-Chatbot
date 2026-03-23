from candidate_movies import (
    build_candidate_result,
    build_semantic_candidates,
    build_similar_candidates,
)
from movie_search import filter_movies
from ranking_layer import rank_movies


def hybrid_search(
    query,
    *,
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
    candidate_k=50,
    top_k=5,
    ranking_context=None,
):
    # Hybrid search means: semantic retrieval first, exact filters second,
    # ranking last.
    semantic_candidates = build_semantic_candidates(query, candidate_k=candidate_k)
    filtered_candidates = filter_movies(
        semantic_candidates,
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
    final_results = rank_movies(
        filtered_candidates,
        ranking_context=ranking_context,
    )[:top_k]
    return build_candidate_result(semantic_candidates, filtered_candidates, final_results)


def hybrid_recommend_similar_movies(
    movie_title,
    *,
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
    candidate_k=50,
    top_k=5,
    ranking_context=None,
):
    # Same pipeline as hybrid_search(), but the candidate pool is built from a
    # reference movie title instead of free text.
    semantic_candidates = build_similar_candidates(
        movie_title,
        candidate_k=candidate_k,
    )
    filtered_candidates = filter_movies(
        semantic_candidates,
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
    final_results = rank_movies(
        filtered_candidates,
        ranking_context=ranking_context,
    )[:top_k]
    return build_candidate_result(semantic_candidates, filtered_candidates, final_results)
