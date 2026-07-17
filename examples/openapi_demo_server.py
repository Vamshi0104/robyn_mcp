from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class DemoHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True})
            return
        if parsed.path.startswith("/customers/"):
            customer_id = parsed.path.rsplit("/", 1)[-1]
            expand = parse_qs(parsed.query).get("expand", [None])[0]
            self._json(200, {"customer_id": customer_id, "status": "active", "expand": expand})
            return
        self._json(404, {"error": "not_found"})

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8098), DemoHandler)
    print("openapi demo server listening on http://127.0.0.1:8098")
    server.serve_forever()
