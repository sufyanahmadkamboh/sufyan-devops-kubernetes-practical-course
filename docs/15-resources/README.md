# 15 · Resource requests and limits

> Level 9 · Scaling & Scheduling · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

Every container can declare how much **CPU** and **memory** it needs:

- **requests**: what the container is guaranteed. The scheduler only places a Pod on a node that still has its
  requests free.
- **limits**: the most it may use. Above the CPU limit it is slowed down (throttled); above the memory limit the
  kernel **kills** it (`OOMKilled`, out of memory).

Units: CPU in cores or millicores (`1` = one core, `100m` = 0.1 core); memory in bytes with binary suffixes
(`128Mi` = 128 mebibytes, `1Gi`).

## Why do we need it?

Many Pods share a node. Without requests, the scheduler cannot know whether a node is full and packs too much onto
it; without limits, one leaking application can take all the memory and take its neighbours down with it. Requests
and limits make a cluster predictable: each application gets what it asked for, and no more than it is allowed.

## How does it work?

```text
node: 2 CPU allocatable
 ├─ Pod A requests 1.5 CPU   ✓ scheduled (1.5 of 2 reserved)
 ├─ Pod B requests 0.4 CPU   ✓ scheduled (1.9 of 2 reserved)
 └─ Pod C requests 0.5 CPU   ✗ Pending: "Insufficient cpu"      (requests decide scheduling)

container with memory limit 128Mi uses 130Mi  →  kernel kills it  →  reason OOMKilled, exit code 137
container with cpu limit 250m wants 1 CPU     →  slowed down to 0.25 CPU, never killed
```

- The scheduler adds up **requests**, not real usage: a node can be "full" while mostly idle.
- Memory cannot be taken back from a process, so the only answer to too much memory is a kill. CPU can be shared,
  so too much CPU only means waiting.
- **QoS class**, set from requests and limits: `Guaranteed` (requests = limits for CPU and memory), `Burstable`
  (some requests), `BestEffort` (none, killed first when a node runs out of memory).

## Architecture

```text
            Pod spec: requests / limits
                 │                    │
                 ▼                    ▼
   Scheduler: "does a node still have    kubelet + kernel (cgroups) on the node:
   the requests free?"                   CPU above the limit → throttle
     yes → bind to the node              memory above the limit → OOM kill (exit 137)
     no  → Pending (Insufficient …)
```

## YAML

<!-- test: contains=requests; contains=limits -->
```bash
cat manifests/scaling/resources-pod.yaml
```

| Field | Meaning |
|---|---|
| `resources.requests.cpu: "100m"` | 0.1 CPU reserved: the scheduler counts it against the node |
| `resources.requests.memory: "64Mi"` | 64 MiB reserved |
| `resources.limits.cpu: "250m"` | never more than 0.25 CPU: throttled above |
| `resources.limits.memory: "128Mi"` | never more than 128 MiB: killed above |

## Hands-On Lab

**1. A Pod with requests and limits:**

<!-- test: contains=condition met -->
```bash
kubectl create namespace resources-lab
kubectl apply -n resources-lab -f manifests/scaling/resources-pod.yaml
kubectl wait --for=condition=Ready pod/sized -n resources-lab --timeout=120s
```

**2. Its QoS class and its resources:**

<!-- test: contains=Burstable; output -->
```bash
kubectl get pod sized -n resources-lab -o jsonpath='qos={.status.qosClass} requests={.spec.containers[0].resources.requests} limits={.spec.containers[0].resources.limits}{"\n"}'
```

```text
qos=Burstable requests={"cpu":"100m","memory":"64Mi"} limits={"cpu":"250m","memory":"128Mi"}
```

`Burstable`: requests are set but lower than the limits.

**3. What the node has reserved for all its Pods:**

<!-- test: contains=Allocated resources -->
```bash
kubectl describe node minikube | grep -A8 'Allocated resources'
```

## Expected Result

`sized` runs with QoS class `Burstable`, and its 100m CPU and 64Mi memory are part of the node's "Allocated
resources" (the sum of all requests on the node).

## Inspect

Current usage needs the metrics-server add-on (lesson 26 enables it); requests and limits are always in the spec:

<!-- test: contains=sized -->
```bash
kubectl get pods -n resources-lab -o custom-columns=NAME:.metadata.name,CPU_REQ:.spec.containers[0].resources.requests.cpu,CPU_LIM:.spec.containers[0].resources.limits.cpu,MEM_REQ:.spec.containers[0].resources.requests.memory,MEM_LIM:.spec.containers[0].resources.limits.memory,QOS:.status.qosClass
```

## Experiment

Ask for more CPU than the node has (100 CPUs):

<!-- test: contains=pod/too-big created -->
```bash
kubectl apply -n resources-lab -f manifests/scaling/resources-too-big.yaml
```

<!-- test: retry=10; contains=Insufficient cpu; output -->
```bash
kubectl get events -n resources-lab --field-selector involvedObject.name=too-big,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

The Pod stays `Pending`: no node has 100 CPUs free. This is the scheduler's job (lesson 16), driven only by requests.

## Break It

A container whose memory keeps growing, with a 32Mi limit:

<!-- test: contains=tail; contains=32Mi -->
```bash
cat manifests/scaling/resources-memory-hog.yaml
kubectl apply -n resources-lab -f manifests/scaling/resources-memory-hog.yaml
```

<!-- test: retry=20; contains=OOMKilled; output -->
```bash
kubectl get pod memory-hog -n resources-lab
```

```text
NAME         READY   STATUS      RESTARTS   AGE
memory-hog   0/1     OOMKilled   0          3s
```

## Troubleshoot It

*What should happen?* The container runs. *What happened?* `OOMKilled`. *Which object controls it?* The container's
memory limit. The container's last state says exactly how it ended:

<!-- test: retry=10; contains=reason=OOMKilled; contains=exitCode=137; output -->
```bash
kubectl get pod memory-hog -n resources-lab -o jsonpath='reason={.status.containerStatuses[0].state.terminated.reason} exitCode={.status.containerStatuses[0].state.terminated.exitCode} limit={.spec.containers[0].resources.limits.memory}{"\n"}'
```

```text
reason=OOMKilled exitCode=137 limit=32Mi
```

Exit code 137 = 128 + 9: killed by signal 9 (SIGKILL), sent by the kernel because the container went over its 32Mi
memory limit. In a Deployment the Pod would restart and be killed again (`CrashLoopBackOff`, with `OOMKilled` as the
last state). Root cause: the process needs more memory than its limit, either because the limit is too low or because
the application leaks memory (here: it grows forever, a leak).

## Fix It

For a real application: raise the limit to what it really needs (measure first), or fix the leak. Our `tail` grows
forever, so no limit is enough; replace it with a bounded command and give it room:

<!-- test: contains=Completed; retry=20 -->
```bash
kubectl delete pod memory-hog -n resources-lab
kubectl run memory-ok -n resources-lab --image=alpine:3.23 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"ok","image":"alpine:3.23","command":["sh","-c","head -c 20m /dev/zero | wc -c"],"resources":{"requests":{"memory":"64Mi"},"limits":{"memory":"64Mi"}}}]}}' > /dev/null
sleep 3
kubectl get pod memory-ok -n resources-lab
```

`head -c 20m /dev/zero | wc -c` streams 20 MB without keeping it: it finishes (`Completed`) well inside 64Mi.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Memory limit below the application's real need | `OOMKilled`, exit 137, `CrashLoopBackOff` | measure usage, set the limit above the peak |
| Requests far above real use | Pods `Pending` with `Insufficient cpu/memory` while nodes are idle | requests ≈ normal usage |
| No requests at all | the scheduler overloads nodes; Pods are `BestEffort`, evicted first | always set requests |
| CPU limit too low | slow responses, probe timeouts, but no errors | raise the CPU limit or remove it (requests only) |
| Writing `128M` instead of `128Mi` | slightly different sizes (10^6 vs 2^20) | use `Mi`/`Gi` |

## Best Practices

- Every container: memory request and limit, CPU request; a CPU limit only when you need to cap a noisy neighbour.
- Base the numbers on measurements (`kubectl top`, lesson 26), not guesses, and revisit them.
- `Guaranteed` QoS (requests = limits) for the most important workloads, such as databases.

## Challenge

**Task:** create a Pod `steady` (image `nginx:1.30-alpine`) with QoS class `Guaranteed`.

**Requirements:** CPU and memory requests and limits on its container; prove the class with `kubectl get`.

**Hints:** `Guaranteed` needs requests equal to limits, for both CPU and memory.

**Expected Result:** `qos=Guaranteed`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=qos=Guaranteed -->
```bash
kubectl apply -n resources-lab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: steady
spec:
  containers:
    - name: web
      image: nginx:1.30-alpine
      resources:
        requests: {cpu: "200m", memory: "64Mi"}
        limits: {cpu: "200m", memory: "64Mi"}
EOF
kubectl wait --for=condition=Ready pod/steady -n resources-lab --timeout=120s > /dev/null
kubectl get pod steady -n resources-lab -o jsonpath='qos={.status.qosClass}{"\n"}'
```

</details>

When a node runs out of memory, the kubelet evicts `BestEffort` Pods first, then `Burstable` ones above their
requests; `Guaranteed` Pods are the last to go.

## Key Takeaways

- Requests decide **where** a Pod can run (scheduling); limits decide **how much** it may use.
- Over the memory limit → `OOMKilled`, exit code 137; over the CPU limit → throttled.
- `Pending` with `Insufficient cpu/memory` means requests do not fit on any node.
- Real-world use: sizing requests and limits is daily platform work: it decides cluster cost, stability and how
  many Pods fit on each node.

## Cleanup

🧹 Delete the namespace `resources-lab` and its Pods (`sized`, `too-big`, `memory-ok`, `steady`):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace resources-lab
```

Next: [16 · Scheduling basics](../16-scheduling/README.md)
