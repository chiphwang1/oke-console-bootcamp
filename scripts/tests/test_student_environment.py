"""Exercise allocation isolation, credential handling, and failure boundaries."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("allocation", ROOT / "scripts/student-environment.py")
allocation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(allocation)


def launch():
    return dict(os.environ, LUNA_DEPLOYMENT="1", CI_DEBUG_TRACE="false",
                CI_COMMIT_REF_PROTECTED="true", CI_COMMIT_BRANCH="main",
                CI_DEFAULT_BRANCH="main", CI_PIPELINE_ID="123",
                TF_VAR_private_key="test-only-key", TF_VAR_user_ocid="ocid1.user.oc1.test",
                TF_VAR_tenancy_ocid="ocid1.tenancy.oc1.test",
                TF_VAR_compartment_ocid="ocid1.compartment.oc1.student",
                TF_VAR_fingerprint=":".join(["ab"] * 16), TF_VAR_region="us-phoenix-1",
                LAB_KUBERNETES_MINOR="1.36")


def responses():
    return [
        {"id": "ocid1.user.oc1.test", "compartment-id": "ocid1.tenancy.oc1.test", "lifecycle-state": "ACTIVE"},
        {"id": "ocid1.compartment.oc1.student", "compartment-id": "ocid1.compartment.oc1.parent", "lifecycle-state": "ACTIVE"},
        {"id": "ocid1.compartment.oc1.parent", "compartment-id": "ocid1.tenancy.oc1.test", "lifecycle-state": "ACTIVE"},
        [{"region-name": "us-phoenix-1", "status": "READY"}],
        {"kubernetes-versions": ["v1.35.2", "v1.36.1"]},
    ]


class StudentEnvironment(unittest.TestCase):
    def test_untrusted_launches_rejected(self):
        for change in ({"LUNA_DEPLOYMENT": "0"}, {"CI_COMMIT_REF_PROTECTED": "false"},
                       {"CI_COMMIT_BRANCH": "feature"}, {"CI_DEFAULT_BRANCH": ""},
                       {"CI_DEBUG_TRACE": "true"}, {"CI_PIPELINE_ID": ""}):
            with self.subTest(change=change), self.assertRaises(allocation.AllocationError):
                allocation.validate_launch(dict(launch(), **change))

    def test_missing_raw_key_never_falls_back(self):
        env = dict(launch(), TF_VAR_private_key="", OCI_PRIVATE_KEY_B64="legacy-key")
        with self.assertRaisesRegex(allocation.AllocationError, "TF_VAR_private_key"):
            allocation.validate_launch(env)

    def test_config_injection_root_compartment_and_unsupported_minor_rejected(self):
        for field, value in (("TF_VAR_region", "us-phoenix-1\nkey_file=other"),
                             ("TF_VAR_user_ocid", "ocid1.user.oc1.test\nauth=other"),
                             ("TF_VAR_compartment_ocid", "ocid1.tenancy.oc1.test"),
                             ("LAB_KUBERNETES_MINOR", "1.37")):
            with self.subTest(field=field), self.assertRaises(allocation.AllocationError):
                allocation.validate_launch(dict(launch(), **{field: value}))

    def test_nested_compartment_verified_with_read_only_operations(self):
        with patch.object(allocation, "require", wraps=allocation.require):
            from unittest.mock import Mock
            query = Mock(side_effect=responses())
            allocation.check_allocation(launch(), query)
        for call in query.call_args_list:
            self.assertIn(call.args[2], ("get", "list"))
        self.assertEqual(query.call_args_list[2].args[-1], "ocid1.compartment.oc1.parent")

    def test_cross_tenancy_user_rejected(self):
        data = responses()
        data[0]["compartment-id"] = "ocid1.tenancy.oc1.wrong"
        with self.assertRaisesRegex(allocation.AllocationError, "user does not belong"):
            allocation.check_allocation(launch(), lambda *args: data.pop(0))

    def test_inactive_or_mismatched_compartment_rejected(self):
        for field, value in (("lifecycle-state", "DELETED"), ("id", "wrong")):
            data = responses()
            data[1][field] = value
            with self.subTest(field=field), self.assertRaises(allocation.AllocationError):
                allocation.check_allocation(launch(), lambda *args: data.pop(0))

    def test_wrong_tenancy_ancestry_and_cycles_rejected(self):
        for parent in (None, "ocid1.compartment.oc1.student"):
            data = responses()
            data[2]["compartment-id"] = parent
            with self.subTest(parent=parent), self.assertRaisesRegex(allocation.AllocationError, "ancestry"):
                allocation.check_allocation(launch(), lambda *args: data.pop(0))

    def test_unsubscribed_region_and_preview_only_versions_rejected(self):
        for index, value in ((3, [{"region-name": "us-ashburn-1", "status": "READY"}]),
                             (3, [{"region-name": "us-phoenix-1", "status": "IN_PROGRESS"}]),
                             (4, {"kubernetes-versions": ["v1.36.0", "v1.37.1"]})):
            data = responses()
            data[index] = value
            with self.subTest(value=value), self.assertRaises(allocation.AllocationError):
                allocation.check_allocation(launch(), lambda *args: data.pop(0))

    def test_key_permissions_environment_isolation_and_failure_cleanup(self):
        paths = []
        env = dict(launch(), OCI_PRIVATE_KEY_B64="inherited-secret", OCI_CLI_AUTH="instance_principal",
                   OCI_CLI_KEY_CONTENT="inherited-secret", TF_LOG="TRACE")

        def process(args, **kwargs):
            self.assertFalse(any(k.startswith(("OCI_", "TF_VAR_", "TF_LOG")) for k in kwargs["env"]))
            if args[0] == "openssl":
                key = Path(args[args.index("-in") + 1])
                paths.append(key.parent)
                self.assertEqual(key.stat().st_mode & 0o777, 0o600)
                self.assertEqual(key.parent.stat().st_mode & 0o777, 0o700)
                self.assertEqual(key.read_text(), env["TF_VAR_private_key"])
                return subprocess.CompletedProcess(args, 0, b"", b"")
            config = Path(args[args.index("--config-file") + 1])
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertEqual(args[args.index("--auth") + 1], "api_key")
            return subprocess.CompletedProcess(args, 1, "private response", "inherited-secret")

        with patch.object(allocation.subprocess, "run", side_effect=process):
            with self.assertRaises(allocation.AllocationError) as raised:
                allocation.run(env)
        self.assertNotIn("secret", str(raised.exception))
        self.assertNotIn("private response", str(raised.exception))
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())

    def test_invalid_key_fails_before_oci_and_is_removed(self):
        paths = []

        def reject(args, **kwargs):
            self.assertEqual(args[0], "openssl")
            paths.append(Path(args[args.index("-in") + 1]).parent)
            return subprocess.CompletedProcess(args, 1, b"", b"secret")

        with patch.object(allocation.subprocess, "run", side_effect=reject):
            with self.assertRaisesRegex(allocation.AllocationError, "invalid unencrypted PEM"):
                allocation.run(launch())
        self.assertFalse(paths[0].exists())


if __name__ == "__main__":
    unittest.main()
