# 18 · DaemonSets

> Level 11 · Jobs & CronJobs · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **DaemonSet** runs **one Pod on every suitable node** of the cluster. Add a node, and it gets its Pod
automatically; remove a node, and its Pod goes with it.

The analogy: a Deployment is "three cashiers, wherever there is room"; a DaemonSet is "one security guard in every
building", however many buildings there are.

## Why do we need it?

Some work belongs to the **node**, not to the application: collecting the node's log files, measuring its CPU and
disk, configuring its network. That work must happen exactly once per node. With a Deployment you would have to keep
`replicas` equal to the number of nodes and hope the scheduler spreads them evenly; a DaemonSet guarantees it.

You have already met DaemonSets: `kube-proxy` and `calico-node` (lesson 02) run on every node for exactly this reason.

## How does it work?

The DaemonSet controller looks at every node, checks whether the node is **suitable** (it matches the
`nodeSelector`, its taints are tolerated: lesson 16), and makes sure exactly one Pod of the DaemonSet runs there.
There is no `replicas` field: the number of Pods is the number of suitable nodes.

A node agent often needs to see the node itself, so it mounts a folder of the node with a **hostPath** volume (lesson
13 covers volumes): here, read-only, the folder where the node keeps the logs of every Pod.

## Architecture

```text
                 DaemonSet node-agent
                         │  one Pod per suitable node
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   Node 1          Node 2          Node 3 (added later)
   [node-agent]    [node-agent]    [node-agent]   ← created automatically
   reads           reads           reads
   /var/log/pods   /var/log/pods   /var/log/pods

Minikube has one node, so the DaemonSet runs one Pod.
```

## YAML

<!-- test: contains=kind: DaemonSet -->
```bash
cat manifests/workloads/daemonsets-node-agent.yaml
```

| Field | Meaning |
|---|---|
| `kind: DaemonSet` (`apps/v1`) | one Pod per suitable node; note: no `replicas` |
| `spec.selector.matchLabels` | which Pods belong to this DaemonSet (must match the template's labels, lesson 07) |
| `spec.template` | the Pod to run on each node |
| `env[].valueFrom.fieldRef: spec.nodeName` | the **Downward API**: Kubernetes fills the variable with the node's name |
| `volumes[].hostPath` | a folder of the node, `/var/log/pods`; `type: Directory` refuses to start if it does not exist |
| `volumeMounts[].readOnly: true` | the agent may read the node's logs, never change them |
| `resources` | small requests and limits: an agent on every node must be cheap (lesson 15) |

## Hands-On Lab

**1. A namespace and the DaemonSet:**

<!-- test: contains=daemonset.apps/node-agent created -->
```bash
kubectl create namespace ds-lab
kubectl apply -f manifests/workloads/daemonsets-node-agent.yaml -n ds-lab
kubectl rollout status daemonset/node-agent -n ds-lab --timeout=120s
```

**2. One Pod per node:**

<!-- test: contains=node-agent; output -->
```bash
kubectl get daemonset node-agent -n ds-lab
kubectl get nodes --no-headers | wc -l
```

```text
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
node-agent   1         1         1       1            1           <none>          1s
1
```

## Expected Result

`DESIRED 1, READY 1`: one node, one agent. `DESIRED` always equals the number of suitable nodes.

## Inspect

Where the Pod runs, and what the agent sees on its node:

<!-- test: contains=agent on minikube -->
```bash
kubectl get pods -n ds-lab -l app=node-agent -o wide
kubectl logs -n ds-lab -l app=node-agent --tail=1
```

The Pod runs on `minikube` and reads the node's Pod log folders: something no ordinary application Pod can see.

## Experiment

Delete the agent's Pod: the DaemonSet puts a new one on the same node, because that node has no agent any more.

<!-- test: contains=deleted -->
```bash
kubectl delete pod -n ds-lab -l app=node-agent --wait=false
```

<!-- test: contains=Running; absent=Terminating; retry=20 -->
```bash
kubectl get pods -n ds-lab -l app=node-agent
```

A new Pod with a new name. Try `kubectl scale daemonset node-agent --replicas=3 -n ds-lab`: it fails, because a
DaemonSet has no replicas to scale; the number of nodes decides.

## Break It

A second agent, meant only for nodes labelled `lab=agents`:

<!-- test: contains=disk-agent; output -->
```bash
kubectl apply -f manifests/workloads/daemonsets-disk-agent.yaml -n ds-lab > /dev/null
sleep 3
kubectl get daemonset disk-agent -n ds-lab
```

```text
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
disk-agent   0         0         0       0            0           lab=agents      3s
```

## Troubleshoot It

*What should happen?* One `disk-agent` Pod. *What happened?* `DESIRED 0`: the DaemonSet does not even want a Pod. No
Pod means no Pod events, so look at the **DaemonSet** and at what it asks of nodes: the `NODE SELECTOR` column says
`lab=agents`. Does any node have that label?

<!-- test: contains=minikube -->
```bash
kubectl get nodes -L lab
kubectl get nodes -l lab=agents 2>&1
```

The `LAB` column is empty and the label query finds nothing. Root cause: no node is "suitable", so zero Pods is the
correct desired state. Nothing is broken in Kubernetes: the DaemonSet does exactly what it was told.

## Fix It

Either remove the `nodeSelector`, or give the node the label (the usual way to say "this node is for this kind of
agent"):

<!-- test: contains=ready Pods: 1; output -->
```bash
kubectl label node minikube lab=agents
kubectl rollout status daemonset/disk-agent -n ds-lab --timeout=120s > /dev/null
kubectl get daemonset disk-agent -n ds-lab
kubectl get daemonset disk-agent -n ds-lab -o jsonpath='ready Pods: {.status.numberReady}{"\n"}'
```

```text
node/minikube labeled
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
disk-agent   1         1         1       1            1           lab=agents      5s
ready Pods: 1
```

As soon as a node matched, the DaemonSet created its Pod there, without any change to the DaemonSet itself.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| A `nodeSelector` no node matches | `DESIRED 0` | label the nodes (`kubectl get nodes -L KEY` shows them) or fix the selector |
| Nodes with taints (control plane, GPU nodes) | no Pod on those nodes | add `tolerations` to the template (lesson 16) |
| Heavy agents with no limits | every node loses CPU/memory to the agent | small `requests` and `limits` |
| Writable `hostPath` mounts | an agent can damage the node | `readOnly: true`; mount only what is needed |

## Best Practices

- Use DaemonSets only for node-level work; application Pods belong in Deployments.
- Keep agents small, give them resource limits and read-only access to the node.
- Update them with the default `RollingUpdate` strategy, one node at a time.

## Challenge

**Task:** find every DaemonSet in the whole cluster, with its namespace and how many Pods it wants.

**Requirements:** one command.

**Hints:** `-A`; the system namespaces have DaemonSets too.

**Expected Result:** `kube-proxy` and `calico-node` in `kube-system`, `node-agent` and `disk-agent` in `ds-lab`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=kube-proxy; contains=calico-node; contains=node-agent -->
```bash
kubectl get daemonsets -A
```

</details>

The cluster's own network components are DaemonSets: every node needs a `kube-proxy` (Service networking, lesson 10)
and a `calico-node` (Pod networking and NetworkPolicies, lessons 21–22). Your agents follow the same pattern.

## Key Takeaways

- DaemonSet = exactly one Pod on every suitable node; no `replicas`.
- "Suitable" = matches the `nodeSelector` and tolerates the node's taints.
- `DESIRED 0` is not an error: no node matches.
- Real-world use: log collectors (Fluent Bit), monitoring agents (node-exporter), network plugins (Calico, Cilium),
  storage drivers, security agents.

## Cleanup

🧹 Delete the namespace `ds-lab` (both DaemonSets and their Pods) and remove the `lab` label from the node:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace ds-lab
kubectl label node minikube lab-
```

Next: [19 · StatefulSets](../19-statefulsets/README.md)
