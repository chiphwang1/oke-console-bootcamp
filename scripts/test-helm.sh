#!/usr/bin/env bash
# Render charts only; never connect to a Kubernetes cluster.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
task_tmp=$(mktemp -d)
trap 'rm -rf -- "$task_tmp"' EXIT
export HELM_CACHE_HOME="$task_tmp/cache" HELM_CONFIG_HOME="$task_tmp/config" HELM_DATA_HOME="$task_tmp/data"
set -a
# shellcheck disable=SC1091
source helm/versions.env
set +a
helm lint charts/oke-mesh-app --kube-version 1.36.1 --strict
python3 scripts/tests/check_mesh_charts.py "$@"
