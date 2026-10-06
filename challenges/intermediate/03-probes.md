# Challenge 03 · Health checks for a slow backend

> Intermediate · after lesson 14 · ⏱ 20 minutes · cluster: minikube

## Task

Deploy the backend with `STARTUP_DELAY=10` and 2 replicas in a namespace `challenge-03`, with a startup, a readiness
and a liveness probe, so that it starts without a single restart.

## Requirements

- Startup probe on `/livez` allowing at least 30 seconds.
- Readiness probe on `/readyz`, liveness probe on `/livez`, port 8080.
- Both Pods `1/1`, restart count 0.

## Hints

- Lesson 14's manifest; `periodSeconds × failureThreshold` is the startup budget.

## Expected Result

`2/2` replicas ready, restart count 0 for both Pods.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=restarts=0 0; timeout=300 -->
```bash
kubectl create namespace challenge-03
kubectl apply -n challenge-03 -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 2
  selector:
    matchLabels: {app: backend}
  template:
    metadata:
      labels: {app: backend}
    spec:
      containers:
        - name: backend
          image: learning-app/backend:1.0.0
          env:
            - {name: STARTUP_DELAY, value: "10"}
          startupProbe:
            httpGet: {path: /livez, port: 8080}
            periodSeconds: 2
            failureThreshold: 20
          readinessProbe:
            httpGet: {path: /readyz, port: 8080}
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /livez, port: 8080}
            periodSeconds: 10
EOF
kubectl rollout status deployment/backend -n challenge-03 --timeout=180s
echo "restarts=$(kubectl get pods -n challenge-03 -l app=backend -o jsonpath='{.items[*].status.containerStatuses[0].restartCount}')"
```

</details>

## Explanation

The startup probe gives 2 × 20 = 40 seconds to start; liveness only begins afterwards, so the slow start is never
mistaken for a hang (lab 08 shows the opposite).

## Cleanup

🧹 Delete the namespace `challenge-03` and the backend:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-03
```
