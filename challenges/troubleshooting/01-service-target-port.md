# Troubleshooting challenge 01 · The Service has endpoints, but refuses

> After lessons 10 and 27 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

Set up the broken application:

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace tchallenge-01
kubectl apply -f challenges/troubleshooting/manifests/01-target-port.yaml -n tchallenge-01
kubectl rollout status deployment/backend -n tchallenge-01 --timeout=120s
```

## Task

Both backend Pods are `Running` and `1/1` ready, the Service `backend` has endpoints, yet
`wget http://backend` from a Pod in the namespace fails. Find the cause and fix it.

## Requirements

- Do not delete or recreate the Deployment.
- A client Pod in `tchallenge-01` gets the backend's JSON from `http://backend`.

## Hints

- Compare `Connection refused` with a timeout: which one do you get?
- `kubectl describe service backend` shows the Service port, the target port and the endpoints with their ports.
- On which port does the backend listen (`containerPort`, lesson 06)?

## Expected Result

```text
{"message":"Hello from the backend","pod":"backend-…","version":"1.0.0"}
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=TargetPort; contains=80/TCP; output -->
```bash
kubectl describe service backend -n tchallenge-01 | grep -E '^(TargetPort|Endpoints)'
```

```text
TargetPort:               80/TCP
Endpoints:                10.244.120.105:80,10.244.120.125:80
```

<!-- test: contains=Hello from the backend -->
```bash
kubectl patch service backend -n tchallenge-01 --type=json -p '[{"op":"replace","path":"/spec/ports/0/targetPort","value":8080}]'
kubectl run client -n tchallenge-01 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 10); do wget -qO- -T 5 http://backend && exit 0; sleep 2; done; exit 1'
```

</details>

## Explanation

The Service forwarded to port 80 of each Pod (`targetPort: 80`), but the backend listens on 8080: the Pods refused
the connection. Endpoints only prove that the selector matches ready Pods, not that the port is right. Read the
endpoint list with its ports (`IP:80`) and compare it with the container's port.

## Cleanup

🧹 Delete the namespace `tchallenge-01`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace tchallenge-01
```
