"""Local chat page for the student support agent. Run: python app.py"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import agent
import memory
import tools

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
PORT = 8765
RUNTIME_FILES = ("memory.json", "traces.jsonl", "support_requests.json")


def reset_runtime():
    for name in RUNTIME_FILES:
        path = DATA / name
        if path.exists():
            path.unlink()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

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
        if path == "/api/memory":
            query = parse_qs(urlparse(self.path).query)
            student_id = (query.get("student_id") or [""])[0]
            self.send_json(200, memory.dump_student(student_id, DATA))
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_body()
        except json.JSONDecodeError:
            self.send_json(400, {"error": "bad_json"})
            return
        if path == "/api/chat":
            result = agent.run_turn(
                str(body.get("question") or ""),
                str(body.get("student_id") or ""),
                DATA,
            )
            self.send_json(200, result)
            return
        if path == "/api/reset":
            reset_runtime()
            self.send_json(200, {"ok": True})
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
    print(f"Student Support Agent: http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
        server.server_close()


if __name__ == "__main__":
    main()
