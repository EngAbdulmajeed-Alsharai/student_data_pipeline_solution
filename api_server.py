from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_DATA_FILE = BASE_DIR / "data" / "raw" / "api_students.json"
HOST = "127.0.0.1"
PORT = 8000


class StudentAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/students":
            self.send_response(404)
            self.end_headers()
            return

        try:
            payload = json.loads(API_DATA_FILE.read_text(encoding="utf-8"))
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except Exception as exc:  # pragma: no cover
            message = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), StudentAPIHandler)
    print(f"Mock REST API running at http://{HOST}:{PORT}/students")
    print("Press Ctrl+C to stop the API server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
