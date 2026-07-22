import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from feedback_dataset import (
    log_feedback_label,
    log_feedback_reason,
    log_recommendation_impression,
)
from langchain_chains import contextualize_user_message
from langchain_memory import append_messages
from movie_query_parser import (
    CAST_NAME_ALIASES,
    DIRECTOR_NAME_ALIASES,
    parse_user_query,
)
from movie_search import find_person_candidates
from router import DEFAULT_TOP_K, recommend_movies_with_metadata


ROOT_DIR = Path(__file__).parent
LOG_DIR = ROOT_DIR / "logs"
FEEDBACK_LOG_PATH = LOG_DIR / "search_feedback_log.jsonl"


def handle_chat_request(
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
    language = detect_language((clarification or {}).get("original_message") or message)

    if not message and not clarification:
        raise ValueError("需要輸入訊息。" if language == "zh" else "Message is required.")

    query_override = None
    effective_message = message
    memory_user_text = message

    if clarification:
        effective_message, query_override, memory_user_text = build_query_override_from_clarification(
            clarification,
            user_id=user_id,
        )
    else:
        effective_message = contextualize_user_message(message, user_id=user_id)
        parsed_query = parse_user_query(effective_message)
        clarification_payload = maybe_build_person_clarification(
            message,
            parsed_query,
            language=language,
        )
        if clarification_payload:
            append_messages(
                user_id,
                HumanMessage(content=message),
                AIMessage(content=clarification_payload["prompt"]),
            )
            return {
                "user_input": message,
                "effective_input": effective_message,
                "ui_language": language,
                "needs_clarification": True,
                "clarification": clarification_payload,
            }
        query_override = parsed_query

    bundle = recommend_movies_with_metadata(
        effective_message,
        top_k=int(top_k or DEFAULT_TOP_K),
        exclude_ids=exclude_ids,
        user_id=user_id,
        query_override=query_override,
        debug=False,
        explain=True,
    )
    results = json_safe(bundle.get("results", []))
    recommendation_id = None
    if results:
        recommendation_id = log_recommendation_impression(
            user_id=user_id,
            query=message or effective_message,
            ui_language=language,
            route=bundle.get("route"),
            parsed_query=bundle.get("parsed_query", {}),
            results=results,
        )

    reply_text = build_reply_text(
        results,
        bundle.get("parsed_query", {}),
        language=language,
    )
    append_messages(
        user_id,
        HumanMessage(content=memory_user_text or effective_message),
        AIMessage(content=_build_memory_reply_text(reply_text, results)),
    )

    return {
        "user_input": message,
        "effective_input": effective_message,
        "ui_language": language,
        "parsed_query": json_safe(bundle.get("parsed_query", {})),
        "route": bundle.get("route"),
        "results": results,
        "recommendation_id": recommendation_id,
        "needs_clarification": False,
        "reply_text": reply_text,
    }


def handle_feedback_request(
    *,
    helpful=None,
    feedback_id="",
    recommendation_id="",
    reason="",
    query="",
    ui_language="",
    route="",
    parsed_query=None,
    results=None,
    user_id="anonymous",
):
    parsed_query = parsed_query or {}
    results = results or []
    language = detect_language(query or ui_language or "")
    feedback_id = str(feedback_id or "").strip()
    recommendation_id = str(recommendation_id or "").strip()
    user_id = str(user_id or "").strip() or "anonymous"
    reason = str(reason or "").strip()

    if helpful is None and not (feedback_id and reason):
        raise ValueError("需要回饋結果。" if language == "zh" else "Feedback value is required.")

    if feedback_id and reason:
        log_feedback_reason(
            recommendation_id=feedback_id,
            user_id=user_id,
            reason=reason,
            ui_language=ui_language or language,
        )
        append_feedback_log(
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "feedback_id": feedback_id,
                "feedback": "reason",
                "reason": reason,
                "user_id": user_id,
                "ui_language": ui_language or language,
            }
        )
        return {"ok": True, "logged": True, "feedback_id": feedback_id}

    feedback_id = feedback_id or recommendation_id or str(uuid4())
    log_feedback_label(
        recommendation_id=feedback_id,
        user_id=user_id,
        helpful=bool(helpful),
        query=query,
        ui_language=ui_language or language,
        route=route,
        parsed_query=parsed_query,
        results=results,
    )
    append_feedback_log(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "feedback_id": feedback_id,
            "user_id": user_id,
            "query": query,
            "ui_language": ui_language or language,
            "route": route,
            "parsed_query": json_safe(parsed_query),
            "results": json_safe(results),
            "feedback": "helpful" if helpful else "not_helpful",
        }
    )
    return {"ok": True, "logged": True, "feedback_id": feedback_id}


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def append_feedback_log(entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_reply_text(results, parsed_query, *, language):
    if not results:
        return _build_no_results_text(parsed_query, language=language)

    top_pick = results[0]
    top_pick_text = str(top_pick.get("top_pick_text", "")).strip()
    if top_pick_text:
        return top_pick_text

    fallback_title = "這部電影" if language == "zh" else "This movie"
    title = str(top_pick.get("title", fallback_title)).strip() or fallback_title
    year = top_pick.get("year")
    genres = top_pick.get("genres") or top_pick.get("genre") or []
    if not isinstance(genres, list):
        genres = [genres]
    genre_text = ", ".join(str(item) for item in genres[:2] if str(item).strip())
    if language == "zh":
        if year and genre_text:
            return f"{title} ({year}) 看起來是最符合你需求的選擇，尤其如果你想看{genre_text.lower()}類型。"
        if year:
            return f"{title} ({year}) 看起來是最符合你需求的選擇。"
        return f"{title} 看起來是最符合你需求的選擇。"
    if year and genre_text:
        return (
            f"{title} ({year}) looks like the strongest match here, "
            f"especially if you want {genre_text.lower()}."
        )
    if year:
        return f"{title} ({year}) looks like the strongest match for your request."
    return f"{title} looks like the strongest match for your request."


def detect_language(text):
    if re.search(r"[\u4e00-\u9fff]", str(text or "")):
        return "zh"
    return "en"


def maybe_build_person_clarification(message, parsed_query, *, language):
    if _has_explicit_person_role(message):
        return None

    fragment = str(parsed_query.get("cast") or parsed_query.get("director") or "").strip()
    if not fragment:
        return None

    candidates = find_person_candidates(fragment, limit=1)
    cast_candidates = candidates.get("cast", [])
    director_candidates = candidates.get("director", [])

    cast_alias_candidate = _best_alias_candidate(fragment, "cast")
    if cast_alias_candidate:
        cast_candidates = [{"name": cast_alias_candidate, "score": 999}] + [
            item for item in cast_candidates if item["name"] != cast_alias_candidate
        ]

    director_alias_candidate = _best_alias_candidate(fragment, "director")
    if director_alias_candidate:
        director_candidates = [{"name": director_alias_candidate, "score": 999}] + [
            item for item in director_candidates if item["name"] != director_alias_candidate
        ]

    if not cast_candidates or not director_candidates:
        return None

    top_cast = cast_candidates[0]["name"]
    top_director = director_candidates[0]["name"]
    normalized_fragment = _normalize_person_fragment(fragment)
    if not normalized_fragment:
        return None
    if _normalize_person_fragment(top_cast) == _normalize_person_fragment(top_director):
        return None
    if normalized_fragment in {
        _normalize_person_fragment(top_cast),
        _normalize_person_fragment(top_director),
    }:
        return None

    return {
        "kind": "person_role",
        "original_message": message,
        "fragment": fragment,
        "prompt": (
            f"你是指導演「{top_director}」還是演員「{top_cast}」？你也可以選擇「其他」。"
            if language == "zh"
            else f'Did you mean director "{top_director}" or cast "{top_cast}"? You can also choose Other.'
        ),
        "options": [
            {
                "id": "director",
                "role": "director",
                "name": top_director,
                "label": f"導演：{top_director}" if language == "zh" else f"Director: {top_director}",
            },
            {
                "id": "cast",
                "role": "cast",
                "name": top_cast,
                "label": f"演員：{top_cast}" if language == "zh" else f"Cast: {top_cast}",
            },
            {
                "id": "other",
                "role": "other",
                "name": "",
                "label": "其他" if language == "zh" else "Other",
            },
        ],
    }


def build_query_override_from_clarification(clarification, *, user_id=""):
    original_message = str((clarification or {}).get("original_message", "")).strip()
    role = str((clarification or {}).get("role", "")).strip().lower()
    name = str((clarification or {}).get("name", "")).strip()
    if not original_message or role not in {"cast", "director"} or not name:
        raise ValueError("Invalid clarification payload.")

    effective_message = contextualize_user_message(original_message, user_id=user_id)
    query = parse_user_query(effective_message)
    query["cast"] = name if role == "cast" else None
    query["director"] = name if role == "director" else None
    query["similar_to"] = None
    if query.get("semantic_query") == effective_message:
        query["semantic_query"] = None

    memory_user_text = f"{role} {name}"
    return effective_message, query, memory_user_text


def _build_memory_reply_text(reply_text, results):
    titles = [
        str(movie.get("title", "")).strip()
        for movie in (results or [])[:3]
        if str(movie.get("title", "")).strip()
    ]
    if not titles:
        return reply_text
    return f"{reply_text} Top results: {', '.join(titles)}."


def _normalize_person_fragment(value):
    text = str(value or "").strip().lower()
    return "".join(char for char in text if char.isalnum())


def _best_alias_candidate(fragment, role):
    normalized_fragment = _normalize_person_fragment(fragment)
    if not normalized_fragment:
        return None

    alias_map = DIRECTOR_NAME_ALIASES if role == "director" else CAST_NAME_ALIASES
    best_name = None
    best_score = -1
    for alias, canonical_name in alias_map.items():
        alias_tokens = [token for token in alias.lower().split() if token]
        canonical_tokens = [token for token in canonical_name.lower().split() if token]
        score = None
        if any(token == normalized_fragment for token in alias_tokens):
            score = 120
        elif any(token.startswith(normalized_fragment) for token in alias_tokens + canonical_tokens):
            score = 110
        elif normalized_fragment in _normalize_person_fragment(alias):
            score = 90
        if score is not None and score > best_score:
            best_name = canonical_name
            best_score = score
    return best_name


def _has_explicit_person_role(message):
    lowered = str(message or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "directed by",
            "from director",
            "director is",
            "starring",
            "cast by",
            "with ",
        )
    )


def _build_no_results_text(parsed_query, *, language):
    cast = str(parsed_query.get("cast") or "").strip()
    director = str(parsed_query.get("director") or "").strip()
    requested_language = str(parsed_query.get("language") or "").strip()
    year = parsed_query.get("year")
    year_min = parsed_query.get("year_min")
    year_max = parsed_query.get("year_max")
    is_zh = language == "zh"

    if cast:
        if year or year_min or year_max or requested_language:
            return (
                f"目前的年份或語言條件下找不到 {cast} 參演的電影。試著放寬條件，或換一位演員。"
                if is_zh
                else f"No movies found with {cast} under the current year or language filters. Try relaxing those filters or using another actor name."
            )
        return (
            f"找不到 {cast} 參演的電影。試著換一位演員。"
            if is_zh
            else f"No movies found with {cast}. Try another actor name."
        )

    if director:
        if year or year_min or year_max or requested_language:
            return (
                f"目前的年份或語言條件下找不到導演 {director} 的電影。試著放寬條件，或換一位導演。"
                if is_zh
                else f"No movies found for director {director} with the current year or language filters. Try relaxing those filters or trying another director."
            )
        return (
            f"找不到導演 {director} 的電影。試著換一位導演。"
            if is_zh
            else f"No movies found for director {director}. Try another director name."
        )

    if requested_language and (year or year_min or year_max):
        return (
            "目前的年份和語言條件下找不到結果，試著放寬其中一個條件。"
            if is_zh
            else "No movies found with the current year and language filters. Try relaxing one of them."
        )

    if requested_language:
        return (
            "找不到這個語言的電影，試著換一個語言或移除語言條件。"
            if is_zh
            else "No movies found in that language. Try another language or remove the language filter."
        )

    if year is not None:
        return (
            f"找不到 {year} 年的電影，試著放寬年份範圍。"
            if is_zh
            else f"No movies found from {year}. Try a wider year range."
        )

    if year_min is not None or year_max is not None:
        return (
            "這個年份範圍內找不到結果，試著放寬範圍。"
            if is_zh
            else "No movies found in that year range. Try widening the range."
        )

    return (
        "我找不到很符合這個需求的電影，試著放寬年份、語言或關鍵字條件。"
        if is_zh
        else "I could not find a strong match for that request. Try relaxing the year, language, or keywords."
    )
