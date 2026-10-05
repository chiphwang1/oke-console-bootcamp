# Lab architecture

Use this same diagram during the opening lecture and the [student walkthrough](../README.md). It includes the optional HPA extension: the core lab uses the requests and monitoring paths, while the autoscaling path applies only after enabling HPA in step 6. It shows logical relationships, not individual network hops or current cluster health. Each learner has a dedicated cluster with three worker nodes; the diagram shows one of several application pods. The paths share one cluster; they do not imply fixed node placement.

[View the architecture diagram](../README.md#architecture) and [completion sheet](completion-sheet.md).

Trace three paths:

1. **Requests:** the public LoadBalancer reaches application pods through the Service. The in-cluster traffic generator uses the Service directly, without the public LoadBalancer. Istio proxies observe requests to the app.
2. **Dashboards:** Prometheus scrapes request metrics from the proxies and control-plane metrics from Istiod. Kiali queries it for traffic relationships; Grafana queries it for history. Localhost port-forwards give your browser access to these internal dashboards.
3. **Optional autoscaling:** Metrics Server obtains resource usage from the kubelets. The HPA uses the `web` container's CPU utilization to change the Deployment's replica count; its ReplicaSet maintains those pods. This path does not use Prometheus and does not add worker nodes. In the core lab, students change the desired count manually using Helm instead.

The diagram is rendered as Mermaid by GitHub and GitLab. The descriptions above cover the same paths in text.

## Component ownership

| Component | Who provides it | Role |
|---|---|---|
| OKE, three workers, networking | Student through OCI Console | Runs the workloads; created during step 1 |
| Cert Manager and Metrics Server | Student enables OCI-managed add-ons in the Console | Cert Manager is a dependency of this Metrics Server add-on; Metrics Server supplies resource metrics |
| Istio base and Istiod | Student, using Helm | Register Istio object types and configure the workload proxies |
| Prometheus | Student, using Helm | Scrapes and stores mesh metrics |
| Kiali and Grafana | Student, using Helm | Query Prometheus; remain internal, with anonymous read-only lab access |
| App and traffic generator | Student, using the local Helm chart | Serve requests and produce baseline traffic |
| HPA | Student, optional extension in step 6 | Adjust app replicas using CPU metrics |
| OCI LoadBalancer | OCI, in response to the app's Service | Exposes the training app publicly; not the dashboards |

## Vocabulary for the lecture

| Term | Meaning in this lab |
|---|---|
| Worker node | A machine that runs pods; this lab has three workers even when app replicas change |
| Kubernetes control plane / Istiod | OKE-managed cluster coordination / the separate Istio control plane that configures proxies |
| Pod | A running unit containing the app and its Istio proxy |
| Deployment / ReplicaSet | Declares the desired app state / maintains the desired pod count |
| Desired state | The requested state Kubernetes works to maintain; you or the HPA can change the app's desired replica count |
| Service | Gives selected pods a stable address as pods change |
| Namespace | Groups related resources, such as `oke-lab` |
| Helm chart / release | A package of Kubernetes templates / a named installation of that package |
| Readiness / liveness | Whether a container can accept traffic / whether it needs restarting |
| HPA | Horizontal Pod Autoscaler; adjusts application replicas from metrics |

Use only training data: the app is public and unauthenticated. Dashboard access is restricted to the cluster and localhost forwards, but anonymous access is still unsuitable for sensitive production data. Metrics are ephemeral; copy your observations before ending the session.
