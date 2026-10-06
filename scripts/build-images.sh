#!/usr/bin/env bash
# build-images.sh: build the course application's images inside Minikube, so the cluster finds them without a
# registry. Run it once after `minikube start` (lesson 03), from the course folder:
#
#   bash scripts/build-images.sh
#
#   learning-app/backend:1.0.0   the backend, version 1.0.0
#   learning-app/backend:2.0.0   the same backend, version 2.0.0 (rolling updates, lesson 09)
set -euo pipefail
cd "$(dirname "$0")/.."

for version in 1.0.0 2.0.0; do
  if minikube image ls 2> /dev/null | grep -q "learning-app/backend:$version"; then
    echo "already built: learning-app/backend:$version"
  else
    minikube image build -t "learning-app/backend:$version" --build-opt="opt=build-arg:APP_VERSION=$version" apps/backend > /dev/null
    echo "built:         learning-app/backend:$version"
  fi
done
