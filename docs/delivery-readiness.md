# Delivery readiness record

**Status: instructor pilot pending; classroom delivery not yet verified.** This is an operator/instructor record. It does not add learner resource-removal steps.

## Configuration baseline

- Luna lab: [OKE Console Bootcamp](https://luna.oracle.com/lab/14dae9a8-6c89-4200-9e9b-7a522f846665).
- Materials release: `console-lab-2026-10-05.4`; publish matching GitHub and GitLab tags.
- Luna content/provisioning: new GitLab project, protected `main`, `README.md`, Shared Platform enabled.
- Session limit: 150 minutes; core estimate 90–120 minutes. Introductory lecture before launch; final 10 minutes reserved for debrief.
- Visibility: Private until the owner selects learner sharing. Verify intended-user access before distributing the URL.
- Allocation: one enhanced cluster, three private managed E5 workers, 3 OCPUs and 48 GB memory total, 150 GB block storage, and one flexible load balancer at 10 Mbps.

Record dates, release/commit, job links, elapsed minutes, and sanitized observations. Never put passwords, private keys, tokens, kubeconfigs, full environment dumps, or private operational logs into this public repository. Keep sensitive session references in the team's restricted records.

## Evidence required before classroom delivery

| Check | Evidence to record | Current result |
|---|---|---|
| Intended learner access | Visibility/audience and successful access using the intended learner role | Pending; private team access only |
| Luna allocation and CI | New-project pipeline URL; successful `student:environment`; correct identity/compartment/region; initially empty OKE list | Not run |
| Desktop readiness | OCI CLI, kubectl, Helm, Git, curl versions; correct session profile; kubeconfig authentication from a second terminal | Not run |
| Required instructions | Open cluster-creation and completion-sheet links from the Luna learner view; return to the main instructions; matching release | Not run |
| Console permissions and capacity | Quick Create and add-ons succeed using the student identity; actual region, supported patch, E5 capacity, image boot size within quota | Not run |
| Cluster readiness | Three Ready workers; numeric metrics for all three; required Helm permissions | Not run |
| Application and monitoring | Five monitoring releases; custom HTTP response; Kiali traffic; Grafana metrics; manual replicas 2 → 4 → 2 | Not run |
| Beginner timing | Allocation, cluster, add-ons, charts, app/LB, dashboards, scaling, and debrief durations; remaining buffer | Not measured |
| Optional exercises | HPA/pod recovery observed; HPA burst reset and return to two replicas, if attempted | Not run; optional |
| Security analyzers | Successful SAST and Secret Detection jobs, reports, and review of findings | Blocked by runner image policy |
| Resource lifecycle | Operator evidence from normal session completion and expiry; orphan handling after partial provisioning | Not verified |

## Pilot timing worksheet

Record elapsed time from the student's launch, including waits and instructor interventions. Do not subtract troubleshooting time from the result.

| Milestone | Elapsed minutes | Blockers/interventions |
|---|---|---|
| Desktop and allocated credentials ready | ___ | ___ |
| Allocation CI passed | ___ | ___ |
| Cluster and three workers Active | ___ | ___ |
| Add-ons and preflight passed | ___ | ___ |
| Chart downloads and five releases ready | ___ | ___ |
| Customized app reachable | ___ | ___ |
| Kiali and Grafana observations recorded | ___ | ___ |
| Manual scaling and core debrief complete | ___ | ___ |
| Session time remaining | ___ | ___ |

Proceed with a beginner class only after the core pilot succeeds with usable troubleshooting margin. If core work consumes the buffer, shorten the core or increase the session allocation before the class. Optional exercises may be omitted.

## Operator verification of resource reclamation

The new CI validates allocation and does not remove OCI resources. Assign an operator before the pilot; do not infer reclamation from a closed desktop or an expired account.

Operator: ___  Verification date: ___  Restricted evidence location: ___

- [ ] Identify the platform's actual reclamation mechanism, trigger, expected completion time, and escalation owner for this new lab.
- [ ] Inventory pilot-created resources before ending the session: cluster, node pool, worker instances, boot volumes, application load balancer, VCN, subnets, gateways, and public IPs.
- [ ] Verify normal session completion removes the allocated resources through the supported operator/platform process.
- [ ] Verify expiry behavior in a controlled operator test, including resources created by the student rather than CI.
- [ ] Confirm how the operator detects and resolves leftovers after a partial Quick Create failure or a failed reclamation attempt.
- [ ] Record the observed result and any follow-up; do not mark this complete solely because credentials expired.

## Delivery decision

Release/commit: ___  Pilot date: ___  Instructor: ___

Decision: pending / ready for classroom delivery / blocked

Unresolved items and owners: ___

Static results belong in [validation](validation.md). Keep live checks marked pending until there is observed evidence.
