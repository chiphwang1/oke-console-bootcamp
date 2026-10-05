"""Preflight safety and failure paths, with no real cluster or credentials."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOCK = r'''#!PYTHON
import json, os, pathlib, sys
args = sys.argv[1:]
with pathlib.Path(os.environ["CALL_LOG"]).open("a") as stream:
    stream.write(json.dumps(args) + "\n")
if args == ["config", "current-context"]:
    if os.environ.get("FAIL_AT") == "context":
        sys.exit(1)
    print(os.environ.get("MOCK_CONTEXT", "assigned-lab"))
    sys.exit(0)
assert args[0] == "--context" and args[2] == "--request-timeout=15s", args
args = args[3:]
if args == ["version", "--client", "-o", "json"]:
    print(json.dumps({"clientVersion": {"gitVersion": os.environ.get("CLIENT_VERSION", "v1.36.0")}}))
elif args == ["get", "--raw=/version"]:
    if os.environ.get("FAIL_AT") == "api":
        print("SECRET_TOKEN_MUST_NOT_BE_PRINTED", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"gitVersion": os.environ.get("SERVER_VERSION", "v1.36.1")}))
elif args[:2] == ["get", "nodes"]:
    if os.environ.get("FAIL_AT") == "nodes":
        sys.exit(1)
    print(os.environ.get("NODES", "worker-a True false\nworker-b True false"))
elif args == ["top", "nodes", "--no-headers"]:
    if os.environ.get("FAIL_AT") == "metrics":
        sys.exit(1)
    print(os.environ.get("METRICS", "worker-a 60m 3% 3000Mi 22%\nworker-b 70m 4% 4000Mi 30%"))
else:
    raise AssertionError("Unexpected/mutating kubectl command: " + repr(args))
'''


class CheckReady(unittest.TestCase):
    def run_check(self, arguments=None, wrong_directory=False, missing_config=False,
                  extra_config=False, empty_config=False, missing_tool=None,
                  default_config=False, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            binary_dir = directory / "bin"
            binary_dir.mkdir()
            mock = MOCK.replace("PYTHON", sys.executable, 1)
            for name in ("kubectl", "oci", "helm", "git", "curl"):
                if name == missing_tool:
                    continue
                binary = binary_dir / name
                binary.write_text(mock)
                binary.chmod(0o755)
            # A controlled PATH makes missing-tool tests independent of the host.
            for name in ("awk", "sed"):
                (binary_dir / name).symlink_to(Path("/usr/bin") / name)
            config = directory / "kubeconfig"
            if default_config:
                config = directory / ".kube" / "config"
                config.parent.mkdir()
            if not missing_config:
                config.write_text("" if empty_config else "mock config; never parsed by real kubectl\n")
            selected_config = str(config)
            if extra_config:
                second = directory / "other-config"
                second.write_text("second mock config\n")
                selected_config += ":" + str(second)
            log = directory / "calls"
            environment = {**os.environ, "PATH": str(binary_dir), "CALL_LOG": str(log),
                           "KUBECONFIG": selected_config, **overrides}
            if default_config:
                environment["HOME"] = str(directory)
                environment.pop("KUBECONFIG", None)
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "scripts/check-ready.sh"),
                 *(arguments if arguments is not None else [])],
                cwd=directory if wrong_directory else ROOT,
                env=environment,
                text=True, capture_output=True, timeout=10,
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_pass_uses_only_allowlisted_read_commands_and_pins_current_context(self):
        result, calls = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Preflight passed", result.stdout)
        self.assertIn("Complete the chart downloads, archive checks, and connection confirmation", result.stdout)
        self.assertNotIn("separate instructor checks", result.stdout)
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(call[:2] == ["--context", "assigned-lab"] for call in calls[1:]))

    def test_uses_the_current_context_without_an_expected_context_argument(self):
        result, calls = self.run_check(MOCK_CONTEXT="production")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Selected context: production", result.stdout)
        self.assertTrue(all(call[:2] == ["--context", "production"] for call in calls[1:]))

    def test_bad_arguments_do_not_invoke_tools(self):
        for arguments in (["--context"], ["--context", "assigned-lab"],
                          ["--unknown", "assigned-lab"]):
            with self.subTest(arguments=arguments):
                result, calls = self.run_check(arguments=arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_help_does_not_require_repo_or_cluster(self):
        result, calls = self.run_check(arguments=["--help"], wrong_directory=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_wrong_directory_stops_before_kubectl(self):
        result, calls = self.run_check(wrong_directory=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checkout root", result.stderr)
        self.assertEqual(calls, [])

    def test_missing_tool_stops_before_kubectl(self):
        result, calls = self.run_check(missing_tool="oci")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("oci is missing", result.stderr)
        self.assertEqual(calls, [])

    def test_missing_or_empty_config_stops_before_kubectl(self):
        for option in ("missing_config", "empty_config"):
            with self.subTest(option=option):
                result, calls = self.run_check(**{option: True})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Kubeconfig", result.stderr)
                self.assertEqual(calls, [])

    def test_multiple_kubeconfig_files_are_supported(self):
        result, _ = self.run_check(extra_config=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_kubeconfig_without_environment_override(self):
        result, calls = self.run_check(default_config=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Preflight passed", result.stdout)
        self.assertEqual(len(calls), 5)

    def test_missing_default_kubeconfig_stops_before_kubectl(self):
        result, calls = self.run_check(default_config=True, missing_config=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".kube/config is missing", result.stderr)
        self.assertEqual(calls, [])

    def test_api_failure_is_actionable_and_does_not_print_auth_output(self):
        result, calls = self.run_check(FAIL_AT="api")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("connection/authentication failed", result.stderr)
        self.assertNotIn("SECRET_TOKEN", result.stdout + result.stderr)
        self.assertEqual(len(calls), 3)

    def test_version_mismatch_or_invalid_output_fails_before_nodes(self):
        for overrides in ({"CLIENT_VERSION": "v1.34.3"}, {"SERVER_VERSION": "v1.37.0"},
                          {"CLIENT_VERSION": "v2.36.0"}, {"SERVER_VERSION": "unknown"}):
            with self.subTest(overrides=overrides):
                result, calls = self.run_check(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 3)

    def test_one_minor_skew_is_supported(self):
        result, _ = self.run_check(CLIENT_VERSION="v1.35.3")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unready_cordoned_or_wrong_node_count_fails(self):
        for nodes in ("", "worker-a True false", "worker-a True false\nworker-b False false",
                      "worker-a True false\nworker-b True true",
                      "worker-a True false\nworker-b True false\nworker-c True false"):
            with self.subTest(nodes=nodes):
                result, calls = self.run_check(NODES=nodes)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 4)

    def test_missing_context_and_node_api_failures_are_actionable(self):
        for failure in ("context", "nodes"):
            with self.subTest(failure=failure):
                result, _ = self.run_check(FAIL_AT=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FAIL", result.stderr)

    def test_metrics_must_be_numeric_and_present_for_both_actual_nodes(self):
        for overrides in ({"FAIL_AT": "metrics"}, {"METRICS": ""},
                          {"METRICS": "worker-a 10m 1% 100Mi 1%"},
                          {"METRICS": "worker-a 10m 1% 100Mi 1%\nworker-b <unknown> 1% 100Mi 1%"},
                          {"METRICS": "worker-a 10m 1% 100Mi 1%\nother-node 20m 1% 100Mi 1%"}):
            with self.subTest(overrides=overrides):
                result, _ = self.run_check(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Resource metrics", result.stderr)


if __name__ == "__main__":
    unittest.main()
