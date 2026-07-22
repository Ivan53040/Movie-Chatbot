import json
import mimetypes
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from chatbot_service import handle_chat_request, handle_feedback_request
from router import DEFAULT_TOP_K


ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"


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
            response_payload = handle_chat_request(
                message=payload.get("message", ""),
                top_k=int(payload.get("top_k", DEFAULT_TOP_K) or DEFAULT_TOP_K),
                exclude_ids=payload.get("exclude_ids", []),
                clarification=payload.get("clarification"),
                user_id=payload.get("user_id", "anonymous"),
            )
            self._send_json(response_payload)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_feedback(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body or b"{}")
            response_payload = handle_feedback_request(
                helpful=payload.get("helpful"),
                feedback_id=payload.get("feedback_id", ""),
                recommendation_id=payload.get("recommendation_id", ""),
                reason=payload.get("reason", ""),
                query=payload.get("query", ""),
                ui_language=payload.get("ui_language", ""),
                route=payload.get("route", ""),
                parsed_query=payload.get("parsed_query", {}),
                results=payload.get("results", []),
                user_id=payload.get("user_id", "anonymous"),
            )
            self._send_json(response_payload)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
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


def main():
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), FrontendHandler)
    print(f"Serving frontend at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
