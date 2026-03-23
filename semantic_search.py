import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


MOVIES_PATH = Path(__file__).parent / "movies.json"
EMBEDDINGS_PATH = Path(__file__).parent / "movie_embeddings.npz"

model = SentenceTransformer("all-MiniLM-L6-v2")

SEMANTIC_QUERY_HINTS = {
    "ai": "artificial intelligence robot science fiction movie",
    "alien": "alien first contact science fiction movie",
    "anime": "anime animated movie",
    "animation": "animated movie",
    "crime": "crime movie",
    "dc": "dc universe dceu dcu superhero comic book movie",
    "dceu": "dc universe dceu superhero comic book movie",
    "dcu": "dc universe dcu superhero comic book movie",
    "horror": "horror movie",
    "marvel": "marvel mcu superhero comic book movie",
    "mcu": "marvel cinematic universe superhero movie",
    "robot": "robot android artificial intelligence science fiction movie",
    "space": "space exploration science fiction movie",
    "star wars": "star wars space opera jedi rebellion sci fi movie",
    "starwars": "star wars space opera jedi rebellion sci fi movie",
    "sport": "sports competition athlete inspirational movie",
    "sports": "sports competition athlete inspirational movie",
    "super hero": "superhero comic book action movie",
    "superhero": "superhero comic book action movie",
    "thriller": "thriller suspense movie",
    "war": "war movie",
    "運動": "sports competition athlete inspirational movie",
    "运动": "sports competition athlete inspirational movie",
    "體育": "sports competition athlete inspirational movie",
    "体育": "sports competition athlete inspirational movie",
    "動畫": "anime animated movie",
    "动画": "anime animated movie",
    "愛情": "romantic emotional movie",
    "爱情": "romantic emotional movie",
    "懸疑": "mystery thriller movie",
    "悬疑": "mystery thriller movie",
    "戰爭": "war movie",
    "战争": "war movie",
    "機器人": "robot android artificial intelligence science fiction movie",
    "机器人": "robot android artificial intelligence science fiction movie",
    "科幻": "science fiction movie",
    "犯罪": "crime movie",
    "空間": "space exploration science fiction movie",
    "太空": "space exploration science fiction movie",
    "宇宙": "space exploration science fiction movie",
    "韓國": "korean cinema korean language movie",
    "韩国": "korean cinema korean language movie",
    "日本": "japanese cinema japanese language movie",
    "恐怖": "horror movie",
    "惊悚": "thriller suspense movie",
    "驚悚": "thriller suspense movie",
}


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


def normalize_semantic_query(query):
    # Expand a few high-signal topic words before embedding so broad requests
    # retrieve better candidates.
    query_text = str(query).strip()
    query_lower = query_text.lower()

    expansions = []
    for token, expanded in SEMANTIC_QUERY_HINTS.items():
        if token in query_text or token in query_lower:
            expansions.append(expanded)

    if expansions:
        return f"{query_text}. {' '.join(expansions)}"

    return query_text


def cosine_search(query, top_k=5):
    # Embeddings are pre-normalized, so a dot product acts like cosine
    # similarity here.
    movies = load_movies()
    movie_embeddings = load_embeddings()
    normalized_query = normalize_semantic_query(query)

    query_embedding = model.encode(
        [normalized_query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]
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


def _list_to_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    return str(value)


def make_movie_text(movie):
    # This text layout defines what information the embedding model "sees"
    # when movie vectors are generated.
    title = movie.get("title", "")
    year = movie.get("year", "")
    genres = _list_to_text(movie.get("genres", movie.get("genre", [])))
    keywords = _list_to_text(movie.get("keywords", []))
    cast = _list_to_text(movie.get("cast", []))
    director = movie.get("director", "")
    language = _list_to_text(movie.get("language", ""))
    overview = movie.get("overview", "")
    runtime = movie.get("runtime", "")

    return (
        f"Title: {title}. "
        f"Year: {year}. "
        f"Genres: {genres}. "
        f"Keywords: {keywords}. "
        f"Director: {director}. "
        f"Cast: {cast}. "
        f"Language: {language}. "
        f"Runtime: {runtime} minutes. "
        f"Overview: {overview}"
    )


if __name__ == "__main__":
    query = "movies like Interstellar with space exploration and emotional sci-fi themes"
    results = cosine_search(query, top_k=5)

    for movie in results:
        print(
            f"{movie['title']} ({movie.get('year', 'N/A')}) "
            f"- score={movie['similarity']:.4f}"
        )
