# 16 · Scheduling basics

> Level 9 · Scaling & Scheduling · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

**Scheduling** is choosing a node for a new Pod. The scheduler (lesson 02) filters out the nodes that cannot run it,
scores the rest and writes the winner into the Pod. You influence its choice with:

- **node labels** and **`nodeSelector`**: "only on nodes labelled `disktype=ssd`" (the Pod chooses the node);
- **taints** and **tolerations**: a node says "keep away unless you tolerate `lab=demo`" (the node rejects Pods).

## Why do we need it?

Nodes are not all equal: some have GPUs or fast disks, some are reserved for one team or for system components, some
are being drained for maintenance. Labels and selectors send Pods where they belong; taints keep the wrong Pods away
from special nodes.

## How does it work?

```text
new Pod (no node) ──▶ scheduler
        filter:  enough free requests? (lesson 15)
                 nodeSelector labels match?
                 taints tolerated?
        score:   spread, least loaded, …
        bind:    pod.spec.nodeName = winner        nothing fits → Pending + FailedScheduling event
```

- `nodeSelector` is a hard rule: no matching node, no scheduling. (`nodeAffinity` is the richer version: preferences,
  `In`/`NotIn` expressions.)
- A taint has a key, a value and an **effect**: `NoSchedule` (new Pods without a toleration are not placed there),
  `PreferNoSchedule` (avoid if possible), `NoExecute` (also evict running Pods). A toleration only *allows* a Pod onto a
  tainted node; it does not attract it there.
- Control-plane nodes in real clusters carry the taint `node-role.kubernetes.io/control-plane:NoSchedule`; Minikube's
  single node does not, so it can run your Pods.

## Architecture

```text
   node minikube
   labels:  kubernetes.io/hostname=minikube, disktype=ssd (added in the lab)
   taints:  lab=demo:NoSchedule (added in Break It)
        ▲                               ▲
        │ nodeSelector: disktype=ssd    │ tolerations: lab=demo:NoSchedule
   Pod fast-disk                    Pod tolerant
```

## YAML

<!-- test: contains=nodeSelector; contains=tolerations -->
```bash
cat manifests/workloads/scheduling-nodeselector-pod.yaml manifests/workloads/scheduling-toleration-pod.yaml
```

| Field | Meaning |
|---|---|
| `spec.nodeSelector` | labels a node must have (all of them) |
| `spec.tolerations[].key/value` | the taint this Pod accepts |
| `operator: Equal` | key and value must match (`Exists`: any value of that key) |
| `effect: NoSchedule` | which taint effect is tolerated |

## Hands-On Lab

**1. The node's labels and taints:**

<!-- test: contains=kubernetes.io/hostname=minikube; contains=Taints -->
```bash
kubectl create namespace scheduling-lab
kubectl get node minikube --show-labels
kubectl describe node minikube | grep -E '^Taints'
```

**2. A Pod that wants an SSD node:**

<!-- test: contains=pod/fast-disk created -->
```bash
kubectl apply -n scheduling-lab -f manifests/workloads/scheduling-nodeselector-pod.yaml
```

<!-- test: retry=10; contains=didn't match; output -->
```bash
kubectl get pod fast-disk -n scheduling-lab
kubectl get events -n scheduling-lab --field-selector involvedObject.name=fast-disk,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
NAME        READY   STATUS    RESTARTS   AGE
fast-disk   0/1     Pending   0          0s
0/1 nodes are available: 1 node(s) didn't match Pod's node affinity/selector. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

**3. Label the node,** and the scheduler places the Pod on its next try:

<!-- test: contains=condition met -->
```bash
kubectl label node minikube disktype=ssd
kubectl wait --for=condition=Ready pod/fast-disk -n scheduling-lab --timeout=120s
```

## Expected Result

`fast-disk` was `Pending` with "didn't match Pod's node affinity/selector" until the node got the label
`disktype=ssd`, then it ran on `minikube`.

## Inspect

<!-- test: contains=minikube; contains=DISKTYPE -->
```bash
kubectl get pod fast-disk -n scheduling-lab -o jsonpath='{.spec.nodeName}{"\n"}'
kubectl get nodes -L disktype
```

`-L disktype` adds the label as a column, handy on clusters with many nodes.

## Experiment

Remove the label: does the running Pod move away?

<!-- test: contains=Running -->
```bash
kubectl label node minikube disktype-
kubectl get pod fast-disk -n scheduling-lab
```

It keeps running. `nodeSelector` is only checked when the Pod is scheduled; a Pod is never moved afterwards (only
`NoExecute` taints and evictions remove running Pods). Put the label back for later: `kubectl label node minikube
disktype=ssd`.

## Break It

Taint the node, as an administrator would to reserve it, and create an ordinary Pod:

<!-- test: contains=tainted -->
```bash
kubectl taint node minikube lab=demo:NoSchedule
kubectl run plain -n scheduling-lab --image=nginx:1.30-alpine
```

<!-- test: retry=10; contains=Pending; output -->
```bash
kubectl get pod plain -n scheduling-lab
```

```text
NAME    READY   STATUS    RESTARTS   AGE
plain   0/1     Pending   0          0s
```

## Troubleshoot It

*What should happen?* The Pod runs. *What happened?* `Pending`, no node assigned. *Which component decides?* The
scheduler: its event says why it found no node.

<!-- test: retry=10; contains=untolerated taint; output -->
```bash
kubectl get events -n scheduling-lab --field-selector involvedObject.name=plain,reason=FailedScheduling -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
0/1 nodes are available: 1 node(s) had untolerated taint(s). preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

Which taint?

<!-- test: contains=lab=demo:NoSchedule -->
```bash
kubectl describe node minikube | grep -E '^Taints'
```

Root cause: the only node is tainted `lab=demo:NoSchedule`, and `plain` has no matching toleration. Running Pods
(like `fast-disk` and the system Pods) are not affected: `NoSchedule` only blocks new placements.

## Fix It

Two fixes, for two situations. If the Pod **belongs** on that node, give it a toleration:

<!-- test: contains=condition met -->
```bash
kubectl apply -n scheduling-lab -f manifests/workloads/scheduling-toleration-pod.yaml
kubectl wait --for=condition=Ready pod/tolerant -n scheduling-lab --timeout=120s
```

If the taint was set by mistake, remove it (the `-` at the end), and the waiting Pod is scheduled:

<!-- test: contains=condition met -->
```bash
kubectl taint node minikube lab=demo:NoSchedule-
kubectl wait --for=condition=Ready pod/plain -n scheduling-lab --timeout=120s
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `nodeSelector` label nobody has (or a typo) | `Pending`, "didn't match Pod's node affinity/selector" | `kubectl get nodes --show-labels`; label the node or fix the selector |
| Expecting a toleration to attract a Pod | the Pod lands on other nodes | combine a toleration with a `nodeSelector` |
| Forgetting the effect in `kubectl taint` | `error: unknown taint spec` | `key=value:NoSchedule` |
| Removing a label and expecting Pods to move | nothing happens | delete the Pods; the Deployment recreates them where they fit |
| Tainting the only node | every new Pod `Pending` | remove the taint: `kubectl taint node NAME key=value:EFFECT-` |

## Best Practices

- Label nodes by capability (`disktype`, `gpu`), never by name; select capabilities, not hosts.
- Use taints to reserve special nodes, with a toleration *and* a nodeSelector on the Pods meant for them.
- Prefer letting the scheduler decide; constrain only for a real reason.

## Challenge

**Task:** reserve the node for "batch" work: taint it `dedicated=batch:NoSchedule`, then run a Pod `batch-job`
(`busybox:1.37`, `sleep 3600`) that may run there **and** must run on a node labelled `lab=batch`.

**Requirements:** the Pod runs; a Pod without toleration would not.

**Hints:** label first; `tolerations` with key `dedicated`; `nodeSelector` with `lab: batch`.

**Expected Result:** `batch-job` is `Running` on `minikube`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=minikube -->
```bash
kubectl label node minikube lab=batch
kubectl taint node minikube dedicated=batch:NoSchedule
kubectl apply -n scheduling-lab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: batch-job
spec:
  nodeSelector:
    lab: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  containers:
    - name: job
      image: busybox:1.37
      command: ["sleep", "3600"]
EOF
kubectl wait --for=condition=Ready pod/batch-job -n scheduling-lab --timeout=120s > /dev/null
kubectl get pod batch-job -n scheduling-lab -o jsonpath='{.spec.nodeName}{"\n"}'
kubectl taint node minikube dedicated=batch:NoSchedule-
kubectl label node minikube lab-
```

</details>

The toleration lets the Pod onto the reserved node; the nodeSelector makes it go there. With many nodes, ordinary
Pods stay off the batch nodes and batch Pods stay on them: the standard pattern for GPU or high-memory node pools.

## Key Takeaways

- The scheduler filters nodes by free requests, `nodeSelector` labels and taints, then picks one.
- `nodeSelector` pulls a Pod to labelled nodes; a taint pushes Pods away unless they tolerate it.
- `Pending` + `FailedScheduling` event = read the message: it names the rule no node satisfied.
- Real-world use: GPU and high-memory node pools, nodes reserved for a team or for system agents, and draining nodes
  for maintenance (`kubectl drain` adds a `NoSchedule` taint).

## Cleanup

🧹 Remove the node label `disktype` and the taint `lab` (if still there), then delete the namespace `scheduling-lab`
and its Pods:

<!-- test: contains=deleted -->
```bash
kubectl label node minikube disktype- lab- > /dev/null 2>&1 || true
kubectl taint node minikube lab- dedicated- > /dev/null 2>&1 || true
kubectl describe node minikube | grep -E '^Taints'
kubectl delete namespace scheduling-lab
```

Next: [17 · Jobs and CronJobs](../17-jobs-cronjobs/README.md)
