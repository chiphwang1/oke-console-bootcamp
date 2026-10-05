#!/usr/bin/env bash
# Prepare local chart archives only. Never access or change a cluster.
set -euo pipefail

fail() {
  printf 'FAIL %s\n' "$*" >&2
  exit 1
}

if [[ $# != 1 || ( $1 != --download && $1 != --check ) ]]; then
  printf '%s\n' 'Usage: bash scripts/prepare-charts.sh --download | --check' >&2
  printf '%s\n' 'Use --download to fetch missing pinned charts, then --check to verify them without downloads. Neither installs releases.' >&2
  exit 1
fi
mode=$1
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
command -v helm >/dev/null 2>&1 || fail 'Helm is missing from this Bash PATH.'
# shellcheck disable=SC1091
source helm/versions.env
cache_dir="$repo_dir/.lab-cache/charts"

check_archive() {
  local archive=$1 expected_name=$2 expected_version=$3 metadata actual_name actual_version
  [[ -r "$archive" && -s "$archive" ]] || fail "Missing chart: $archive. Run bash scripts/prepare-charts.sh --download, then retry --check."
  metadata=$(helm show chart "$archive") || fail "Cannot read chart: $archive. Ask the instructor to inspect it; existing files are never replaced."
  actual_name=$(sed -n 's/^name: *//p' <<< "$metadata")
  actual_version=$(sed -n 's/^version: *//p' <<< "$metadata")
  [[ "$actual_name" == "$expected_name" && "$actual_version" == "$expected_version" ]] || \
    fail "Chart mismatch: expected $expected_name $expected_version in $archive. Ask the instructor; existing files are never replaced."
}

prepare_chart() {
  local name=$1 version=$2 repository=$3 archive staging
  archive="$cache_dir/$name-$version.tgz"
  if [[ ! -e "$archive" && "$mode" == --download ]]; then
    mkdir -p "$cache_dir"
    staging=$(mktemp -d "$cache_dir/.download.XXXXXX")
    printf 'Downloading %s %s\n' "$name" "$version"
    # Use a separate directory so a failed download cannot become a ready archive.
    # On failure retain that directory for diagnosis; never remove user files.
    helm pull "$name" --repo "$repository" --version "$version" --destination "$staging" || \
      fail "Download failed for $name. Check network access and retry --download; partial files remain in $staging."
    check_archive "$staging/$name-$version.tgz" "$name" "$version"
    mv -n "$staging/$name-$version.tgz" "$archive"
    rmdir "$staging" 2>/dev/null || true
  fi
  check_archive "$archive" "$name" "$version"
  printf 'PASS Prepared chart: %s %s\n' "$name" "$version"
}

prepare_chart base "$ISTIO_VERSION" https://blob.istio.io/istio-release/charts
prepare_chart istiod "$ISTIO_VERSION" https://blob.istio.io/istio-release/charts
prepare_chart prometheus "$PROMETHEUS_CHART_VERSION" https://prometheus-community.github.io/helm-charts
prepare_chart kiali-server "$KIALI_CHART_VERSION" https://kiali.org/helm-charts
prepare_chart grafana "$GRAFANA_CHART_VERSION" https://grafana-community.github.io/helm-charts
printf '%s\n' 'Chart archives match helm/versions.env. No releases were installed and no container images were pulled.'
