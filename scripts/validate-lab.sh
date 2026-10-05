#!/usr/bin/env bash
set -euo pipefail

namespace="oke-lab"
deployment="hello-oke"
kubectl=(kubectl --request-timeout=30s)

echo "Context:"
"${kubectl[@]}" config current-context
echo "Nodes:"
"${kubectl[@]}" wait --for=condition=Ready nodes --all --timeout=300s
"${kubectl[@]}" get nodes
echo
echo "Application:"
"${kubectl[@]}" -n "$namespace" rollout status "deployment/$deployment" --timeout=300s
"${kubectl[@]}" -n "$namespace" get pods -l app.kubernetes.io/name="$deployment"
echo
echo "Recent events:"
"${kubectl[@]}" -n "$namespace" get events --sort-by=.lastTimestamp | tail -n 12
echo
echo "Service endpoint:"
"${kubectl[@]}" -n "$namespace" wait --for=jsonpath='{.status.loadBalancer.ingress[0].ip}' \
  "service/$deployment" --timeout=600s
endpoint=$("${kubectl[@]}" -n "$namespace" get service "$deployment" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [[ -z "$endpoint" ]]; then
  echo "Load Balancer endpoint is not assigned yet." >&2
  exit 1
fi
# OCI can assign the address before its backends pass their health checks.
for attempt in {1..12}; do
  if curl --fail --silent --show-error --connect-timeout 5 --max-time 10 "http://$endpoint/"; then
    echo
    exit 0
  fi
  if (( attempt < 12 )); then
    sleep 5
  fi
done
echo "Load Balancer endpoint did not respond successfully within 12 attempts." >&2
exit 1
