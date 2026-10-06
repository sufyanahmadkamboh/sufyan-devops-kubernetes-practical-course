# Problem 03 · ImagePullBackOff

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

A web server was deployed "with the usual nginx image", but it never starts. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-03
kubectl apply -f labs/12-troubleshooting/manifests/03-imagepull.yaml -n trouble-03
```

## Symptoms

<!-- test: anyof=ImagePullBackOff||ErrImagePull; retry=30; output -->
```bash
kubectl get pods -n trouble-03 | grep -E 'ImagePullBackOff|ErrImagePull'
```

```text
web-597f85f646-26k2z   0/1     ErrImagePull   0          2s
```

`ErrImagePull` (the attempt failed) then `ImagePullBackOff` (Kubernetes waits before trying again).

## First command to run

The events say which image was requested and what the registry answered:

<!-- test: contains=Failed to pull image; output -->
```bash
kubectl describe pod -n trouble-03 -l app=web | grep -m1 'Failed to pull image'
```

```text
  Warning  Failed     1s    kubelet            spec.containers{web}: Failed to pull image "nginx:1.30-alpne": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:1.30-alpne": failed to resolve reference "docker.io/library/nginx:1.30-alpne": docker.io/library/nginx:1.30-alpne: not found
```

## Investigation

*Which object is involved?* The kubelet tried to download the image named in the Pod spec, from the registry
(`docker.io/library/nginx`), and the registry said `not found`. Read the name carefully: `1.30-alpne`. Compare it with
a tag you know works:

<!-- test: contains=1.30-alpne -->
```bash
kubectl get deployment web -n trouble-03 -o jsonpath='image: {.spec.template.spec.containers[0].image}{"\n"}'
```

Other answers mean other causes: `pull access denied` / `unauthorized` (a private image without credentials,
`imagePullSecrets`), `429 Too Many Requests` (Docker Hub's rate limit), a timeout (no network from the node).

## Root cause

A typo in the tag: `alpne` instead of `alpine`. No such image exists, so the kubelet can never start the container.

## Fix

<!-- test: contains=successfully rolled out -->
```bash
kubectl set image deployment/web -n trouble-03 web=nginx:1.30-alpine
kubectl rollout status deployment/web -n trouble-03 --timeout=120s
```

## Verification

<!-- test: contains=Running -->
```bash
kubectl get pods -n trouble-03
```

## Lesson learned

- `ErrImagePull` / `ImagePullBackOff`: read the `Failed to pull image` event, it quotes the exact name and the
  registry's answer.
- `not found` = wrong name or tag; `unauthorized` = credentials; `429` = rate limit; timeout = network.
- Copy image references from a source that was tested; pin exact tags.

## Cleanup

🧹 Delete the namespace `trouble-03` and the web Deployment in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-03
```

Next: [Problem 04 · Container exits immediately](04-container-exits-immediately.md)
