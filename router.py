from hybrid_search import hybrid_recommend_similar_movies, hybrid_search
from llama_parser import parse_user_query
from movie_search import search_movies
from ranking_layer import rank_movies
from semantic_search import cosine_search
from similar_search import recommend_similar_movies


def build_ranking_context(query):
    return {
        "genre": query.get("genre"),
        "mood": query.get("mood"),
        "year": query.get("year"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "language": query.get("language"),
        "similar_to": query.get("similar_to"),
        "semantic_query": query.get("semantic_query"),
        "prefer_recent": query.get("year") is None and query.get("year_min") is None,
    }


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
        similarity = float(movie.get("similarity", 0.0) or 0.0)
        ranking_score = float(movie.get("ranking_score", 0.0) or 0.0)
        print(
            f"  - {movie['title']} ({movie.get('year', 'N/A')}) "
            f"sim={similarity:.4f} rank={ranking_score:.4f}"
        )


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

    ranking_context = build_ranking_context(query)
    has_hard_filters = any(
        query.get(key) is not None
        for key in ("genre", "mood", "year_min", "year_max", "year", "language")
    )

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
                ranking_context=ranking_context,
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
                ranking_context=ranking_context,
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

    if movies:
        movies = rank_movies(movies, ranking_context=ranking_context)

    if not movies and not has_hard_filters:
        try:
            movies = cosine_search(user_input, top_k=5)
        except FileNotFoundError:
            pass

    return movies


def main():
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
                ranking_score = float(movie.get("ranking_score", 0.0) or 0.0)
                if similarity is None:
                    print(f"{movie['title']} ({movie['year']}) - rank={ranking_score:.4f}")
                else:
                    print(
                        f"{movie['title']} ({movie['year']}) "
                        f"- sim={similarity:.4f} rank={ranking_score:.4f}"
                    )


if __name__ == "__main__":
    main()
