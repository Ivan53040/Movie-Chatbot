import json
from ollama import chat
from pydantic import BaseModel
from movie_search import search_movies


class MovieQuery(BaseModel):
    genre: str | None = None
    mood: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    year: int | None = None
    language: str | None = None


def parse_user_query(user_input: str) -> dict:
    """
    Use Llama to extract movie search filters from natural language.
    Returns a dictionary matching MovieQuery schema.
    """

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

    return json.loads(response.message.content)


def recommend_movies(user_input: str):
    """
    Full pipeline:
    user input → Llama parse → search_movies → return results
    """

    query = parse_user_query(user_input)

    print("\nParsed query:")
    print(query)

    movies = search_movies(
        genre=query.get("genre"),
        mood=query.get("mood"),
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