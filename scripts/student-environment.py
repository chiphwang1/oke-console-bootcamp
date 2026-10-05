#!/usr/bin/env python3
"""Validate Luna's allocated environment without creating OCI resources."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


class AllocationError(Exception):
    """An allocation check failed; messages must never include credentials."""


def require(condition, message):
    if not condition:
        raise AllocationError(message)


def validate_launch(env):
    require(env.get("CI_DEBUG_TRACE", "false").lower() != "true",
            "Disable CI_DEBUG_TRACE for credential-bearing jobs.")
    require(env.get("LUNA_DEPLOYMENT") == "1", "A trusted Luna launch is required.")
    require(env.get("CI_COMMIT_REF_PROTECTED") == "true"
            and bool(env.get("CI_DEFAULT_BRANCH"))
            and env.get("CI_COMMIT_BRANCH") == env.get("CI_DEFAULT_BRANCH"),
            "Luna requires the protected default branch.")
    require(bool(re.fullmatch(r"[0-9]+", env.get("CI_PIPELINE_ID", ""))),
            "CI_PIPELINE_ID is missing or invalid.")
    for name in ("private_key", "user_ocid", "fingerprint", "tenancy_ocid",
                 "compartment_ocid", "region"):
        require(bool(env.get("TF_VAR_" + name, "").strip()),
                "Missing Luna variable: TF_VAR_" + name)
    for name, kind in (("user_ocid", "user"), ("tenancy_ocid", "tenancy"),
                       ("compartment_ocid", "compartment")):
        require(bool(re.fullmatch(r"ocid1\." + kind + r"\.[A-Za-z0-9._-]+",
                                 env["TF_VAR_" + name])),
                "Invalid allocated " + name + ".")
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", env["TF_VAR_region"])),
            "Invalid allocated region.")
    require(bool(re.fullmatch(r"(?:[0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}",
                             env["TF_VAR_fingerprint"])), "Invalid API-key fingerprint.")
    require(env.get("LAB_KUBERNETES_MINOR", "1.36") in
            {"1.32", "1.33", "1.34", "1.35", "1.36"},
            "LAB_KUBERNETES_MINOR is outside the lab chart compatibility range.")


def check_allocation(env, query):
    """query is injected for tests. All operations below are read-only."""
    tenancy = env["TF_VAR_tenancy_ocid"]
    user = query("iam", "user", "get", "--user-id", env["TF_VAR_user_ocid"])
    require(user.get("id") == env["TF_VAR_user_ocid"]
            and user.get("compartment-id") == tenancy,
            "The allocated user does not belong to the allocated tenancy.")
    require(user.get("lifecycle-state") == "ACTIVE", "The allocated user is not active.")

    target = env["TF_VAR_compartment_ocid"]
    seen = set()
    while target != tenancy:
        require(target and target not in seen and len(seen) < 64,
                "Cannot verify the allocated compartment's tenancy ancestry.")
        seen.add(target)
        compartment = query("iam", "compartment", "get", "--compartment-id", target)
        require(compartment.get("id") == target, "Compartment response target mismatch.")
        require(compartment.get("lifecycle-state") == "ACTIVE",
                "The allocated compartment or an ancestor is not active.")
        target = compartment.get("compartment-id")

    regions = query("iam", "region-subscription", "list", "--tenancy-id", tenancy, "--all")
    require(any(item.get("region-name") == env["TF_VAR_region"]
                and item.get("status") == "READY" for item in regions),
            "The allocated region is not a ready tenancy subscription.")
    options = query("ce", "cluster-options", "get", "--cluster-option-id", "all")
    minor = env.get("LAB_KUBERNETES_MINOR", "1.36")
    versions = options.get("kubernetes-versions", [])
    require(any(re.fullmatch(r"v?" + re.escape(minor) + r"(?:\.[1-9][0-9]*)?", v)
                for v in versions),
            "The rehearsed Kubernetes minor has no supported stable version in this region.")


def run(env):
    validate_launch(env)
    # Remove all inherited OCI settings, raw keys, and Terraform credentials from
    # child processes. A private, explicit CLI config is the sole auth source.
    child_env = {k: v for k, v in env.items()
                 if not k.startswith(("OCI_", "TF_VAR_", "TF_LOG"))}
    with tempfile.TemporaryDirectory(prefix="oke-console-session-") as directory:
        key = Path(directory) / "key.pem"
        key.touch(mode=0o600)
        key.write_text(env["TF_VAR_private_key"])
        validation = subprocess.run(
            ["openssl", "pkey", "-in", str(key), "-passin", "pass:", "-noout"],
            env=child_env, capture_output=True, timeout=15, check=False)
        require(validation.returncode == 0, "Luna supplied an invalid unencrypted PEM key.")
        config = Path(directory) / "config"
        config.touch(mode=0o600)
        config.write_text("[DEFAULT]\n" + "\n".join([
            "user=" + env["TF_VAR_user_ocid"],
            "tenancy=" + env["TF_VAR_tenancy_ocid"],
            "fingerprint=" + env["TF_VAR_fingerprint"],
            "region=" + env["TF_VAR_region"],
            "key_file=" + str(key),
        ]) + "\n")

        def query(*args):
            result = subprocess.run([
                "oci", *args, "--config-file", str(config), "--profile", "DEFAULT",
                "--auth", "api_key", "--region", env["TF_VAR_region"],
                "--output", "json", "--connection-timeout", "10", "--read-timeout", "30",
            ], env=child_env, capture_output=True, text=True, timeout=120, check=False)
            require(result.returncode == 0,
                    "OCI read failed during " + " ".join(args[:3]) +
                    "; check session permissions, identity, and connectivity.")
            try:
                return json.loads(result.stdout)["data"]
            except (ValueError, KeyError, TypeError):
                raise AllocationError("OCI returned an invalid allocation response.") from None

        check_allocation(env, query)
    print("PASS Student allocation: identity, active compartment, region, and OKE version options.")
    print("Student environment ready. Create the OKE cluster through the Console in lab step 1.")


def main():
    try:
        run(os.environ)
    except (AllocationError, OSError, subprocess.TimeoutExpired) as exc:
        # Never print subprocess exceptions (which can carry captured output).
        message = str(exc) if isinstance(exc, AllocationError) else "Allocation check could not complete; check tools and connectivity."
        print("FAIL " + message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
