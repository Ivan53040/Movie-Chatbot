import json
import mimetypes
import re
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from feedback_dataset import (
    log_feedback_label,
    log_feedback_reason,
    log_recommendation_impression,
)
from llama_parser import (
    CAST_NAME_ALIASES,
    DIRECTOR_NAME_ALIASES,
    parse_user_query,
)
from movie_search import find_person_candidates
from router import DEFAULT_TOP_K, recommend_movies_with_metadata


ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
LOG_DIR = ROOT_DIR / "logs"
FEEDBACK_LOG_PATH = LOG_DIR / "search_feedback_log.jsonl"


def _detect_language(text):
    if re.search(r"[\u4e00-\u9fff]", str(text or "")):
        return "zh"
    return "en"


class FrontendHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._serve_file(FRONTEND_DIR / "index.html")
            return

        if parsed.path in {"/styles.css", "/app.js"}:
            self._serve_file(FRONTEND_DIR / parsed.path.lstrip("/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/feedback":
            self._handle_feedback()
            return

        if parsed.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Route not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body or b"{}")
            message = str(payload.get("message", "")).strip()
            top_k = int(payload.get("top_k", DEFAULT_TOP_K) or DEFAULT_TOP_K)
            exclude_ids = payload.get("exclude_ids", [])
            clarification = payload.get("clarification")
            user_id = str(payload.get("user_id", "")).strip() or "anonymous"
            language = _detect_language(
                (clarification or {}).get("original_message") or message
            )

            if not message and not clarification:
                error_text = "需要輸入訊息。" if language == "zh" else "Message is required."
                self._send_json({"error": error_text}, status=HTTPStatus.BAD_REQUEST)
                return

            query_override = None
            effective_message = message
            if clarification:
                # A clarification response bypasses parsing and rewrites the
                # query explicitly with the chosen role.
                effective_message, query_override = _build_query_override_from_clarification(clarification)
            else:
                parsed_query = parse_user_query(message)
                clarification_payload = _maybe_build_person_clarification(
                    message,
                    parsed_query,
                    language=language,
                )
                if clarification_payload:
                    self._send_json(
                        {
                            "user_input": message,
                            "ui_language": language,
                            "needs_clarification": True,
                            "clarification": clarification_payload,
                        }
                    )
                    return

            bundle = recommend_movies_with_metadata(
                effective_message,
                top_k=top_k,
                exclude_ids=exclude_ids,
                user_id=user_id,
                query_override=query_override,
                debug=False,
                explain=True,
            )
            results = _json_safe(bundle.get("results", []))
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

            self._send_json(
                {
                    "user_input": message,
                    "ui_language": language,
                    "parsed_query": _json_safe(bundle.get("parsed_query", {})),
                    "route": bundle.get("route"),
                    "results": results,
                    "recommendation_id": recommendation_id,
                    "needs_clarification": False,
                    "reply_text": _build_reply_text(
                        results,
                        bundle.get("parsed_query", {}),
                        language=language,
                    ),
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_feedback(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body or b"{}")
            language = _detect_language(payload.get("query") or payload.get("ui_language") or "")
            helpful = payload.get("helpful")
            feedback_id = str(payload.get("feedback_id", "")).strip()
            recommendation_id = str(payload.get("recommendation_id", "")).strip()
            user_id = str(payload.get("user_id", "")).strip() or "anonymous"
            reason = str(payload.get("reason", "")).strip()

            if helpful is None and not (feedback_id and reason):
                error_text = "需要回饋結果。" if language == "zh" else "Feedback value is required."
                self._send_json({"error": error_text}, status=HTTPStatus.BAD_REQUEST)
                return

            if feedback_id and reason:
                log_feedback_reason(
                    recommendation_id=feedback_id,
                    user_id=user_id,
                    reason=reason,
                    ui_language=payload.get("ui_language") or language,
                )
                _append_feedback_log(
                    {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "feedback_id": feedback_id,
                        "feedback": "reason",
                        "reason": reason,
                        "user_id": user_id,
                        "ui_language": payload.get("ui_language") or language,
                    }
                )
                self._send_json({"ok": True, "logged": True, "feedback_id": feedback_id})
                return

            feedback_id = feedback_id or recommendation_id or str(uuid4())
            log_feedback_label(
                recommendation_id=feedback_id,
                user_id=user_id,
                helpful=bool(helpful),
                query=str(payload.get("query", "")).strip(),
                ui_language=payload.get("ui_language") or language,
                route=payload.get("route"),
                parsed_query=payload.get("parsed_query", {}),
                results=payload.get("results", []),
            )
            _append_feedback_log(
                {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "feedback_id": feedback_id,
                    "user_id": user_id,
                    "query": str(payload.get("query", "")).strip(),
                    "ui_language": payload.get("ui_language") or language,
                    "route": payload.get("route"),
                    "parsed_query": _json_safe(payload.get("parsed_query", {})),
                    "results": _json_safe(payload.get("results", [])),
                    "feedback": "helpful" if helpful else "not_helpful",
                }
            )
            self._send_json({"ok": True, "logged": True, "feedback_id": feedback_id})
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format, *args):
        return

    def _serve_file(self, file_path: Path):
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload, *, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _json_safe(value):
    # Convert NumPy scalars and other non-JSON-native values before serializing.
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


def _append_feedback_log(entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _build_reply_text(results, parsed_query, *, language):
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


def _maybe_build_person_clarification(message, parsed_query, *, language):
    # Only interrupt the flow when the parser found a short ambiguous fragment
    # that could plausibly map to both cast and director.
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

    # Only interrupt when the query looks genuinely partial or ambiguous.
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
            (
                f'你是指導演「{top_director}」還是演員「{top_cast}」？你也可以選擇「其他」。'
                if language == "zh"
                else (
                    f'Did you mean director "{top_director}" or cast "{top_cast}"? '
                    "You can also choose Other."
                )
            )
        ),
        "options": [
            {
                "id": "director",
                "role": "director",
                "name": top_director,
                "label": (
                    f"導演：{top_director}"
                    if language == "zh"
                    else f"Director: {top_director}"
                ),
            },
            {
                "id": "cast",
                "role": "cast",
                "name": top_cast,
                "label": (
                    f"演員：{top_cast}"
                    if language == "zh"
                    else f"Cast: {top_cast}"
                ),
            },
            {
                "id": "other",
                "role": "other",
                "name": "",
                "label": "其他" if language == "zh" else "Other",
            },
        ],
    }


def _build_query_override_from_clarification(clarification):
    # Re-parse the original message, then pin the chosen role so downstream
    # routing behaves like the user had said it explicitly.
    original_message = str((clarification or {}).get("original_message", "")).strip()
    role = str((clarification or {}).get("role", "")).strip().lower()
    name = str((clarification or {}).get("name", "")).strip()
    if not original_message or role not in {"cast", "director"} or not name:
        raise ValueError("Invalid clarification payload.")

    query = parse_user_query(original_message)
    query["cast"] = name if role == "cast" else None
    query["director"] = name if role == "director" else None
    query["similar_to"] = None
    if query.get("semantic_query") == original_message:
        query["semantic_query"] = None
    return original_message, query


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
                else (
                    f"No movies found with {cast} under the current year or language filters. "
                    "Try relaxing those filters or using another actor name."
                )
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
                else (
                    f"No movies found for director {director} with the current year or language filters. "
                    "Try relaxing those filters or trying another director."
                )
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


def main():
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), FrontendHandler)
    print(f"Serving frontend at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
