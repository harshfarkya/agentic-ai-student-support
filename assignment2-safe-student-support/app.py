"""Local chat page with login, approval, and audit. Run: python app.py"""

import json
import secrets
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import agent
import approvals
import audit
import auth
import memory
import tools

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
PORT = 8766
SESSIONS = {}
RUNTIME_FILES = (
    "memory.json",
    "traces.jsonl",
    "support_requests.json",
    "audit.json",
    "approvals.json",
)


def reset_runtime():
    for name in RUNTIME_FILES:
        path = DATA / name
        if path.exists():
            path.unlink()
    shutil.copy(DATA / "students_seed.json", DATA / "students.json")
    SESSIONS.clear()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def actor(self):
        return SESSIONS.get(self.headers.get("X-Session", ""))

    def _send(self, code, body, content_type):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json")

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/api/students":
            self.send_json(200, tools.list_public(DATA))
            return
        actor_id = self.actor()
        if not actor_id:
            self.send_json(401, {"error": "login_required"})
            return
        if path == "/api/me":
            self.send_json(200, auth.profile(actor_id, DATA))
            return
        if path == "/api/memory":
            self.send_json(200, memory.dump_student(actor_id, DATA))
            return
        if path == "/api/audit":
            self.send_json(200, audit.all_rows(DATA))
            return
        if path == "/api/approvals":
            self.send_json(200, approvals.all_rows(DATA))
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_body()
        except json.JSONDecodeError:
            self.send_json(400, {"error": "bad_json"})
            return
        if path == "/api/login":
            user = auth.authenticate(body.get("student_id"), body.get("pin"), DATA)
            if not user:
                self.send_json(401, {"error": "Invalid student id or PIN."})
                return
            token = secrets.token_hex(16)
            SESSIONS[token] = user["student_id"]
            user["token"] = token
            self.send_json(200, user)
            return
        if path == "/api/reset":
            reset_runtime()
            self.send_json(200, {"ok": True})
            return
        actor_id = self.actor()
        if not actor_id:
            self.send_json(401, {"error": "login_required"})
            return
        if path == "/api/chat":
            result = agent.run_turn(str(body.get("question") or ""), actor_id, DATA)
            self.send_json(200, result)
            return
        if path == "/api/decision":
            result = approvals.decide(
                str(body.get("approval_id") or ""),
                str(body.get("decision") or ""),
                "staff.admin",
                DATA,
            )
            code = 200 if result.get("ok") else 400
            self.send_json(code, result)
            return
        self.send_json(404, {"error": "not_found"})


def main():
    class Server(ThreadingHTTPServer):
        allow_reuse_address = True

    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Port {PORT} is already in use. Close the other app.py window and try again.")
        raise SystemExit(1)
    print(f"Safe Student Support Agent: http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
        server.server_close()


if __name__ == "__main__":
    main()
