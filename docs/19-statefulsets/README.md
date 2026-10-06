# 19 · StatefulSets

> Level 12 · Stateful Applications · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **StatefulSet** runs Pods that each have a **stable identity**: a fixed name (`notes-0`, `notes-1`, `notes-2`), a
fixed DNS name, and **their own disk** that follows them when they are replaced. Pods are created in order and
removed in reverse order.

The analogy: Deployment Pods are like hotel guests: any room will do, and nobody minds who is in which room. StatefulSet
Pods are like employees with a desk and a locker: `notes-1` always comes back to locker `data-notes-1`.

## Why do we need it?

Deployments treat Pods as **interchangeable**: random names, shared or no storage, any order. That is perfect for a
stateless web server. It breaks for databases and clustered systems (PostgreSQL replicas, Kafka, Elasticsearch,
etcd): each member keeps its own data, the others must find it by a stable name, and the first member often has to
start before the others join.

```text
Deployment   → interchangeable Pods: web-7f9c-abcde, web-7f9c-xyz12, same template, no own disk
StatefulSet  → stable identity and storage: notes-0, notes-1, notes-2, each with data-notes-N
```

## How does it work?

- **Names**: `<statefulset>-<ordinal>`, from 0 up. A replaced Pod gets the **same** name.
- **Order**: with the default `podManagementPolicy: OrderedReady`, `notes-1` is created only when `notes-0` is ready;
  scaling down removes the highest number first.
- **Storage**: `volumeClaimTemplates` creates one PersistentVolumeClaim per Pod (`data-notes-0`, …), and the Pod with
  that number always mounts it. The PVCs are **not** deleted with the Pods or the StatefulSet: the data survives.
- **Network identity**: a **headless Service** (`clusterIP: None`) gives each Pod a DNS name,
  `notes-0.notes.<namespace>.svc.cluster.local`, so the members can address each other directly.

## Architecture

```text
                 headless Service "notes" (clusterIP: None)
                 notes-0.notes   notes-1.notes   notes-2.notes     ← one DNS name per Pod
                       │               │               │
StatefulSet notes ─▶ notes-0 ──▶  notes-1 ──▶   notes-2              created in this order
                       │               │               │
                 PVC data-notes-0  data-notes-1  data-notes-2        one disk each, kept forever
                       │               │               │
                    PV (standard StorageClass, Minikube's hostpath provisioner)
```

## YAML

<!-- test: contains=kind: StatefulSet; contains=clusterIP: None -->
```bash
cat manifests/workloads/statefulsets-notes.yaml
```

| Field | Meaning |
|---|---|
| `Service` with `clusterIP: None` | a **headless** Service: no load-balancing IP; DNS answers with the Pods' own addresses and gives each Pod a name |
| `kind: StatefulSet` (`apps/v1`) | Pods with stable names, order and storage |
| `spec.serviceName: notes` | the headless Service that names the Pods; it must exist |
| `spec.replicas: 3` | `notes-0`, `notes-1`, `notes-2` |
| `initContainers` | runs before the main container (lesson 06): writes the page once, on first boot only |
| `volumeClaimTemplates` | a template for one PVC per Pod; the PVC is named `<template name>-<pod name>`: `data-notes-0` |
| `storageClassName: standard` | Minikube's StorageClass, which creates the disks automatically (lesson 13) |
| `accessModes: ReadWriteOnce` | the disk is mounted by one node at a time |

## Hands-On Lab

**1. Create the namespace and the StatefulSet**, and watch the Pods start one after the other:

<!-- test: contains=statefulset.apps/notes created; timeout=300 -->
```bash
kubectl create namespace sts-lab
kubectl apply -f manifests/workloads/statefulsets-notes.yaml -n sts-lab
kubectl rollout status statefulset/notes -n sts-lab --timeout=240s
```

**2. Stable names, in creation order:**

<!-- test: contains=notes-0; contains=notes-2; output -->
```bash
kubectl get pods -n sts-lab -l app=notes --sort-by=.metadata.creationTimestamp -o custom-columns=NAME:.metadata.name,CREATED:.metadata.creationTimestamp,STATUS:.status.phase
```

```text
NAME      CREATED                STATUS
notes-0   2026-10-06T14:02:09Z   Running
notes-1   2026-10-06T14:02:11Z   Running
notes-2   2026-10-06T14:02:12Z   Running
```

**3. One disk per Pod:**

<!-- test: contains=data-notes-0; contains=Bound; output -->
```bash
kubectl get pvc -n sts-lab
```

```text
NAME           STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
data-notes-0   Bound    pvc-d64dc2f2-f2e8-4a15-9e07-2f3134e589ad   64Mi       RWO            standard       <unset>                 4s
data-notes-1   Bound    pvc-5291a53e-9015-4f64-8a03-78fd05636d77   64Mi       RWO            standard       <unset>                 2s
data-notes-2   Bound    pvc-ccc0fbad-746e-4000-a71b-fe7ae9957b5a   64Mi       RWO            standard       <unset>                 1s
```

**4. One DNS name per Pod**, through the headless Service: ask for `notes-1` by name from a client Pod.

<!-- test: contains=notes-1: created at; output -->
```bash
kubectl run client -n sts-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://notes-1.notes
```

```text
notes-1: created at 14:02:11
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_sts-lab
notes-1: created at 14:02:11
```

## Expected Result

Three Pods `notes-0`, `notes-1`, `notes-2`, created a few seconds apart in that order; three PVCs `Bound`; each Pod
reachable at `notes-N.notes` and answering with its own name.

## Inspect

The headless Service has no cluster IP, and DNS returns the three Pod addresses:

<!-- test: contains=None -->
```bash
kubectl get service notes -n sts-lab
kubectl run dns -n sts-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- nslookup notes.sts-lab.svc.cluster.local
```

## Experiment

Delete `notes-1`. A Deployment would create a Pod with a new random name and an empty disk; a StatefulSet recreates
`notes-1`, with **the same disk**:

<!-- test: contains=notes-1: created at; output -->
```bash
kubectl delete pod notes-1 -n sts-lab
kubectl wait --for=condition=Ready pod/notes-1 -n sts-lab --timeout=180s > /dev/null
kubectl run client -n sts-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://notes-1.notes
```

```text
pod "notes-1" deleted from sts-lab namespace
notes-1: created at 14:02:11
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_sts-lab
notes-1: created at 14:02:11
```

The time is the **first** boot's time: the init container found `index.html` on `data-notes-1` and did not overwrite
it. The new Pod got the old identity and the old data. Scale down to one replica: `notes-2` goes first, then
`notes-1` (reverse order), and their PVCs stay for the day you scale up again.

## Break It

A second StatefulSet, `archive`, asks for a StorageClass called `fast-ssd`:

<!-- test: contains=Pending; output -->
```bash
kubectl apply -f manifests/workloads/statefulsets-broken.yaml -n sts-lab > /dev/null
sleep 10
kubectl get pods,pvc -n sts-lab -l app=archive
kubectl get pvc data-archive-0 -n sts-lab
```

```text
NAME            READY   STATUS    RESTARTS   AGE
pod/archive-0   0/1     Pending   0          10s

NAME                                   STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/data-archive-0   Pending                                      fast-ssd       <unset>                 10s
NAME             STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
data-archive-0   Pending                                      fast-ssd       <unset>                 10s
```

## Troubleshoot It

*What should happen?* `archive-0` runs. *What happened?* It is `Pending`, and only `archive-0` exists: a StatefulSet
waits for each Pod before the next. *Which object is it waiting for?* The Pod's events:

<!-- test: contains=unbound; output=tail:1 -->
```bash
kubectl describe pod archive-0 -n sts-lab | grep -A4 '^Events' | tail -1
```

```text
  Warning  FailedScheduling  10s   default-scheduler  0/1 nodes are available: pod has unbound immediate PersistentVolumeClaims. not found
```

The Pod waits for its PVC. Why is the PVC not bound?

<!-- test: contains=fast-ssd; output=tail:1 -->
```bash
kubectl describe pvc data-archive-0 -n sts-lab | grep -A4 '^Events' | tail -1
kubectl get storageclass
```

```text
...
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate           false                  13h
```

Root cause: the cluster has one StorageClass, `standard`; nobody can create a `fast-ssd` disk, so the PVC stays
`Pending`, so the Pod cannot be scheduled, so the StatefulSet never gets to `archive-1`.

## Fix It

`volumeClaimTemplates` cannot be changed on an existing StatefulSet, and the PVC it already created keeps the wrong
class. Delete both (the StatefulSet first, so no Pod uses the PVC), then create it with the right class:

<!-- test: contains=archive; timeout=300 -->
```bash
kubectl delete statefulset archive -n sts-lab --timeout=60s
kubectl delete pvc data-archive-0 -n sts-lab --timeout=60s
sed 's/storageClassName: fast-ssd/storageClassName: standard/' manifests/workloads/statefulsets-broken.yaml | kubectl apply -n sts-lab -f -
kubectl rollout status statefulset/archive -n sts-lab --timeout=240s
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| No headless Service, or a different `serviceName` | the Pods run but `notes-0.notes` does not resolve | create the headless Service named in `serviceName` |
| A StorageClass that does not exist | PVC and first Pod `Pending` | `kubectl get storageclass`; fix the template, delete the StatefulSet and its PVCs |
| Expecting PVCs to go away with the StatefulSet | disks pile up; old data reappears on re-create | delete PVCs explicitly when the data is really no longer needed |
| Changing `volumeClaimTemplates` with apply | `Forbidden: updates to statefulset spec ... are forbidden` | delete and re-create (with `--cascade=orphan` to keep the Pods running) |
| Using a StatefulSet for a stateless app | slower rollouts, ordering for nothing | use a Deployment |

## Best Practices

- For production databases, prefer a well-maintained operator or Helm chart (lesson 28): replication, backup and
  failover are more than a StatefulSet.
- Set a `PodDisruptionBudget` and resource requests for stateful members.
- Back up the data in the PVCs; a PVC is not a backup.

## Challenge

**Task:** scale `notes` to 5 replicas, then back to 2. Predict the names that appear and disappear, and how many PVCs
remain at the end.

**Requirements:** `kubectl scale`; verify your prediction with `kubectl get`.

**Hints:** scaling up adds the next numbers in order; scaling down removes the highest numbers; PVCs stay.

**Expected Result:** `notes-3` and `notes-4` appear, then `notes-4`, `notes-3`, `notes-2` go; 5 PVCs remain.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=data-notes-4; timeout=420 -->
```bash
kubectl scale statefulset notes -n sts-lab --replicas=5
kubectl rollout status statefulset/notes -n sts-lab --timeout=240s
kubectl scale statefulset notes -n sts-lab --replicas=2
kubectl wait --for=delete pod/notes-2 -n sts-lab --timeout=120s
kubectl get pods -n sts-lab -l app=notes
kubectl get pvc -n sts-lab -l app=notes -o name
```

</details>

Two Pods remain (`notes-0`, `notes-1`) but five PVCs: a StatefulSet never deletes data on its own. Scale up to 5
again and `notes-4` gets its old disk back.

## Key Takeaways

- StatefulSet = stable names (`name-0…`), ordered start/stop, one PVC per Pod that survives the Pod.
- A headless Service (`clusterIP: None`) gives each Pod a DNS name: `pod.service.namespace.svc.cluster.local`.
- PVCs outlive Pods and the StatefulSet: deleting data is always an explicit step.
- Real-world use: databases and clustered systems (PostgreSQL, MySQL, Kafka, Redis, Elasticsearch, etcd), usually
  installed through an operator or a Helm chart that uses StatefulSets underneath.

## Cleanup

🧹 Delete the namespace `sts-lab`: the StatefulSets, their Pods, the headless Service and the PVCs (and with them the
data on their disks):

<!-- test: contains=deleted; timeout=300 -->
```bash
kubectl delete namespace sts-lab --timeout=240s
```

Next: [20 · Ingress](../20-ingress/README.md)
