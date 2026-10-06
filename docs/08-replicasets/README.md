# 08 · ReplicaSets

> Level 4 · Deployments · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **ReplicaSet** keeps a given number of identical Pods running. You say "3 Pods like this"; it counts the Pods that
match its selector, and creates or deletes Pods until the count is right, forever.

Analogy: a thermostat. You set 21 °C; it does not heat once, it keeps measuring and corrects whenever the room drifts.
A ReplicaSet does that with a number of Pods.

## Why do we need it?

Lesson 06 showed that a deleted Pod never comes back. One Pod is also one point of failure and has a fixed capacity.
Applications need several copies (**replicas**) for availability and load, and they need something that replaces a
copy when it dies. That is **self-healing**, and the ReplicaSet is the controller that does it.

## How does it work?

The controller manager (lesson 02) runs a loop for every ReplicaSet:

```text
desired = spec.replicas                       3
current = Pods matching spec.selector         2   (one was deleted)
desired > current → create Pods from spec.template
desired < current → delete the extra Pods
```

The Pods it creates get the labels of the **template**, and the selector must match those labels; otherwise the
ReplicaSet could never count its own Pods, and the API server refuses it.

In practice you rarely create ReplicaSets yourself: a **Deployment** (lesson 09) creates and replaces them for you.
Understanding the ReplicaSet is understanding what a Deployment does underneath.

## Architecture

```text
            ReplicaSet "web"   replicas: 3   selector: app=web
                    │  creates from template, counts by selector
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Pod web-xxxxx  Pod web-yyyyy  Pod web-zzzzz      (app=web)
        ✕ deleted
        → a new Pod web-qqqqq is created within seconds
```

## YAML

<!-- test: contains=kind: ReplicaSet -->
```bash
cat manifests/workloads/08-web-replicaset.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: apps/v1` | ReplicaSets are in the `apps` API group, version `v1` |
| `kind: ReplicaSet` | the controller that keeps N Pods running |
| `spec.replicas: 3` | the desired number of Pods |
| `spec.selector.matchLabels` | how the ReplicaSet recognises its Pods: `app=web` |
| `spec.template` | the Pod to create, without a name (each copy gets a generated one) |
| `spec.template.metadata.labels` | the labels every created Pod gets: they **must** match the selector |
| `spec.template.spec` | the Pod spec of lesson 06 |

## Hands-On Lab

<!-- test: contains=replicaset.apps/web created -->
```bash
kubectl create namespace rs-lab
kubectl apply -f manifests/workloads/08-web-replicaset.yaml -n rs-lab
kubectl wait --for=condition=Ready pods -l app=web -n rs-lab --timeout=120s > /dev/null
```

**1. The ReplicaSet and its Pods:**

<!-- test: contains=web; output -->
```bash
kubectl get replicaset -n rs-lab
kubectl get pods -n rs-lab -l app=web
```

```text
NAME   DESIRED   CURRENT   READY   AGE
web    3         3         3       1s
NAME        READY   STATUS    RESTARTS   AGE
web-6k5zq   1/1     Running   0          1s
web-r55dh   1/1     Running   0          1s
web-tkg2b   1/1     Running   0          1s
```

The Pod names are the ReplicaSet's name plus a random suffix.

**2. Self-healing: delete a Pod.** 🧹 This deletes one of the three `web` Pods on purpose:

<!-- test: contains=deleted -->
```bash
victim=$(kubectl get pods -n rs-lab -l app=web -o jsonpath='{.items[0].metadata.name}')
echo "deleting $victim"
kubectl delete pod "$victim" -n rs-lab
```

<!-- test: contains=3/3; retry=20 -->
```bash
kubectl wait --for=condition=Ready pods -l app=web -n rs-lab --timeout=60s > /dev/null
echo "$(kubectl get pods -n rs-lab -l app=web --field-selector=status.phase=Running -o name | wc -l | tr -d ' ')/3 running"
```

<!-- test: contains=SuccessfulCreate; output -->
```bash
kubectl describe replicaset web -n rs-lab | grep SuccessfulCreate | tail -1
```

```text
  Normal  SuccessfulCreate  3s    replicaset-controller  Created pod: web-587m6
```

**3. Scale:** change the desired number.

<!-- test: contains=5 -->
```bash
kubectl scale replicaset web -n rs-lab --replicas=5
kubectl wait --for=condition=Ready pods -l app=web -n rs-lab --timeout=120s > /dev/null
kubectl get replicaset web -n rs-lab -o jsonpath='desired={.spec.replicas} ready={.status.readyReplicas}{"\n"}'
```

## Expected Result

Three Pods; a deleted Pod is replaced by a new one with a new name; after scaling, five Pods.

## Inspect

Every Pod records who owns it:

<!-- test: contains=ReplicaSet/web -->
```bash
kubectl get pods -n rs-lab -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{"  owner: "}{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

The `ownerReferences` link is how deleting a ReplicaSet also deletes its Pods.

## Experiment

The ReplicaSet counts **labels**, not names. Start a lone Pod by hand that happens to carry `app=web`:

<!-- test: contains=5 -->
```bash
kubectl run intruder -n rs-lab --image=nginx:1.30-alpine --labels=app=web
sleep 5
kubectl get pods -n rs-lab -l app=web --no-headers | wc -l | tr -d ' '
kubectl get pod intruder -n rs-lab 2>&1 | tail -1
```

Still 5: the ReplicaSet saw 6 matching Pods, wanted 5, and deleted one of them, quite possibly your `intruder`. Labels
are a contract: never reuse a controller's selector labels on other Pods.

## Break It

A ReplicaSet whose selector does not match its own template:

<!-- test: fail; contains=does not match template; output -->
```bash
kubectl apply -f manifests/workloads/08-web-replicaset-broken.yaml -n rs-lab 2>&1
```

```text
The ReplicaSet "web-broken" is invalid: spec.template.metadata.labels: Invalid value: {"app":"webserver"}: `selector` does not match template `labels`
```

## Troubleshoot It

*What should happen?* A second ReplicaSet. *What happened?* The API server refused it before storing anything. The
message names both sides: the selector wants `app=web`, the template would create Pods with `app=webserver`. Such a
ReplicaSet would create Pods it can never count, then create more, forever; Kubernetes prevents that.

<!-- test: contains=webserver -->
```bash
grep -A2 -E 'matchLabels|labels:' manifests/workloads/08-web-replicaset-broken.yaml
```

Root cause: `spec.selector.matchLabels` and `spec.template.metadata.labels` disagree.

## Fix It

Make the template's labels match the selector (here, by applying a corrected copy through standard input):

<!-- test: contains=web-broken created -->
```bash
sed 's/app: webserver/app: web-broken/; s/app: web$/app: web-broken/' manifests/workloads/08-web-replicaset-broken.yaml |
  kubectl apply -n rs-lab -f -
kubectl get replicaset web-broken -n rs-lab
```

Both now say `app: web-broken` (a different label from the first ReplicaSet, so the two never fight over Pods).

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Selector ≠ template labels | `selector does not match template labels` | the same labels in both places |
| Two controllers selecting the same labels | Pods deleted and recreated endlessly | unique selector labels per controller |
| Editing the template of a ReplicaSet | existing Pods keep the old version | a ReplicaSet only creates Pods, never updates them: use a Deployment |
| Deleting Pods to "fix" them | identical replacements appear | fix the template (or the Deployment) |

## Best Practices

- Use Deployments, not ReplicaSets, for applications: they add updates and rollbacks (lesson 09).
- Run at least 2 replicas of anything that must stay available.

## Challenge

**Task:** change the image of the `web` ReplicaSet to `learning-app/backend:2.0.0` with `kubectl set image`, and find
out which image the running Pods use afterwards. Then make all Pods use the new image.

**Requirements:** do not delete the ReplicaSet.

**Hints:** `kubectl set image replicaset/web web=IMAGE`; list images with `-o custom-columns`; Pods are only created
from the template when one is missing.

**Expected Result:** first the old image on every Pod; after deleting the Pods (the ReplicaSet recreates them), the new
one.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=learning-app/backend:2.0.0 -->
```bash
kubectl set image replicaset/web web=learning-app/backend:2.0.0 -n rs-lab
kubectl get pods -n rs-lab -l app=web -o custom-columns=POD:.metadata.name,IMAGE:.spec.containers[0].image | head -3
kubectl delete pods -n rs-lab -l app=web --wait=true > /dev/null
kubectl wait --for=condition=Ready pods -l app=web -n rs-lab --timeout=180s > /dev/null
echo "after recreating:"
kubectl get pods -n rs-lab -l app=web -o custom-columns=IMAGE:.spec.containers[0].image --no-headers | sort -u
```

</details>

Changing the template does not touch existing Pods: they were created earlier and keep their image. Only new Pods use
the new template, and deleting all of them at once means downtime. Doing this safely, a few Pods at a time, is
exactly what a Deployment's rolling update automates (lesson 09).

## Key Takeaways

- A ReplicaSet keeps `replicas` Pods matching its selector running: self-healing.
- The selector must match the template's labels; Pods are counted by labels, not names.
- A ReplicaSet never updates existing Pods; Deployments manage ReplicaSets to do updates.
- Real-world use: every Deployment you run creates ReplicaSets; you will see them in `kubectl get rs` daily.

## Cleanup

🧹 Delete the namespace `rs-lab` (both ReplicaSets and their Pods):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace rs-lab
```

Next: [09 · Deployments](../09-deployments/README.md)
