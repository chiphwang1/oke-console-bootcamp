"""Disposable training app, not a production web server.

/work performs a fixed amount of CPU work. Clients cannot increase its cost.
Health probes avoid that work, and only two work requests run at once per pod.
"""
import hashlib
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


WORK_SLOTS = threading.BoundedSemaphore(2)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        super().setup()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            self.reply(200, {"status": "ok"})
        elif path in ("/", "/work"):
            if path == "/work":
                if not WORK_SLOTS.acquire(blocking=False):
                    self.reply(429, {"error": "work slots busy"})
                    return
                try:
                    hashlib.pbkdf2_hmac("sha256", b"oke-lab", b"training-only", 200000)
                finally:
                    WORK_SLOTS.release()
            self.reply(200, {
                "message": os.environ.get("APP_MESSAGE", "Hello from the OKE bootcamp"),
                "pod": socket.gethostname(),
                "work": path == "/work",
            })
        else:
            self.reply(404, {"error": "not found"})

    def reply(self, status, payload):
        body = (json.dumps(payload) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A timed-out load client is normal during this exercise.

    def log_message(self, format, *args):
        if urlsplit(getattr(self, "path", "")).path != "/healthz":
            super().log_message(format, *args)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 5678), Handler).serve_forever()
