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


def make_movie_text(movie):
    title = movie.get("title", "")
    genres = ", ".join(movie.get("genre", [])) if isinstance(movie.get("genre"), list) else movie.get("genre", "")
    moods = ", ".join(movie.get("mood", [])) if isinstance(movie.get("mood"), list) else movie.get("mood", "")
    language = movie.get("language", "")
    overview = movie.get("overview", "")

    return (
        f"Title: {title}. "
        f"Genres: {genres}. "
        f"Mood: {moods}. "
        f"Language: {language}. "
        f"Overview: {overview}"
    )


def main():
    movies = load_movies()
    texts = [make_movie_text(movie) for movie in movies]

    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    np.savez_compressed(
        EMBEDDINGS_PATH,
        embeddings=embeddings,
        texts=np.array(texts, dtype=object)
    )

    print(f"Saved {len(movies)} movie embeddings to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    main()