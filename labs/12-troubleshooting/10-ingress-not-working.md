# Problem 10 · Ingress not working

> Lab 12 · Troubleshooting · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

## Problem

The shop's website should answer on `shop.local` through the Ingress. The web Pod runs, the Service exists, but the
site answers with an error. Set it up (the Ingress controller is Minikube's `ingress` addon, lesson 20):

<!-- test: contains=created; timeout=600 -->
```bash
minikube addons enable ingress 2>&1 | tail -1
kubectl wait --for=condition=Ready pod -n ingress-nginx -l app.kubernetes.io/component=controller --timeout=300s > /dev/null
kubectl create namespace trouble-10
kubectl apply -f labs/12-troubleshooting/manifests/10-ingress.yaml -n trouble-10
kubectl rollout status deployment/web -n trouble-10 --timeout=120s
```

## Symptoms

Call the Ingress controller with the host name, from a client inside the cluster:

<!-- test: contains=503; output -->
```bash
kubectl run client -n trouble-10 --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  for i in $(seq 1 15); do
    out=$(wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx 2>&1)
    case "$out" in *503*) break;; esac; sleep 2
  done; echo "$out" | tail -1'
```

```text
wget: server returned error: HTTP/1.1 503 Service Temporarily Unavailable
```

`503` from the controller: it received the request and recognised the host, but has nowhere to send it.

## First command to run

<!-- test: contains=frontend; output -->
```bash
kubectl describe ingress shop -n trouble-10 | grep -A4 '^Rules'
```

```text
Rules:
  Host        Path  Backends
  ----        ----  --------
  shop.local  
              /   frontend:80 (<error: services "frontend" not found>)
```

## Investigation

The rule sends `/` to a Service called `frontend`, and Kubernetes says it does not exist. Which Services exist?

<!-- test: contains=web; output -->
```bash
kubectl get services -n trouble-10
```

```text
NAME   TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)   AGE
web    ClusterIP   10.99.0.235   <none>        80/TCP    6s
```

Other things to check when an Ingress fails: the `ingressClassName` (no controller picks up the Ingress → 404 from the
default backend or no answer), the host header (another host → 404), the Service port number, and whether the
Service has endpoints (problem 05).

## Root cause

The Ingress points at a Service name (`frontend`) that does not exist in its namespace; the Service is called `web`.

## Fix

<!-- test: contains=patched -->
```bash
kubectl patch ingress shop -n trouble-10 --type=json \
  -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/backend/service/name","value":"web"}]'
```

## Verification

<!-- test: contains=Welcome to nginx -->
```bash
kubectl run client2 -n trouble-10 --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  for i in $(seq 1 15); do
    wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx && exit 0; sleep 2
  done; exit 1' | grep -o '<title>.*</title>'
```

The controller retried in the loop above because it picks up Ingress changes within a few seconds, not instantly.

## Lesson learned

- Ingress problems are a chain: controller → rule (host, path) → Service → endpoints → Pods. Check each link.
- `kubectl describe ingress` shows each backend and an `<error: …>` when the Service is missing.
- 503 = the rule matched but the backend is missing or has no endpoints; 404 = no rule matched (host or path).

## Cleanup

🧹 Delete the namespace `trouble-10` (Deployment, Service, Ingress). The ingress addon stays enabled for later
lessons.

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-10
```

Next: [Problem 11 · Deployment rollout stuck](11-rollout-stuck.md)
