# Beginner challenge 04 · Release, notice, roll back

> After lesson 09 · ⏱ 20 minutes · run every command from the course folder · cluster: minikube

## Task

Run the course backend `learning-app/backend:1.0.0` as a Deployment `orders` (2 replicas) in `challenge-04`, release
version `2.0.0`, then pretend 2.0.0 has a bug and go back to **exactly** revision 1, not just "the previous one".

## Requirements

- Each release has a change cause in the history.
- The rollback names the revision explicitly.
- At the end the Pods run `1.0.0`; explain the revision numbers you see in the history.

## Hints

- `kubectl create deployment … --replicas=2`, `kubectl set image deployment/orders backend=…` (the container name
  created by `kubectl create deployment` is the image's name: `backend`).
- `kubectl annotate deployment orders kubernetes.io/change-cause="…" --overwrite`.
- `kubectl rollout undo deployment/orders --to-revision=N`.

## Expected Result

Pods on `learning-app/backend:1.0.0`; `kubectl rollout history` lists revisions **2** and **3**: rolling back to
revision 1 re-uses its template as a new revision (3), and revision 1 disappears from the list.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace challenge-04
kubectl create deployment orders -n challenge-04 --image=learning-app/backend:1.0.0 --replicas=2
kubectl annotate deployment orders -n challenge-04 kubernetes.io/change-cause="release 1.0.0"
kubectl rollout status deployment/orders -n challenge-04 --timeout=120s
kubectl set image deployment/orders -n challenge-04 backend=learning-app/backend:2.0.0
kubectl annotate deployment orders -n challenge-04 kubernetes.io/change-cause="release 2.0.0" --overwrite
kubectl rollout status deployment/orders -n challenge-04 --timeout=120s
```

<!-- test: contains=learning-app/backend:1.0.0; output -->
```bash
kubectl rollout undo deployment/orders -n challenge-04 --to-revision=1
kubectl rollout status deployment/orders -n challenge-04 --timeout=120s > /dev/null
kubectl get deployment orders -n challenge-04 -o jsonpath='image: {.spec.template.spec.containers[0].image}{"\n"}'
kubectl rollout history deployment/orders -n challenge-04
```

```text
deployment.apps/orders rolled back
image: learning-app/backend:1.0.0
deployment.apps/orders 
REVISION  CHANGE-CAUSE
2         release 2.0.0
3         release 1.0.0
```

🧹 Clean up (deletes the namespace `challenge-04` and the Deployment):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-04
```

</details>

## Explanation

A rollback is a rollout of an older template: Kubernetes takes revision 1's ReplicaSet, makes it current again and
gives it the next number. `--to-revision` matters when the last release was not the only bad one: "undo" alone
always returns to the revision just before the current one.
