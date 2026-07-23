from langchain_chains import generate_movie_explanations


def generate_recommendation_explanation(
    movies,
    *,
    user_input,
    parsed_query,
    ranking_context,
):
    if not movies:
        return {"top_pick_text": "", "movie_texts": []}

    try:
        response = generate_movie_explanations(
            movies,
            user_input=user_input,
            parsed_query=parsed_query,
            ranking_context=ranking_context,
        )
        movie_texts = []
        for item in response.get("movie_texts", []):
            title = str(item.get("title", "")).strip()
            text = str(item.get("text", "")).strip()
            if title and text:
                movie_texts.append({"title": title, "text": text})
        if movie_texts:
            return {
                "top_pick_text": movie_texts[0]["text"],
                "movie_texts": movie_texts,
            }
    except Exception:
        pass

    movie_texts = [
        {
            "title": movie.get("title", ""),
            "text": _fallback_movie_text(movie),
        }
        for movie in movies[:5]
    ]
    return {
        "top_pick_text": movie_texts[0]["text"] if movie_texts else "",
        "movie_texts": movie_texts,
    }


def _fallback_movie_text(movie):
    title = str(movie.get("title", "This movie")).strip() or "This movie"
    overview = str(movie.get("overview", "")).strip()
    genres = movie.get("genres") or movie.get("genre") or []
    if not isinstance(genres, list):
        genres = [genres]
    genre_text = ", ".join(str(item).strip() for item in genres[:2] if str(item).strip())
    keywords = [str(item).strip() for item in movie.get("keywords", []) if str(item).strip()]

    reason_bits = []
    if genre_text:
        reason_bits.append(f"it leans into {genre_text.lower()}")
    if keywords:
        reason_bits.append(f"it carries themes like {keywords[0].lower()}")
    if not reason_bits:
        reason_bits.append("it stays close to the tone and themes of your request")

    if overview:
        return f"{title} {overview} It fits because {reason_bits[0]}."
    return f"{title} fits because {reason_bits[0]}."
