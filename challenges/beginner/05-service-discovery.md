# Beginner challenge 05 · Expose the backend and call it by name

> After lesson 10 · ⏱ 20 minutes · run every command from the course folder · cluster: minikube

## Task

In `challenge-05`, run the course backend (`learning-app/backend:1.0.0`, 3 replicas) and give it a Service named
`api` on port **8000**. From a temporary client Pod, call `http://api:8000/` six times and show which backend Pods
answered.

## Requirements

- The Service is created with `kubectl expose` (no YAML).
- Clients use the name `api` and port 8000; the backend itself listens on 8080.
- At least one call answers; the output shows the answering Pod names.

## Hints

- `kubectl expose deployment NAME --name=api --port=8000 --target-port=8080`.
- The backend's `/` answer contains `"pod":"…"`.
- A loop in the client: `sh -c 'for i in 1 2 3 4 5 6; do wget -qO- http://api:8000/; echo; done'`.

## Expected Result

Six JSON answers from the backend, usually from more than one Pod.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace challenge-05
kubectl create deployment backend -n challenge-05 --image=learning-app/backend:1.0.0 --replicas=3
kubectl rollout status deployment/backend -n challenge-05 --timeout=120s
kubectl expose deployment backend -n challenge-05 --name=api --port=8000 --target-port=8080
```

<!-- test: contains=Hello from the backend; retry=5 -->
```bash
kubectl run client -n challenge-05 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in 1 2 3 4 5 6; do wget -qO- -T 5 http://api:8000/; echo; done'
```

🧹 Clean up (deletes the namespace `challenge-05`, the Deployment and the Service):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-05
```

</details>

## Explanation

`kubectl expose` creates a Service whose selector is copied from the Deployment (`app=backend`), with
`port: 8000` (what clients call) and `targetPort: 8080` (where the Pods listen). The name `api` resolves through the
cluster DNS in the same namespace, and each connection is sent to one of the ready Pods.
