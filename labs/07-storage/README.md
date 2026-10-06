# Lab 07 · Storage: the database that refuses to start

> ⏱ 25 minutes · after lesson 13 · run every command from the course folder · cluster: minikube

## Objective

Run PostgreSQL 18 on a PersistentVolumeClaim, diagnose why it crashes with a mount path copied from an older guide,
fix it, and prove the data survives.

## Setup

<!-- test: contains=persistentvolumeclaim/db-data created -->
```bash
kubectl create namespace lab-storage
kubectl apply -n lab-storage -f manifests/storage/storage-db-pvc.yaml
```

## Steps

A colleague copied a manifest written for older PostgreSQL versions: the volume is mounted at
`/var/lib/postgresql/data`.

<!-- test: contains=deployment.apps/db created -->
```bash
sed 's#mountPath: /var/lib/postgresql  #mountPath: /var/lib/postgresql/data  #' manifests/storage/storage-db-deployment.yaml > old-db.yaml
grep 'mountPath' old-db.yaml
kubectl apply -n lab-storage -f old-db.yaml
```

## Break It

<!-- test: retry=30; anyof=CrashLoopBackOff||Error; output -->
```bash
kubectl get pods -n lab-storage -l app=db
```

```text
NAME                  READY   STATUS             RESTARTS     AGE
db-5b69d9bdfc-jzpj9   0/1     CrashLoopBackOff   1 (3s ago)   4s
```

## Troubleshoot It

*What is broken?* The database restarts again and again. *What should happen?* `Running`. *Which object controls it?*
The container itself exits: its logs say why (`--previous` shows the last crashed run):

<!-- test: retry=10; contains=/var/lib/postgresql; output=tail:6 -->
```bash
pod=$(kubectl get pods -n lab-storage -l app=db -o name | head -1)
kubectl logs -n lab-storage "$pod" --previous 2>/dev/null || kubectl logs -n lab-storage "$pod"
```

```text
...
       at /var/lib/postgresql which will then place PostgreSQL data in a
       subdirectory, allowing usage of "pg_upgrade --link" without mount point
       boundary issues.

       See https://github.com/docker-library/postgres/issues/37 for a (long)
       discussion around this process, and suggestions for how to do so.
```

Root cause: PostgreSQL 18 images keep their data in a version folder below `/var/lib/postgresql` and refuse to start
when a volume is mounted at the old `/var/lib/postgresql/data` path. The storage is fine; the mount path is wrong.

## Fix It

Use the path from lesson 13. The claim is not deleted, so nothing is lost:

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl apply -n lab-storage -f manifests/storage/storage-db-deployment.yaml
kubectl rollout status deployment/db -n lab-storage --timeout=180s
rm old-db.yaml
```

## Verification

<!-- test: retry=15; contains=accepting connections -->
```bash
kubectl exec -n lab-storage deploy/db -- pg_isready -U app -d app
```

<!-- test: contains=INSERT 0 1 -->
```bash
kubectl exec -n lab-storage deploy/db -- psql -U app -d app -c "CREATE TABLE checks (t text); INSERT INTO checks VALUES ('verified');"
```

<!-- test: timeout=300; contains=successfully rolled out -->
```bash
kubectl delete pod -n lab-storage -l app=db
kubectl rollout status deployment/db -n lab-storage --timeout=180s
```

<!-- test: retry=15; contains=verified -->
```bash
kubectl exec -n lab-storage deploy/db -- psql -U app -d app -tAc "SELECT t FROM checks;"
```

The row survives the new Pod: the data lives on the claim, in the right place.

## Cleanup

🧹 Delete the database first (so the claim is no longer in use), then the namespace `lab-storage` with its claim:

<!-- test: contains=deleted; timeout=300 -->
```bash
kubectl delete deployment db -n lab-storage --timeout=120s
kubectl delete namespace lab-storage --timeout=180s
```
