# 26 · Horizontal Pod Autoscaler

> Level 9 · Scaling & Scheduling · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **HorizontalPodAutoscaler** (HPA) changes a Deployment's `replicas` for you, based on a measurement: usually CPU
usage. When the Pods work hard it adds Pods; when they are idle it removes them, between a minimum and a maximum you
choose. "Horizontal" means more Pods, as opposed to "vertical", bigger Pods.

It is the supermarket manager of lesson 25 with a rule written down: "open a till whenever the queues are longer than
5 people; close one when they are shorter; never fewer than 1 or more than 5 tills".

## Why do we need it?

Traffic changes during the day: busy at lunch, quiet at night, a spike when a newsletter goes out. Scaling by hand
means someone watches graphs and types `kubectl scale`, and is always too late or wastes capacity. The HPA reacts
within a minute, around the clock, and only uses the resources the load needs.

## How does it work?

```text
CPU increases ──▶ HPA detects load ──▶ more Pods ──▶ CPU per Pod decreases ──▶ (later) Pods scale down
```

1. **metrics-server** (a cluster add-on) collects every Pod's CPU and memory usage from the kubelets, every 15 s.
2. The HPA controller (in the controller manager) compares the average usage with the **target**, as a percentage of
   what each Pod **requests**: request 100m, use 80m → 80 %.
3. It computes `desired = ceil(current replicas × current % / target %)`, within `minReplicas`…`maxReplicas`, and
   sets the Deployment's `replicas`.
4. Scaling up happens quickly; scaling down waits for a **stabilization window** (5 minutes by default), so a short
   pause in traffic does not remove Pods that are needed a moment later.

Because utilization is relative to the **request**, an HPA cannot work for containers without CPU requests: that is
this lesson's Break It.

## Architecture

```text
             ┌──────────────────────┐   usage per Pod   ┌────────────────┐
  kubelets ──▶│   metrics-server     │ ────────────────▶ │ HPA controller │
             └──────────────────────┘                   └───────┬────────┘
                                                                │ sets spec.replicas (1 … 5)
                                                                ▼
                                   Deployment backend ──▶ ReplicaSet ──▶ Pods ◀── load
```

## YAML

The backend Deployment and Service from lesson 25 (with `requests.cpu: 100m`), and the autoscaler:

<!-- test: contains=HorizontalPodAutoscaler -->
```bash
cat manifests/scaling/hpa-backend.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: autoscaling/v2` | the current autoscaling API (v1 only knew CPU) |
| `scaleTargetRef` | which object to scale: the Deployment `backend` |
| `minReplicas` / `maxReplicas` | the range the HPA may choose from |
| `metrics[].resource.name: cpu`, `averageUtilization: 50` | aim for 50 % of the requested CPU per Pod, on average |
| `behavior.scaleDown.stabilizationWindowSeconds: 30` | wait 30 s of low usage before scaling down (default 300 s, shortened for the lab) |

The load: two Pods that call the backend's `/api/burn?ms=400` (400 ms of CPU work per request) in a loop:

<!-- test: contains=api/burn -->
```bash
cat manifests/scaling/load-generator.yaml
```

## Hands-On Lab

**1. Install metrics-server** (a Minikube add-on) and wait until the metrics API answers:

<!-- test: contains=enabled; timeout=600 -->
```bash
minikube addons enable metrics-server 2>&1 | tail -1
kubectl wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=300s
```

**2. The backend, and its first measurements.** metrics-server needs about a minute before the first values:

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace hpa-lab
kubectl apply -f manifests/scaling/scaling-backend.yaml -n hpa-lab
kubectl rollout status deployment/backend -n hpa-lab --timeout=120s
```

<!-- test: contains=backend-; retry=60; output -->
```bash
kubectl top pods -n hpa-lab
```

```text
NAME                       CPU(cores)   MEMORY(bytes)   
backend-5f65986b87-wtxdk   2m           1Mi             
```

**3. The autoscaler.** Its `TARGETS` column shows the current usage against the target, once it has a measurement:

<!-- test: contains=horizontalpodautoscaler.autoscaling/backend created -->
```bash
kubectl apply -f manifests/scaling/hpa-backend.yaml -n hpa-lab
```

<!-- test: contains=%/50%; retry=40; output -->
```bash
kubectl get hpa backend -n hpa-lab
```

```text
NAME      REFERENCE            TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
backend   Deployment/backend   cpu: 1%/50%   1         5         1          61s
```

**4. Load.** Start the two load Pods and wait until the HPA has added Pods:

<!-- test: contains=deployment.apps/load created -->
```bash
kubectl apply -f manifests/scaling/load-generator.yaml -n hpa-lab
```

<!-- test: contains=replicas now; retry=90; timeout=300 -->
```bash
replicas=$(kubectl get hpa backend -n hpa-lab -o jsonpath='{.status.currentReplicas}')
echo "replicas now: $replicas"
[ "$replicas" -ge 3 ]
```

<!-- test: contains=Deployment/backend; output -->
```bash
kubectl get hpa backend -n hpa-lab
kubectl top pods -n hpa-lab -l app=backend
```

```text
NAME      REFERENCE            TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
backend   Deployment/backend   cpu: 394%/50%   1         5         5          2m18s
NAME                       CPU(cores)   MEMORY(bytes)   
backend-5f65986b87-wtxdk   394m         3Mi             
```

The decisions are in the HPA's events, with the reason for each:

<!-- test: contains=SuccessfulRescale; output -->
```bash
kubectl describe hpa backend -n hpa-lab | grep SuccessfulRescale
```

```text
  Normal   SuccessfulRescale             18s                  horizontal-pod-autoscaler  New size: 5; reason: cpu resource utilization (percentage of request) above target
```

**5. Stop the load** and watch the HPA scale back down after the stabilization window:

<!-- test: contains=deleted -->
```bash
kubectl delete deployment load -n hpa-lab
```

<!-- test: contains=replicas now: 1; retry=120; timeout=420 -->
```bash
replicas=$(kubectl get hpa backend -n hpa-lab -o jsonpath='{.status.currentReplicas}')
echo "replicas now: $replicas"
[ "$replicas" -eq 1 ]
```

<!-- test: contains=below target; output -->
```bash
kubectl describe hpa backend -n hpa-lab | grep SuccessfulRescale
```

```text
  Normal   SuccessfulRescale             2m31s                  horizontal-pod-autoscaler  New size: 5; reason: cpu resource utilization (percentage of request) above target
  Normal   SuccessfulRescale             16s                    horizontal-pod-autoscaler  New size: 1; reason: All metrics below target
```

## Expected Result

Under load the HPA raised the Deployment from 1 to several Pods (its events say "above target"); after the load
stopped it went back to 1 ("All metrics below target"). The exact numbers depend on your computer's speed.

## Inspect

The HPA's own status: current and desired replicas, and the last measurement:

<!-- test: contains=currentReplicas -->
```bash
kubectl get hpa backend -n hpa-lab -o jsonpath='{.status}{"\n"}'
```

Who changed the Deployment? The HPA writes `spec.replicas`; the Deployment's events show each change:

<!-- test: contains=Scaled -->
```bash
kubectl get events -n hpa-lab --field-selector involvedObject.kind=Deployment,involvedObject.name=backend -o custom-columns=MESSAGE:.message
```

## Experiment

Try to scale the Deployment by hand while the HPA manages it:

<!-- test: contains=scaled -->
```bash
kubectl scale deployment backend -n hpa-lab --replicas=4
```

Within a minute or two:

<!-- test: contains=replicas: 1; retry=60; timeout=300 -->
```bash
echo "replicas: $(kubectl get deployment backend -n hpa-lab -o jsonpath='{.spec.replicas}')"
[ "$(kubectl get deployment backend -n hpa-lab -o jsonpath='{.spec.replicas}')" = 1 ]
```

The HPA undid it: it owns `replicas` now, and with no load its answer is 1. To change the range, edit the HPA
(`minReplicas`, `maxReplicas`), not the Deployment (lab 13).

## Break It

An autoscaler for a "reports" Deployment that was written without resource requests:

<!-- test: contains=created -->
```bash
kubectl apply -f manifests/scaling/hpa-no-requests.yaml -n hpa-lab
kubectl rollout status deployment/reports -n hpa-lab --timeout=120s > /dev/null
```

<!-- test: contains=<unknown>; retry=30; output -->
```bash
kubectl get hpa reports -n hpa-lab
```

```text
NAME      REFERENCE            TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
reports   Deployment/reports   cpu: <unknown>/50%   1         3         1          0s
```

## Troubleshoot It

*What should happen?* A percentage in `TARGETS`. *What happened?* `<unknown>`: the HPA has no number to work with, so
it will never scale. Is metrics-server the problem? No: the backend's HPA works. Read this HPA's conditions (during
the first minute they may only say that no metrics were returned yet; then the real reason appears):

<!-- test: contains=missing request for cpu; retry=60; timeout=900; output -->
```bash
kubectl describe hpa reports -n hpa-lab | grep -m1 'missing request for cpu'
```

```text
  ScalingActive  False   FailedGetResourceMetric  the HPA was unable to compute the replica count: failed to get cpu utilization: missing request for cpu in container reports of Pod reports-6c68ff5c57-7vwtx
```

Utilization is "usage as a percentage of the request"; without a request there is nothing to divide by. Root cause:
the container has no `resources.requests.cpu`.

## Fix It

Give the container a CPU request (in real life, in the manifest):

<!-- test: contains=%/50%; retry=90; timeout=900 -->
```bash
kubectl set resources deployment reports -n hpa-lab --requests=cpu=100m,memory=32Mi > /dev/null 2>&1 || true
kubectl get hpa reports -n hpa-lab
kubectl get hpa reports -n hpa-lab | grep -q '%/50%'
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| No metrics-server | `TARGETS <unknown>`, `failed to get cpu utilization: unable to get metrics` | install it (`minikube addons enable metrics-server`) |
| No CPU request | `<unknown>`, `missing request for cpu` | set `resources.requests.cpu` on every container |
| Scaling by hand an HPA-managed Deployment | the number jumps back | change the HPA's min/max |
| `replicas:` in the Deployment file re-applied | brief jumps to the file's value | remove `replicas` from the manifest when an HPA manages it |
| Expecting instant scale-down | Pods stay for minutes after the load | that is the stabilization window (300 s by default), on purpose |

## Best Practices

- Set realistic requests: they are the HPA's yardstick and the scheduler's (lesson 15).
- `minReplicas: 2` for anything users depend on; `maxReplicas` bounded by what the cluster (and the database) can take.
- Scale on what limits the application: CPU is common; memory rarely works well; custom metrics (requests per second,
  queue length) need extra components.
- Load-test before trusting an HPA: measure how fast it reacts and whether the extra Pods actually help.

## Challenge

**Task:** change the backend's autoscaler so that it never runs fewer than 2 Pods and aims for 70 % CPU.

**Requirements:** change the HPA, not the Deployment; `kubectl get hpa backend -n hpa-lab` shows `MINPODS 2` and
`/70%`.

**Hints:** `kubectl patch hpa` with a JSON patch, or `sed` on the manifest and `kubectl apply`.

**Expected Result:** the HPA shows `cpu: …/70%`, `MINPODS 2`, and the Deployment soon has 2 Pods.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=/70%; contains=2 -->
```bash
sed -e 's/minReplicas: 1/minReplicas: 2/' -e 's/averageUtilization: 50/averageUtilization: 70/' \
  manifests/scaling/hpa-backend.yaml | kubectl apply -n hpa-lab -f -
kubectl get hpa backend -n hpa-lab
```

</details>

The HPA raises the Deployment to 2 at its next check (every 15 s), even without load: `minReplicas` is a floor. The
manifest is still the source of truth: the same `sed` could be a change in Git.

## Key Takeaways

- An HPA sets `replicas` from a measurement, between min and max; metrics-server provides CPU and memory.
- CPU utilization is relative to the **request**: no request, no autoscaling (`<unknown>`).
- Scale-up is fast; scale-down waits for the stabilization window (default 5 minutes).
- Real-world use: web services and APIs whose traffic varies over the day scale with an HPA; it is also the first
  step towards cost control in the cloud.

## Cleanup

🧹 Delete the namespace `hpa-lab` (backend, autoscalers, reports). metrics-server stays enabled (lab 13 uses it).

<!-- test: contains=deleted -->
```bash
kubectl delete namespace hpa-lab
```

Next: [27 · Troubleshooting](../27-troubleshooting/README.md)
