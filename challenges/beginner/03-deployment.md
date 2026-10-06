# Beginner challenge 03 · A well-formed Deployment

> After lesson 09 (lessons 14 and 15 explain probes and resources in depth) · ⏱ 25 minutes · cluster: minikube

## Task

Create a Deployment `catalog` in a namespace `challenge-03` that a reviewer would accept for a real service.

## Requirements

- 3 replicas of `nginx:1.30-alpine`, labelled `app: catalog`.
- CPU and memory **requests**: `50m` CPU, `32Mi` memory.
- CPU and memory **limits**: `200m` CPU, `64Mi` memory.
- A **readiness probe**: HTTP `GET /` on port 80.
- All 3 Pods ready.

## Hints

- Start from `kubectl create deployment catalog --image=nginx:1.30-alpine --replicas=3 --dry-run=client -o yaml`
  (lesson 04), then add the fields.
- `resources` and `readinessProbe` belong to the **container**, next to `image`.
- `kubectl explain deployment.spec.template.spec.containers.readinessProbe.httpGet` shows the fields.

## Expected Result

`kubectl get deployment catalog -n challenge-03` shows `3/3`; every Pod has the requests, limits and probe.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace challenge-03
kubectl apply -n challenge-03 -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalog
spec:
  replicas: 3
  selector:
    matchLabels:
      app: catalog
  template:
    metadata:
      labels:
        app: catalog
    spec:
      containers:
        - name: catalog
          image: nginx:1.30-alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 64Mi
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 5
EOF
kubectl rollout status deployment/catalog -n challenge-03 --timeout=180s
```

<!-- test: contains=3/3; contains=64Mi; output -->
```bash
kubectl get deployment catalog -n challenge-03 -o jsonpath='{.status.readyReplicas}/{.spec.replicas} ready{"\n"}'
kubectl get pods -n challenge-03 -l app=catalog -o jsonpath='{range .items[*]}{.metadata.name}: requests {.spec.containers[0].resources.requests} limits {.spec.containers[0].resources.limits}{"\n"}{end}'
```

```text
3/3 ready
catalog-64f68ff945-fnvql: requests {"cpu":"50m","memory":"32Mi"} limits {"cpu":"200m","memory":"64Mi"}
catalog-64f68ff945-hk4jq: requests {"cpu":"50m","memory":"32Mi"} limits {"cpu":"200m","memory":"64Mi"}
catalog-64f68ff945-ps5dz: requests {"cpu":"50m","memory":"32Mi"} limits {"cpu":"200m","memory":"64Mi"}
```

🧹 Clean up (deletes the namespace `challenge-03` and the Deployment):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-03
```

</details>

## Explanation

**Requests** are what the scheduler reserves for each Pod; **limits** are the most it may use (above the memory
limit the container is killed, lesson 15). The **readiness probe** decides when a Pod receives traffic and when a
rolling update may continue (lessons 09, 14). A Deployment with all three is predictable for the scheduler, safe to
update and safe to put behind a Service.
