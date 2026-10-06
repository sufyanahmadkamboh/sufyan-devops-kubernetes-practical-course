# 09 · Deployments, rolling updates and rollbacks

> Level 4 · Deployments · ⏱ 60 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **Deployment** is the standard way to run a stateless application on Kubernetes. It manages ReplicaSets (lesson
08), which manage Pods. When you change the Deployment (a new image, a new setting), it creates a **new** ReplicaSet
and moves the Pods over to it gradually: a **rolling update**. It keeps the old ReplicaSets, so it can go back: a
**rollback**.

Analogy: replacing the tyres of a bus while it keeps driving its route, one wheel at a time, with the old tyres kept
in the boot in case the new ones are wrong.

## Why do we need it?

Lesson 08 ended with a problem: a ReplicaSet never updates its Pods, and replacing them all at once means downtime.
Real applications are updated many times a week. A Deployment updates them **without downtime**, stops when something
goes wrong, records the **history** of versions and lets you return to a previous one with one command.

## How does it work?

```text
Deployment backend           image 1.0.0 → you change it to 2.0.0
   ├── ReplicaSet backend-aaa   (1.0.0)   3 → 2 → 1 → 0 Pods
   └── ReplicaSet backend-bbb   (2.0.0)   0 → 1 → 2 → 3 Pods
```

1. The Deployment controller creates a new ReplicaSet from the changed template.
2. It scales the new one up and the old one down, a few Pods at a time, within two limits:
   - `maxSurge`: how many Pods **above** `replicas` may exist during the update (extra capacity);
   - `maxUnavailable`: how many Pods **below** `replicas` may be not ready.
3. A new Pod counts only once it is **ready** (its readiness probe passes, lesson 14). A new version that never becomes
   ready stops the update halfway: the old Pods keep serving.
4. Each template change is a **revision**; old ReplicaSets are kept (scaled to 0) for rollbacks.

## Architecture

```text
 Old Pods (v1)  ███  ███  ███
 Step 1         ███  ███  ███  ░░░ new v2 Pod starting       (maxSurge: 1 → 4 Pods)
 Step 2         ███  ███       ███ v2 ready, one v1 removed  (maxUnavailable: 1)
 Step 3         ███            ███  ███
 Done                          ███  ███  ███                 all v2, old ReplicaSet kept at 0
```

```text
Deployment ──▶ ReplicaSet (revision 2, current) ──▶ Pod  Pod  Pod
           └─▶ ReplicaSet (revision 1, 0 Pods)       (kept for rollback)
```

## YAML

<!-- test: contains=kind: Deployment -->
```bash
cat manifests/deployments/09-backend-deployment.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: apps/v1`, `kind: Deployment` | a Deployment, in the `apps` API group |
| `spec.replicas: 3` | the number of Pods to keep running |
| `spec.revisionHistoryLimit: 5` | how many old ReplicaSets to keep for rollbacks |
| `spec.selector.matchLabels` | the Pods this Deployment owns: `app=backend` (must match the template labels) |
| `spec.strategy.type: RollingUpdate` | replace Pods gradually (the other type, `Recreate`, stops all old Pods first) |
| `rollingUpdate.maxSurge: 1` | at most 1 extra Pod during the update |
| `rollingUpdate.maxUnavailable: 1` | at most 1 Pod missing during the update |
| `spec.template` | the Pod template: a change here starts a rolling update |
| `containers[].image` | `learning-app/backend:1.0.0`, the course's backend |
| `containers[].ports[].containerPort: 8080` | the port the backend listens on |
| `readinessProbe.httpGet` | the Pod is "ready" only when `GET /readyz` on port 8080 answers 200 (lesson 14) |

## Hands-On Lab

<!-- test: contains=created -->
```bash
kubectl create namespace deploy-lab
kubectl config set-context --current --namespace=deploy-lab
```

**1. Deploy version 1.0.0** and record why (the `change-cause` annotation shows up in the history):

<!-- test: contains=successfully rolled out -->
```bash
kubectl apply -f manifests/deployments/09-backend-deployment.yaml
kubectl annotate deployment backend kubernetes.io/change-cause="initial version 1.0.0"
kubectl rollout status deployment/backend --timeout=120s
```

**2. Deployment → ReplicaSet → Pods:**

<!-- test: contains=deployment.apps/backend; output -->
```bash
kubectl get deployment,replicaset,pods -l app=backend
```

```text
NAME                      READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/backend   3/3     3            3           1s

NAME                                 DESIRED   CURRENT   READY   AGE
replicaset.apps/backend-6668bd5576   3         3         3       1s

NAME                           READY   STATUS    RESTARTS   AGE
pod/backend-6668bd5576-8j6vh   1/1     Running   0          1s
pod/backend-6668bd5576-lzt9n   1/1     Running   0          1s
pod/backend-6668bd5576-pww4w   1/1     Running   0          1s
```

The Pod names carry the ReplicaSet's name, which carries a hash of the template.

**3. Ask the application which version it is** (through `port-forward` to the Deployment, lesson 04):

<!-- test: contains="version":"1.0.0" -->
```bash
kubectl port-forward deployment/backend 18090:8080 > /dev/null 2>&1 &
pf=$!
sleep 3
curl -s http://localhost:18090/
kill $pf
```

**4. The rolling update to 2.0.0:**

<!-- test: contains=successfully rolled out -->
```bash
kubectl set image deployment/backend backend=learning-app/backend:2.0.0
kubectl annotate deployment backend kubernetes.io/change-cause="update to 2.0.0" --overwrite
kubectl rollout status deployment/backend --timeout=180s
```

How it happened, step by step:

<!-- test: contains=Scaled up; output -->
```bash
kubectl describe deployment backend | grep -E 'Scaled (up|down)'
```

```text
  Normal  ScalingReplicaSet  8s    deployment-controller  Scaled up replica set backend-6668bd5576 from 0 to 3
  Normal  ScalingReplicaSet  3s    deployment-controller  Scaled up replica set backend-677d5c6995 from 0 to 1
  Normal  ScalingReplicaSet  3s    deployment-controller  Scaled down replica set backend-6668bd5576 from 3 to 2
  Normal  ScalingReplicaSet  3s    deployment-controller  Scaled up replica set backend-677d5c6995 from 1 to 2
  Normal  ScalingReplicaSet  2s    deployment-controller  Scaled down replica set backend-6668bd5576 from 2 to 1
  Normal  ScalingReplicaSet  2s    deployment-controller  Scaled up replica set backend-677d5c6995 from 2 to 3
  Normal  ScalingReplicaSet  2s    deployment-controller  Scaled down replica set backend-6668bd5576 from 1 to 0
```

Up one, down one, never fewer than 2 ready Pods: no downtime. Two ReplicaSets now exist, the old one at 0:

<!-- test: contains=2.0.0; output -->
```bash
kubectl get replicaset -l app=backend -o custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image
```

```text
NAME                 DESIRED   IMAGE
backend-6668bd5576   0         learning-app/backend:1.0.0
backend-677d5c6995   3         learning-app/backend:2.0.0
```

<!-- test: contains="version":"2.0.0" -->
```bash
kubectl port-forward deployment/backend 18090:8080 > /dev/null 2>&1 &
pf=$!
sleep 3
curl -s http://localhost:18090/
kill $pf
```

**5. The history:**

<!-- test: contains=update to 2.0.0; output -->
```bash
kubectl rollout history deployment/backend
```

```text
deployment.apps/backend 
REVISION  CHANGE-CAUSE
1         initial version 1.0.0
2         update to 2.0.0
```

## Expected Result

The Deployment is at revision 2, three Pods run `2.0.0`, the old ReplicaSet (1.0.0) is kept with 0 Pods, and the
history shows both revisions with their causes.

## Inspect

<!-- test: contains=learning-app/backend:2.0.0 -->
```bash
kubectl rollout history deployment/backend --revision=2 | grep -E 'Image|change-cause'
kubectl get deployment backend -o jsonpath='revision {.metadata.annotations.deployment\.kubernetes\.io/revision}, image {.spec.template.spec.containers[0].image}{"\n"}'
```

## Experiment

Scaling is not an update: it changes `replicas`, not the template.

<!-- test: contains=update to 2.0.0 -->
```bash
kubectl scale deployment backend --replicas=5
kubectl rollout status deployment/backend --timeout=120s > /dev/null
kubectl get replicaset -l app=backend
kubectl rollout history deployment/backend | tail -2
kubectl scale deployment backend --replicas=3
```

Same ReplicaSet with 5 Pods, no new revision. Only a change to `spec.template` (image, environment, probes,
labels…) creates a new ReplicaSet and a rollout.

## Break It

A release with a typo in the image tag, `9.9.9`, a version that was never built:

<!-- test: fail; contains=timed out; output -->
```bash
kubectl set image deployment/backend backend=learning-app/backend:9.9.9
kubectl annotate deployment backend kubernetes.io/change-cause="update to 9.9.9" --overwrite
kubectl rollout status deployment/backend --timeout=40s 2>&1
```

```text
deployment.apps/backend image updated
deployment.apps/backend annotated
Waiting for deployment "backend" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "backend" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "backend" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "backend" rollout to finish: 2 out of 3 new replicas have been updated...
error: timed out waiting for the condition
```

## Troubleshoot It

*What should happen?* Three Pods on the new version. *What happened?* The rollout never finishes. *Which object
controls it?* The Deployment, then its new ReplicaSet, then the new Pod. Look at the Pods:

<!-- test: contains=ImagePullBackOff; retry=10; output -->
```bash
kubectl get pods -l app=backend
```

```text
NAME                       READY   STATUS             RESTARTS   AGE
backend-677d5c6995-6tz6k   1/1     Running            0          51s
backend-677d5c6995-zw47t   1/1     Running            0          51s
backend-784dc59884-2p5jm   0/1     ErrImagePull       0          43s
backend-784dc59884-z42t9   0/1     ImagePullBackOff   0          43s
```

The new Pod cannot get its image; the old version still runs. The events say why:

<!-- test: contains=9.9.9 -->
```bash
kubectl describe pods -l app=backend | grep -E '9\.9\.9' | head -3
```

Root cause: the image `learning-app/backend:9.9.9` does not exist (not in the node, not in any registry). Thanks to
`maxUnavailable: 1` and the readiness rule, at least 2 Pods of the working version kept serving the whole time.

## Fix It

Roll back to the previous revision:

<!-- test: contains=successfully rolled out -->
```bash
kubectl rollout undo deployment/backend
kubectl rollout status deployment/backend --timeout=120s
```

<!-- test: contains=learning-app/backend:2.0.0; absent=9.9.9; retry=10 -->
```bash
kubectl get pods -l app=backend -o custom-columns=POD:.metadata.name,IMAGE:.spec.containers[0].image,STATUS:.status.phase
```

<!-- test: contains=REVISION; output -->
```bash
kubectl rollout history deployment/backend
```

```text
deployment.apps/backend 
REVISION  CHANGE-CAUSE
1         initial version 1.0.0
3         update to 9.9.9
4         update to 2.0.0
```

The broken Pod is gone, three Pods run `2.0.0`. In the history the undo is a new revision (the old number moves to
the end), because a rollback is just another rollout of an old template.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| A wrong image tag | rollout stuck, a Pod `ErrImagePull` / `ImagePullBackOff` | `kubectl rollout undo`, then fix the tag |
| No readiness probe | a broken version counts as ready and replaces all old Pods | always define a readiness probe (lesson 14) |
| Using `latest` | you cannot tell which version runs, rollbacks do nothing | immutable version tags |
| `kubectl edit` in production | the change exists only in the cluster, not in Git | change the file, `kubectl apply -f` |
| Changing `spec.selector` | `field is immutable` | the selector is fixed at creation; create a new Deployment |

## Best Practices

- Keep manifests in Git and apply them; record a change cause (or rely on your CI/CD tool's history).
- `maxUnavailable: 0` + `maxSurge: 1` for services that must never lose capacity during an update.
- Watch a rollout with `kubectl rollout status` (in scripts it exits non-zero on failure) and roll back fast.

## Challenge

**Task:** update the Deployment **declaratively**: make a copy of the manifest with image `learning-app/backend:1.0.0`
and 4 replicas, apply it, and verify the rollout and the history.

**Requirements:** `kubectl apply -f` (no `set image`); finish with 4 ready Pods running 1.0.0.

**Hints:** `sed 's/old/new/' FILE | kubectl apply -f -`; the file already has 1.0.0, so only `replicas` changes… or
does it? Compare with what is running now.

**Expected Result:** 4 Pods, image 1.0.0, a new revision in the history.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=learning-app/backend:1.0.0; contains=4/4 -->
```bash
sed 's/replicas: 3/replicas: 4/' manifests/deployments/09-backend-deployment.yaml | kubectl apply -f -
kubectl rollout status deployment/backend --timeout=180s > /dev/null
kubectl get deployment backend -o jsonpath='{.status.readyReplicas}/{.spec.replicas} ready, image {.spec.template.spec.containers[0].image}{"\n"}'
kubectl rollout history deployment/backend | tail -3
```

</details>

The file says 1.0.0; the cluster ran 2.0.0 (changed with `set image`). `apply` makes the cluster match the file, so
it rolled the Pods back to 1.0.0 as a new revision. This is why imperative changes and files must not drift apart:
the next `apply` silently undoes the imperative change.

## Key Takeaways

- Deployment → ReplicaSets → Pods; a template change creates a new ReplicaSet and a rolling update.
- `maxSurge` and `maxUnavailable` control the pace; readiness decides when a new Pod counts.
- `rollout status`, `rollout history`, `rollout undo` watch, explain and revert.
- A broken version stops the rollout halfway while the old Pods keep serving.
- Real-world use: every stateless service (web apps, APIs, workers) is a Deployment; CI/CD pipelines change its image.

## Cleanup

🧹 Delete the namespace `deploy-lab` (the Deployment, its ReplicaSets and Pods) and switch back to `default`:

<!-- test: contains=deleted -->
```bash
kubectl config set-context --current --namespace=default
kubectl delete namespace deploy-lab
```

Next: [10 · Services](../10-services/README.md)
