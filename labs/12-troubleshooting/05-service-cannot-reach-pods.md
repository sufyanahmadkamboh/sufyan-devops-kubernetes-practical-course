# Problem 05 · Service cannot reach Pods

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The backend Pods run fine, but every request to the `backend` Service fails. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-05
kubectl apply -f labs/12-troubleshooting/manifests/05-service-no-endpoints.yaml -n trouble-05
kubectl rollout status deployment/backend -n trouble-05 --timeout=120s
```

## Symptoms

<!-- test: contains=Connection refused; output -->
```bash
kubectl run client -n trouble-05 --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://backend > /dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Failed pod/client -n trouble-05 --timeout=60s > /dev/null
kubectl logs client -n trouble-05
```

```text
wget: can't connect to remote host (10.111.243.195): Connection refused
```

The name `backend` resolved to an address (DNS works), but nothing accepted the connection.

## First command to run

Does the Service have **endpoints**, the Pod addresses it forwards to?

<!-- test: contains=Endpoints; output -->
```bash
kubectl describe service backend -n trouble-05 | grep -E '^(Selector|Endpoints)'
```

```text
Selector:                 app=back-end
Endpoints:                
```

## Investigation

*Which object decides where a Service sends traffic?* Its **selector**: every ready Pod whose labels match it becomes
an endpoint. No endpoints means no Pod matches. Compare the selector with the Pods' labels:

<!-- test: contains=app=backend; output -->
```bash
kubectl get pods -n trouble-05 --show-labels
kubectl get pods -n trouble-05 -l app=back-end 2>&1
```

```text
NAME                       READY   STATUS    RESTARTS   AGE   LABELS
backend-5599cd7d88-5jt79   1/1     Running   0          5s    app=backend,pod-template-hash=5599cd7d88
backend-5599cd7d88-868z4   1/1     Running   0          5s    app=backend,pod-template-hash=5599cd7d88
client                     0/1     Error     0          4s    run=client
No resources found in trouble-05 namespace.
```

The Pods say `app=backend`; the Service looks for `app=back-end`.

## Root cause

A typo in the Service selector. Labels match exactly; one character is enough to match nothing (lesson 07).

## Fix

<!-- test: contains=patched -->
```bash
kubectl patch service backend -n trouble-05 -p '{"spec":{"selector":{"app":"backend"}}}'
```

## Verification

<!-- test: contains=Hello from the backend -->
```bash
kubectl describe service backend -n trouble-05 | grep '^Endpoints'
kubectl run client2 -n trouble-05 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 10); do wget -qO- -T 5 http://backend && exit 0; sleep 2; done; exit 1'
```

## Lesson learned

- "Service does not work" → first `kubectl describe service`: an empty `Endpoints:` points at the selector or at Pods
  that are not ready (problem 06).
- `kubectl get pods -l SELECTOR` with the Service's exact selector shows what it matches.
- `Connection refused` from a Service IP = no endpoints; a timeout = endpoints exist but do not answer (or a
  NetworkPolicy, problem 14).

## Cleanup

🧹 Delete the namespace `trouble-05` (backend Deployment, Service, client Pod):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-05
```

Next: [Problem 06 · Readiness probe failing](06-readiness-probe-failing.md)
