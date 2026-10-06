# 29 · Capstone: a production-style application

> Level 16 · Production-Style Capstone · ⏱ 2–3 hours · run every command from the course folder · cluster: minikube

## What is it?

The whole course in one application. Everything you learned, used once, on purpose: a frontend, a backend API and a
PostgreSQL database in their own namespace, reachable through an Ingress, configured with ConfigMaps and a Secret,
persistent, health-checked, limited, autoscaled, backed up every night, isolated by NetworkPolicies and protected by
RBAC. You deploy it, inspect it, access it, scale it, update it, roll it back, and then break it six ways and fix it.

## Why do we need it?

Each lesson taught one object in isolation. Real applications are made of many objects that depend on each other: a
Service that selects the wrong label, a ConfigMap with one wrong value or a NetworkPolicy that is too strict breaks
the whole chain, and the symptom appears somewhere else. The capstone trains exactly that: following a symptom
through the objects to its cause.

## How does it work?

| Concept | Where in the capstone | Lesson |
|---|---|---|
| Namespace | `learning-app` | 05 |
| Deployments, ReplicaSets, Pods, labels, selectors | frontend and backend | 06–09 |
| Services, DNS | `frontend`, `backend`, headless `db`; the frontend proxies to `http://backend:8080` | 10 |
| ConfigMaps | backend settings (env), frontend nginx.conf and page (files) | 11 |
| Secret | database credentials, the password mounted as a file | 12 |
| StatefulSet, PVC, StorageClass | PostgreSQL with a 1 Gi volume from `standard`; backups on their own PVC | 13, 19 |
| Probes | startup, liveness and readiness on every container | 14 |
| Requests and limits | every container | 15 |
| CronJob, Job | nightly `pg_dump`, started by hand with `kubectl create job --from=cronjob/...` | 17 |
| Ingress | `learning-app.local` → frontend | 20 |
| NetworkPolicies | default deny; ingress → frontend → backend → database ← backup | 22 |
| ServiceAccounts | one per component, no API token mounted | 23 |
| RBAC | the user `developer` may view, not change | 24 |
| Rolling updates, rollbacks, scaling, HPA | backend 1.0.0 → 2.0.0 → 1.0.0; HPA 2–5 Pods | 09, 25, 26 |
| Helm | the same application from the course chart | 28 |

## Architecture

```text
                         User
                           │  http://learning-app.local
                           ▼
                       Ingress (nginx, addon)
                           │
                           ▼
                    Frontend Service ─────▶ Frontend Pods (nginx, non-root, read-only)
                                                  │  /api/ → http://backend:8080
                                                  ▼
                                           Backend Service ─────▶ Backend Pods (2–5, HPA)
                                                                        │  db:5432
                                                                        ▼
                                                                 Database Service (headless)
                                                                        │
                                                                        ▼
                                                                 Database Pod db-0 (StatefulSet)
                                                                        │
                                                                        ▼
                                                                  PVC data-db-0 ──▶ persistent data
   NetworkPolicies:  ingress-nginx ─▶ frontend ─▶ backend ─▶ db ◀─ backup CronJob      (frontend ✕ db)
```

## YAML

The capstone is a folder of ordinary manifests, one folder per concern:

<!-- test: contains=statefulset.yaml; output -->
```bash
find capstone -name '*.yaml' | sort
```

```text
capstone/backend/configmap.yaml
capstone/backend/deployment.yaml
capstone/backend/service.yaml
capstone/database/secret.yaml
capstone/database/service.yaml
capstone/database/statefulset.yaml
capstone/frontend/configmap.yaml
capstone/frontend/deployment.yaml
capstone/frontend/service.yaml
capstone/ingress/ingress.yaml
capstone/jobs/backup-cronjob.yaml
capstone/namespace.yaml
capstone/networking/network-policies.yaml
capstone/scaling/backend-hpa.yaml
capstone/security/developer-rbac.yaml
capstone/security/service-accounts.yaml
capstone/storage/backup-pvc.yaml
```

Read them before you apply them; every one starts with a comment that says what it is for. The parts that are new
compared with the lessons:

| Field | File | Why |
|---|---|---|
| `strategy.rollingUpdate.maxUnavailable: 0` | backend | an update never removes a working Pod before its replacement is ready |
| `securityContext.runAsUser: 65532`, `readOnlyRootFilesystem`, `capabilities.drop: [ALL]` | backend, frontend | least privilege; the kubelet can only verify numeric users for `runAsNonRoot` |
| `volumeMounts[].subPath` | frontend | mounts one key of a ConfigMap as one file, without hiding the rest of the folder |
| `volumeClaimTemplates` | database | the StatefulSet creates one PVC per Pod (`data-db-0`) that outlives the Pod |
| `automountServiceAccountToken: false` | all | none of the components talks to the Kubernetes API |

## Hands-On Lab

**1. Addons.** The Ingress needs an ingress controller, the HPA needs metrics (lessons 20 and 26):

<!-- test: contains=enabled; timeout=900 -->
```bash
minikube addons enable ingress 2>&1 | tail -1
minikube addons enable metrics-server 2>&1 | tail -1
```

**2. Deploy**, in dependency order (the namespace first, then identities and data, then the application):

<!-- test: contains=statefulset.apps/db created; contains=ingress.networking.k8s.io/learning-app created -->
```bash
kubectl apply -f capstone/namespace.yaml
kubectl apply -f capstone/security -f capstone/database -f capstone/storage -f capstone/backend \
  -f capstone/frontend -f capstone/networking -f capstone/ingress -f capstone/jobs -f capstone/scaling
```

**3. Wait** until every part is ready:

<!-- test: contains=successfully rolled out; timeout=900 -->
```bash
kubectl rollout status statefulset/db -n learning-app --timeout=300s
kubectl rollout status deployment/backend -n learning-app --timeout=300s
kubectl rollout status deployment/frontend -n learning-app --timeout=300s
```

## Expected Result

<!-- test: contains=db-0; contains=Bound; output -->
```bash
kubectl get pods,svc,ingress,pvc -n learning-app
```

```text
(recorded by the test run)
```

Five Pods `Running` and `1/1` (two frontend, two backend, `db-0`), three Services (`db` is headless: `None`), the
Ingress for `learning-app.local`, two PVCs `Bound`.

## Inspect

**The chain, object by object:** the Ingress points at the frontend Service, the Services have endpoints, the
backend reads its configuration:

<!-- test: contains=frontend; output -->
```bash
kubectl describe ingress learning-app -n learning-app | grep -A3 'Rules:'
kubectl get endpointslices -n learning-app -o custom-columns=SERVICE:.metadata.labels.kubernetes\.io/service-name,ADDRESSES:.endpoints[*].addresses[0]
```

```text
(recorded by the test run)
```

**Access it.** From your computer, through `port-forward` (open <http://localhost:8080> in a browser while it runs):

<!-- test: contains=Learning App -->
```bash
kubectl port-forward -n learning-app svc/frontend 8080:80 > /dev/null 2>&1 &
pf=$!
sleep 3
curl -s http://localhost:8080/ | grep -o '<title>.*</title>'
curl -s http://localhost:8080/api/info
echo
kill $pf
```

Through the Ingress, the way users reach it. A client inside the cluster calls the node's address with the host
name in the `Host` header (on your computer, `minikube tunnel` plus a hosts-file entry does the same for a browser):

<!-- test: contains=visits; retry=10; output -->
```bash
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- --header 'Host: learning-app.local' "http://$(minikube ip)/api/visits"
```

```text
(recorded by the test run)
```

The request went Ingress → frontend → backend → database, and the database counted it.

**The data survives the Pod.** Delete the database Pod; the StatefulSet recreates `db-0` with the same volume:

<!-- test: contains=pod "db-0" deleted -->
```bash
kubectl delete pod db-0 -n learning-app
kubectl wait --for=condition=Ready pod/db-0 -n learning-app --timeout=180s
kubectl wait --for=condition=Ready pod -n learning-app -l app.kubernetes.io/name=backend --timeout=180s
```

<!-- test: contains=visits; retry=10; output -->
```bash
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- --header 'Host: learning-app.local' "http://$(minikube ip)/api/visits"
```

```text
(recorded by the test run)
```

The counter continued from where it was: the data lives on the PVC, not in the Pod.

**Scale**, **update** and **roll back**:

<!-- test: contains=3/3 -->
```bash
kubectl scale deployment frontend -n learning-app --replicas=3
kubectl rollout status deployment/frontend -n learning-app --timeout=120s
kubectl get deployment frontend -n learning-app
```

<!-- test: contains=2.0.0; output=tail:1 -->
```bash
kubectl set image deployment/backend backend=learning-app/backend:2.0.0 -n learning-app
kubectl rollout status deployment/backend -n learning-app --timeout=180s
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- --header 'Host: learning-app.local' "http://$(minikube ip)/api/info"
```

```text
(recorded by the test run)
```

<!-- test: contains=1.0.0; output -->
```bash
kubectl rollout undo deployment/backend -n learning-app
kubectl rollout status deployment/backend -n learning-app --timeout=180s
kubectl get deployment backend -n learning-app -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
(recorded by the test run)
```

**The nightly backup**, run now from its CronJob:

<!-- test: contains=wrote /backup; output -->
```bash
kubectl create job backup-now --from=cronjob/db-backup -n learning-app
kubectl wait --for=condition=complete job/backup-now -n learning-app --timeout=180s
kubectl logs job/backup-now -n learning-app
```

```text
(recorded by the test run)
```

**Security, checked:** the developer may look, not delete; the frontend cannot reach the database:

<!-- test: contains=yes; contains=no; output -->
```bash
kubectl auth can-i list pods -n learning-app --as developer
kubectl auth can-i delete pods -n learning-app --as developer || true
```

```text
yes
no
```

<!-- test: contains=blocked -->
```bash
kubectl run nettest -n learning-app --rm -i --quiet --restart=Never --labels tier=frontend --image=busybox:1.37 -- \
  sh -c 'nc -z -w 3 db 5432 && echo "db reachable from the frontend" || echo "db blocked for the frontend"'
```

## Experiment

Put load on the backend and watch the HPA react (lesson 26). Each request burns 500 ms of CPU:

<!-- test: contains=REPLICAS; timeout=600 -->
```bash
kubectl run load -n learning-app --labels tier=frontend --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 600); do wget -qO- -T 5 "http://backend:8080/api/burn?ms=500" > /dev/null; done'
sleep 90
kubectl get hpa backend -n learning-app
kubectl delete pod load -n learning-app --wait=false
```

With a CPU target of 60% of each Pod's request (100m), sustained load makes the HPA add Pods up to 5; when the load
stops it removes them again after its 60-second stabilization window.

## Break It

Six realistic breaks, **one at a time**: break, look at the symptom, find the cause, fix, verify. Try to find each
cause yourself before reading the investigation, with the method of lesson 27: *what is broken, what should happen,
which object controls it, inspect it, events, logs, configuration*. The user's view, used after every break, is
one request through the Ingress:

<!-- test: contains=visits; retry=10 -->
```bash
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c "wget -qO- -T 10 --header 'Host: learning-app.local' http://$(minikube ip)/api/visits 2>&1 || true"
```

### Break 1 · Image

A typo in the version of a release:

<!-- test: anyof=ImagePullBackOff||ErrImagePull; retry=20; output -->
```bash
kubectl set image deployment/backend backend=learning-app/backend:1.0.1 -n learning-app > /dev/null
kubectl get pods -n learning-app -l app.kubernetes.io/name=backend
```

```text
(recorded by the test run)
```

*Investigation:* the new Pod cannot get its image; the events say why, and the rollout is stuck:

<!-- test: contains=1.0.1; output -->
```bash
kubectl get events -n learning-app --field-selector reason=Failed -o custom-columns=MESSAGE:.message | grep 1.0.1 | tail -1
```

```text
(recorded by the test run)
```

The users see nothing: with `maxUnavailable: 0` the old Pods keep serving until a new one is ready, which never
happens. *Root cause:* the tag `1.0.1` does not exist. *Fix:* roll back.

<!-- test: contains=successfully rolled out -->
```bash
kubectl rollout undo deployment/backend -n learning-app > /dev/null
kubectl rollout status deployment/backend -n learning-app --timeout=180s
```

### Break 2 · Service

A selector that matches nothing:

<!-- test: anyof=502||503||Bad Gateway; output -->
```bash
kubectl patch service backend -n learning-app -p '{"spec":{"selector":{"app.kubernetes.io/name":"backend-api"}}}' > /dev/null
sleep 3
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c "wget -qO- -T 10 --header 'Host: learning-app.local' http://$(minikube ip)/api/visits 2>&1 || true"
```

```text
(recorded by the test run)
```

*Investigation:* the frontend answers (the error comes from nginx), the backend Pods are `Running` and ready. Does
the backend Service have endpoints?

<!-- test: contains=backend-api; output -->
```bash
kubectl get endpointslices -n learning-app -l kubernetes.io/service-name=backend -o jsonpath='endpoints: [{.items[*].endpoints[*].addresses}]{"\n"}'
kubectl get service backend -n learning-app -o jsonpath='selector: {.spec.selector}{"\n"}'
kubectl get pods -n learning-app -l app.kubernetes.io/name=backend --show-labels | head -2
```

```text
(recorded by the test run)
```

*Root cause:* no endpoints, because the selector `backend-api` matches no Pod (they are `backend`). *Fix:* apply
the reviewed Service again.

<!-- test: contains=visits; retry=10 -->
```bash
kubectl apply -f capstone/backend/service.yaml > /dev/null
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c "wget -qO- -T 10 --header 'Host: learning-app.local' http://$(minikube ip)/api/visits 2>&1 || true"
```

### Break 3 · Configuration

The database host name is changed in the ConfigMap, and the backend restarted to pick it up:

<!-- test: contains=0/1; timeout=300 -->
```bash
kubectl create configmap backend-config -n learning-app --from-literal=MESSAGE="Hello from the capstone" \
  --from-literal=LOG_LEVEL=info --from-literal=DB_HOST=database --from-literal=DB_PORT=5432 \
  --dry-run=client -o yaml | kubectl apply -f - > /dev/null
kubectl rollout restart deployment/backend -n learning-app > /dev/null
sleep 20
kubectl rollout status deployment/backend -n learning-app --timeout=10s 2>&1 | tail -1 || true
kubectl get pods -n learning-app -l app.kubernetes.io/name=backend
```

The rollout does not finish: the new Pods start (liveness is fine) but never become ready, and `maxUnavailable: 0`
keeps the old ones.

*Investigation:* ask the new Pod why it is not ready:

<!-- test: contains=Readiness probe failed; retry=10; output -->
```bash
pod=$(kubectl get pods -n learning-app -l app.kubernetes.io/name=backend --sort-by=.metadata.creationTimestamp -o name | tail -1)
kubectl get "$pod" -n learning-app -o jsonpath='{.status.containerStatuses[0].ready}{"\n"}'
kubectl describe "$pod" -n learning-app | grep 'Readiness probe failed' | tail -1
```

```text
(recorded by the test run)
```

The probe gets `503` (`/readyz` answers `database unavailable`), or times out while the API is still trying to find
the database host. The configuration it got says why:

<!-- test: contains=database -->
```bash
kubectl get configmap backend-config -n learning-app -o jsonpath='DB_HOST={.data.DB_HOST}{"\n"}'
kubectl get service -n learning-app
```

*Root cause:* `DB_HOST=database`, and no Service has that name (it is `db`). *Fix:* the reviewed ConfigMap, and a
restart (environment variables are read when a container starts):

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl apply -f capstone/backend/configmap.yaml > /dev/null
kubectl rollout restart deployment/backend -n learning-app > /dev/null
kubectl rollout status deployment/backend -n learning-app --timeout=240s
```

### Break 4 · Probe

The frontend's readiness probe is pointed at the wrong port:

<!-- test: contains=0/1; retry=15; output -->
```bash
kubectl patch deployment frontend -n learning-app --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/port","value":9090}]' > /dev/null
sleep 15
kubectl get pods -n learning-app -l app.kubernetes.io/name=frontend
```

```text
(recorded by the test run)
```

*Investigation:* the new Pod runs but is never ready; its events say why:

<!-- test: contains=Readiness probe failed; retry=10; output -->
```bash
kubectl get events -n learning-app --field-selector reason=Unhealthy -o custom-columns=MESSAGE:.message | grep 9090 | tail -1
```

```text
(recorded by the test run)
```

*Root cause:* nothing listens on 9090; nginx listens on 8080. *Fix:* the reviewed Deployment.

<!-- test: contains=successfully rolled out -->
```bash
kubectl apply -f capstone/frontend/deployment.yaml > /dev/null
kubectl rollout status deployment/frontend -n learning-app --timeout=180s
```

### Break 5 · Storage

The backup volume is recreated with a StorageClass that does not exist, then a backup runs. Kubernetes refuses to
remove a claim that a Pod still uses (the claim stays `Terminating`, protected by the finalizer
`kubernetes.io/pvc-protection`), so the finished backup Jobs, whose Pods use it, are deleted first:

<!-- test: contains=Pending; retry=10; output -->
```bash
kubectl delete jobs --all -n learning-app > /dev/null
kubectl delete pvc db-backups -n learning-app --timeout=120s > /dev/null
sed 's/storageClassName: standard/storageClassName: fast-ssd/' capstone/storage/backup-pvc.yaml | kubectl apply -f - > /dev/null
kubectl create job backup-broken --from=cronjob/db-backup -n learning-app > /dev/null
sleep 10
kubectl get pvc db-backups -n learning-app
kubectl get pods -n learning-app -l job-name=backup-broken
```

```text
(recorded by the test run)
```

*Investigation:* the Pod waits for its volume, the volume waits for a provisioner:

<!-- test: contains=fast-ssd; output -->
```bash
kubectl describe pvc db-backups -n learning-app | grep -A3 '^Events' | tail -1
kubectl get storageclass
```

```text
(recorded by the test run)
```

*Root cause:* StorageClass `fast-ssd` does not exist; only `standard`. A PVC's class cannot be changed, so: delete
the broken Job and PVC, apply the reviewed PVC, run the backup again.

<!-- test: contains=wrote /backup; timeout=300 -->
```bash
kubectl delete job backup-broken -n learning-app > /dev/null
kubectl delete pvc db-backups -n learning-app --timeout=120s > /dev/null
kubectl apply -f capstone/storage/backup-pvc.yaml > /dev/null
kubectl create job backup-fixed --from=cronjob/db-backup -n learning-app > /dev/null
kubectl wait --for=condition=complete job/backup-fixed -n learning-app --timeout=180s > /dev/null
kubectl logs job/backup-fixed -n learning-app
```

### Break 6 · NetworkPolicy

A "tidy-up" of the backend policy changes the label it allows:

<!-- test: anyof=504||502||Gateway; output -->
```bash
kubectl patch networkpolicy backend-from-frontend -n learning-app --type=json \
  -p '[{"op":"replace","path":"/spec/ingress/0/from/0/podSelector/matchLabels/tier","value":"front"}]' > /dev/null
sleep 3
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c "wget -qO- -T 10 --header 'Host: learning-app.local' http://$(minikube ip)/api/visits 2>&1 || true"
```

```text
(recorded by the test run)
```

*Investigation:* every Pod is ready and every Service has endpoints (check both as in breaks 2 and 4), yet the
frontend cannot get an answer from the backend. Test the path directly, as the frontend:

<!-- test: contains=timed out -->
```bash
kubectl run nettest -n learning-app --rm -i --quiet --restart=Never --labels tier=frontend --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 http://backend:8080/readyz 2>&1 || echo "connection timed out"'
```

<!-- test: contains=tier=front; output -->
```bash
kubectl describe networkpolicy backend-from-frontend -n learning-app | grep -A2 'From:'
```

```text
(recorded by the test run)
```

*Root cause:* the policy allows Pods labelled `tier: front`; the frontend Pods are `tier: frontend`, so the default
deny applies. *Fix:* the reviewed policies.

<!-- test: contains=visits; retry=10 -->
```bash
kubectl apply -f capstone/networking/network-policies.yaml > /dev/null
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c "wget -qO- -T 10 --header 'Host: learning-app.local' http://$(minikube ip)/api/visits 2>&1 || true"
```

## Troubleshoot It

The six breaks, side by side: the symptom points at an object, the object's events or configuration name the cause.

| Break | What the user saw | Object that explained it | Root cause |
|---|---|---|---|
| Image | nothing (old Pods kept serving) | Deployment events: `ImagePullBackOff` | tag `1.0.1` does not exist |
| Service | `502 Bad Gateway` | Service: no endpoints, selector vs labels | selector `backend-api` |
| Configuration | nothing at first; the rollout never finished | new Pod: `Readiness probe failed` (`/readyz`: database unavailable) | `DB_HOST=database` |
| Probe | nothing (old Pod kept serving) | Pod events: probe on `:9090` refused | wrong probe port |
| Storage | backups silently not made | PVC events: no StorageClass `fast-ssd` | wrong StorageClass |
| NetworkPolicy | `504 Gateway Time-out` | policy `From:` vs the Pods' labels | `tier: front` |

The pattern behind all six: **user → Ingress → Service → endpoints → Pods → events → logs → configuration →
dependencies → policies**, and the habit of checking each layer instead of guessing.

## Fix It

Every fix above applied a reviewed file from `capstone/`, never a hand-made patch. Verify the whole application once
more, as the user, and the backups:

<!-- test: contains=visits; retry=10; output -->
```bash
kubectl run client -n default --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- --header 'Host: learning-app.local' "http://$(minikube ip)/api/visits"
kubectl get pods -n learning-app
```

```text
(recorded by the test run)
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Applying everything at once into a missing namespace | `namespaces "learning-app" not found` | the namespace first, then the rest |
| Fixing the live object by hand (`kubectl edit`) | the next `apply` brings the bug back, or undoes the fix | fix the file, apply the file |
| Reading only one Pod's state | the cause is in another object (Service, ConfigMap, policy) | follow the chain: Ingress → Service → endpoints → Pods → config → dependencies |
| Removing a NetworkPolicy to "make it work" | the security goal is lost | correct the selector; test the allowed and the forbidden path |

## Best Practices

- One namespace per application; labels on everything (`app.kubernetes.io/name`, `part-of`).
- Probes, requests and limits on every container; non-root, read-only file system, no capabilities.
- Default-deny NetworkPolicies plus explicit allows; one ServiceAccount per component; RBAC for people.
- Updates that cannot reduce capacity (`maxUnavailable: 0`), and rollbacks you have practised.
- Back up data with a CronJob and test the restore, not only the backup.

## Challenge

**Task:** deploy the same application with Helm, from the course chart, into a second namespace `learning-app-helm`,
with three backend replicas.

**Requirements:** use `helm/learning-app` and the values file `capstone/helm/values-capstone.yaml`; set the replica
count on the command line; the backend answers.

**Hints:** lesson 28; `helm install NAME CHART -n NS --create-namespace -f FILE --set KEY=VALUE`; look at
`helm/learning-app/values.yaml` for the key of the backend's replicas.

**Expected Result:** `helm list -n learning-app-helm` shows the release `deployed`; three backend Pods are ready.

## Solution

<details>
<summary>Solution</summary>

See the Helm part of the capstone in [capstone/helm/README.md](../../capstone/helm/README.md): it is filled in once
the course chart (lesson 28) is final.

</details>

## Key Takeaways

- A working application is a chain of objects; a break anywhere shows up at the user.
- Troubleshoot from the outside in: user → Ingress → Service → endpoints → Pods → events → logs → configuration →
  dependencies → policies.
- Fix the reviewed files and apply them; verify as the user, then check the parts the user does not see (backups).
- Real-world use: this is the shape of most applications on Kubernetes, and the six breaks are the six most common
  causes of incidents after a change.

## Cleanup

🧹 Delete the whole capstone: the namespace `learning-app` and everything in it, including both PVCs and their data.

<!-- test: contains=deleted; timeout=600 -->
```bash
kubectl delete namespace learning-app
```

You have finished the course. Go back to the [knowledge checklist](../../README.md#final-knowledge-checklist).
