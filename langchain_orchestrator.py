from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory

from chatbot_service import (
    _build_memory_reply_text,
    build_query_override_from_clarification,
    build_reply_text,
    detect_language,
    json_safe,
    maybe_build_person_clarification,
)
from hybrid_search import hybrid_recommend_similar_movies, hybrid_search
from item_based_cf import score_movies_for_user
from langchain_chains import (
    choose_search_route,
    contextualize_user_message_with_history,
)
from langchain_history_adapter import get_session_history
from llm_explanation import generate_recommendation_explanation
from movie_query_parser import parse_user_query
from movie_search import filter_movies, search_movies
from ranking_layer import rank_movies
from semantic_search import cosine_search
from similar_search import recommend_similar_movies
from top_k_movies import DEFAULT_TOP_K, MAX_TOP_K, candidate_k_for_top_k, normalize_top_k

VALID_ROUTE_NAMES = {"hybrid_similar", "hybrid_semantic", "filter_search"}
MOOD_GENRE_MAP = {
    "funny": "Comedy",
    "romantic": "Romance",
    "emotional": "Drama",
    "exciting": "Action",
    "uplifting": "Drama",
    "light": "Comedy",
}


def _rule_based_route_name_from_query(query):
    if query.get("similar_to"):
        return "hybrid_similar"
    if query.get("semantic_query"):
        return "hybrid_semantic"
    return "filter_search"


def _normalize_message(value):
    if hasattr(value, "content"):
        return str(value.content or "").strip()
    return str(value or "").strip()


def _requests_latest(user_input):
    lowered = str(user_input or "").lower()
    return any(
        token in lowered
        for token in ("latest", "lastest", "lastes", "newest", "most recent", "recent")
    )


def _strict_filter_kwargs(query):
    keyword_value = str(query.get("keywords") or "").strip().lower()
    return {
        "genre": query.get("genre"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "year": query.get("year"),
        "language": query.get("language"),
        "keywords": query.get("keywords")
        if keyword_value in {
            "dc extended universe",
            "dc universe",
            "marvel cinematic universe",
            "star wars",
        }
        else None,
        "franchise": query.get("franchise"),
    }


def _build_ranking_context(query):
    return {
        "genre": query.get("genre"),
        "mood": query.get("mood"),
        "year": query.get("year"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "language": query.get("language"),
        "cast": query.get("cast"),
        "director": query.get("director"),
        "keywords": query.get("keywords"),
        "franchise": query.get("franchise"),
        "similar_to": query.get("similar_to"),
        "semantic_query": query.get("semantic_query"),
        "prefer_latest": query.get("prefer_latest", False),
        "prefer_recent": query.get("year") is None and query.get("year_min") is None,
    }


def _has_hard_filters(query):
    return any(
        query.get(key) is not None
        for key in (
            "genre",
            "year_min",
            "year_max",
            "year",
            "language",
            "cast",
            "director",
            "franchise",
        )
    )


def _enforce_identity_filters(movies, query):
    if not movies:
        return movies
    if query.get("cast") is None and query.get("director") is None:
        return movies
    return filter_movies(
        movies,
        cast=query.get("cast"),
        director=query.get("director"),
    )


def _exclude_seen_movies(movies, exclude_ids):
    if not movies or not exclude_ids:
        return movies
    excluded = {str(value) for value in exclude_ids}
    return [
        movie
        for movie in movies
        if str(movie.get("id", movie.get("title", ""))) not in excluded
    ]


def _apply_cf_personalization(movies, *, user_id, top_k):
    if not movies or not user_id:
        return movies[:top_k]

    try:
        cf_scores = score_movies_for_user(user_id, movies)
    except Exception:
        return movies[:top_k]

    if not cf_scores:
        return movies[:top_k]

    personalized = []
    for movie in movies:
        enriched_movie = movie.copy()
        movie_id = str(movie.get("id", movie.get("movie_id", "")))
        cf_bundle = cf_scores.get(movie_id)
        if cf_bundle:
            cf_score = float(cf_bundle.get("cf_score", 0.0) or 0.0)
            enriched_movie["cf_score"] = cf_score
            enriched_movie["cf_contributors"] = cf_bundle.get("contributors", [])
            enriched_movie["ranking_score"] = float(
                enriched_movie.get("ranking_score", 0.0) or 0.0
            ) + (cf_score * 0.18)
        personalized.append(enriched_movie)

    return sorted(
        personalized,
        key=lambda movie: (
            float(movie.get("ranking_score", 0.0) or 0.0),
            float(movie.get("cf_score", 0.0) or 0.0),
            float(movie.get("similarity", 0.0) or 0.0),
            float(movie.get("vote_average", 0.0) or 0.0),
            float(movie.get("popularity", 0.0) or 0.0),
        ),
        reverse=True,
    )[:top_k]


def _prepare_query(parsed_query, *, effective_input, selected_route):
    query = dict(parsed_query or {})
    if _requests_latest(effective_input):
        query["prefer_latest"] = True

    if not query.get("genre") and query.get("mood") in MOOD_GENRE_MAP:
        query["genre"] = MOOD_GENRE_MAP[query["mood"]]

    if selected_route == "hybrid_semantic" and not query.get("semantic_query"):
        semantic_seed = str(effective_input or "").strip()
        if semantic_seed:
            query["semantic_query"] = semantic_seed

    return query


def _run_similar_retrieval(state):
    query = state["prepared_query"]
    top_k = state["top_k"]
    expanded_top_k = state["expanded_top_k"]
    candidate_k = state["expanded_candidate_k"]
    ranking_context = _build_ranking_context(query)

    try:
        hybrid_result = hybrid_recommend_similar_movies(
            query["similar_to"],
            candidate_k=candidate_k,
            top_k=expanded_top_k,
            ranking_context=ranking_context,
            **_strict_filter_kwargs(query),
        )
        movies = _enforce_identity_filters(hybrid_result["final_results"], query)
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )
        if movies:
            return {
                **state,
                "route": "hybrid_similar",
                "raw_results": movies,
            }

        movies = _enforce_identity_filters(
            recommend_similar_movies(query["similar_to"], top_k=expanded_top_k),
            query,
        )
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )
        return {
            **state,
            "route": "hybrid_similar",
            "raw_results": movies[:top_k],
        }
    except FileNotFoundError:
        return {
            **state,
            "route": "hybrid_similar",
            "raw_results": [],
        }


def _run_semantic_retrieval(state):
    query = state["prepared_query"]
    top_k = state["top_k"]
    expanded_top_k = state["expanded_top_k"]
    candidate_k = state["expanded_candidate_k"]
    ranking_context = _build_ranking_context(query)

    try:
        hybrid_result = hybrid_search(
            query["semantic_query"],
            candidate_k=candidate_k,
            top_k=expanded_top_k,
            ranking_context=ranking_context,
            **_strict_filter_kwargs(query),
        )
        movies = _enforce_identity_filters(hybrid_result["final_results"], query)
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )
        if movies:
            return {
                **state,
                "route": "hybrid_semantic",
                "raw_results": movies,
            }

        movies = _enforce_identity_filters(
            cosine_search(query["semantic_query"], top_k=expanded_top_k),
            query,
        )
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )
        return {
            **state,
            "route": "hybrid_semantic",
            "raw_results": movies[:top_k],
        }
    except FileNotFoundError:
        return {
            **state,
            "route": "hybrid_semantic",
            "raw_results": [],
        }


def _run_filter_retrieval(state):
    query = state["prepared_query"]
    top_k = state["top_k"]
    ranking_context = _build_ranking_context(query)

    movies = search_movies(**_strict_filter_kwargs(query))
    if movies:
        movies = rank_movies(movies, ranking_context=ranking_context)
        movies = _enforce_identity_filters(movies, query)
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )
        return {
            **state,
            "route": "filter_search",
            "raw_results": movies[:top_k],
        }

    if not _has_hard_filters(query):
        try:
            movies = cosine_search(state["effective_input"], top_k=top_k)
        except FileNotFoundError:
            movies = []
        movies = _enforce_identity_filters(movies, query)
        movies = _exclude_seen_movies(movies, state["exclude_ids"])
        movies = _apply_cf_personalization(
            movies,
            user_id=state["user_id"],
            top_k=top_k,
        )

    return {
        **state,
        "route": "filter_search",
        "raw_results": movies[:top_k],
    }


def _skip_retrieval(state):
    return {
        **state,
        "route": "clarification",
        "raw_results": [],
    }


def _attach_explanations(state):
    movies = state.get("raw_results", [])
    if not movies or state.get("needs_clarification"):
        return movies

    ranking_context = _build_ranking_context(state["prepared_query"])
    try:
        explanation_bundle = generate_recommendation_explanation(
            movies,
            user_input=state["effective_input"],
            parsed_query=state["prepared_query"],
            ranking_context=ranking_context,
        )
        enriched_movies = [movie.copy() for movie in movies]
        explanation_by_title = {
            str(item.get("title", "")).strip(): str(item.get("text", "")).strip()
            for item in explanation_bundle.get("movie_texts", [])
            if str(item.get("title", "")).strip()
            and str(item.get("text", "")).strip()
        }
        for index, movie in enumerate(enriched_movies):
            explanation_text = explanation_by_title.get(
                str(movie.get("title", "")).strip(),
                "",
            )
            if explanation_text:
                movie["match_reason_text"] = explanation_text
                if index == 0:
                    movie["top_pick_text"] = explanation_text
        if enriched_movies and not enriched_movies[0].get("top_pick_text"):
            enriched_movies[0]["top_pick_text"] = explanation_bundle.get(
                "top_pick_text",
                "",
            )
        return enriched_movies
    except Exception:
        return movies


def _build_reply_message(state):
    if state.get("needs_clarification"):
        prompt = state.get("clarification_payload", {}).get("prompt", "")
        return AIMessage(content=str(prompt or "").strip())
    return AIMessage(
        content=_build_memory_reply_text(state.get("reply_text", ""), state.get("results", []))
    )


def _build_pipeline_trace(state):
    trace = ["RunnableWithMessageHistory", "contextualize", "parse"]
    if state.get("needs_clarification"):
        trace.append("clarification")
        return trace
    trace.append("route_select")
    trace.append(state.get("selected_route", "filter_search"))
    trace.append("explain")
    return trace


def _build_response(state):
    if state.get("needs_clarification"):
        return {
            "user_input": state["original_message"],
            "effective_input": state["effective_input"],
            "ui_language": state["ui_language"],
            "needs_clarification": True,
            "clarification": state["clarification_payload"],
            "pipeline_trace": _build_pipeline_trace(state),
        }

    results = json_safe(state.get("results", []))
    return {
        "user_input": state["original_message"],
        "effective_input": state["effective_input"],
        "ui_language": state["ui_language"],
        "parsed_query": json_safe(state["prepared_query"]),
        "route": state["route"],
        "results": results,
        "needs_clarification": False,
        "reply_text": state["reply_text"],
        "pipeline_trace": _build_pipeline_trace(state),
    }


def _compute_effective_input(state):
    override = str(state.get("effective_input_override", "")).strip()
    if override:
        return override
    return contextualize_user_message_with_history(
        state["original_message"],
        history_messages=state.get("history", []),
    )


def _compute_parsed_query(state):
    query_override = state.get("query_override")
    if query_override is not None:
        return dict(query_override)
    return parse_user_query(state["effective_input"])


def _compute_selected_route(state):
    if state.get("needs_clarification"):
        return ""

    parsed_query = state["parsed_query"]
    fallback_route = _rule_based_route_name_from_query(parsed_query)
    try:
        route_bundle = choose_search_route(
            user_input=state["effective_input"],
            parsed_query=parsed_query,
        )
    except Exception:
        route_bundle = {}

    candidate_route = str(route_bundle.get("route", "")).strip().lower()
    if candidate_route not in VALID_ROUTE_NAMES:
        return fallback_route
    if candidate_route == "hybrid_similar" and not parsed_query.get("similar_to"):
        return fallback_route
    return candidate_route


def _normalize_request(state):
    message = _normalize_message(state.get("message"))
    top_k = normalize_top_k(state.get("top_k", DEFAULT_TOP_K))
    exclude_ids = state.get("exclude_ids") or []
    expanded_top_k = normalize_top_k(min(MAX_TOP_K, top_k + len(exclude_ids)))
    return {
        "message": message,
        "original_message": _normalize_message(state.get("original_message")) or message,
        "user_id": str(state.get("user_id") or "").strip() or "anonymous",
        "top_k": top_k,
        "exclude_ids": exclude_ids,
        "expanded_top_k": expanded_top_k,
        "expanded_candidate_k": candidate_k_for_top_k(expanded_top_k),
        "query_override": state.get("query_override"),
        "effective_input_override": state.get("effective_input_override"),
        "history": state.get("history", []),
        "clarification": state.get("clarification"),
    }


_retrieval_branch = RunnableBranch(
    (lambda state: state.get("needs_clarification", False), RunnableLambda(_skip_retrieval)),
    (lambda state: state.get("selected_route") == "hybrid_similar", RunnableLambda(_run_similar_retrieval)),
    (lambda state: state.get("selected_route") == "hybrid_semantic", RunnableLambda(_run_semantic_retrieval)),
    RunnableLambda(_run_filter_retrieval),
)

_base_chain = (
    RunnableLambda(_normalize_request)
    | RunnablePassthrough.assign(
        ui_language=RunnableLambda(lambda state: detect_language(state["original_message"])),
        effective_input=RunnableLambda(_compute_effective_input),
    )
    | RunnablePassthrough.assign(
        parsed_query=RunnableLambda(_compute_parsed_query),
    )
    | RunnablePassthrough.assign(
        clarification_payload=RunnableLambda(
            lambda state: maybe_build_person_clarification(
                state["original_message"],
                state["parsed_query"],
                language=state["ui_language"],
            )
        ),
        needs_clarification=RunnableLambda(lambda state: bool(state.get("clarification_payload"))),
    )
    | RunnablePassthrough.assign(
        selected_route=RunnableLambda(_compute_selected_route),
    )
    | RunnablePassthrough.assign(
        prepared_query=RunnableLambda(
            lambda state: _prepare_query(
                state["parsed_query"],
                effective_input=state["effective_input"],
                selected_route=state["selected_route"],
            )
        ),
    )
    | _retrieval_branch
    | RunnablePassthrough.assign(
        results=RunnableLambda(_attach_explanations),
    )
    | RunnablePassthrough.assign(
        reply_text=RunnableLambda(
            lambda state: ""
            if state.get("needs_clarification")
            else build_reply_text(
                state.get("results", []),
                state.get("prepared_query", {}),
                language=state["ui_language"],
            )
        ),
    )
    | RunnablePassthrough.assign(
        reply_message=RunnableLambda(_build_reply_message),
    )
    | RunnablePassthrough.assign(
        response=RunnableLambda(_build_response),
    )
)

movie_chat_chain = RunnableWithMessageHistory(
    _base_chain,
    get_session_history,
    input_messages_key="message",
    history_messages_key="history",
    output_messages_key="reply_message",
)


def invoke_langchain_movie_chat(
    *,
    message="",
    top_k=DEFAULT_TOP_K,
    exclude_ids=None,
    clarification=None,
    user_id="anonymous",
):
    message = str(message or "").strip()
    clarification = clarification or None
    exclude_ids = exclude_ids or []
    user_id = str(user_id or "").strip() or "anonymous"

    if clarification:
        effective_message, query_override, memory_user_text = build_query_override_from_clarification(
            clarification,
            user_id=user_id,
        )
        chain_input = {
            "message": memory_user_text,
            "original_message": str(clarification.get("original_message", "")).strip() or message,
            "effective_input_override": effective_message,
            "query_override": query_override,
            "top_k": top_k,
            "exclude_ids": exclude_ids,
            "user_id": user_id,
            "clarification": clarification,
        }
    else:
        chain_input = {
            "message": message,
            "top_k": top_k,
            "exclude_ids": exclude_ids,
            "user_id": user_id,
            "clarification": clarification,
        }

    result = movie_chat_chain.invoke(
        chain_input,
        config={"configurable": {"session_id": user_id}},
    )
    return result["response"]
