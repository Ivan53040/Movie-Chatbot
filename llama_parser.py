import json

from ollama import chat
from pydantic import BaseModel

from movie_search import search_movies
from semantic_search import (
    cosine_search,
    hybrid_recommend_similar_movies,
    hybrid_search,
    recommend_similar_movies,
)


VALID_MOODS = [
    "light",
    "funny",
    "emotional",
    "dark",
    "exciting",
    "uplifting",
    "romantic",
]


class MovieQuery(BaseModel):
    genre: str | None = None
    mood: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    year: int | None = None
    language: str | None = None
    similar_to: str | None = None
    semantic_query: str | None = None


def _to_int_or_none(value):
    try:
        if value is None:
            return None
        parsed = int(value)
        if parsed <= 1800:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _to_str_or_none(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def parse_user_query(user_input: str) -> dict:
    response = chat(
        model="llama3.1:8b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a movie preference parser.\n"
                    "Extract movie search filters from the user's message.\n\n"
                    "Rules:\n"
                    "- genre should be a movie genre (Romance, Comedy, Sci-Fi, Drama, etc)\n"
                    "- mood should be a simple word (light, emotional, dark, funny, exciting)\n"
                    "- year_min means movies after that year\n"
                    "- year_max means movies before that year\n"
                    "- year means exactly that year\n"
                    "- language means movie language\n"
                    "- similar_to must only be used when the user explicitly mentions a specific movie title\n"
                    "- Never use similar_to for generic concepts, topics, themes, or categories\n"
                    "- Phrases like robot movies, space movies, sad movies, war movies, or action movies are not movie titles\n"
                    "- semantic_query is a free-text taste query about themes, vibe, or story style\n"
                    "- If the user says 'like Interstellar', set similar_to to 'Interstellar'\n"
                    "- If the user says they want robot-related movies, set semantic_query to 'robot movies'\n"
                    "- If the user asks in Chinese for machine, robot, AI, or space related movies, use semantic_query, not similar_to\n"
                    "- Example: 'I want movies like Interstellar' -> similar_to='Interstellar'\n"
                    "- Example: 'Recommend robot movies' -> semantic_query='robot movies'\n"
                    "- Example: '我想看機器人相關的電影' -> semantic_query='robot movies'\n"
                    "- Example: '推薦像星際效應的電影' -> similar_to='Interstellar'\n"
                    "- If the user describes a vibe or concept, copy that into semantic_query\n"
                    "- If information is missing return null\n"
                    "- Return ONLY valid JSON"
                ),
            },
            {
                "role": "user",
                "content": user_input,
            },
        ],
        format=MovieQuery.model_json_schema(),
    )

    data = json.loads(response.message.content)

    return {
        "genre": _to_str_or_none(data.get("genre")),
        "mood": _to_str_or_none(data.get("mood")),
        "year_min": _to_int_or_none(data.get("year_min")),
        "year_max": _to_int_or_none(data.get("year_max")),
        "year": _to_int_or_none(data.get("year")),
        "language": _to_str_or_none(data.get("language")),
        "similar_to": _to_str_or_none(data.get("similar_to")),
        "semantic_query": _to_str_or_none(data.get("semantic_query")),
    }


def recommend_movies(user_input: str):
    query = parse_user_query(user_input)

    print("\nParsed query:")
    print(query)

    mood_genre_map = {
        "funny": "Comedy",
        "romantic": "Romance",
        "emotional": "Drama",
        "exciting": "Action",
        "uplifting": "Drama",
        "light": "Comedy",
    }

    if not query.get("genre") and query.get("mood") in mood_genre_map:
        query["genre"] = mood_genre_map[query["mood"]]

    has_hard_filters = any(
        query.get(key) is not None
        for key in ("genre", "mood", "year_min", "year_max", "year", "language")
    )

    def print_hybrid_debug(hybrid_result):
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
        print("final top 5:")
        for movie in hybrid_result["final_results"]:
            score = float(movie.get("similarity", 0.0) or 0.0)
            print(f"  - {movie['title']} ({movie.get('year', 'N/A')}) score={score:.4f}")

    if query.get("similar_to"):
        try:
            hybrid_result = hybrid_recommend_similar_movies(
                query["similar_to"],
                genre=query.get("genre"),
                mood=query.get("mood"),
                year_min=query.get("year_min"),
                year_max=query.get("year_max"),
                year=query.get("year"),
                language=query.get("language"),
                candidate_k=50,
                top_k=5,
            )
            movies = hybrid_result["final_results"]
            if movies:
                print_hybrid_debug(hybrid_result)
                return movies
            if has_hard_filters:
                print_hybrid_debug(hybrid_result)
                return []
            return recommend_similar_movies(query["similar_to"], top_k=5)
        except FileNotFoundError:
            pass

    if query.get("semantic_query"):
        try:
            hybrid_result = hybrid_search(
                query["semantic_query"],
                genre=query.get("genre"),
                mood=query.get("mood"),
                year_min=query.get("year_min"),
                year_max=query.get("year_max"),
                year=query.get("year"),
                language=query.get("language"),
                candidate_k=50,
                top_k=5,
            )
            movies = hybrid_result["final_results"]
            if movies:
                print_hybrid_debug(hybrid_result)
                return movies
            if has_hard_filters:
                print_hybrid_debug(hybrid_result)
                return []
            return cosine_search(query["semantic_query"], top_k=5)
        except FileNotFoundError:
            pass

    movies = search_movies(
        genre=query.get("genre"),
        mood=query.get("mood"),
        year_min=query.get("year_min"),
        year_max=query.get("year_max"),
        year=query.get("year"),
        language=query.get("language"),
    )

    if not movies and query.get("mood"):
        movies = search_movies(
            genre=query.get("genre"),
            mood=None,
            year_min=query.get("year_min"),
            year_max=query.get("year_max"),
            year=query.get("year"),
            language=query.get("language"),
        )

    if not movies and not has_hard_filters:
        try:
            movies = cosine_search(user_input, top_k=5)
        except FileNotFoundError:
            pass

    return movies


if __name__ == "__main__":
    while True:
        user_input = input("\nWhat movie do you want to watch? (type 'exit' to quit)\n> ")

        if user_input.lower() == "exit":
            break

        results = recommend_movies(user_input)

        print("\nRecommended Movies:\n")

        if not results:
            print("No movies found matching your request.\n")
        else:
            for movie in results[:5]:
                similarity = movie.get("similarity")
                if similarity is None:
                    print(f"{movie['title']} ({movie['year']})")
                else:
                    print(f"{movie['title']} ({movie['year']}) - score={similarity:.4f}")
