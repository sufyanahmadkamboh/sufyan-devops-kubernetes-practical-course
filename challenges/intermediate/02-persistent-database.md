# Challenge 02 · A database that keeps its data

> Intermediate · after lesson 13 · ⏱ 25 minutes · cluster: minikube

## Task

Run PostgreSQL 18 in a namespace `challenge-02` so that its data survives the deletion of its Pod.

## Requirements

- A PersistentVolumeClaim `pg-data` of 1Gi (default StorageClass).
- A Deployment `pg` (`postgres:18-alpine`, strategy `Recreate`) mounting the claim at the right path for PostgreSQL 18.
- Write a row, delete the Pod, read the row back.

## Hints

- `manifests/storage/storage-db-pvc.yaml` and `storage-db-deployment.yaml` are a good start (`sed` the names).
- The mount path is `/var/lib/postgresql` (lab 07 shows what happens otherwise).
- Wait for `pg_isready` before using `psql`.

## Expected Result

`SELECT` returns the row after the Pod was replaced.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=still here; timeout=600 -->
```bash
kubectl create namespace challenge-02
sed 's/name: db-data/name: pg-data/' manifests/storage/storage-db-pvc.yaml | kubectl apply -n challenge-02 -f -
sed 's/claimName: db-data/claimName: pg-data/; s/name: db$/name: pg/; s/app: db/app: pg/' manifests/storage/storage-db-deployment.yaml | kubectl apply -n challenge-02 -f -
kubectl rollout status deployment/pg -n challenge-02 --timeout=180s > /dev/null
for i in $(seq 1 30); do kubectl exec -n challenge-02 deploy/pg -- pg_isready -U app -d app > /dev/null 2>&1 && break; sleep 2; done
kubectl exec -n challenge-02 deploy/pg -- psql -U app -d app -c "CREATE TABLE t (v text); INSERT INTO t VALUES ('still here');" > /dev/null
kubectl delete pod -n challenge-02 -l app=pg > /dev/null
kubectl rollout status deployment/pg -n challenge-02 --timeout=180s > /dev/null
for i in $(seq 1 30); do kubectl exec -n challenge-02 deploy/pg -- pg_isready -U app -d app > /dev/null 2>&1 && break; sleep 2; done
kubectl exec -n challenge-02 deploy/pg -- psql -U app -d app -tAc "SELECT v FROM t;"
```

</details>

## Explanation

The Pod is disposable; the claim is not. `Recreate` stops the old Pod before the new one mounts the same
`ReadWriteOnce` volume.

## Cleanup

🧹 Delete the Deployment first (the claim is in use), then the namespace `challenge-02` with its claim:

<!-- test: contains=deleted; timeout=300 -->
```bash
kubectl delete deployment pg -n challenge-02 --timeout=120s
kubectl delete namespace challenge-02 --timeout=180s
```
