"""Exercise validation failures and delayed LB readiness without a cluster."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOCK = '''#!{python}
import json, os, pathlib, sys
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
log = pathlib.Path(os.environ["CALL_LOG"])
with log.open("a") as stream:
    stream.write(json.dumps([tool, *args]) + "\\n")
failure = os.environ.get("FAIL_AT", "")
if tool == "kubectl":
    if failure == "nodes" and "nodes" in args and "wait" in args:
        sys.exit(1)
    if failure == "load-balancer" and "service/hello-oke" in args:
        sys.exit(1)
    if "get" in args and "service" in args:
        print("192.0.2.10")
elif tool == "curl":
    calls = sum(json.loads(line)[0] == "curl" for line in log.read_text().splitlines())
    if calls <= int(os.environ.get("CURL_FAILURES", "0")):
        sys.exit(7)
    print("hello from mock OKE")
'''


class ValidateLab(unittest.TestCase):
    def run_validation(self, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for name in ("kubectl", "curl", "sleep"):
                path = directory / name
                path.write_text(MOCK.format(python=sys.executable))
                path.chmod(0o755)
            log = directory / "calls"
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/validate-lab.sh")],
                env={**os.environ, "PATH": f'{directory}:{os.environ["PATH"]}',
                     "CALL_LOG": str(log), **overrides},
                capture_output=True, text=True, timeout=30,
            )
            return result, [json.loads(line) for line in log.read_text().splitlines()]

    def test_retries_until_load_balancer_serves_http(self):
        result, calls = self.run_validation(CURL_FAILURES="2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hello from mock OKE", result.stdout)
        requests = [call for call in calls if call[0] == "curl"]
        self.assertEqual(len(requests), 3)
        self.assertTrue(all("--max-time" in call for call in requests))
        self.assertTrue(all(call[-1] == "http://192.0.2.10/" for call in requests))

    def test_persistent_http_failure_is_bounded(self):
        result, calls = self.run_validation(CURL_FAILURES="99")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(call[0] == "curl" for call in calls), 12)
        self.assertIn("12 attempts", result.stderr)

    def test_unready_nodes_stop_validation(self):
        result, calls = self.run_validation(FAIL_AT="nodes")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call[0] == "curl" for call in calls))

    def test_missing_load_balancer_address_stops_validation(self):
        result, calls = self.run_validation(FAIL_AT="load-balancer")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call[0] == "curl" for call in calls))


if __name__ == "__main__":
    unittest.main()
