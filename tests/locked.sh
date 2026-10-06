#!/usr/bin/env bash
# locked.sh COMMAND [ARG ...]: run a command against the course cluster while holding the test lock (tests/.lock).
#
# The test runner resets the cluster before and after every lesson file. Anything you try out by hand on the same
# cluster while a test run is going would be deleted under your feet (and could break that run), so experiments go
# through this script. It uses the same Minikube home as the tests and its own kubeconfig (tests/out/kubeconfig),
# never ~/.kube/config:
#
#   bash tests/locked.sh bash -c 'kubectl get nodes'
#
# A run that was killed can leave the lock behind: remove tests/.lock if no test run is going.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
lock="$root/tests/.lock"
until mkdir "$lock" 2> /dev/null; do
  echo "waiting for another test run to finish ($lock)" >&2
  sleep 10
done
trap 'rm -rf "$lock"' EXIT

if [ -d "$root/../.tools" ]; then tools=$(cd "$root/../.tools" && pwd); export PATH="$tools:$PATH"; fi
mkdir -p "$root/tests/out"
if pwd -W > /dev/null 2>&1; then
  : "${MINIKUBE_HOME:=$(cd "$root/.." && pwd -W)/.minikube-lab}"
  KUBECONFIG="$(cd "$root/tests/out" && pwd -W)/kubeconfig"
else
  : "${MINIKUBE_HOME:=$HOME/.minikube}"
  KUBECONFIG="$root/tests/out/kubeconfig"
fi
export MINIKUBE_HOME KUBECONFIG MSYS_NO_PATHCONV=1
minikube update-context > /dev/null 2>&1 || true
"$@"
