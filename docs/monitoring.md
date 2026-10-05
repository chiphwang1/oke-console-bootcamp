# Observe the application with Kiali and Grafana

Complete steps 1–4 of the [student walkthrough](../README.md) first: Istio, Prometheus, Kiali, Grafana, and the Helm application must be installed, with traffic enabled. After cluster creation, the application exercises take approximately 45 minutes; reserve five more minutes for debrief and delays. HPA is optional and stays disabled in the core. This page provides reference commands and deeper checks; direct Prometheus exploration, controlled outages, and OCI exercises require additional time. Use the Luna desktop and your dedicated lab kubeconfig.

## Traffic and health

1. Open Kiali through the localhost port-forward in the walkthrough.
2. Select `oke-lab`, a recent time range, and automatic refresh.
3. Find the `hello-oke-traffic` client and `hello-oke` service/workload. Observe HTTP request volume, success rate, and latency; graph names/grouping vary with the selected view.
4. Open the workload details and inspect its replicas and proxy status. This lab supplies metrics, not distributed tracing. Compare the traffic graph with the provisioned Grafana dashboard below.

If a health indicator shows Degraded or Not Ready, inspect its details before drawing a conclusion. Follow [Kiali health and probe troubleshooting](troubleshooting.md#kiali-shows-degraded-or-not-ready) to distinguish readiness, container restarts, and request errors. The scaling step in the walkthrough explains readiness versus liveness; a warning is not guaranteed during a healthy rollout.

## Grafana dashboard

Grafana is installed in step 2 of the main walkthrough and opened in step 4. It reads the existing Prometheus instance; it requests no additional node, load balancer, or persistent volume. If already installed, skip the Helm command below and open the port-forward. To reproduce or update the installation, run from the repository root with the lab kubeconfig selected:

```bash
source helm/versions.env
bash scripts/prepare-charts.sh --check
helm upgrade --install grafana ".lab-cache/charts/grafana-${GRAFANA_CHART_VERSION}.tgz" \
  --namespace istio-system \
  -f helm/values/grafana.yaml \
  --set-file dashboards.default.oke-lab.json=helm/dashboards/oke-lab.json \
  --wait --timeout 10m
kubectl -n istio-system port-forward --address 127.0.0.1 svc/grafana 13000:80
```

Open **http://127.0.0.1:13000/d/oke-lab** on the same workstation. The **OKE Lab — Traffic & Scaling** dashboard refreshes every 15 seconds and shows request rate, success rate, latency, response codes, application proxy count, and Istiod scrape health. Use a 30-minute time range to see the load test and scale-in together. No login is required for Viewer access. This setting is only for the disposable lab: the Service is reachable within the cluster, so never expose it using a public LoadBalancer, Ingress, or `--address 0.0.0.0`.

The dashboard is provisioned from `helm/dashboards/oke-lab.json`; do not edit a temporary UI copy. Grafana storage is ephemeral, and Prometheus retains only two hours of metrics (lost earlier if its pod is replaced). Proxy count is an observation of successful scrapes, **not** pod readiness or an HPA desired/current replica metric. In the core, compare it with `kubectl -n oke-lab get pods -l app=hello-oke`. Only inspect HPA after enabling it in the optional extension.

The four summary cards use instant queries evaluated at the end of the selected time range. Keep that range ending at **now**. Graphs retain range queries for history. Missing or undefined results display **No data**, rather than an earlier non-null value from the graph window. Scrape and rate windows still introduce delay; an instant query is not a live readiness test. See [Grafana query types](https://grafana.com/docs/grafana/latest/datasources/prometheus/query-editor/#type).

Ignore the chart's generic administrator-login instructions; the lab uses anonymous Viewer access. Grafana's revised memory request/limit are 512Mi/1Gi, with a `512MiB` soft Go runtime target to leave process headroom. If browser access repeatedly fails, inspect [restart and memory evidence](troubleshooting.md#grafana-memory-and-repeated-restarts) rather than repeatedly opening new forwards.

## Core: compare baseline and manual scaling

Use the completion sheet's core table to record Ready app pods and Grafana readings at two replicas, four replicas, and after restoring two. Baseline requests continue at the same interval; additional replicas do not create additional demand. Your manual curl requests can briefly increase the request rate. Compare proxy count with actual Ready pods and explain any discovery delay. Do not require a particular latency improvement under this low load.

Complete the core debrief without enabling HPA. The following HPA, Prometheus, outage, and OCI exercises are optional.

## Optional: compare HPA baseline, load, and recovery

During optional step 6, record Grafana request rate, latency, success rate, and proxy count before load, during `/work` traffic, and after returning to baseline. Compare with Kiali's traffic graph and the actual HPA replica count. Use `kubectl -n oke-lab top pods --containers` and `kubectl -n oke-lab describe hpa hello-oke` for CPU and scaling evidence; neither dashboard is the HPA's metric source.

Use the optional HPA observation table on the [completion sheet](completion-sheet.md), and record the same latency statistic (p95) each time. Baseline requests call `/`, while the burst calls `/work`, which performs CPU-intensive calculations. The generator maintains two concurrent streams rather than a fixed request rate. Heavier requests need not increase requests per second; use app CPU to explain the HPA response. Explain changes in workload and replicas together; comparing those phases alone does not isolate autoscaling's effect on latency. If a panel has no data, record that instead of zero.

Deleting one pod during Recover tests the Deployment controller's self-healing. It does not guarantee a visible outage: other replicas can continue serving requests. Use the optional exercise below only if you want to see a deliberate complete loss of application endpoints.

## Optional: Prometheus browser checks and repeatable load

With the lab kubeconfig selected, open a second localhost-only port-forward:

```bash
kubectl -n istio-system port-forward --address 127.0.0.1 svc/prometheus-server 19090:80
```

Open `http://127.0.0.1:19090`. In Query, execute each expression and select Graph with a 15-minute range:

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="oke-lab",destination_workload="hello-oke"}[1m]))
```

```promql
count(up{job="istio-workloads",namespace="oke-lab",pod=~"hello-oke-[a-f0-9]+-.*"} == 1)
```

The first graph shows inbound requests/second. The second counts successfully scraped application proxies, excluding the traffic generator. It is a useful scaling visualization, not a readiness or HPA metric: scrape discovery can lag pod changes. This lightweight Prometheus configuration does not install kube-state-metrics; use `kubectl -n oke-lab get hpa hello-oke` and `kubectl -n oke-lab describe hpa hello-oke` for HPA replica status and CPU utilization after enabling it. The HPA uses Metrics Server, not Prometheus.

For scrape health, use Table with `up{job=~"istiod|istio-workloads"}`; current targets should return `1`. In Kiali, check Mesh for the control plane, Workloads → `hello-oke` for health and pods, and its Envoy tab for service routing configuration. A warning during scale-out may clear after readiness and traffic recover; inspect its details rather than assuming every Degraded badge is a readiness issue.

Reuse the chart's built-in, two-worker load generator for a bounded five-minute burst:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values \
  --set autoscaling.enabled=true --set traffic.enabled=true \
  --set traffic.loadEnabled=true --set traffic.durationSeconds=300 \
  --set traffic.concurrency=2 --wait --timeout 10m
kubectl -n oke-lab get hpa hello-oke --watch
```

Watch Kiali traffic and the Grafana dashboard (or the direct Prometheus graphs above) while replicas increase. After the generator logs `CPU load finished; returning to baseline traffic.`, reset the burst flag so a later pod restart cannot trigger another burst:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app -n oke-lab --reuse-values \
  --set traffic.loadEnabled=false --wait --timeout 10m
kubectl -n oke-lab get hpa,deploy
```

Allow several minutes for CPU metrics and stabilization before expecting two replicas again. To repeat, start only after the previous burst is disabled and scale-in completes. Leave the namespace filter at `oke-lab`; unrelated system workloads are outside this exercise.

## Optional: controlled outage and recovery

Only do this in your own disposable lab cluster, while baseline traffic is running. Disable the HPA first so it does not undo your manual scaling:

```bash
helm upgrade hello-oke ./charts/oke-mesh-app --namespace oke-lab \
  --reuse-values --set autoscaling.enabled=false --set replicaCount=2 \
  --set traffic.loadEnabled=false --wait --timeout 10m
kubectl -n oke-lab scale deployment/hello-oke --replicas=0
kubectl -n oke-lab logs deployment/hello-oke-traffic -c traffic --tail=10
# Wait 30–60 seconds, observe failed requests in Kiali, then restore promptly:
kubectl -n oke-lab scale deployment/hello-oke --replicas=2
kubectl -n oke-lab rollout status deployment/hello-oke --timeout=300s
```

The client's proxy should record failures while the service has no ready endpoints. After restoring the app, new requests should succeed. A five-minute graph still includes older errors until they age out; do not confuse historical errors with a continuing outage. Helm's desired replica count remains two; the HPA stays disabled unless you explicitly enable it using optional step 6 of the walkthrough.

## Kubernetes evidence

Start with Kubernetes, which gives immediate state and application evidence:

```bash
kubectl get nodes
kubectl -n oke-lab get deploy,pods,svc
kubectl top nodes
kubectl -n oke-lab top pods
kubectl -n oke-lab logs deployment/hello-oke -c web --tail=50
kubectl -n oke-lab logs deployment/hello-oke -c istio-proxy --tail=50
kubectl -n oke-lab get events --sort-by=.lastTimestamp
```

Expected: all nodes are `Ready`, the Deployment's ready replicas match its desired count (two at baseline, more during scaling), each app pod has its injected proxy, and the Service has an external IP. `kubectl top` needs Metrics Server; its absence does not mean Istio/Prometheus is broken. Use `web` logs for application requests and `istio-proxy` logs for mesh access logs. Health probes are omitted from application logs.

## Optional: OCI dashboard (instructor-enabled)

This is separate from Kiali. Only continue if the instructor has enabled the required telemetry and permissions. Open **Observability & Management → Monitoring → Metrics Explorer** and build a dashboard with available Container Engine / Container Insights metrics:

| Signal | Why it matters | Suggested alarm |
|---|---|---|
| Unhealthy nodes | Detects loss of compute capacity | Any unhealthy node for 5 minutes |
| Node CPU/memory | Detects saturation | Above 80% for 10 minutes |
| Pod restarts | Detects crashes or failed probes | More than 3 in 10 minutes |
| Ready vs desired replicas | Detects failed rollout | Ready below desired for 5 minutes |
| LB backend health | Measures user reachability | Healthy backends below expected |

Metric names and dimensions differ by OKE version, region, and enabled services. Select them from Metrics Explorer rather than copying values from another tenancy. Set log retention deliberately: telemetry creates cost and can contain sensitive output.

## Logs

```bash
kubectl -n oke-lab logs deployment/hello-oke -c istio-proxy --since=15m
```

For OCI-collected workload logs, use **Logging → Log Search**, then filter to the cluster, `oke-lab` namespace, and `hello-oke` workload. Make one `curl` request and correlate it to its log record.

## Optional: OCI alarm test

1. Create an OCI Monitoring alarm on pod readiness or Load Balancer backend health, routed to a test Notifications topic.
2. Record its normal `OK` state.
3. Disable the HPA and burst load as shown above, then cause a temporary, reversible outage:

   ```bash
   kubectl -n oke-lab scale deployment/hello-oke --replicas=0
   ```

4. Verify zero ready replicas and wait for the evaluation window.
5. Restore immediately:

   ```bash
   kubectl -n oke-lab scale deployment/hello-oke --replicas=2
   kubectl -n oke-lab rollout status deployment/hello-oke
   ```

6. Confirm the alarm returns to `OK`, then remove test alerting resources when finished.

Optional OCI alarm/notification resources are outside the core lab; agree their lifecycle with the instructor before creating them.
