#!/usr/bin/env bash
# Read-only preflight for the three-worker student lab. Never select a context,
# install software, retrieve secrets, or change Kubernetes/OCI resources.
set -euo pipefail

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'PASS %s\n' "$*"
}

usage() {
  printf '%s\n' 'Usage: bash scripts/check-ready.sh'
  printf '%s\n' 'Run from the repository root with the assigned kubeconfig/OCI environment. The current kubeconfig context is checked.'
}

if [[ ${1:-} == --help && $# == 1 ]]; then
  usage
  exit 0
fi
if [[ $# != 0 ]]; then
  usage >&2
  fail 'This check uses the current kubeconfig context; do not supply a context argument.'
fi

for lab_file in README.md charts/oke-mesh-app/Chart.yaml helm/versions.env \
  helm/values/student.yaml helm/values/istiod.yaml helm/values/prometheus.yaml \
  helm/values/kiali.yaml helm/values/grafana.yaml helm/dashboards/oke-lab.json; do
  [[ -r "$lab_file" ]] || fail "Repository files: missing $lab_file. Run from the checkout root (README.md, charts/, helm/, scripts/); ask for complete files if needed."
done
pass 'Repository files and working directory'

for tool in oci kubectl helm git curl; do
  command -v "$tool" >/dev/null 2>&1 || fail "Tools: $tool is missing from this Bash PATH. Ask the instructor; do not run the CI installer on the desktop."
done
pass 'Tools found: oci, kubectl, helm, git, curl'

# Match kubectl's default and colon-separated KUBECONFIG behavior, while
# explicitly rejecting unreadable named files instead of silently skipping them.
IFS=: read -r -a kube_files <<< "${KUBECONFIG:-${HOME}/.kube/config}"
for kube_file in "${kube_files[@]}"; do
  [[ -z "$kube_file" ]] && continue
  [[ -f "$kube_file" && -r "$kube_file" && -s "$kube_file" ]] || \
    fail "Kubeconfig: $kube_file is missing, unreadable, or empty. See docs/cluster-access.md; changing directories will not fix the connection."
done
if ! current_context=$(kubectl config current-context 2>/dev/null); then
  fail 'Context: no usable current context. See docs/cluster-access.md.'
fi
pass "Selected context: $current_context"

# Pin every subsequent call to the checked context, even if another terminal
# changes current-context during this check. Suppress raw auth output/tokens.
kube=(kubectl --context "$current_context" --request-timeout=15s)
if ! client_json=$("${kube[@]}" version --client -o json 2>/dev/null); then
  fail 'kubectl: cannot read the client version. Check command -v kubectl in this Bash terminal.'
fi
if ! server_json=$("${kube[@]}" get --raw=/version 2>/dev/null); then
  fail 'Cluster API: connection/authentication failed. Check the assigned kubeconfig, OCI profile/environment, and network with the instructor; see docs/cluster-access.md.'
fi
pass 'Cluster API reachable with the selected authentication'

version_pattern='"gitVersion"[[:space:]]*:[[:space:]]*"v([0-9]+)\.([0-9]+)\.[^"]+"'
[[ "$client_json" =~ $version_pattern ]] || fail 'kubectl: unrecognized client version output.'
client_major=$((10#${BASH_REMATCH[1]}))
client_minor=$((10#${BASH_REMATCH[2]}))
[[ "$server_json" =~ $version_pattern ]] || fail 'Cluster API: unrecognized server version output.'
server_major=$((10#${BASH_REMATCH[1]}))
server_minor=$((10#${BASH_REMATCH[2]}))
skew=$((client_minor - server_minor))
((client_major == server_major && skew >= -1 && skew <= 1)) || \
  fail "Version skew: kubectl $client_major.$client_minor, server $server_major.$server_minor. Ask the instructor for a client within one server minor version."

# Keep this range in sync when changing the Istio pin. See the instructor guide
# and https://istio.io/latest/docs/releases/supported-releases/.
pinned_istio=$(sed -n 's/^ISTIO_VERSION=//p' helm/versions.env)
[[ "$pinned_istio" == 1.31.* ]] || fail 'Istio pin changed: instructor must review/update this compatibility check before class.'
((server_major == 1 && server_minor >= 32 && server_minor <= 36)) || \
  fail "Istio $pinned_istio: this lab expects Kubernetes 1.32-1.36, found $server_major.$server_minor. Ask the instructor; do not replace the cluster."
pass "Versions: kubectl $client_major.$client_minor, server $server_major.$server_minor, Istio $pinned_istio"

if ! node_rows=$("${kube[@]}" get nodes -o 'jsonpath={range .items[*]}{.metadata.name}{" "}{.status.conditions[?(@.type=="Ready")].status}{" "}{.spec.unschedulable}{"\n"}{end}' 2>/dev/null); then
  fail 'Nodes: cannot list workers. Ask the instructor to check provisioning and permissions.'
fi
node_count=0
while read -r node ready unschedulable; do
  [[ -z "$node" ]] && continue
  node_count=$((node_count + 1))
  [[ "$ready" == True && "$unschedulable" != true ]] || \
    fail "Nodes: $node is not Ready or is cordoned. Ask the instructor; do not uncordon or resize the pool."
done <<< "$node_rows"
[[ "$node_count" == 3 ]] || fail "Nodes: expected the assigned lab's three workers, found $node_count. Ask the instructor to verify provisioning and the assignment."
pass 'Workers: 3/3 Ready and not cordoned'

if ! metrics=$("${kube[@]}" top nodes --no-headers 2>/dev/null); then
  fail 'Resource metrics: unavailable. Ask the instructor to check Metrics Server; Prometheus is not its replacement.'
fi
while read -r node _; do
  [[ -z "$node" ]] && continue
  if ! awk -v wanted="$node" '
    $1 == wanted && $2 ~ /^[0-9]+m?$/ && $4 ~ /^[0-9]+(Ki|Mi|Gi|Ti|Pi|Ei)?$/ { found++ }
    END { exit(found == 1 ? 0 : 1) }
  ' <<< "$metrics"; then
    fail "Resource metrics: missing/non-numeric CPU or memory for $node. Wait briefly, rerun once, then ask the instructor."
  fi
done <<< "$node_rows"
pass 'Resource metrics: numeric CPU and memory for all three workers'
printf '%s\n' "$metrics"
printf '\n%s\n' 'Preflight passed. Complete the chart downloads, archive checks, and connection confirmation in README step 1, then continue to step 2.'
printf '%s\n' 'No context, kubeconfig, or cluster resources were changed. OCI authentication may use its normal local cache.'
