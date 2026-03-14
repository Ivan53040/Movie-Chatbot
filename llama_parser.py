import json
from ollama import chat
from pydantic import BaseModel
from movie_search import search_movies

# -----------------------
# Parser configuration
# -----------------------

VALID_MOODS = [
    "light",
    "funny",
    "emotional",
    "dark",
    "exciting",
    "uplifting",
    "romantic"
]


class MovieQuery(BaseModel):
    genre: str | None = None
    mood: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    year: int | None = None
    language: str | None = None

def _to_int_or_none(value):
    try:
        return int(value) if value is not None else None
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
                    "- If information is missing return null\n"
                    "- Return ONLY valid JSON"
                )
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        format=MovieQuery.model_json_schema()
    )

    data = json.loads(response.message.content)

    normalized_data = {
        "genre": _to_str_or_none(data.get("genre")),
        "mood": _to_str_or_none(data.get("mood")),
        "year_min": _to_int_or_none(data.get("year_min")),
        "year_max": _to_int_or_none(data.get("year_max")),
        "year": _to_int_or_none(data.get("year")),
        "language": _to_str_or_none(data.get("language")),
    }

    return normalized_data

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
        "light": "Comedy"
    }

    if not query.get("genre") and query.get("mood") in mood_genre_map:
        query["genre"] = mood_genre_map[query["mood"]]

    # 第一次：全部條件都用
    movies = search_movies(
        genre=query.get("genre"),
        mood=query.get("mood"),
        year_min=query.get("year_min"),
        year_max=query.get("year_max"),
        year=query.get("year"),
        language=query.get("language")
    )

    # 第二次：如果沒有結果，拿掉 mood 再試一次
    if not movies and query.get("mood"):
        movies = search_movies(
            genre=query.get("genre"),
            mood=None,
            year_min=query.get("year_min"),
            year_max=query.get("year_max"),
            year=query.get("year"),
            language=query.get("language")
        )

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
                print(f"{movie['title']} ({movie['year']})")