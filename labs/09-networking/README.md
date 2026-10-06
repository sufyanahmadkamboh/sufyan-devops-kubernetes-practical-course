# Lab 09 · Networking: the frontend cannot reach the backend

> Lessons 10, 21, 22 · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## Objective

A frontend calls the backend through the Service `backend`. After a "small cleanup" of the Service the calls fail.
Find which step of the path is broken (name → Service → Pods → port) and fix it.

## Setup

<!-- test: contains=deployment.apps/backend created -->
```bash
kubectl create namespace lab09
kubectl apply -f labs/09-networking/app.yaml -n lab09
kubectl rollout status deployment/backend -n lab09 --timeout=120s
kubectl wait --for=condition=Ready pod/frontend -n lab09 --timeout=120s
```

`app.yaml`: the course backend (port 8080), a Service `backend` in front of it, and a `frontend` Pod to send requests
from.

## Steps

The path works:

<!-- test: retry=10; contains=Hello from the backend -->
```bash
kubectl exec frontend -n lab09 -- wget -qO- -T 3 http://backend:8080/
```

## Break It

The cleaned-up Service is applied:

<!-- test: contains=refused; output -->
```bash
kubectl apply -f labs/09-networking/service-broken.yaml -n lab09 > /dev/null
sleep 2
kubectl exec frontend -n lab09 -- sh -c 'wget -qO- -T 3 http://backend:8080/ 2>&1 || true'
```

```text
wget: can't connect to remote host (10.110.86.226): Connection refused
```

## Troubleshoot It

Walk the path one step at a time.

1. **Does the name resolve?** Yes: the error shows an IP address, so DNS answered.
2. **Is it the Service's IP?**

<!-- test: contains=backend -->
```bash
kubectl get service backend -n lab09
```

3. **Does the Service have Pods behind it?** An EndpointSlice lists the Pod addresses and ports a Service forwards to:

<!-- test: contains=8081; output -->
```bash
kubectl get endpointslices -n lab09 -l kubernetes.io/service-name=backend
```

```text
NAME            ADDRESSTYPE   PORTS   ENDPOINTS        AGE
backend-hmx95   IPv4          8081    10.244.120.125   5s
```

The Pod is there (the selector matches), but the Service forwards to port **8081**.

4. **Which port does the container listen on?**

<!-- test: contains=8080 -->
```bash
kubectl get deployment backend -n lab09 -o jsonpath='{.spec.template.spec.containers[0].ports[0].containerPort}{"\n"}'
kubectl logs -n lab09 -l app=backend --tail=1
```

Root cause: `targetPort: 8081` in the Service, while the backend listens on 8080. "Connection refused" (an
immediate answer) means the packet reached the Pod and nothing listened on that port; a NetworkPolicy would cause a
timeout instead (lesson 22).

## Fix It

<!-- test: retry=10; contains=Hello from the backend -->
```bash
kubectl apply -f labs/09-networking/app.yaml -n lab09 > /dev/null
kubectl exec frontend -n lab09 -- wget -qO- -T 3 http://backend:8080/
```

## Verification

<!-- test: contains=8080 -->
```bash
kubectl get endpointslices -n lab09 -l kubernetes.io/service-name=backend -o jsonpath='{.items[0].ports[0].port}{"\n"}'
```

The EndpointSlice now lists port 8080, and the frontend gets the backend's JSON.

## Cleanup

🧹 Delete the namespace `lab09` (backend, Service, frontend Pod):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab09
```
