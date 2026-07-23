import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from api_parser_client import invoke_json_messages
from build_explanation_input import build_explanation_input
from langchain_memory import get_history_messages


_CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You rewrite movie recommendation follow-up requests into standalone requests.\n"
            "Use the chat history only when the latest message depends on earlier context.\n"
            "Keep the user's language.\n"
            "Preserve exact movie titles, actor names, director names, years, and constraints.\n"
            "If the latest message is already standalone, return it unchanged.\n"
            "Return JSON only in this form: {{\"standalone_query\":\"...\"}}",
        ),
        MessagesPlaceholder("history"),
        ("human", "{user_input}"),
    ]
)

_PARSER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a movie preference parser.\n"
            "Extract movie search filters from the user's message.\n\n"
            "Return a JSON object with these keys only:\n"
            "genre, mood, year_min, year_max, year, language, cast, director, keywords, similar_to, semantic_query\n\n"
            "Rules:\n"
            "- genre should be a movie genre (Romance, Comedy, Sci-Fi, Drama, etc)\n"
            "- mood should be a simple word (light, emotional, dark, funny, exciting)\n"
            "- Only set mood when the user explicitly states a mood or feeling\n"
            "- Do not infer mood from genre, plot, or semantic_query\n"
            "- year_min means movies after that year\n"
            "- year_max means movies before that year\n"
            "- year means exactly that year\n"
            "- If the user asks for movies after a year, set year_min to one year after that year\n"
            "- If the user asks for movies before or earlier than a year, set year_max to one year before that year\n"
            "- If the user asks for movies since a year, set year_min to that year\n"
            "- If the user asks for movies from a year and it clearly means a lower bound, set year_min to that year\n"
            "- If the user asks for movies in a specific year, set year to that exact year\n"
            "- If the user gives one exact year, prefer year over year_min or year_max\n"
            "- Never set both year and year_min/year_max unless the user clearly gives a range\n"
            "- If the user does not mention a year, year/year_min/year_max must be null, never 0\n"
            "- language means movie language\n"
            "- language can also be a short code like en, ja, ko, tl, ta, sv, or cs\n"
            "- cast is a person or actor name the user wants in the movie\n"
            "- director is a director name the user wants in the movie\n"
            "- If the user asks for movies starring an actor, put the name in cast\n"
            "- If the user asks for movies with an actor in it, put the name in cast\n"
            "- If the user asks for a movie cast by someone, put the name in cast\n"
            "- If the user asks for movies directed by someone, put the name in director\n"
            "- If the user asks for movies from a director or says director is someone, put the name in director\n"
            "- If the user clearly wants cast or director, do not put that person into semantic_query\n"
            "- keywords is a short topic like robot, superhero, anime, time travel, or space survival\n"
            "- If the user asks for movies about a short concrete topic, put that topic in keywords\n"
            "- similar_to must only be used when the user explicitly mentions a specific movie title\n"
            "- Never use similar_to for generic concepts, topics, themes, or categories\n"
            "- Phrases like robot movies, space movies, sad movies, war movies, or action movies are not movie titles\n"
            "- semantic_query is a free-text taste query about themes, vibe, or story style\n"
            "- If the user describes a broad vibe, story idea, or concept, copy that into semantic_query\n"
            "- If the user asks for a broad topic like superhero or anime movies, use keywords or semantic_query, not similar_to\n"
            "- If the user says 'like Interstellar', set similar_to to 'Interstellar'\n"
            "- If the user says 'something like' a specific movie title, set similar_to to that movie title\n"
            "- If the user says they want robot-related movies, set semantic_query to 'robot movies'\n"
            "- Do not use similar_to for superhero, anime, robot, sports, space, alien, romance, thriller, or other generic categories unless they are clearly movie titles\n"
            "- For superhero or super hero requests, prefer keywords='superhero'\n"
            "- For anime, animated, or animation movie requests, prefer genre='Animation' and keywords='anime'\n"
            "- For robot, AI, artificial intelligence, space, alien, sports, war, crime, horror, thriller, or similar topic requests, semantic_query is often appropriate\n"
            "- If the user asks in Chinese for machine, robot, AI, sports, anime, space, war, thriller, romance, horror, Korean movies, or Japanese movies, map that to keywords, genre, language, or semantic_query instead of similar_to unless a real movie title is named\n"
            "- Example: 'I want a movie cast by Keanu Reeves' -> cast='Keanu Reeves'\n"
            "- Example: 'I want a movie directed by Christopher Nolan' -> director='Christopher Nolan'\n"
            "- Example: 'I want a superhero movie' -> keywords='superhero'\n"
            "- Example: 'I want a tl Thriller movie' -> language='tl', genre='Thriller'\n"
            "- Example: 'I want a movie about alien life-form after 1930' -> keywords='alien life-form', year_min=1931\n"
            "- Example: 'movies after 2010' -> year_min=2011\n"
            "- Example: 'movies before 2000' -> year_max=1999\n"
            "- Example: 'movies from 1999' -> year=1999\n"
            "- Example: 'movies since 2015' -> year_min=2015\n"
            "- Example: 'movies with Leonardo DiCaprio in it' -> cast='Leonardo DiCaprio'\n"
            "- Example: 'movies from director Nolan' -> director='Christopher Nolan'\n"
            "- Example: 'something like Interstellar but after 2010' -> similar_to='Interstellar', year_min=2011\n"
            "- Example: 'I want movies like Interstellar' -> similar_to='Interstellar'\n"
            "- Example: 'Recommend robot movies' -> semantic_query='robot movies'\n"
            "- If information is missing return null\n"
            "- Return ONLY valid JSON",
        ),
        ("human", "{user_input}"),
    ]
)

_EXPLANATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You explain movie recommendations to the user.\n"
            "Write one short paragraph for each movie in the input.\n"
            "Respond in the same language as the user's input.\n"
            "Use only facts provided in the input.\n"
            "Keep every explanation to 2 or 3 sentences.\n"
            "Sentence 1 should summarize what the movie is about using the overview.\n"
            "Sentence 2 should explain why the movie fits the user's request.\n"
            "If there is a useful third sentence, keep it short.\n"
            "Write like a recommendation engine, not like customer support.\n"
            "Do not start with phrases like 'Based on your input', 'I recommend', or 'This movie is a great choice'.\n"
            "Directly mention the movie title and the strongest reasons it fits.\n"
            "Prefer reasoning such as tone, themes, emotional feel, genre fit, similarity, and year constraints.\n"
            "If relevant, compare it briefly to the user's reference movie or stated preference.\n"
            "Every movie must include a why-it-fits reason, not just plot summary.\n"
            "Return JSON only in this form: "
            "{{\"movie_texts\":[{{\"title\":\"...\",\"text\":\"...\"}}]}}",
        ),
        ("human", "{payload_json}"),
    ]
)

_ROUTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You choose the best search route for a movie recommendation request.\n"
            "Available routes:\n"
            "- hybrid_similar: use when the request is anchored on a specific reference movie title\n"
            "- hybrid_semantic: use when the request is about vibe, themes, plot ideas, topics, or broad fuzzy matching\n"
            "- filter_search: use when the request is mostly structured filters like genre, year, language, cast, director, or franchise\n\n"
            "Use both the raw user message and the parsed query.\n"
            "Prefer hybrid_similar when parsed_query.similar_to is present.\n"
            "Prefer hybrid_semantic when parsed_query.semantic_query is present.\n"
            "Prefer filter_search when the request is mostly metadata constraints and does not need fuzzy retrieval.\n"
            "Return JSON only in this form: "
            "{{\"route\":\"hybrid_similar|hybrid_semantic|filter_search\",\"reason\":\"...\"}}",
        ),
        ("human", "User message:\n{user_input}\n\nParsed query:\n{parsed_query_json}"),
    ]
)


def contextualize_user_message(user_input, *, user_id=""):
    history = get_history_messages(user_id)
    return contextualize_user_message_with_history(user_input, history_messages=history)


def contextualize_user_message_with_history(user_input, *, history_messages=None):
    history = history_messages or []
    if not history:
        return str(user_input or "").strip()

    prompt_value = _CONTEXTUALIZE_PROMPT.invoke(
        {
            "history": history,
            "user_input": str(user_input or "").strip(),
        }
    )
    response = invoke_json_messages(messages=prompt_value.to_messages(), temperature=0)
    standalone_query = str(response.get("standalone_query", "")).strip()
    return standalone_query or str(user_input or "").strip()


def invoke_movie_parser(user_input):
    prompt_value = _PARSER_PROMPT.invoke({"user_input": str(user_input or "").strip()})
    return invoke_json_messages(messages=prompt_value.to_messages(), temperature=0)


def choose_search_route(*, user_input, parsed_query):
    prompt_value = _ROUTE_PROMPT.invoke(
        {
            "user_input": str(user_input or "").strip(),
            "parsed_query_json": json.dumps(parsed_query or {}, ensure_ascii=False),
        }
    )
    return invoke_json_messages(messages=prompt_value.to_messages(), temperature=0)


def generate_movie_explanations(
    movies,
    *,
    user_input,
    parsed_query,
    ranking_context,
):
    explanation_input = build_explanation_input(
        movies,
        user_input=user_input,
        parsed_query=parsed_query,
        ranking_context=ranking_context,
    )
    prompt_value = _EXPLANATION_PROMPT.invoke(
        {"payload_json": json.dumps(explanation_input, ensure_ascii=False)}
    )
    response = invoke_json_messages(messages=prompt_value.to_messages(), temperature=0)
    return response
