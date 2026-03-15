from semantic_search import cosine_search
from similar_search import recommend_similar_movies


def build_semantic_candidates(query, candidate_k=50):
    return cosine_search(query, top_k=candidate_k)


def build_similar_candidates(movie_title, candidate_k=50):
    return recommend_similar_movies(movie_title, top_k=candidate_k)


def build_candidate_result(semantic_candidates, filtered_candidates, final_results):
    return {
        "semantic_candidates": semantic_candidates,
        "filtered_candidates": filtered_candidates,
        "final_results": final_results,
    }
