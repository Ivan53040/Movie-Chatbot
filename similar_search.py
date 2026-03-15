import numpy as np

from semantic_search import cosine_search, load_embeddings, load_movies


def recommend_similar_movies(movie_title, top_k=5):
    movies = load_movies()
    movie_embeddings = load_embeddings()

    target_index = None
    for i, movie in enumerate(movies):
        if movie.get("title", "").strip().lower() == movie_title.strip().lower():
            target_index = i
            break

    if target_index is None:
        return cosine_search(f"movies like {movie_title}", top_k=top_k)

    target_embedding = movie_embeddings[target_index]
    scores = np.dot(movie_embeddings, target_embedding)
    scores[target_index] = -1

    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_indices:
        movie = movies[idx].copy()
        movie["similarity"] = float(scores[idx])
        results.append(movie)

    return results
