# Troubleshooting challenge 02 · Restarts every few seconds

> After lessons 14 and 27 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

Set up the broken application:

<!-- test: contains=created -->
```bash
kubectl create namespace tchallenge-02
kubectl apply -f challenges/troubleshooting/manifests/02-liveness.yaml -n tchallenge-02
```

## Task

The backend's restart counter grows every few seconds, although its logs show no error. Find out who restarts it and
why, and fix it.

## Requirements

- After the fix the restart counter stops growing for at least 30 seconds.
- The backend keeps a liveness probe.

## Hints

- An application that crashes leaves an error in its logs; this one does not. Who else can restart a container?
- The `Events` of the Pod say why each restart happened.
- Which health endpoints does the backend have (lesson 14)?

## Expected Result

`RESTARTS` stays the same over 30 seconds; the Pod is `Running`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=Liveness probe failed; retry=30; output -->
```bash
kubectl describe pod -n tchallenge-02 -l app=backend | grep -m1 'Liveness probe failed'
```

```text
  Warning  Unhealthy  1s    kubelet            spec.containers{backend}: Liveness probe failed: HTTP probe failed with statuscode: 404
```

<!-- test: contains=stable -->
```bash
kubectl patch deployment backend -n tchallenge-02 --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/livez"}]'
kubectl rollout status deployment/backend -n tchallenge-02 --timeout=120s > /dev/null
before=$(kubectl get pods -n tchallenge-02 -l app=backend -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
sleep 30
after=$(kubectl get pods -n tchallenge-02 -l app=backend -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
[ "$before" = "$after" ] && echo "stable: $after restarts"
```

</details>

## Explanation

The kubelet restarted the container because its liveness probe asked `/health`, a path the backend does not have
(404). Two failures in a row (`failureThreshold: 2`, every 3 s) and the kubelet kills the container. The backend's
liveness endpoint is `/livez`. A wrong liveness probe is worse than none: it turns a healthy application into one
that restarts forever.

## Cleanup

🧹 Delete the namespace `tchallenge-02`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace tchallenge-02
```
