from feedback_dataset import log_recommendation_impression

from chatbot_service import handle_feedback_request
from langchain_orchestrator import invoke_langchain_movie_chat
from router import DEFAULT_TOP_K


def handle_chat_request(
    *,
    message="",
    top_k=DEFAULT_TOP_K,
    exclude_ids=None,
    clarification=None,
    user_id="anonymous",
):
    response = invoke_langchain_movie_chat(
        message=message,
        top_k=top_k,
        exclude_ids=exclude_ids,
        clarification=clarification,
        user_id=user_id,
    )

    results = response.get("results", [])
    recommendation_id = None
    if results and not response.get("needs_clarification"):
        recommendation_id = log_recommendation_impression(
            user_id=user_id,
            query=response.get("user_input") or response.get("effective_input", ""),
            ui_language=response.get("ui_language", ""),
            route=response.get("route"),
            parsed_query=response.get("parsed_query", {}),
            results=results,
        )

    response["recommendation_id"] = recommendation_id
    return response
