#!/usr/bin/env bash
set -euo pipefail

# Install only into this disposable CI job. Never print credentials.
dnf install -y curl unzip tar xz git python3 python3-pip openssl diffutils
mkdir -p /usr/local/bin
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT
cd "$task_tmp"
case "${1:-}" in
  helm)
    version=v3.19.0
    archive="helm-${version}-linux-amd64.tar.gz"
    curl -fLsS --retry 3 -O "https://get.helm.sh/$archive"
    curl -fLsS --retry 3 -o helm.sha256 "https://get.helm.sh/$archive.sha256sum"
    sha256sum -c helm.sha256
    tar -xf "$archive"
    install -m 755 linux-amd64/helm /usr/local/bin/helm
    helm version --short
    ;;
  kubectl)
    version=v1.36.1
    curl -fLsS --retry 3 -o kubectl "https://dl.k8s.io/release/$version/bin/linux/amd64/kubectl"
    curl -fLsS --retry 3 -o kubectl.sha256 "https://dl.k8s.io/release/$version/bin/linux/amd64/kubectl.sha256"
    printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum -c -
    install -m 755 kubectl /usr/local/bin/kubectl
    kubectl version --client
    ;;
  shellcheck)
    curl -fLsS --retry 3 -o shellcheck.tar.xz https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz
    tar -xf shellcheck.tar.xz
    install -m 755 shellcheck-v0.11.0/shellcheck /usr/local/bin/shellcheck
    shellcheck --version
    ;;
  oci)
    python3 -m venv /opt/oci-cli
    /opt/oci-cli/bin/pip install 'oci-cli==3.78.0'
    ln -sf /opt/oci-cli/bin/oci /usr/local/bin/oci
    oci --version
    ;;
  *) echo "Usage: $0 helm|kubectl|shellcheck|oci" >&2; exit 2 ;;
esac
