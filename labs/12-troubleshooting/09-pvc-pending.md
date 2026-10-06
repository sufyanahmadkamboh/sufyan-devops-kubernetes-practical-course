# Problem 09 · PVC stuck in Pending

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

A Pod that writes data to a volume never starts. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-09
kubectl apply -f labs/12-troubleshooting/manifests/09-pvc-pending.yaml -n trouble-09
sleep 5
```

## Symptoms

<!-- test: contains=Pending; output -->
```bash
kubectl get pod,pvc -n trouble-09
```

```text
NAME         READY   STATUS    RESTARTS   AGE
pod/writer   0/1     Pending   0          5s

NAME                         STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/data   Pending                                      fast-ssd       <unset>                 5s
```

Both are `Pending`: the Pod waits for its volume, the claim waits for storage.

## First command to run

Start with the object at the bottom of the chain, the claim:

<!-- test: contains=fast-ssd; output -->
```bash
kubectl describe pvc data -n trouble-09 | grep -A3 '^Events'
```

```text
Events:
  Type     Reason              Age   From                         Message
  ----     ------              ----  ----                         -------
  Warning  ProvisioningFailed  5s    persistentvolume-controller  storageclass.storage.k8s.io "fast-ssd" not found
```

## Investigation

Which StorageClasses does the cluster have?

<!-- test: contains=standard; output -->
```bash
kubectl get storageclass
```

```text
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate           false                  13h
```

Only `standard`. The claim asks for `fast-ssd`, a class from another cluster (a cloud provider's, perhaps), copied
into this manifest.

## Root cause

The PVC names a StorageClass that does not exist here, so no provisioner creates a volume; the Pod waits for the
claim forever. (Other causes of a `Pending` PVC: no default StorageClass, or a class with `WaitForFirstConsumer` that
waits until a Pod uses it.)

## Fix

A PVC's `storageClassName` cannot be changed, so recreate the claim without it (the default class is used):

<!-- test: contains=Running; timeout=300 -->
```bash
kubectl delete -n trouble-09 pod/writer pvc/data
sed '/storageClassName: fast-ssd/d' labs/12-troubleshooting/manifests/09-pvc-pending.yaml | kubectl apply -n trouble-09 -f -
kubectl wait --for=condition=Ready pod/writer -n trouble-09 --timeout=120s > /dev/null
kubectl get pod writer -n trouble-09
```

## Verification

<!-- test: contains=Bound -->
```bash
kubectl get pvc data -n trouble-09
kubectl exec writer -n trouble-09 -- cat /data/started.txt
```

## Lesson learned

- A Pod `Pending` because of a volume: look at the PVC, then its events.
- `kubectl get storageclass` shows what this cluster can provision; class names differ between clusters.
- PVC specs are mostly immutable: fix the manifest and recreate the claim (data in a bound volume needs a plan
  first).

## Cleanup

🧹 Delete the namespace `trouble-09` (the Pod, the claim and, through the `Delete` reclaim policy, its volume):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-09
```

Next: [Problem 10 · Ingress not working](10-ingress-not-working.md)
