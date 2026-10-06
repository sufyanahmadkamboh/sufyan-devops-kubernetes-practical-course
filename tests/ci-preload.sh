#!/usr/bin/env bash
# ci-preload.sh: on a CI machine, start the course cluster and load the course's images into it from the host.
# The host pulls through a Docker Hub mirror (anonymous Docker Hub pulls are rate-limited on shared CI machines);
# `minikube image load` then copies the images into the node, so the lessons never pull them from Docker Hub.
set -euo pipefail
cd "$(dirname "$0")/.."

minikube start --driver=docker --cni=calico --cpus=2 --memory=4g
for image in nginx:1.30-alpine busybox:1.37 alpine:3.23 postgres:18-alpine golang:1.26-alpine; do
  docker pull -q "$image" > /dev/null
  minikube image load "$image"
  echo "loaded $image"
done
bash scripts/build-images.sh
