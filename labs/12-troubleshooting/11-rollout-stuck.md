# Problem 11 · Deployment rollout stuck

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

Version 3.0.0 of the backend was released this afternoon. The deploy step has been "waiting for rollout" ever since.
Set up the running version, then the release:

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace trouble-11
kubectl apply -f labs/12-troubleshooting/manifests/11-rollout.yaml -n trouble-11
kubectl rollout status deployment/backend -n trouble-11 --timeout=120s
kubectl set image deployment/backend -n trouble-11 backend=learning-app/backend:3.0.0
```

## Symptoms

<!-- test: fail; contains=timed out; output -->
```bash
kubectl rollout status deployment/backend -n trouble-11 --timeout=30s 2>&1
```

```text
Waiting for deployment "backend" rollout to finish: 1 out of 3 new replicas have been updated...
error: timed out waiting for the condition
```

## First command to run

<!-- test: contains=backend; output -->
```bash
kubectl get pods -n trouble-11 -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,READY:.status.containerStatuses[0].ready,REASON:.status.containerStatuses[0].state.waiting.reason
```

```text
NAME                       IMAGE                        READY   REASON
backend-6fc7cbfff9-f7z2f   learning-app/backend:1.0.0   true    <none>
backend-6fc7cbfff9-hdxvk   learning-app/backend:1.0.0   true    <none>
backend-6fc7cbfff9-vqbfq   learning-app/backend:1.0.0   true    <none>
backend-7c96cd4d65-9gzpz   learning-app/backend:3.0.0   false   ImagePullBackOff
```

## Investigation

The rolling update started one Pod with the new version, and that Pod cannot pull its image. The Deployment waits for
it to become ready before replacing more old Pods, so the three old Pods keep serving: **no outage**, just a rollout
that never finishes. Why can the new image not be pulled?

<!-- test: contains=3.0.0; retry=20 -->
```bash
kubectl get events -n trouble-11 --field-selector reason=Failed -o custom-columns=MESSAGE:.message | grep -m1 '3.0.0'
minikube image ls | grep learning-app/backend
```

The cluster only has `1.0.0` and `2.0.0`; there is no `3.0.0` locally or in any registry.

## Root cause

The release references an image that was never built. The rolling update protects the users (old Pods stay), but the
rollout stays stuck until someone acts.

## Fix

Go back to the last working version (lesson 09), then deal with the release:

<!-- test: contains=successfully rolled out -->
```bash
kubectl rollout undo deployment/backend -n trouble-11
kubectl rollout status deployment/backend -n trouble-11 --timeout=120s
```

## Verification

<!-- test: contains=learning-app/backend:1.0.0; absent=3.0.0; retry=20 -->
```bash
kubectl get pods -n trouble-11 -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
kubectl rollout history deployment/backend -n trouble-11
```

## Lesson learned

- A stuck rollout = a new Pod that never becomes ready; look at the **new** Pods, not the old ones.
- Rolling updates keep the old version serving while the new one fails: users are fine, the deploy is not.
- `kubectl rollout undo` is the fast, safe way back; set `progressDeadlineSeconds` so a stuck rollout is reported.

## Cleanup

🧹 Delete the namespace `trouble-11`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-11
```

Next: [Problem 12 · Pod OOMKilled](12-oomkilled.md)
