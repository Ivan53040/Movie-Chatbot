import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from feedback_dataset import (
    log_feedback_label,
    log_feedback_reason,
    log_recommendation_impression,
)
from frontend_server import (
    _append_feedback_log,
    _build_query_override_from_clarification,
    _build_reply_text,
    _detect_language,
    _json_safe,
    _maybe_build_person_clarification,
)
from llama_parser import parse_user_query
from router import DEFAULT_TOP_K, recommend_movies_with_metadata


ROOT_DIR = Path(__file__).parent
FRONTEND_BUILD_DIR = ROOT_DIR / "frontend-react" / "dist"

app = FastAPI(title="ProjectLLM MovieBot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClarificationPayload(BaseModel):
    original_message: str = ""
    role: str = ""
    name: str = ""


class ChatRequest(BaseModel):
    message: str = ""
    top_k: int = DEFAULT_TOP_K
    exclude_ids: list[Any] = Field(default_factory=list)
    clarification: ClarificationPayload | None = None
    user_id: str = "anonymous"


class FeedbackRequest(BaseModel):
    helpful: bool | None = None
    feedback_id: str = ""
    recommendation_id: str = ""
    reason: str = ""
    query: str = ""
    ui_language: str = ""
    route: str = ""
    parsed_query: dict[str, Any] = Field(default_factory=dict)
    results: list[dict[str, Any]] = Field(default_factory=list)
    user_id: str = "anonymous"


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = str(request.message or "").strip()
    clarification = request.clarification.model_dump() if request.clarification else None
    user_id = str(request.user_id or "").strip() or "anonymous"
    language = _detect_language((clarification or {}).get("original_message") or message)

    if not message and not clarification:
        raise HTTPException(
            status_code=400,
            detail="需要輸入訊息。" if language == "zh" else "Message is required.",
        )

    query_override = None
    effective_message = message

    if clarification:
        effective_message, query_override = _build_query_override_from_clarification(clarification)
    else:
        parsed_query = parse_user_query(message)
        clarification_payload = _maybe_build_person_clarification(
            message,
            parsed_query,
            language=language,
        )
        if clarification_payload:
            return {
                "user_input": message,
                "ui_language": language,
                "needs_clarification": True,
                "clarification": clarification_payload,
            }

    bundle = recommend_movies_with_metadata(
        effective_message,
        top_k=int(request.top_k or DEFAULT_TOP_K),
        exclude_ids=request.exclude_ids or [],
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

    return {
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


@app.post("/api/feedback")
def feedback(request: FeedbackRequest):
    language = _detect_language(request.query or request.ui_language or "")
    helpful = request.helpful
    feedback_id = str(request.feedback_id or "").strip()
    recommendation_id = str(request.recommendation_id or "").strip()
    user_id = str(request.user_id or "").strip() or "anonymous"
    reason = str(request.reason or "").strip()

    if helpful is None and not (feedback_id and reason):
        raise HTTPException(
            status_code=400,
            detail="需要回饋結果。" if language == "zh" else "Feedback value is required.",
        )

    if feedback_id and reason:
        log_feedback_reason(
            recommendation_id=feedback_id,
            user_id=user_id,
            reason=reason,
            ui_language=request.ui_language or language,
        )
        _append_feedback_log(
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "feedback_id": feedback_id,
                "feedback": "reason",
                "reason": reason,
                "user_id": user_id,
                "ui_language": request.ui_language or language,
            }
        )
        return {"ok": True, "logged": True, "feedback_id": feedback_id}

    feedback_id = feedback_id or recommendation_id or str(uuid4())
    log_feedback_label(
        recommendation_id=feedback_id,
        user_id=user_id,
        helpful=bool(helpful),
        query=request.query,
        ui_language=request.ui_language or language,
        route=request.route,
        parsed_query=request.parsed_query,
        results=request.results,
    )
    _append_feedback_log(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "feedback_id": feedback_id,
            "user_id": user_id,
            "query": request.query,
            "ui_language": request.ui_language or language,
            "route": request.route,
            "parsed_query": _json_safe(request.parsed_query),
            "results": _json_safe(request.results),
            "feedback": "helpful" if helpful else "not_helpful",
        }
    )
    return {"ok": True, "logged": True, "feedback_id": feedback_id}


if FRONTEND_BUILD_DIR.exists():
    assets_dir = FRONTEND_BUILD_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def serve_index():
    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "message": "Frontend build not found. Run `cd frontend-react && npm run build` first."
    }


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    candidate = FRONTEND_BUILD_DIR / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)

    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend build not found.")
