# Validation — 2026-10-05

[GitLab pipeline 401325](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-console-bootcamp/-/pipelines/401325) tested source commit `d0f348f` in the new project. Subsequent documentation-only changes record these results.

| Check | Result |
|---|---|
| Python unit tests | **44 passed** locally and in GitLab: application, preflight, chart preparation, live-validator mocks, allocation isolation, and documentation |
| Helm lint and full render contracts | **13 passed, none skipped**, on the GitLab runner, including Istio, Grafana, Kiali, and Prometheus |
| ShellCheck 0.11.0 | Passed for every Bash script locally and in GitLab |
| Legacy Kubernetes rendering | `kubectl kustomize kubernetes` passed locally and in GitLab |
| GitLab instance CI Lint | Valid, no errors, with included security templates resolved |
| Local Gitleaks 8.30.1 | No secrets found in the new source tree |
| GitLab SAST | **Blocked**: runner rejected `registry.gitlab.com/security-products/semgrep:6` |
| GitLab Secret Detection | **Blocked**: runner rejected `registry.gitlab.com/security-products/secrets:7` |
| Student allocation job | Not executed by the ordinary push pipeline; requires a trusted Luna launch and temporary session variables |
| Live OCI / Console workflow | Not run; no OCI resources were created during validation |

The GitLab security templates mark their scanner failures as allowed failures, so overall pipeline success does not mean those scans passed. A runner administrator must approve the analyzer images or provide approved mirrors before classroom release. The existing shared runner configuration was not changed.

The local full Helm attempt could not reach `blob.istio.io`, including an IPv4 retry. Local-only testing passed with four upstream checks skipped. The GitLab runner subsequently completed the full suite, resolving the upstream rendering check for this release.

## New project configuration

The new GitLab project is private, uses the existing approved shared runners, protects `main` for Maintainer push/merge access, disables force pushes, and restricts pipeline variable overrides to Maintainers. The new GitHub repository is public for unauthenticated learner cloning. The initial validated materials tag was `console-lab-2026-10-05.1`; the README identifies the current release.

The existing allocation contract comes from Luna Shared Platform. The new GitLab job validates its identity/compartment/region handoff; it does not itself allocate a tenancy or create an OKE cluster. Configure a new Luna lab to use this project and enable Shared Platform provisioning as described in [CI setup](gitlab-ci.md).

A fresh Luna session is still required to validate runtime credential injection, student permissions/quotas, regional capacity, Console creation, add-on readiness, full Helm deployment, dashboard and HTTP access, and the platform's resource reclamation. Prior rehearsals of the Terraform lab do not establish those results for this lab.

## Source preservation

The original checkout's tracked file hashes and Git status were checked after publication and remained unchanged. No write operation targeted its GitHub repository or GitLab project. The new repositories contain a curated source snapshot, with no copied Git history, credentials, kubeconfigs, Terraform state/plans, or private operational logs.

The app, chart, pinned upstream versions, monitoring values, and operational validation scripts were retained. Terraform and its infrastructure mutation/state/cleanup scripts were excluded because students now create those resources in the Console. Learner cleanup instructions are not part of this lab.

## Three-worker update — console-lab-2026-10-05.3

The Console instructions, diagram, capacity guidance, completion sheet, and preflight now require three managed workers. The preflight tests cover a missing third worker, a fourth worker, an unready or cordoned third worker, and missing/non-numeric third-worker metrics. The Quick Create introduction is included in this release.

All 44 Python tests, all 13 full Helm checks (no skips), ShellCheck, documentation links/examples, and Kubernetes rendering passed locally. Full upstream chart access worked through the workstation's configured network proxy. The three-worker configuration has not been deployed to live OCI; its worker allocation is now 3 OCPUs and 48 GB memory plus three boot volumes. GitLab security analyzer execution remains subject to the runner image restriction recorded above.

## Delivery review follow-up — console-lab-2026-10-05.4

The new [Luna lab](https://luna.oracle.com/lab/14dae9a8-6c89-4200-9e9b-7a522f846665) is registered and connected to the new GitLab project. The three-worker allocation was read back in Luna: one enhanced cluster, three E5 OCPUs, 48 GB memory, 150 GB storage, and one 10 Mbps flexible load balancer. Student management permissions and Shared Platform provisioning are enabled. Resource availability and effective permissions still require a pilot.

The delivery update reserves a 150-minute session for the 90–120-minute core, moves the optional lecture before launch, and bases extension cutoffs on remaining time. README supporting-document links open the public tagged release. The [delivery readiness record](delivery-readiness.md) separates saved configuration, static checks, pending student-session evidence, and operator reclamation verification.

The review of `a5b6fbd` passed 44 Python tests, all 13 Helm checks with upstream rendering, ShellCheck, and Kubernetes rendering. [Pipeline 401331](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-console-bootcamp/-/pipelines/401331) passed the four functional jobs, but both security analyzers failed before execution because their images are disallowed. Approved mirror/runner details are still required; no runner security policy was changed.

No live student launch, OCI deployment, or reclamation test has been performed. The lab remains Private pending the owner's sharing choice. Classroom readiness is still pending the recorded live checks and scanner resolution.

Checks rerun after the `.4` documentation changes: **44 Python tests passed**, **13 full Helm checks passed with no skips**, ShellCheck and Kubernetes rendering passed, and all 23 README public-release document links matched existing files and anchors in the release tree. No application or CI execution code changed.
