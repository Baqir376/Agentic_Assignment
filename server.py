"""
PrivacySwarm Universal API & Web Server
Serves both the modern React/Tailwind frontend and the LangGraph multi-agent API.
Built with Python standard library (http.server.ThreadingHTTPServer).
Runs 100% natively on Python 3.14 without Starlette/FastAPI version conflicts.
Includes strict origin validation, path traversal defense, and input guards.
"""
import sys
import json
import time
import pathlib
import mimetypes
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from pipeline.graph import run_pipeline
from audit.audit_log import get_summary_stats, get_recent_runs
from config import SYNTHETIC_DIR, GROQ_API_KEY, LOCAL_MODEL_NAME

FRONTEND_DIST = (pathlib.Path(__file__).parent / "frontend" / "dist").resolve()
ResilientThreadingHTTPServer = ThreadingHTTPServer

ALLOWED_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
}
MAX_BODY_BYTES = 256000
MAX_TEXT_CHARS = 30000
MAX_TASK_CHARS = 2000


class PrivacySwarmHandler(BaseHTTPRequestHandler):
    def _get_origin(self):
        return self.headers.get("Origin")

    def _is_origin_allowed(self):
        origin = self._get_origin()
        if not origin:
            return True
        return origin in ALLOWED_ORIGINS

    def _send_cors_headers(self):
        origin = self._get_origin()
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        if not self._is_origin_allowed():
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_static_file(self, raw_path: str):
        # Prevent path traversal
        decoded = urllib.parse.unquote(raw_path)
        if ".." in decoded or "/." in decoded or "\\." in decoded:
            self._send_json(403, {"error": "Access forbidden"})
            return

        clean_subpath = decoded.lstrip("/")
        if not clean_subpath:
            clean_subpath = "index.html"

        target_file = (FRONTEND_DIST / clean_subpath).resolve()
        try:
            target_file.relative_to(FRONTEND_DIST)
        except ValueError:
            self._send_json(403, {"error": "Access forbidden"})
            return

        if not target_file.exists() or not target_file.is_file():
            # If requesting specific asset (js, css, png, svg), return 404
            suffix = target_file.suffix.lower()
            if suffix in [".js", ".css", ".png", ".jpg", ".svg", ".json", ".map", ".ico"]:
                self._send_json(404, {"error": "Asset not found"})
                return

            # SPA Fallback for route paths: serve index.html
            index_path = FRONTEND_DIST / "index.html"
            if index_path.exists():
                target_file = index_path
            else:
                self._send_json(404, {"error": "Frontend build not found. Run npm run build."})
                return

        mime_type, _ = mimetypes.guess_type(str(target_file))
        if not mime_type:
            mime_type = "application/octet-stream"
        if target_file.suffix == ".js":
            mime_type = "application/javascript"

        try:
            content = target_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self._send_json(500, {"error": "Failed to read file"})

    def do_GET(self):
        if not self._is_origin_allowed():
            self._send_json(403, {"error": "Untrusted origin forbidden"})
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            import httpx
            ollama_ok = False
            installed = []
            try:
                r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
                if r.status_code == 200:
                    installed = [m.get("name", "") for m in r.json().get("models", [])]
                    ollama_ok = any(LOCAL_MODEL_NAME in m for m in installed) or (len(installed) > 0 and config_has_model(installed))
            except Exception:
                ollama_ok = False

            active_model = LOCAL_MODEL_NAME
            if installed and not any(LOCAL_MODEL_NAME in m for m in installed):
                active_model = installed[0]

            self._send_json(200, {
                "status": "online",
                "ollama_online": ollama_ok,
                "groq_configured": bool(GROQ_API_KEY and len(GROQ_API_KEY) > 10),
                "local_model": active_model,
                "installed_models": installed,
                "framework": "LangGraph + Neuro-Symbolic",
                "timestamp": time.time(),
            })

        elif path == "/api/audit":
            qs = urllib.parse.parse_qs(parsed.query)
            limit_raw = qs.get("limit", ["25"])[0]
            try:
                limit = int(limit_raw)
                if limit < 1 or limit > 100:
                    self._send_json(400, {"error": "Limit must be between 1 and 100"})
                    return
            except (ValueError, TypeError):
                self._send_json(400, {"error": "Invalid limit parameter"})
                return

            runs = get_recent_runs(limit)
            stats = get_summary_stats()
            self._send_json(200, {
                "stats": stats,
                "runs": runs,
            })

        elif path == "/api/samples":
            samples = []
            if SYNTHETIC_DIR.exists():
                for f in sorted(SYNTHETIC_DIR.glob("*.json")):
                    try:
                        samples.append(json.loads(f.read_text(encoding="utf-8")))
                    except Exception:
                        pass
            self._send_json(200, {"samples": samples})

        else:
            self._serve_static_file(path)

    def do_POST(self):
        if not self._is_origin_allowed():
            self._send_json(403, {"error": "Untrusted origin forbidden"})
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path != "/api/run":
            self._send_json(404, {"error": "Endpoint not found"})
            return

        length_hdr = self.headers.get("Content-Length")
        if not length_hdr:
            self._send_json(411, {"error": "Content-Length required"})
            return

        try:
            length = int(length_hdr)
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": f"Payload exceeds {MAX_BODY_BYTES} byte limit"})
            return

        raw_bytes = self.rfile.read(length)
        try:
            raw_body = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self._send_json(400, {"error": "Payload must be valid UTF-8"})
            return

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Payload must be valid JSON"})
            return

        if not isinstance(body, dict):
            self._send_json(400, {"error": "Payload must be a JSON object"})
            return

        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            self._send_json(400, {"error": "Field 'text' must be a non-empty string"})
            return

        task = body.get("task")
        if task is not None:
            if not isinstance(task, str) or not task.strip():
                self._send_json(400, {"error": "Field 'task' must be a non-empty string when provided"})
                return
        else:
            task = "Summarize this document and list all sensitive entities."

        if len(text) > MAX_TEXT_CHARS:
            self._send_json(413, {"error": f"Document length exceeds maximum {MAX_TEXT_CHARS} characters"})
            return

        if len(task) > MAX_TASK_CHARS:
            self._send_json(413, {"error": f"Instruction length exceeds maximum {MAX_TASK_CHARS} characters"})
            return

        try:
            t0 = time.time()
            final_state = run_pipeline(text, task)
            elapsed = round(time.time() - t0, 3)

            final_answer = final_state.get("final_answer", "")
            is_success = bool(final_answer and final_answer.strip())

            response_data = {
                "success": is_success,
                "latency_seconds": elapsed,
                "raw_text": final_state.get("raw_text", ""),
                "sanitized_text": final_state.get("sanitized_text", ""),
                "final_answer": final_answer,
                "pii_token_map": final_state.get("pii_token_map", {}),
                "reverse_map": final_state.get("reverse_map", {}),
                "pii_counts": final_state.get("pii_counts", {}),
                "routing_decision": final_state.get("routing_decision", "local"),
                "routing_reason": final_state.get("routing_reason", ""),
                "routing_stage": final_state.get("routing_stage", "symbolic"),
                "validation_passed": final_state.get("validation_passed", True),
                "validation_attempts": final_state.get("validation_attempts", 1),
                "hallucination_detected": final_state.get("hallucination_detected", False),
                "hallucination_reason": final_state.get("hallucination_reason"),
                "debate_rounds": final_state.get("debate_rounds", 0),
                "errors": final_state.get("errors", []),
            }
            self._send_json(200, response_data)
        except Exception:
            self._send_json(500, {"error": "Pipeline processing encountered an internal error", "success": False})

    def log_message(self, format, *args):
        pass


def config_has_model(installed_models):
    return any(LOCAL_MODEL_NAME in m for m in installed_models)


def start_server(port=8000):
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, PrivacySwarmHandler)
    print("═" * 60)
    print(f"  🔒 PrivacySwarm Unified Web & API Server Online")
    print(f"  🌐 Frontend Dashboard : http://localhost:{port}")
    print(f"  ⚡ LangGraph API      : http://localhost:{port}/api/run")
    print(f"  📋 Audit Ledger API   : http://localhost:{port}/api/audit")
    print("═" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    start_server(8000)
