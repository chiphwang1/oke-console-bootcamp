"""Prepared-chart safety checks with mocked Helm; no network or cluster access."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHARTS = {
    "base": "1.31.0",
    "istiod": "1.31.0",
    "prometheus": "29.30.0",
    "kiali-server": "2.32.0",
    "grafana": "13.2.5",
}
MOCK_HELM = r'''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["HELM_TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\n")
if args[:2] == ["show", "chart"]:
    print(Path(args[2]).read_text(), end="")
elif args[0] == "pull":
    name = args[1]
    version = args[args.index("--version") + 1]
    dest = Path(args[args.index("--destination") + 1])
    archive = dest / (name + "-" + version + ".tgz")
    archive.write_text("name: " + name + "\nversion: " + version + "\n")
    if os.environ.get("HELM_TEST_FAIL_PULL"):
        sys.exit(9)
else:
    sys.exit("Unexpected Helm command: " + repr(args))
'''


class PrepareCharts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="oke-chart-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("scripts", "helm", "bin"):
            (self.root / folder).mkdir()
        shutil.copy2(ROOT / "scripts/prepare-charts.sh", self.root / "scripts")
        shutil.copy2(ROOT / "helm/versions.env", self.root / "helm")
        mock = self.root / "bin/helm"
        mock.write_text("#!" + sys.executable + "\n" + MOCK_HELM)
        mock.chmod(0o755)
        self.log = self.root / "calls.jsonl"
        self.cache = self.root / ".lab-cache/charts"
        self.env = {**os.environ, "PATH": str(mock.parent) + os.pathsep + os.environ["PATH"],
                    "HELM_TEST_LOG": str(self.log)}

    def run_script(self, *args, **env):
        return subprocess.run(
            ["bash", str(self.root / "scripts/prepare-charts.sh"), *args],
            cwd=self.root.parent, env={**self.env, **env}, text=True,
            capture_output=True, timeout=20,
        )

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def prepare(self):
        self.cache.mkdir(parents=True)
        for name, version in CHARTS.items():
            (self.cache / f"{name}-{version}.tgz").write_text(f"name: {name}\nversion: {version}\n")

    def test_missing_check_does_not_download_or_create_cache(self):
        result = self.run_script("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing chart", result.stderr)
        self.assertIn("bash scripts/prepare-charts.sh --download", result.stderr)
        self.assertFalse(self.cache.exists())
        self.assertEqual(self.calls(), [])

    def test_downloads_only_pinned_charts_and_reuses_existing_files(self):
        result = self.run_script("--download")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("PASS Prepared chart:"), 5)
        pulls = [c for c in self.calls() if c[0] == "pull"]
        self.assertEqual({c[1]: c[c.index("--version") + 1] for c in pulls}, CHARTS)
        snapshots = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.cache.glob("*.tgz")}
        again = self.run_script("--download")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(len([c for c in self.calls() if c[0] == "pull"]), 5)
        self.assertEqual(snapshots, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in snapshots})

    def test_check_is_read_only_and_works_outside_repository_root(self):
        self.prepare()
        snapshots = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.cache.iterdir()}
        result = self.run_script("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[:2] for c in self.calls()], [["show", "chart"]] * 5)
        self.assertEqual(snapshots, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in snapshots})

    def test_mismatched_archive_is_not_overwritten(self):
        for metadata in ("name: base\nversion: 0.0.0\n", "name: other\nversion: 1.31.0\n"):
            with self.subTest(metadata=metadata):
                self.cache.mkdir(parents=True, exist_ok=True)
                archive = self.cache / "base-1.31.0.tgz"
                archive.write_text(metadata)
                result = self.run_script("--download")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Chart mismatch", result.stderr)
                self.assertEqual(archive.read_text(), metadata)
                self.assertFalse(any(c[0] == "pull" for c in self.calls()))

    def test_failed_download_is_not_published_as_ready(self):
        result = self.run_script("--download", HELM_TEST_FAIL_PULL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Download failed", result.stderr)
        self.assertIn("retry --download", result.stderr)
        self.assertNotIn("before class", result.stderr)
        self.assertFalse((self.cache / "base-1.31.0.tgz").exists())
        self.assertEqual(len(list(self.cache.glob(".download.*/base-1.31.0.tgz"))), 1)

    def test_invalid_arguments_do_not_invoke_helm(self):
        for args in ((), ("--install",), ("--check", "--download")):
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Usage:", result.stderr)
                self.assertNotIn("unbound variable", result.stderr)
                self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
