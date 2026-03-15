from candidate_movies import build_candidate_result, build_semantic_candidates, build_similar_candidates
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
    candidate_k=50,
    top_k=5,
    ranking_context=None,
):
    semantic_candidates = build_semantic_candidates(query, candidate_k=candidate_k)
    filtered_candidates = filter_movies(
        semantic_candidates,
        genre=genre,
        mood=mood,
        year_min=year_min,
        year_max=year_max,
        year=year,
        language=language,
    )
    final_results = rank_movies(filtered_candidates, ranking_context=ranking_context)[:top_k]
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
    candidate_k=50,
    top_k=5,
    ranking_context=None,
):
    semantic_candidates = build_similar_candidates(movie_title, candidate_k=candidate_k)
    filtered_candidates = filter_movies(
        semantic_candidates,
        genre=genre,
        mood=mood,
        year_min=year_min,
        year_max=year_max,
        year=year,
        language=language,
    )
    final_results = rank_movies(filtered_candidates, ranking_context=ranking_context)[:top_k]
    return build_candidate_result(semantic_candidates, filtered_candidates, final_results)
