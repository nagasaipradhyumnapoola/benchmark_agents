"""Loopback-only protocol fixture for browser tests; never a model capability score."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

calls = []
authenticated = "--authenticated" in sys.argv
model_id = "browser-key-model" if authenticated else "browser-wire-model"
fixture_key = "browser-session-fixture-key"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, payload):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def authorized(self):
        if authenticated and self.headers.get("Authorization") != "Bearer " + fixture_key:
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def do_GET(self):
        if self.path == "/stats":
            self.send({"requests": len(calls), "models": [body["model"] for body in calls]})
        else:
            if self.authorized():
                self.send({"data": [{"id": model_id}]})

    def do_POST(self):
        if not self.authorized():
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["model"] == model_id
        assert "expected" not in body
        calls.append(body)
        self.send({"choices": [{"message": {"content": "37"}}]})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(json.dumps({"base_url": f"http://127.0.0.1:{server.server_port}/v1"}), flush=True)
    server.serve_forever()
