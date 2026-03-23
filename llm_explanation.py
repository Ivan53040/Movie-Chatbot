import json

from api_parser_client import chat_json
from build_explanation_input import build_explanation_input


def generate_recommendation_explanation(
    movies,
    *,
    user_input,
    parsed_query,
    ranking_context,
):
    if not movies:
        return {"top_pick_text": "", "movie_texts": []}

    explanation_input = build_explanation_input(
        movies,
        user_input=user_input,
        parsed_query=parsed_query,
        ranking_context=ranking_context,
    )

    system_prompt = (
        "You explain a movie recommendation to the user.\n"
        "Write one short paragraph for each movie in the input.\n"
        "Respond in the same language as the user's input.\n"
        "Use only facts provided in the input.\n"
        "Keep the explanation to 2 or 3 sentences.\n"
        "Sentence 1 should summarize what the movie is about using the overview.\n"
        "Sentence 2 should explain why the movie fits the user's request.\n"
        "If there is a useful third sentence, keep it short.\n"
        "Write like a recommendation engine, not like customer support.\n"
        "Do not start with phrases like 'Based on your input', 'I recommend', or 'This movie is a great choice'.\n"
        "Directly mention the movie title and the strongest reasons it fits.\n"
        "Prefer reasoning such as tone, themes, emotional feel, genre fit, similarity, and year constraints.\n"
        "If relevant, compare it briefly to the user's reference movie or stated preference.\n"
        "Keep the style concise, natural, and specific.\n"
        "Every movie must include a why-it-fits reason, not just plot summary.\n"
        "Return JSON only in this form: "
        '{"movie_texts":[{"title":"...","text":"..."}]}'
    )
    try:
        response = chat_json(
            system_prompt=system_prompt,
            user_input=json.dumps(explanation_input, ensure_ascii=False),
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
