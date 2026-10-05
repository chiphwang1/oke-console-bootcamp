# OKE lab completion sheet

Record the cluster creation and application exercises below.

Copy this sheet into your own notes. Fill it during the existing [lab checkpoints](../README.md), not as an extra exercise. Complete the core sections; HPA and pod recovery are optional. Keep credentials, kubeconfig contents, and tokens out of your notes.

Name: __________  Date: __________  Tested repository revision: __________

## Cluster creation

- [ ] I created an enhanced OKE cluster in my allocated compartment and region.
- [ ] I selected a public API endpoint, two private managed workers, and inspected the generated VCN/subnets.
- [ ] I enabled Cert Manager, then Kubernetes Metrics Server.

Cluster name: __________  Region: __________  Kubernetes version: __________

Worker shape / OCPUs / memory per node: __________

Explain why the public API endpoint does not make private worker nodes public: __________

## Core checkpoints

- [ ] Preflight passed for my cluster's current context; two workers are Ready with numeric resource metrics.
- [ ] My public app returned my customized message; two app pods showed `2/2` Ready.
- [ ] I identified `web` and `istio-proxy` and found `hello-oke-traffic → hello-oke` in Kiali.
- [ ] Manual scaling changed app replicas 2 → 4 → 2; worker count and Service IP stayed unchanged.

My customized response message: __________

## Core observations

Use Grafana's **Last 30 minutes** range and p95 latency for each row. Use `kubectl -n oke-lab get pods -l app=hello-oke` for Ready app pods. Proxy count can lag and does not measure readiness. Record `no data` for an empty panel. HPA stays disabled in the core lab.

| Phase | Ready app pods | Requests/s | Success % | p95 latency (ms) | App proxies up |
|---|---|---|---|---|---|
| Baseline (2 replicas) | ___ | ___ | ___ | ___ | ___ |
| Manual (4 replicas) | ___ | ___ | ___ | ___ | ___ |
| Restored (2 replicas) | ___ | ___ | ___ | ___ | ___ |

The baseline generator keeps the same request interval during manual scaling; more replicas do not create more traffic. Your manual curl requests may briefly increase the observed rate.

## Optional HPA observations

HPA extension: skipped / completed / blocked. Leave this section blank if skipped; it is not required for core completion. Run `kubectl -n oke-lab get hpa hello-oke` only after enabling HPA in step 6.

- [ ] HPA CPU utilization became numeric before load.
- [ ] I observed scale-out above two and scale-in back to two Ready app pods.
- [ ] I explicitly reset `traffic.loadEnabled=false`, even if the extension was interrupted.

| Phase | HPA replicas / Ready app pods | Requests/s | Success % | p95 latency (ms) | App proxies up |
|---|---|---|---|---|---|
| HPA baseline (`/`) | ___ / ___ | ___ | ___ | ___ | ___ |
| During load (`/work`) | ___ / ___ | ___ | ___ | ___ | ___ |
| After scale-in (`/`) | ___ / ___ | ___ | ___ | ___ | ___ |

Peak HPA replica count observed: ___  Time load started: ___  Time scale-in finished: ___

Six replicas is a limit, not a required peak. The two endpoints do different work; this comparison does not isolate autoscaling's effect on latency.

## Core debrief

1. Which Kubernetes object keeps the application reachable as pods change?
2. Which component supplies Kiali and Grafana with data? Explain one dashboard reading.

My evidence (question 2): Dashboard metric/value: __________  Source: __________

3. What changed during scaling: app replicas, worker nodes, Service IP?

My evidence (question 3): App pods before/during/after: ____ / ____ / ____

Worker names: ____________________  Service IP before/after: ____________________

4. Which probe removes an unready pod from normal Service traffic, and which can restart a container? Can a pod be Running but not Ready, with zero restarts?

## Optional HPA debrief

HPA metrics: CPU source: __________  Why is Grafana outside the scaling control loop? __________

HPA scale-in: Final HPA replicas: ____  Ready app pods: ____  Why can proxy count lag? __________

CPU prediction: a `200m` CPU request with a 60% HPA target corresponds to ___ CPU usage.

## Optional pod recovery

Pod recovery: skipped / completed / blocked. HPA is not a prerequisite.

Recovery evidence: Old/new pod names: ____________________  Service IP changed? __________

## Finish

Core result: completed / needs instructor help / demonstration only. Skipped extensions do not affect this result.

If blocked, record the step, symptom, and last observed state: __________

Reset any HPA burst before leaving. Stop watches and port-forwards; these do not stop in-cluster traffic. Report blocked checkpoints to the instructor.
