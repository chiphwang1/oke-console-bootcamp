# New GitLab project and student environment allocation

Use the new project [luna-labs/ospa/oke-console-bootcamp](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-console-bootcamp). Its source and materials release match [the new GitHub repository](https://github.com/chiphwang1/oke-console-bootcamp). Existing projects are not part of this setup.

## Allocation boundary

The existing integration is **Luna Shared Platform → allocated OCI identity/compartment → GitLab pipeline**. GitLab does not create the student account or tenancy. Preserve that platform allocation by selecting this new project in a new Luna lab and enabling **Provision resources through the Shared Platform**. Luna injects the temporary credentials and target. The `student:environment` job validates the handoff and records the GitLab environment `luna/oke-console-$CI_PIPELINE_ID` after successful checks.

No Terraform is retained because the old Terraform created the OKE cluster and associated infrastructure, not the platform allocation. This pipeline contains no OCI create, update, or delete operation. Students create their cluster and network in the Console. The GitLab environment record is pipeline status metadata, not an OCI compartment allocator.

## Configure only the new project

1. Protect `main`, restrict pipeline variable/trigger permissions to trusted Luna administrators, and attach an approved disposable Linux x86-64 container runner.
2. Create a **new Luna lab configuration**, enable GitLab Content, select this project and `main`, and enable Shared Platform provisioning. The new lab requires its own platform configuration; copying Git content alone does not allocate an environment.
3. Configure the student permissions and quotas described in the [instructor guide](instructor-guide.md). Configure the desktop image/tools and session OCI authentication independently of the runner.
4. Supply the complete launch variable set below. Use raw multiline PEM for the key; never copy credentials from another project or record them in source/artifacts.
5. Launch a new test session and verify that `student:environment` passes, the student can open the correct compartment, and the OKE list is initially empty. Continue through the full Console exercise.

| Variable | Source / meaning |
|---|---|
| `LUNA_DEPLOYMENT=1` | Trusted Luna launch; selects the allocation handoff |
| `TF_VAR_private_key` | Luna's complete unencrypted PEM signing key |
| `TF_VAR_user_ocid` | Temporary user associated with the key |
| `TF_VAR_fingerprint` | Matching API-key fingerprint |
| `TF_VAR_tenancy_ocid` | Allocated tenancy |
| `TF_VAR_compartment_ocid` | Allocated student compartment; never tenancy root |
| `TF_VAR_region` | Allocated subscribed region |
| `LAB_KUBERNETES_MINOR` | Defaults to `1.36`; must match the version rehearsed for class |

The `TF_VAR_` names are retained for compatibility with Luna's existing injection interface; they do not imply Terraform execution. The job never falls back to an inherited Base64 key, CLI profile, or instance principal. It checks protected default-branch execution again inside the script, validates the key, checks the user's tenancy, walks the compartment ancestry to that tenancy, checks the region subscription, and queries regional OKE versions. Credentials live only in a private temporary directory removed on exit. The job captures CLI failures without echoing API responses or credentials; debug tracing is rejected. There are no credential or environment artifacts.

## Pipeline behavior

All pushes run Bash lint, Kubernetes manifest rendering, Python tests, and full Helm chart rendering. `student:environment` runs automatically only for a trusted Luna launch on the protected default branch. A Luna flag on any other branch is denied by workflow rules. The flag alone is not authentication; protect the branch and restrict variable injection.

The source project used automatic Luna provisioning and manual cleanup callbacks. This version has no cluster provisioning job and no manual pipeline jobs for Luna to accidentally start at session end. Student resource lifecycle belongs to the platform/operator. **Before enabling real classes, confirm the new Luna configuration's reclamation process handles student-created OCI resources. This repository does not implement or claim successful cluster teardown.** No learner cleanup exercise is included.

GitLab SAST and Secret Detection templates are retained. Their analyzer images need runner approval, as in the source project. An unavailable or skipped scanner must be reported as such. The default Oracle Linux 9 image does not override template analyzer images.

## Resolve the blocked security scans

The current shared runner permits images from `**.ocir.io/**`, `registry.hap.demo.us-phoenix-1.oci.oraclecloud.com/**`, and `container-registry.oracle.com/**`. It rejects the template defaults `registry.gitlab.com/security-products/semgrep:6` and `registry.gitlab.com/security-products/secrets:7` before either analyzer runs.

Obtain approved analyzer image locations or an approved runner from the platform owner. If both approved mirrors preserve the `semgrep:6` and `secrets:7` names under one registry path, configure **only this new project's** `SECURE_ANALYZERS_PREFIX` CI/CD variable with that path. If the approved images use different names, override each analyzer job's `image` with its approved location instead. Confirm runner pull access and version compatibility with this GitLab instance's templates. Do not move unapproved images into an allowed registry simply to bypass the runner restriction.

See [GitLab's offline analyzer configuration](https://docs.gitlab.com/user/application_security/offline_deployments/) and [Secret Detection configuration](https://docs.gitlab.com/user/application_security/secret_detection/pipeline/configure/). Run CI Lint after configuring the approved images, then run a source pipeline and inspect both analyzer jobs and their reports. An allowed failure, skipped job, or absent report is not a scan pass. Review findings and record the exact pipeline in the [delivery readiness record](delivery-readiness.md).

Until approved locations or a runner are supplied, the scans remain blocked. Keep their template jobs visible so the blocker is reported; do not disable them or claim that a local secret scan replaces SAST and pipeline Secret Detection.

## Runner and checks

Use isolated job containers, not a shared shell runner. `scripts/ci-tools.sh` installs pinned tools inside the disposable container only: Helm 3.19.0, kubectl 1.36.1, ShellCheck 0.11.0, and OCI CLI 3.78.0. The runner needs outbound access to GitLab, Oracle's container/package registries, Helm chart repositories, GitHub downloads, `get.helm.sh`, `dl.k8s.io`, PyPI, and OCI APIs. Allocation validation does not need access to a Kubernetes endpoint because no cluster exists yet.

Local checks:

```bash
shellcheck scripts/*.sh
kubectl kustomize kubernetes
python3 -m unittest discover -s scripts/tests -v
bash scripts/test-helm.sh
```

Use GitLab CI Lint on the new instance to resolve the included security templates. Local YAML checks and unit tests cannot prove instance-specific template support, runner availability, or platform callbacks. See [validation results](validation.md).
