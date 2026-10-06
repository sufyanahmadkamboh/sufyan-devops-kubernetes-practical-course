# 13 · Storage: volumes, PersistentVolumes, PersistentVolumeClaims and StorageClasses

> Level 7 · Storage · ⏱ 60 minutes · run every command from the course folder · cluster: minikube

## What is it?

A container's file system is temporary: when the container is replaced, everything it wrote is gone. A **volume** is
a folder that is mounted into the container and lives longer than it.

- **emptyDir**: a scratch folder that lives as long as the **Pod**; containers of the Pod share it.
- **PersistentVolume (PV)**: a piece of real storage in the cluster (a disk, a network share, a folder on a node),
  which lives independently of any Pod.
- **PersistentVolumeClaim (PVC)**: a request for storage by an application: "I need 1 GiB, read-write". Kubernetes
  binds the claim to a matching PV.
- **StorageClass**: a recipe for creating PVs automatically when a claim asks for one (**dynamic provisioning**).

An analogy: a PV is a storage unit in a warehouse, the PVC is your rental agreement ("one unit, 1 GiB"), and the
StorageClass is the warehouse's catalogue that builds a new unit when nobody has a free one.

## Why do we need it?

Databases, uploaded files and queues must survive restarts, updates and node failures. Pods are disposable (lessons
08–09 replace them freely); their data must not be. PV and PVC separate the two concerns: developers ask for storage
with a claim, without knowing whether it ends up on a cloud disk or a local folder; the cluster provides it.

## How does it work?

```text
Pod ── uses ──▶ PVC "db-data" (1Gi, RWO) ── bound to ──▶ PV (1Gi) ── backed by ──▶ real storage
                      │                                    ▲
                      │ no PV available?                   │ creates
                      └────▶ StorageClass "standard" ──▶ provisioner (Minikube: a folder on the node)
```

- **Static provisioning:** an administrator creates PVs by hand; claims bind to a matching one.
- **Dynamic provisioning:** the claim names a StorageClass (or uses the default one), and its provisioner creates a
  PV for it. This is the normal case in clouds (EBS, Azure Disk, Persistent Disk) and in Minikube (`standard`).
- **Access modes:** `ReadWriteOnce` (RWO, one node at a time, the usual for databases), `ReadOnlyMany`,
  `ReadWriteMany` (many nodes, needs shared storage such as NFS).
- **Reclaim policy:** what happens to the PV when its claim is deleted: `Delete` (the data goes too) or `Retain`
  (kept for an administrator).

## Architecture

```text
   Container
       │  mountPath /var/lib/postgresql
       ▼
      Pod  ── volumes: persistentVolumeClaim db-data
       │
       ▼
      PVC db-data ──bound──▶ PV pvc-…  ◀── created by ── StorageClass standard ── provisioner k8s.io/minikube-hostpath
                                │
                                ▼
                     /tmp/hostpath-provisioner/… on the Minikube node
```

## YAML

**emptyDir**, shared by two containers of one Pod:

<!-- test: contains=emptyDir -->
```bash
cat manifests/storage/storage-emptydir-pod.yaml
```

| Field | Meaning |
|---|---|
| `volumes[].emptyDir: {}` | an empty folder created with the Pod, deleted with the Pod |
| `volumeMounts[].mountPath` | where each container sees it (both use `/data`) |
| `readOnly: true` | the reader cannot change the files |

A **static** PV and a claim for it:

<!-- test: contains=PersistentVolume; contains=PersistentVolumeClaim -->
```bash
cat manifests/storage/storage-static-pv.yaml manifests/storage/storage-static-pvc.yaml
```

| Field | Meaning |
|---|---|
| `kind: PersistentVolume` | cluster-wide storage (no namespace) |
| `capacity.storage: 1Gi` | its size |
| `accessModes: [ReadWriteOnce]` | mounted read-write by one node at a time |
| `persistentVolumeReclaimPolicy` | `Delete` or `Retain` when the claim goes away |
| `storageClassName: manual` | a name only used for matching: the claim asks for class `manual` too |
| `hostPath.path` | the storage itself: a folder on the node (fine for a one-node lab, never for production) |
| `kind: PersistentVolumeClaim` | the request, in a namespace |
| `resources.requests.storage: 500Mi` | at least this much; a bigger PV can satisfy it |

The **database**: a claim without a class (so the default StorageClass provisions it) and PostgreSQL using it:

<!-- test: contains=claimName: db-data -->
```bash
cat manifests/storage/storage-db-pvc.yaml manifests/storage/storage-db-deployment.yaml
```

| Field | Meaning |
|---|---|
| `strategy.type: Recreate` | stop the old Pod before starting the new one: two databases must never share one volume |
| `volumes[].persistentVolumeClaim.claimName` | mount the claim `db-data` |
| `mountPath: /var/lib/postgresql` | PostgreSQL 18 keeps its data below this folder (not `/var/lib/postgresql/data`: lab 07) |

A **StorageClass** of your own:

<!-- test: contains=kind: StorageClass -->
```bash
cat manifests/storage/storage-class.yaml
```

| Field | Meaning |
|---|---|
| `provisioner` | the program that creates the storage (`k8s.io/minikube-hostpath` here; `ebs.csi.aws.com` on AWS…) |
| `reclaimPolicy: Retain` | volumes of this class are kept when their claim is deleted |
| `volumeBindingMode: Immediate` | create the volume as soon as the claim exists (`WaitForFirstConsumer` waits for a Pod) |

## Hands-On Lab

**1. emptyDir:** the writer appends the time every 5 seconds; the reader sees the same file.

<!-- test: contains=pod/scratch created -->
```bash
kubectl create namespace storage-lab
kubectl apply -n storage-lab -f manifests/storage/storage-emptydir-pod.yaml
kubectl wait --for=condition=Ready pod/scratch -n storage-lab --timeout=120s
```

<!-- test: retry=10; contains=UTC -->
```bash
kubectl exec -n storage-lab scratch -c reader -- cat /data/log.txt
```

**2. Static provisioning:** a hand-made PV, and a claim that binds to it.

<!-- test: contains=Bound; retry=10; output -->
```bash
kubectl apply -f manifests/storage/storage-static-pv.yaml > /dev/null
kubectl apply -n storage-lab -f manifests/storage/storage-static-pvc.yaml > /dev/null
kubectl get pvc lab-claim -n storage-lab
```

```text
NAME        STATUS   VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
lab-claim   Bound    lab-pv   1Gi        RWO            manual         <unset>                 0s
```

The claim asked for 500Mi and got the 1Gi PV: the smallest PV that satisfies it.

**3. Dynamic provisioning and a database:**

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl get storageclass
kubectl apply -n storage-lab -f manifests/storage/storage-db-pvc.yaml -f manifests/storage/storage-db-deployment.yaml
kubectl rollout status deployment/db -n storage-lab --timeout=180s
```

<!-- test: retry=15; contains=accepting connections -->
```bash
kubectl exec -n storage-lab deploy/db -- pg_isready -U app -d app
```

**4. Write data, delete the Pod, read it back:**

<!-- test: contains=INSERT 0 1 -->
```bash
kubectl exec -n storage-lab deploy/db -- psql -U app -d app -c "CREATE TABLE notes (t text); INSERT INTO notes VALUES ('survives restarts');"
```

<!-- test: contains=deleted; timeout=300 -->
```bash
kubectl delete pod -n storage-lab -l app=db
kubectl rollout status deployment/db -n storage-lab --timeout=180s
```

<!-- test: retry=15; contains=survives restarts; output -->
```bash
kubectl exec -n storage-lab deploy/db -- psql -U app -d app -c "SELECT * FROM notes;"
```

```text
         t         
-------------------
 survives restarts
(1 row)
```

## Expected Result

The reader container sees the writer's file; `lab-claim` is `Bound` to `lab-pv`; the database's claim `db-data` is
`Bound` to a PV created by the `standard` StorageClass; the row survives the deletion of the database Pod.

## Inspect

<!-- test: contains=db-data; contains=standard -->
```bash
kubectl get pvc -n storage-lab
kubectl get pv -o custom-columns=NAME:.metadata.name,CAPACITY:.spec.capacity.storage,CLAIM:.spec.claimRef.name,CLASS:.spec.storageClassName,RECLAIM:.spec.persistentVolumeReclaimPolicy,STATUS:.status.phase
```

Where the data really is, on the Minikube node:

<!-- test: contains=hostpath-provisioner -->
```bash
pv=$(kubectl get pvc db-data -n storage-lab -o jsonpath='{.spec.volumeName}')
kubectl get pv "$pv" -o jsonpath='{.spec.hostPath.path}{"\n"}'
```

## Experiment

`emptyDir` lives as long as the Pod, not longer. Recreate the scratch Pod and look for the old file:

<!-- test: contains=No such file -->
```bash
kubectl delete pod scratch -n storage-lab
kubectl apply -n storage-lab -f manifests/storage/storage-emptydir-pod.yaml > /dev/null
kubectl wait --for=condition=Ready pod/scratch -n storage-lab --timeout=120s > /dev/null
kubectl exec -n storage-lab scratch -c reader -- sh -c 'wc -l /data/log.txt; ls /data/old-log.txt' 2>&1 || true
```

A fresh, short log: the emptyDir was created again, empty. Use it for caches and files shared between containers,
never for data that must survive.

## Break It

A claim for a StorageClass that does not exist:

<!-- test: contains=persistentvolumeclaim/fast created -->
```bash
kubectl apply -n storage-lab -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fast
spec:
  storageClassName: fast-ssd
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
EOF
```

<!-- test: retry=5; contains=Pending; output -->
```bash
kubectl get pvc fast -n storage-lab
```

```text
NAME   STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
fast   Pending                                      fast-ssd       <unset>                 0s
```

## Troubleshoot It

*What should happen?* The claim becomes `Bound`. *What happened?* It stays `Pending`, and a Pod using it would stay
`Pending` too. *Which object controls it?* The claim's StorageClass. Events first:

<!-- test: retry=10; contains=not found; output=tail:1 -->
```bash
kubectl describe pvc fast -n storage-lab | tail -3
```

```text
...
  Warning  ProvisioningFailed  0s    persistentvolume-controller  storageclass.storage.k8s.io "fast-ssd" not found
```

<!-- test: contains=standard -->
```bash
kubectl get storageclass
```

Root cause: nobody can provision class `fast-ssd`; this cluster has `standard`. (In a cloud, the same message appears
when a manifest written for one provider is used on another.)

## Fix It

`storageClassName` cannot be changed on an existing claim: delete it and create it with an existing class. Here, the
StorageClass of this lesson (`keep`):

<!-- test: contains=Bound; retry=10 -->
```bash
kubectl delete pvc fast -n storage-lab --timeout=120s > /dev/null
kubectl apply -f manifests/storage/storage-class.yaml > /dev/null
kubectl apply -n storage-lab -f - <<'EOF' > /dev/null
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fast
spec:
  storageClassName: keep
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
EOF
kubectl get pvc fast -n storage-lab
```

Because the class `keep` has `reclaimPolicy: Retain`, its volume will outlive the claim: the Cleanup deletes it.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Unknown `storageClassName` | PVC `Pending`, `storageclass … not found` | `kubectl get storageclass`; use an existing class |
| No default StorageClass and no class given | PVC `Pending` forever, no events | name a class, or mark one default |
| `ReadWriteMany` on storage that only supports RWO | `Pending` or mount errors | RWO for databases; shared file storage for RWX |
| Data in the container file system or `emptyDir` | data lost on restart | a PVC |
| Deleting a PVC still used by a Pod | the PVC stays `Terminating` (pvc-protection) | delete the Pod (or Deployment) first |
| `RollingUpdate` for a database on RWO | the new Pod cannot mount the volume | `strategy: Recreate`, or a StatefulSet (lesson 19) |

## Best Practices

- Applications ask with PVCs; leave PVs to StorageClasses (dynamic provisioning).
- `Retain` for data you cannot lose; take backups anyway (a volume is not a backup).
- Never use `hostPath` for real workloads: the data is tied to one node and visible to anything on it.

## Challenge

**Task:** run a second database `notes-db` with its own 500Mi claim `notes-data` of class `standard`, write one row,
delete the Deployment **and** create it again, and show that the row is still there.

**Requirements:** reuse the database manifest with new names; the claim is not deleted.

**Hints:** `sed 's/db-data/notes-data/; s/name: db$/name: notes-db/'` turns the files into new ones; a claim outlives
the Deployment that used it.

**Expected Result:** the row is returned after the Deployment was deleted and recreated.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=kept; timeout=600 -->
```bash
sed 's/name: db-data/name: notes-data/; s/storage: 1Gi/storage: 500Mi/' manifests/storage/storage-db-pvc.yaml > notes-pvc.yaml
sed 's/claimName: db-data/claimName: notes-data/; s/name: db$/name: notes-db/; s/app: db/app: notes-db/' manifests/storage/storage-db-deployment.yaml > notes-db.yaml
kubectl apply -n storage-lab -f notes-pvc.yaml -f notes-db.yaml > /dev/null
kubectl rollout status deployment/notes-db -n storage-lab --timeout=180s > /dev/null
for i in $(seq 1 30); do kubectl exec -n storage-lab deploy/notes-db -- pg_isready -U app -d app > /dev/null 2>&1 && break; sleep 2; done
kubectl exec -n storage-lab deploy/notes-db -- psql -U app -d app -c "CREATE TABLE notes (t text); INSERT INTO notes VALUES ('kept');" > /dev/null
kubectl delete deployment notes-db -n storage-lab --wait=true
kubectl apply -n storage-lab -f notes-db.yaml > /dev/null
kubectl rollout status deployment/notes-db -n storage-lab --timeout=180s > /dev/null
for i in $(seq 1 30); do kubectl exec -n storage-lab deploy/notes-db -- pg_isready -U app -d app > /dev/null 2>&1 && break; sleep 2; done
kubectl exec -n storage-lab deploy/notes-db -- psql -U app -d app -tAc "SELECT t FROM notes;"
rm notes-pvc.yaml notes-db.yaml
```

</details>

The claim and its volume do not belong to the Deployment: deleting the Deployment deleted the Pod, not the data.
Only deleting the claim (with reclaim policy `Delete`) removes the data.

## Key Takeaways

- emptyDir: per Pod, temporary, shared between its containers. PVC: storage that outlives Pods.
- Applications request storage with a PVC; a PV satisfies it, made by hand or by a StorageClass's provisioner.
- `Pending` PVC: read its events (wrong class, no default class, nothing that matches).
- Real-world use: every database, message queue and file store on Kubernetes keeps its data on PVCs backed by cloud
  disks, with StorageClasses chosen for speed and reclaim policy.

## Cleanup

🧹 Delete, in this order, the database Deployments (so the claims are no longer in use), the namespace `storage-lab`
with its claims and Pods, the hand-made PV `lab-pv`, the class `keep`, and the volume it retained:

<!-- test: contains=deleted; timeout=300 -->
```bash
kept=$(kubectl get pvc fast -n storage-lab -o jsonpath='{.spec.volumeName}' 2> /dev/null || true)
kubectl delete deployment --all -n storage-lab --timeout=120s
kubectl delete namespace storage-lab --timeout=180s
kubectl delete pv lab-pv --ignore-not-found --timeout=60s
kubectl delete storageclass keep --ignore-not-found
[ -n "$kept" ] && kubectl delete pv "$kept" --ignore-not-found --timeout=60s || true
```

Next: [14 · Health checks: liveness, readiness and startup probes](../14-health-checks/README.md)
