# Challenge 04 · A guaranteed Pod on a labelled node

> Intermediate · after lessons 15–16 · ⏱ 15 minutes · cluster: minikube

## Task

In a namespace `challenge-04`, run a Pod `critical` (`nginx:1.30-alpine`) with QoS class `Guaranteed` that may only
run on a node labelled `disktype=ssd`.

## Requirements

- Requests equal to limits: 100m CPU, 64Mi memory.
- `nodeSelector` `disktype: ssd`; label the node yourself, remove the label afterwards.

## Hints

- Lesson 15 (QoS classes) and lesson 16 (`kubectl label node`).

## Expected Result

`critical` is `Running` with `qos=Guaranteed` on `minikube`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=qos=Guaranteed node=minikube -->
```bash
kubectl create namespace challenge-04
kubectl label node minikube disktype=ssd
kubectl apply -n challenge-04 -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: critical
spec:
  nodeSelector:
    disktype: ssd
  containers:
    - name: web
      image: nginx:1.30-alpine
      resources:
        requests: {cpu: "100m", memory: "64Mi"}
        limits: {cpu: "100m", memory: "64Mi"}
EOF
kubectl wait --for=condition=Ready pod/critical -n challenge-04 --timeout=120s > /dev/null
kubectl get pod critical -n challenge-04 -o jsonpath='qos={.status.qosClass} node={.spec.nodeName}{"\n"}'
```

</details>

## Explanation

Requests decide where a Pod fits, the selector decides which nodes are allowed, and equal requests and limits make
it the last to be evicted under memory pressure.

## Cleanup

🧹 Remove the label `disktype` from the node, then delete the namespace `challenge-04`:

<!-- test: contains=deleted -->
```bash
kubectl label node minikube disktype-
kubectl delete namespace challenge-04
```
