"""Exercise the training HTTP app on loopback; no OCI or cluster access."""
import importlib.util
import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("bootcamp_app", ROOT / "charts/oke-mesh-app/files/server.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class BootcampApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_message_and_pod_identity(self):
        with patch.dict(app.os.environ, {"APP_MESSAGE": "My bootcamp"}):
            status, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"message": "My bootcamp", "pod": app.socket.gethostname(), "work": False})

    def test_fixed_cpu_work_ignores_client_cost_parameters(self):
        with patch.object(app.hashlib, "pbkdf2_hmac", return_value=b"done") as cpu_work:
            status, body = self.request("/work?iterations=999999999")
        self.assertEqual(status, 200)
        self.assertTrue(body["work"])
        self.assertEqual(cpu_work.call_args.args[-1], 200000)

    def test_cpu_work_completes(self):
        status, body = self.request("/work")
        self.assertEqual(status, 200)
        self.assertTrue(body["work"])

    def test_busy_work_does_not_block_health(self):
        app.WORK_SLOTS.acquire()
        app.WORK_SLOTS.acquire()
        try:
            self.assertEqual(self.request("/work")[0], 429)
            self.assertEqual(self.request("/healthz"), (200, {"status": "ok"}))
        finally:
            app.WORK_SLOTS.release()
            app.WORK_SLOTS.release()

    def test_unknown_route(self):
        self.assertEqual(self.request("/missing")[0], 404)


if __name__ == "__main__":
    unittest.main()
