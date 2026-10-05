"""Check runnable docs, local references, and CI's allocation-only boundary."""
from pathlib import Path
import re
import subprocess
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class ConsoleMaterials(unittest.TestCase):
    def test_bash_examples_and_local_links(self):
        for path in [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "helm/README.md",
                     *sorted((ROOT / "docs").glob("*.md"))]:
            text = path.read_text()
            for block in re.findall(r"^\s*```bash\n(.*?)^\s*```", text, re.M | re.S):
                result = subprocess.run(["bash", "-n"], input=block, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}")
            for target in re.findall(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)", text):
                if "://" in target or target.startswith("mailto:"):
                    continue
                filename, _, anchor = target.partition("#")
                dest = path.parent / filename if filename else path
                self.assertTrue(dest.exists(), f"{path}: {target}")
                if anchor and dest.suffix == ".md":
                    headings = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
                                for h in re.findall(r"^#{1,6} (.+)$", dest.read_text(), re.M)}
                    self.assertIn(anchor, headings, f"{path}: {target}")

    def test_allocation_job_gate_and_no_infrastructure_mutations(self):
        config = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())
        job = config["student:environment"]
        rule = job["rules"][0]
        self.assertIn('$LUNA_DEPLOYMENT == "1"', rule["if"])
        self.assertIn('$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH', rule["if"])
        self.assertIn('$CI_COMMIT_REF_PROTECTED == "true"', rule["if"])
        self.assertEqual(rule["when"], "on_success")
        self.assertEqual(job["rules"][-1]["when"], "never")
        self.assertNotIn("artifacts", job)
        self.assertFalse((ROOT / "terraform").exists())
        self.assertNotIn("terraform:", (ROOT / ".gitlab-ci.yml").read_text())
        self.assertNotIn("when: manual", (ROOT / ".gitlab-ci.yml").read_text())

    def test_documents_do_not_send_students_to_original_lab(self):
        for path in [ROOT / "README.md", ROOT / "helm/README.md", *sorted((ROOT / "docs").glob("*.md"))]:
            text = path.read_text()
            for old in ("github.com/chiphwang1/AI_world_lab", "8f468598-9993-41b8-92ce-e643f5603f9b",
                        "Luna provisions your cluster", "cluster Luna created", "terraform apply"):
                self.assertNotIn(old, text, f"{path}: {old}")
        text = (ROOT / "docs/create-cluster.md").read_text()
        for prerequisite in ("Quick create", "Enhanced", "Private workers", "Cert Manager", "Kubernetes Metrics Server"):
            self.assertIn(prerequisite, text)


if __name__ == "__main__":
    unittest.main()
