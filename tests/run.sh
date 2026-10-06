#!/usr/bin/env bash
# Run lessons exactly as a learner types them, but in a sandbox:
#   * a fresh HOME and a separate kubeconfig (your ~/.kube/config and its contexts are never read or written)
#   * one Minikube cluster for the whole course, kept between runs in MINIKUBE_HOME (default: ../.minikube-lab next
#     to the course on Windows, ~/.minikube elsewhere), started with the course's settings if it is not running
#   * every lesson file starts and ends with a clean cluster (tests/mdrun.py, cluster_reset)
#   * one run at a time: the cluster is shared, so a second run waits for the first one (tests/.lock)
#
#   bash tests/run.sh [--update] [--record DIR] FILE.md [FILE.md ...]
#   MINIKUBE_START_FLAGS="--registry-mirror=https://mirror.gcr.io" bash tests/run.sh ...    (extra flags, CI)
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
py=python3
command -v python3 > /dev/null 2>&1 && python3 -c "" > /dev/null 2>&1 || py=python
windows=false
pwd -W > /dev/null 2>&1 && windows=true

lock="$root/tests/.lock"
until mkdir "$lock" 2> /dev/null; do
  echo "waiting for another test run to finish ($lock)" >&2
  sleep 10
done
trap 'rm -rf "$lock"' EXIT

# pinned tools (kubectl, minikube, helm) next to the course win over anything else on PATH
if [ -d "$root/../.tools" ]; then tools=$(cd "$root/../.tools" && pwd); export PATH="$tools:$PATH"; fi

mkdir -p "$root/tests/out"
lab_home=$(mktemp -d "$root/tests/out/home.XXXXXX")
if $windows; then
  masked=$(cd "$lab_home" && pwd -W)
  : "${MINIKUBE_HOME:=$(cd "$root/.." && pwd -W)/.minikube-lab}"
else
  masked=$lab_home
  : "${MINIKUBE_HOME:=$HOME/.minikube}"
fi
export MINIKUBE_HOME
export HOME="$lab_home" MDRUN_HOME="$masked" MDRUN_HOME_POSIX="posix:$lab_home"
mkdir -p "$lab_home/.kube"
export KUBECONFIG="$masked/.kube/config"          # a C:/ path on Windows: kubectl.exe does not understand /c/...
export NO_COLOR=1 MINIKUBE_IN_STYLE=false        # (tests/mdrun.py sets MSYS_NO_PATHCONV for the lesson commands)

# the course cluster: running, with the course's settings (lesson 03 explains every flag)
if minikube status --format '{{.APIServer}}' 2> /dev/null | grep -q Running; then
  minikube update-context > /dev/null
else
  # shellcheck disable=SC2086
  minikube start --driver=docker --cni=calico --cpus=2 --memory=4g ${MINIKUBE_START_FLAGS:-} > "$lab_home/minikube-start.log" 2>&1 ||
    { cat "$lab_home/minikube-start.log"; exit 1; }
fi
kubectl wait --for=condition=Ready nodes --all --timeout=180s > /dev/null

# the lessons run from a copy of the course (without .git, videos and earlier test output)
work="$lab_home/kubernetes-practical-course"
mkdir -p "$work"
(cd "$root" && tar --exclude=./.git --exclude=./video --exclude=./tests/out --exclude=./tests/.lock -cf - .) | tar -xf - -C "$work"
export MDRUN_CWD="posix:$work"

status=0
"$py" "$root/tests/mdrun.py" "$@" || status=$?
rm -rf "$lab_home"
exit $status
