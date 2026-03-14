import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

MOVIES_PATH = Path(__file__).parent / "movies.json"
EMBEDDINGS_PATH = Path(__file__).parent / "movie_embeddings.npz"

model = SentenceTransformer("all-MiniLM-L6-v2")


def load_movies():
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_embeddings():
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {EMBEDDINGS_PATH}. "
            "Run build_embeddings.py first."
        )
    data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    return data["embeddings"]


def cosine_search(query, top_k=5):
    movies = load_movies()
    movie_embeddings = load_embeddings()

    query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]

    scores = np.dot(movie_embeddings, query_embedding)

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        movie = movies[idx].copy()
        movie["similarity"] = float(scores[idx])
        results.append(movie)

    return results

def find_movie_by_title(title, movies):
    title_lower = title.strip().lower()
    for movie in movies:
        if movie.get("title", "").strip().lower() == title_lower:
            return movie
    return None

def make_movie_text(movie):
    title = movie.get("title", "")
    genres = ", ".join(movie.get("genre", [])) if isinstance(movie.get("genre"), list) else movie.get("genre", "")
    moods = ", ".join(movie.get("mood", [])) if isinstance(movie.get("mood"), list) else movie.get("mood", "")
    language_data = movie.get("language", "")
    language = ", ".join(language_data) if isinstance(language_data, list) else language_data
    overview = movie.get("overview", "")

    return (
        f"Title: {title}. "
        f"Genres: {genres}. "
        f"Mood: {moods}. "
        f"Language: {language}. "
        f"Overview: {overview}"
    )

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

    # 排除自己
    scores[target_index] = -1

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        movie = movies[idx].copy()
        movie["similarity"] = float(scores[idx])
        results.append(movie)

    return results


if __name__ == "__main__":
    query = "movies like Interstellar with space exploration and emotional sci-fi themes"
    results = cosine_search(query, top_k=5)

    for movie in results:
        print(f"{movie['title']} ({movie.get('year', 'N/A')}) - score={movie['similarity']:.4f}")
