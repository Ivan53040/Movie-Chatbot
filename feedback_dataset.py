import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


ROOT_DIR = Path(__file__).parent
LOG_DIR = ROOT_DIR / "logs"
RECOMMENDATION_EVENTS_PATH = LOG_DIR / "recommendation_events.jsonl"
USER_MOVIE_RATINGS_PATH = LOG_DIR / "user_movie_ratings.jsonl"


def _timestamp():
    return datetime.utcnow().isoformat() + "Z"


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _append_jsonl(path, entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(entry), ensure_ascii=False) + "\n")


def _movie_identity(movie):
    return {
        "movie_id": movie.get("id"),
        "movie_title": movie.get("title"),
        "movie_year": movie.get("year"),
    }


def log_recommendation_impression(
    *,
    user_id,
    query,
    ui_language,
    route,
    parsed_query,
    results,
):
    recommendation_id = str(uuid4())
    timestamp = _timestamp()
    sanitized_results = _json_safe(results)
    sanitized_query = _json_safe(parsed_query)

    _append_jsonl(
        RECOMMENDATION_EVENTS_PATH,
        {
            "timestamp": timestamp,
            "event_type": "recommendation_impression",
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "query": str(query or "").strip(),
            "ui_language": ui_language,
            "route": route,
            "parsed_query": sanitized_query,
            "results": sanitized_results,
        },
    )

    for index, movie in enumerate(sanitized_results, start=1):
        _append_jsonl(
            USER_MOVIE_RATINGS_PATH,
            {
                "timestamp": timestamp,
                "event_type": "impression",
                "recommendation_id": recommendation_id,
                "user_id": user_id,
                "query": str(query or "").strip(),
                "ui_language": ui_language,
                "route": route,
                "position": index,
                "feedback_label": None,
                "implicit_rating": None,
                **_movie_identity(movie),
            },
        )

    return recommendation_id


def log_feedback_label(
    *,
    recommendation_id,
    user_id,
    helpful,
    query,
    ui_language,
    route,
    parsed_query,
    results,
):
    timestamp = _timestamp()
    sanitized_results = _json_safe(results)
    sanitized_query = _json_safe(parsed_query)
    feedback_label = "helpful" if helpful else "not_helpful"
    implicit_rating = 1.0 if helpful else 0.0

    _append_jsonl(
        RECOMMENDATION_EVENTS_PATH,
        {
            "timestamp": timestamp,
            "event_type": "recommendation_feedback",
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "query": str(query or "").strip(),
            "ui_language": ui_language,
            "route": route,
            "parsed_query": sanitized_query,
            "feedback_label": feedback_label,
            "results": sanitized_results,
        },
    )

    for index, movie in enumerate(sanitized_results, start=1):
        _append_jsonl(
            USER_MOVIE_RATINGS_PATH,
            {
                "timestamp": timestamp,
                "event_type": "feedback",
                "recommendation_id": recommendation_id,
                "user_id": user_id,
                "query": str(query or "").strip(),
                "ui_language": ui_language,
                "route": route,
                "position": index,
                "feedback_label": feedback_label,
                "implicit_rating": implicit_rating,
                **_movie_identity(movie),
            },
        )


def log_feedback_reason(*, recommendation_id, user_id, reason, ui_language):
    _append_jsonl(
        RECOMMENDATION_EVENTS_PATH,
        {
            "timestamp": _timestamp(),
            "event_type": "feedback_reason",
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "ui_language": ui_language,
            "reason": str(reason or "").strip(),
        },
    )
