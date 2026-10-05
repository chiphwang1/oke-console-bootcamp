# Create your OKE cluster in the OCI Console

This is a required exercise in [step 1](../README.md#1-create-your-cluster-and-confirm-your-connection--4070-minutes). Allow 30–60 minutes, including provisioning and add-on waits. Luna supplies your student environment; you initiate cluster creation yourself.

## Check your allocation

1. Open **Luna-Lab → Quick Links → OCI Console** and sign in with the assigned temporary account.
2. Match the Console region and compartment to **Lab Details**. Use your allocated compartment throughout the exercise.
3. Confirm the instructor has checked permissions to create OKE clusters, node pools, compute, network resources, and load balancers, and that your identity can install cluster-wide Helm resources. The allocation CI job checks read access; it cannot prove these create permissions.
4. Confirm the desktop has OCI CLI, kubectl, Helm, Git, and curl. Desktop CLI authentication must use your session's OCI profile. The Console login alone does not configure the terminal.

The instructor must reserve capacity for three workers, their boot volumes, one enhanced cluster, networking, and one flexible load balancer at 10 Mbps. This lab uses x86 images. Regional shape and Kubernetes availability must be rehearsed in the allocated region. See [Oracle's cluster creation permissions](https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengpolicyconfig.htm).

## Create the cluster and network

1. Open **Developer Services → Containers & Artifacts → Kubernetes Clusters (OKE)**, and select your assigned compartment.
2. Select **Create cluster → Quick create → Proceed**. Quick Create creates the network resources with the cluster. [Oracle Quick Create reference](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengcreatingclusterusingoke_topic-Using_the_Console_to_create_a_Quick_Cluster_with_Default_Settings.htm).
3. Enter the lab settings below. If an option is unavailable, ask the instructor before substituting it.

| Setting | Lab value |
|---|---|
| Name | `oke-console-lab` in your own allocated compartment |
| Compartment | The exact compartment shown in Luna Lab Details |
| Kubernetes version | The instructor's rehearsed stable **1.36** version; select a supported patch in that minor if shown |
| Kubernetes API endpoint | **Public endpoint** |
| Node type | **Managed** |
| Kubernetes worker nodes | **Private workers** |
| Node shape | **VM.Standard.E5.Flex**, if available with the allocated quota |
| OCPUs per node | **1** |
| Memory per node | **16 GB** |
| Image | An **OKE Worker Node Image**, x86, matching the selected Kubernetes version |
| Node count | **3** |
| Boot volume | Keep the selected image's default size and Oracle-managed encryption |
| SSH key | Leave unset; this lab uses Kubernetes access rather than node SSH |

The inherited chart/preflight compatibility range is Kubernetes **1.32–1.36**. If 1.36 is unavailable, the instructor must select and rehearse another minor within that range, update `LAB_KUBERNETES_MINOR` in the new GitLab project, and confirm the desktop kubectl is within one server minor version. A shape being listed does not guarantee available capacity.

4. Select **Next** and review the compartment, node count, and machine sizes. Keep the cluster type **Enhanced**; do not switch to Basic. Enhanced clusters support managed add-on configuration. [Oracle cluster types](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengcreatingenhancedclusters.htm).
5. Select **Create cluster**. Record the name and inspect the work requests. Wait for the cluster to become **Active**, then open its node pool and confirm all three nodes are **Active**. Work-request errors need instructor help; avoid submitting another cluster while the first request is unresolved.

## Inspect what you created

From the cluster/network details, locate the generated VCN, API subnet, worker subnet, load-balancer subnet, routes, and gateways. Quick Create assigns generated names; keep them. The API and load-balancer subnets are public; the worker subnet is private. Private workers need outbound access for images and services, using the generated NAT route. [Oracle networking requirements](https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengnetworkconfig.htm).

Inspect the API subnet's security rules: TCP **6443** must be reachable from the Luna desktop's public egress address. Have the instructor verify the source CIDR against the classroom access policy. A public API still requires OCI authentication and Kubernetes permissions; private workers do not gain public IPs because the API is public.

**Checkpoint:** identify the API subnet, worker subnet, and load-balancer subnet. Explain which component will create the app's load balancer later.

## Enable resource metrics

The app's optional HPA and the required `kubectl top nodes` check need Metrics Server. Prometheus is installed later for application dashboards.

1. Open the enhanced cluster's **Add-ons** tab and select **Manage add-ons**.
2. Edit **Cert Manager**, enable it, choose **Automatic updates**, and save. Wait for its work request to succeed.
3. Return to **Manage add-ons**, edit **Kubernetes Metrics Server**, enable it with **Automatic updates**, and save. Wait for completion.
4. Leave the essential networking/DNS add-ons enabled. Keep the optional managed Istio add-on disabled: the next exercise installs the lab's pinned Istio charts.

OCI's Metrics Server add-on depends on Cert Manager. See [the Metrics Server dependency](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengworkingwithmetricsserver_cluster-add-on.htm) and [Console add-on installation](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/install-add-on.htm).

Return to [configure access](../README.md#open-your-cluster-and-configure-access), generate kubeconfig, and run the read-only preflight. Continue only when all three workers are Ready and have numeric CPU/memory metrics. An Active OCI status alone does not prove Kubernetes readiness.
