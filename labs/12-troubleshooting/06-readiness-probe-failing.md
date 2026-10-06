# Problem 06 · Readiness probe failing

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

After someone "added health checks", the backend Pods run but the Service sends them nothing. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-06
kubectl apply -f labs/12-troubleshooting/manifests/06-readiness.yaml -n trouble-06
sleep 15
```

## Symptoms

<!-- test: contains=0/1; output -->
```bash
kubectl get pods -n trouble-06
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
backend-6b89dbb776-2mxr7   0/1     Running   0          15s
backend-6b89dbb776-kkmr4   0/1     Running   0          15s
```

`Running` but `READY 0/1`: the container runs, Kubernetes does not consider it ready for traffic. The events say
why (`kubectl describe pod` shows the same events at the end of its output):

## First command to run

<!-- test: contains=Readiness probe failed; retry=20; output -->
```bash
kubectl get events -n trouble-06 --field-selector reason=Unhealthy -o custom-columns=MESSAGE:.message | grep -m1 'Readiness probe failed'
```

```text
Readiness probe failed: HTTP probe failed with statuscode: 404
```

## Investigation

`statuscode: 404`: the kubelet reached the application (so the port is right), but the **path** does not exist. Which
path does the probe ask, and which paths does the application have?

<!-- test: contains=/ready -->
```bash
kubectl get deployment backend -n trouble-06 -o jsonpath='probe path: {.spec.template.spec.containers[0].readinessProbe.httpGet.path}{"\n"}'
```

The backend serves `/readyz` and `/livez` (lesson 14), not `/ready`. Because no Pod is ready, the Service has no
endpoints:

<!-- test: contains=Endpoints -->
```bash
kubectl describe service backend -n trouble-06 | grep '^Endpoints'
```

## Root cause

The readiness probe checks `/ready`, a path the application does not have. Every check gets 404, so the Pods never
become ready and receive no traffic. (A failing **liveness** probe would also restart them; readiness only removes
them from the Service.)

## Fix

<!-- test: contains=successfully rolled out -->
```bash
kubectl patch deployment backend -n trouble-06 --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/readyz"}]'
kubectl rollout status deployment/backend -n trouble-06 --timeout=120s
```

## Verification

<!-- test: contains=2/2 -->
```bash
kubectl get deployment backend -n trouble-06
```

## Lesson learned

- `Running` + `0/1 READY` = a readiness problem: the `Unhealthy` event says why.
- The HTTP status tells you where to look: 404 path, 500/503 the application, `connection refused` the port.
- Test a probe's URL by hand before you put it in a manifest.

## Cleanup

🧹 Delete the namespace `trouble-06`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-06
```

Next: [Problem 07 · Wrong ConfigMap](07-wrong-configmap.md)
