# Repository guidelines

This standalone lab has a new GitHub repository and new GitLab project. Learners create OKE through the OCI Console with exactly three managed worker nodes. Luna allocates the student identity/compartment; GitLab validates that handoff. Do not add cluster provisioning to CI or Terraform.

`charts/oke-mesh-app/files/server.py` is the training app, mounted in a published Python image. `helm/` pins upstream charts and holds values/dashboard settings. `scripts/` contains preflight, live validation, chart preparation, CI tool installation, and allocation checks. `kubernetes/` is a legacy maintainer render fixture; never apply it alongside Helm resources. `docs/` contains the cluster creation and instructor workflows.

Run ShellCheck on scripts, `kubectl kustomize kubernetes`, `python3 -m unittest discover -s scripts/tests -v`, and `bash scripts/test-helm.sh`. `--local-only` skips upstream rendering; report it explicitly. Run `scripts/ci-tools.sh` only in disposable CI containers. Terraform validation is not applicable. Live cluster operations require the intended session identity/context; report when live validation and security scans have not run.

Use two-space YAML indentation, consistent selectors, and lowercase hyphenated resource names. Bash uses `set -euo pipefail`. Never commit credentials, kubeconfigs, local state, plans, or private operational logs. Keep inherited source projects unchanged. Commits use conventional subjects; describe behavior, checks, and infrastructure/cost implications.
