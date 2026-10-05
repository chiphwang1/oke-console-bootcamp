# Initial validation — 2026-10-05

| Check | Result |
|---|---|
| Python unit tests | 44 passed: app, preflight, chart preparation, live-validator mocks, allocation isolation, and documentation checks |
| ShellCheck 0.11.0 | Passed for every Bash script |
| Legacy Kubernetes rendering | `kubectl kustomize kubernetes` passed |
| Local Helm lint/render and dashboard contracts | Passed |
| Upstream Helm renders | Grafana, Kiali, and Prometheus passed; Istio download blocked by local connectivity to `blob.istio.io`, including an IPv4 retry |
| GitLab instance CI Lint | Valid, no errors, with included security templates resolved |
| Gitleaks 8.30.1 | No secrets found in the new source tree |

A pipeline in the new GitLab project will exercise the same source checks on its runner. The inherited security analyzer images need runner approval; their actual execution is recorded after the first pipeline.

The new student Console flow has not been run against live OCI. A fresh Luna launch is required to validate runtime credential injection, student permissions/quotas, regional capacity, Console cluster creation, add-on readiness, full Helm deployment, dashboards, HTTP access, and platform reclamation. Prior rehearsals of the Terraform lab do not establish those results for this lab. No OCI resources were created by these checks.

The old lab's app, chart, pinned versions, monitoring values, and operational validation scripts were retained. Its Terraform, state handling, and infrastructure mutation/cleanup scripts were excluded because students now create those resources through the Console.
