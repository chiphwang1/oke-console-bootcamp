# Instructor preparation

This lab teaches students to create their own OKE cluster before deploying the existing application and monitoring stack. Plan for **90–120 minutes of core exercises in a 150-minute Luna session**, leaving 30 minutes beyond the upper estimate for provisioning delays and troubleshooting. Give the optional 30-minute lecture before launching the timed session. Reserve the final 10 minutes for debrief; verify the schedule in a beginner pilot.

## New project setup

Use [the new GitLab allocation project](https://gitlab.hap.demo.us-phoenix-1.oci.oraclecloud.com/luna-labs/ospa/oke-console-bootcamp) and [new GitHub learner repository](https://github.com/chiphwang1/oke-console-bootcamp). Publish the same `console-lab-2026-10-05.4` tag to both. Verify unauthenticated access to the GitHub tag and a fresh clone before class. Point a new Luna lab's content/allocation settings at the new GitLab project following [CI setup](gitlab-ci.md).

Luna provides the desktop, temporary identity, and compartment. GitLab validates the allocation; students create the OKE/network/worker resources. The CI job's successful read requests do not prove write permissions, quota, or capacity. No Terraform provider, state, plan, or OCI credentials from the existing project should be copied.

## Luna delivery settings

Use [OKE Console Bootcamp in Luna](https://luna.oracle.com/lab/14dae9a8-6c89-4200-9e9b-7a522f846665). Its content is the new GitLab project's `main` branch and `README.md`; Shared Platform provisioning must stay enabled. Keep `main` at the published materials release during a class so Luna instructions and the learner tag stay consistent. Do not select a tag as the provisioning ref: the allocation job requires the protected default branch.

Set the session limit to **150 minutes**. The current visibility is **Private** (team access only). Before an external class, select Unlisted for access through the lab URL, or Public for homepage discovery, and verify access as an intended learner. The Customers audience setting does not override Private visibility.

README supporting-document links use the public GitHub release so learners do not need GitLab access. Check them in the actual Luna learner view during the pilot, including cluster creation, the completion sheet, and the return to the main instructions.

Use the [delivery readiness record](delivery-readiness.md) to record evidence and unresolved items. A configured lab or a passing source pipeline is not evidence of a completed student session.

## Capacity and identity prerequisites

- Rehearse a supported stable Kubernetes 1.36 version in the actual allocated region. Keep `LAB_KUBERNETES_MINOR`, learner instructions, kubectl compatibility, and the pinned Istio range consistent if changing it.
- Reserve one enhanced OKE cluster and three managed x86 workers. The starting shape is VM.Standard.E5.Flex, each with 1 OCPU and 16 GB memory (3 OCPUs and 48 GB total across the workers). Choose an available equivalent only after a full rehearsal. The saved allocation provides 150 GB total block storage and a volume count of three. Confirm the selected OKE image's actual boot-volume size fits that total before launch; if it does not, the operator must adjust the quota. Include network gateways in the allocation budget.
- Allow one flexible application load balancer: the source lab uses `lb-flexible-count=1` and `lb-flexible-bandwidth-sum=10`. Check the effective quota on a fresh allocation.
- Permit the assigned student identity to create/manage OKE, managed nodes, networking, and the workload's load balancer in the allocated compartment. Validate the required OKE/cloud-controller IAM policies; no Terraform module will create IAM resources here. Use [Oracle's policy guidance](https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengpolicyconfig.htm).
- Confirm the student can install add-ons and cluster-scoped Kubernetes resources required by the Helm charts. Check desktop CLI identity and kubeconfig authentication in every new terminal.
- Permit public API TCP 6443 from the desktop's egress CIDR and verify private worker image access through NAT. Do not apply the source lab's broad subnet-security mutation script to this new network.
- Ensure the Luna operator's session reclamation process covers resources the student creates. The new CI validates allocation and contains no teardown implementation. Verify that platform behavior before classroom use.

## Classroom pilot

- [ ] Start a fresh Luna session using only the new project; observe automatic allocation validation without an OKE cluster being created by CI.
- [ ] Confirm an unprotected/non-default Luna launch is refused and no secrets appear in logs or artifacts.
- [ ] Complete every Console step as the student: Quick Create, enhanced cluster, three private workers, public API, Cert Manager, and Metrics Server.
- [ ] Generate kubeconfig on the desktop, then pass `scripts/check-ready.sh` with three Ready workers and numeric metrics.
- [ ] Clone the pinned GitHub tag, download all five chart archives, and complete clean Helm installs. Distinguish fresh downloads/installs from cached runs.
- [ ] Confirm a public app response, both dashboard UIs, and manual 2→4→2 scaling with HPA disabled throughout. Record provisioning and exercise times.
- [ ] Rehearse optional HPA separately, including resetting an interrupted load burst, and optionally pod recovery.
- [ ] Run `scripts/validate-lab.sh` after deployment; static tests alone are insufficient.
- [ ] Verify GitLab security scanners actually run using runner-approved images. Record blocked/skipped scans explicitly.
- [ ] Confirm the new Luna platform's session lifecycle with the operator, including reclamation of student-created resources; complete the operator section of the [delivery readiness record](delivery-readiness.md).

Before hands-on, learners launch their allocated environment. They perform all cluster creation during step 1. No HPA resource or load burst is required for core completion. The completion sheet includes both cluster creation and application observations. Do not distribute operational logs or private files as learner materials.

## Repository boundaries

`charts/` and `helm/` are the learner application materials. `kubernetes/` remains a maintainer-only legacy render fixture and must not be applied to the Helm-managed lab. CI scripts validate student allocation and source quality. There is no image build step and no Terraform workflow.
