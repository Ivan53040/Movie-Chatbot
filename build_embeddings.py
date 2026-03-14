import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from semantic_search import make_movie_text


MOVIES_PATH = Path(__file__).parent / "movies.json"
EMBEDDINGS_PATH = Path(__file__).parent / "movie_embeddings.npz"

model = SentenceTransformer("all-MiniLM-L6-v2")


def load_movies():
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    movies = load_movies()
    texts = [make_movie_text(movie) for movie in movies]
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    np.savez_compressed(
        EMBEDDINGS_PATH,
        embeddings=embeddings,
        texts=np.array(texts, dtype=object),
    )

    print(f"Saved {len(movies)} movie embeddings to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    main()
