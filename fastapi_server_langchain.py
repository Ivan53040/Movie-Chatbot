from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from langchain_chatbot_service import handle_chat_request, handle_feedback_request
from router import DEFAULT_TOP_K


ROOT_DIR = Path(__file__).parent
FRONTEND_BUILD_DIR = ROOT_DIR / "frontend-react" / "dist"

app = FastAPI(title="ProjectLLM MovieBot API (LangChain Pipeline)")
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
    try:
        return handle_chat_request(
            message=request.message,
            top_k=int(request.top_k or DEFAULT_TOP_K),
            exclude_ids=request.exclude_ids or [],
            clarification=request.clarification.model_dump() if request.clarification else None,
            user_id=request.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/feedback")
def feedback(request: FeedbackRequest):
    try:
        return handle_feedback_request(
            helpful=request.helpful,
            feedback_id=request.feedback_id,
            recommendation_id=request.recommendation_id,
            reason=request.reason,
            query=request.query,
            ui_language=request.ui_language,
            route=request.route,
            parsed_query=request.parsed_query,
            results=request.results,
            user_id=request.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
