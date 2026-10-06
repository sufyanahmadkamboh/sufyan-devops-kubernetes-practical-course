# Lab 08 · Probes: killed before it could start

> ⏱ 20 minutes · after lesson 14 · run every command from the course folder · cluster: minikube

## Objective

Diagnose an application that is restarted in a loop by its own liveness probe, and fix it with a startup probe.

## Setup

<!-- test: contains=created -->
```bash
kubectl create namespace lab-probes
```

## Steps

The backend takes 20 seconds to start (`STARTUP_DELAY=20`); its liveness probe allows 3 × 5 seconds:

<!-- test: contains=deployment.apps/backend created -->
```bash
kubectl apply -n lab-probes -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
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
            - name: STARTUP_DELAY
              value: "20"
          livenessProbe:
            httpGet: {path: /livez, port: 8080}
            periodSeconds: 5
            failureThreshold: 3
EOF
```

## Break It

Wait a minute and look at the restarts:

<!-- test: retry=40; absent=RESTARTS=0 -->
```bash
echo "RESTARTS=$(kubectl get pods -n lab-probes -l app=backend -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')"
```

<!-- test: output -->
```bash
kubectl get pods -n lab-probes -l app=backend
```

```text
NAME                       READY   STATUS    RESTARTS     AGE
backend-6b6b9d8c56-stjxb   1/1     Running   1 (2s ago)   18s
```

## Troubleshoot It

*What is broken?* The Pod restarts every 15–20 seconds and is never ready. *What should happen?* One start. *Who
restarts it?* The kubelet, because of a probe. Events:

<!-- test: retry=10; contains=Liveness probe failed; output -->
```bash
kubectl get events -n lab-probes --field-selector reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
Liveness probe failed: Get "http://10.244.120.111:8080/livez": dial tcp 10.244.120.111:8080: connect: connection refused
```

The logs of the killed container show it was still in its slow start:

<!-- test: contains=slow start -->
```bash
kubectl logs -n lab-probes -l app=backend --previous --tail=2 2>/dev/null || kubectl logs -n lab-probes -l app=backend --tail=2
```

Root cause: `connection refused` because nothing listens yet: the application needs 20 s, the liveness probe gives
up after 15 s and restarts it, so it never finishes starting. The probe is right that it does not answer, wrong about
why.

## Fix It

Add a startup probe: liveness is not checked until it succeeds, and it allows up to 60 seconds:

<!-- test: contains=patched -->
```bash
kubectl patch deployment backend -n lab-probes --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/startupProbe","value":{"httpGet":{"path":"/livez","port":8080},"periodSeconds":2,"failureThreshold":30}}]'
```

## Verification

<!-- test: contains=successfully rolled out; timeout=300 -->
```bash
kubectl rollout status deployment/backend -n lab-probes --timeout=180s
```

<!-- test: contains=RESTARTS=0 -->
```bash
echo "RESTARTS=$(kubectl get pods -n lab-probes -l app=backend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].status.containerStatuses[0].restartCount}')"
```

The new Pod started once and stayed up: the startup probe gave it time; liveness took over afterwards.

## Cleanup

🧹 Delete the namespace `lab-probes` and the backend:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-probes
```
