# 14 · Health checks: liveness, readiness and startup probes

> Level 8 · Health Checks · ⏱ 50 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **probe** is a check the kubelet runs against a container, again and again: an HTTP request, a TCP connection or
a command. Kubernetes has three, each answering a different question:

```text
startupProbe     "Has the application finished starting?"   until it succeeds, the other two are not run
readinessProbe   "Can the application receive traffic?"     failing → removed from the Service, not restarted
livenessProbe    "Is the application alive?"                failing → the container is killed and restarted
```

## Why do we need it?

"The process runs" is not "the application works". A web server can be running while it is still loading, while its
database is unreachable, or while it is stuck in a deadlock. Without probes Kubernetes sends traffic to all of these
and never restarts the stuck one. With probes, users only reach Pods that can answer, broken Pods heal themselves, and
a rolling update stops before a broken version takes over.

## How does it work?

The kubelet on the Pod's node runs each probe every `periodSeconds`. After `failureThreshold` failures in a row:

| Probe fails | What Kubernetes does | Typical endpoint |
|---|---|---|
| startup | keeps waiting; after `failureThreshold × periodSeconds` it restarts the container | the same as liveness |
| readiness | marks the Pod **not Ready**: the Service stops sending it traffic; the Pod keeps running | checks dependencies (database) |
| liveness | **restarts** the container (the restart counter goes up) | checks only the process itself |

An HTTP probe succeeds on any status from 200 to 399. Our backend has two endpoints made for this: `/livez` (always
200 while the process runs) and `/readyz` (200 only when its database answers, or when it has none).

Rule of thumb: **liveness must never depend on other services.** If the database is down, restarting every backend
does not help; marking them not-ready does.

## Architecture

```text
              kubelet (on the node)
        ┌────────────┼──────────────┐
  startup /livez   readiness /readyz   liveness /livez
        │            │                    │
        ▼            ▼                    ▼
  ┌──────────────────────────────┐   fails 3×: restart the container
  │ backend Pod                  │
  │ Ready? ──yes──▶ in Service ──┼──▶ receives traffic
  │        ──no───▶ out of it    │
  └──────────────────────────────┘
```

## YAML

<!-- test: contains=startupProbe; contains=readinessProbe; contains=livenessProbe -->
```bash
cat manifests/deployments/probes-backend.yaml
```

| Field | Meaning |
|---|---|
| `env STARTUP_DELAY: "15"` | the backend waits 15 s before it listens, like an application that loads data |
| `startupProbe.httpGet.path/port` | the check: `GET http://POD_IP:8080/livez` |
| `startupProbe.periodSeconds: 2`, `failureThreshold: 30` | check every 2 s, give up after 30 failures (60 s) |
| `readinessProbe` on `/readyz`, `failureThreshold: 2` | 2 failures in a row (10 s) take the Pod out of the Service |
| `livenessProbe` on `/livez`, `periodSeconds: 10`, `failureThreshold: 3` | 30 s without an answer → restart |
| other fields | `initialDelaySeconds` (wait before the first check), `timeoutSeconds` (1 s default), `successThreshold` |

The Service `backend` (lesson 10) sends traffic to the Pods labelled `app: backend` that are **Ready**.

## Hands-On Lab

**1. Deploy, and look at the Pod while it starts:**

<!-- test: contains=0/1 -->
```bash
kubectl create namespace probes-lab
kubectl apply -n probes-lab -f manifests/deployments/probes-backend.yaml -f manifests/deployments/probes-backend-service.yaml
sleep 5
kubectl get pods -n probes-lab
```

`Running` but `0/1` ready: the container runs, the startup probe has not succeeded yet (the backend sleeps 15 s).

**2. Wait until it is ready:**

<!-- test: contains=successfully rolled out; output=tail:1 -->
```bash
kubectl rollout status deployment/backend -n probes-lab --timeout=120s
kubectl get pods -n probes-lab
```

```text
...
backend-758ff7b684-cn6j7   1/1     Running   0          17s
```

**3. Traffic through the Service:**

<!-- test: contains=Hello from the backend -->
```bash
kubectl run client -n probes-lab --image=busybox:1.37 -- sleep 3600
kubectl wait --for=condition=Ready pod/client -n probes-lab --timeout=120s
kubectl exec -n probes-lab client -- wget -qO- -T 5 http://backend/
```

## Expected Result

The Pod is `0/1` for about 15 seconds, then `1/1 Running` with 0 restarts, and the Service answers.

## Inspect

The probes as Kubernetes understood them, and the Pod's readiness condition:

<!-- test: contains=Liveness; contains=Readiness; contains=Startup -->
```bash
kubectl describe pod -n probes-lab -l app=backend | grep -E '^ +(Liveness|Readiness|Startup):'
kubectl get pods -n probes-lab -l app=backend -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}{"\n"}'
```

The Service's endpoints: the addresses it sends traffic to (only Ready Pods):

<!-- test: contains=true -->
```bash
kubectl get endpointslices -n probes-lab -l kubernetes.io/service-name=backend \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{"\n"}{end}'
```

## Experiment

Point the liveness probe at a path that does not exist, and watch Kubernetes restart the container:

<!-- test: contains=patched -->
```bash
kubectl patch deployment backend -n probes-lab --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/does-not-exist"}]'
```

<!-- test: retry=60; contains=Liveness probe failed -->
```bash
kubectl get events -n probes-lab --field-selector reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | grep Liveness | tail -1
```

<!-- test: retry=60; absent=RESTARTS=0 -->
```bash
echo "RESTARTS=$(kubectl get pods -n probes-lab -l app=backend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].status.containerStatuses[0].restartCount}')"
```

`404` is a failure, three in a row → the kubelet kills and restarts the container; after a few rounds the Pod shows
`CrashLoopBackOff` between restarts. Undo the experiment:

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl rollout undo deployment/backend -n probes-lab
kubectl rollout status deployment/backend -n probes-lab --timeout=180s
```

## Break It

Tell the backend to use a database that does not exist (lesson 12's variables, set with `kubectl set env`):

<!-- test: contains=deployment.apps/backend env updated -->
```bash
kubectl set env deployment/backend -n probes-lab DB_HOST=db-missing
```

<!-- test: fail; contains=timed out; output -->
```bash
kubectl rollout status deployment/backend -n probes-lab --timeout=60s 2>&1
```

```text
Waiting for deployment "backend" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "backend" rollout to finish: 1 old replicas are pending termination...
error: timed out waiting for the condition
```

## Troubleshoot It

*What should happen?* The update rolls out. *What happened?* It never finishes. *Which object controls it?* The
Deployment waits for the new Pod to be **Ready**. Look at the Pods:

<!-- test: contains=0/1; contains=1/1 -->
```bash
kubectl get pods -n probes-lab -l app=backend
```

The new Pod is `Running` but `0/1`; the old one is still `1/1` and still serving. Why is the new one not ready? Its
events:

<!-- test: retry=10; contains=Readiness probe failed; output -->
```bash
new=$(kubectl get pods -n probes-lab -l app=backend --sort-by=.metadata.creationTimestamp -o name | tail -1)
kubectl describe -n probes-lab "$new" | grep 'Readiness probe failed' | tail -1
```

```text
  Warning  Unhealthy  3s (x9 over 43s)   kubelet            spec.containers{backend}: Readiness probe failed: Get "http://10.244.120.109:8080/readyz": context deadline exceeded (Client.Timeout exceeded while awaiting headers)
```

Ask the endpoint yourself, from the client Pod:

<!-- test: contains=503 -->
```bash
ip=$(kubectl get -n probes-lab "$(kubectl get pods -n probes-lab -l app=backend --sort-by=.metadata.creationTimestamp -o name | tail -1)" -o jsonpath='{.status.podIP}')
kubectl exec -n probes-lab client -- wget -qO- -T 5 "http://$ip:8080/readyz" 2>&1 || true
```

Root cause: `/readyz` checks the database; `db-missing` does not exist, so the new Pod reports 503 and is kept out of
the Service. The readiness probe did its job: the broken version never received traffic, and the old version kept
serving users.

## Fix It

Roll back to the previous version of the Deployment (lesson 09):

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl rollout undo deployment/backend -n probes-lab
kubectl rollout status deployment/backend -n probes-lab --timeout=180s
kubectl exec -n probes-lab client -- wget -qO- -T 5 http://backend/readyz
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Liveness checks the database | the database blips, every Pod restarts | liveness = the process only; dependencies in readiness |
| Liveness without a startup probe on a slow application | restarted before it ever started: `CrashLoopBackOff` | a startup probe (lab 08) |
| Probe on the wrong port or path | `connection refused` / `404` in events, restarts or never Ready | match the container's real port and path |
| Timeouts too short | flapping between Ready and not Ready under load | `timeoutSeconds`, `failureThreshold` |
| No readiness probe | traffic reaches Pods that are still starting | add one to every Service-backed Pod |

## Best Practices

- Every long-running container gets a readiness probe; add liveness only when a restart really fixes the problem.
- Use a startup probe for applications that take long to start, instead of a long `initialDelaySeconds`.
- Keep probe endpoints cheap and fast; never let them do work.

## Challenge

**Task:** give a Deployment `web` (image `nginx:1.30-alpine`, 2 replicas) a readiness probe on `/` and a liveness
probe as a TCP check on port 80.

**Requirements:** both Pods `1/1`; `kubectl describe` shows both probes.

**Hints:** `tcpSocket: {port: 80}` instead of `httpGet`; `kubectl create deployment --dry-run=client -o yaml` for a
starting file.

**Expected Result:** `2/2` ready replicas.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=tcp-socket :80; timeout=300 -->
```bash
kubectl apply -n probes-lab -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: nginx
          image: nginx:1.30-alpine
          readinessProbe:
            httpGet: {path: /, port: 80}
            periodSeconds: 5
          livenessProbe:
            tcpSocket: {port: 80}
            periodSeconds: 10
EOF
kubectl rollout status deployment/web -n probes-lab --timeout=120s
kubectl describe pod -n probes-lab -l app=web | grep -E '^ +(Liveness|Readiness):' | sort -u
```

</details>

A TCP probe only checks that something accepts connections on the port: cheaper than HTTP, but it cannot see an
application that accepts connections and then answers errors.

## Key Takeaways

- Startup: finished starting? Readiness: may it get traffic? Liveness: is it alive (else restart)?
- A failing readiness probe removes the Pod from the Service and stalls a rolling update, protecting users.
- Liveness checks only the process; a liveness probe that depends on other services causes restart storms.
- Real-world use: every production Deployment has probes; they make rolling updates safe and recover hung
  processes without anyone being paged.

## Cleanup

🧹 Delete the namespace `probes-lab` (the backend, its Service, the `web` Deployment and the client):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace probes-lab
```

Next: [15 · Resource requests and limits](../15-resources/README.md)
