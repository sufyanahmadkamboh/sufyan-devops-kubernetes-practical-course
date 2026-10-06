# Lab 02 · Debugging Pods

> After lesson 06 · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## Objective

Two Pods of an online shop do not start. Find out why for each one, using only what Kubernetes tells you: the
status, the events, the logs. Then fix them. The method (from lesson 27): *what is broken → what should happen →
what happened → which object → events → logs → configuration → root cause → fix → verify*.

## Setup

<!-- test: contains=created -->
```bash
kubectl create namespace lab-02
kubectl apply -f labs/02-pod-debugging/broken/ -n lab-02
```

## Steps

**1. The overview:**

<!-- test: contains=shop-web; contains=shop-worker; retry=20; anyof=ImagePullBackOff||ErrImagePull -->
```bash
kubectl get pods -n lab-02
```

Two different problems: `shop-web` never starts (`ErrImagePull`, then `ImagePullBackOff`), `shop-worker` starts and
dies (`Error`, then `CrashLoopBackOff`). They are investigated differently.

## Break It

The two Pods are already broken (`labs/02-pod-debugging/broken/`). Do not read the files yet: investigate as if you
had only the cluster.

## Troubleshoot It

**Problem 1: `shop-web`.** `ImagePullBackOff` means the kubelet could not get the image and is waiting before it
tries again. The container never ran, so there are no logs: the **events** hold the answer.

<!-- test: contains=Failed; contains=nginx:1.30-alpne -->
```bash
kubectl describe pod shop-web -n lab-02 | grep -E 'Image:|Failed' | head -4
```

The image is `nginx:1.30-alpne`: a typo (`alpne`). The registry has no such tag (`not found`).

**Problem 2: `shop-worker`.** The image was pulled and the container started, then exited. A running-then-exiting
container is explained by its **logs** and its **exit code**:

<!-- test: contains=APP_MODE is not set; retry=15 -->
```bash
kubectl describe pod shop-worker -n lab-02 | grep -E 'Exit Code|Restart Count' | head -2
kubectl logs shop-worker -n lab-02 --tail=5 2>/dev/null || kubectl logs shop-worker -n lab-02 --previous
```

`ERROR: APP_MODE is not set`, exit code 1: the program needs a setting that the Pod does not give it.

## Fix It

Most fields of a Pod's containers cannot be changed in place; recreate the Pods with the corrections. 🧹 This
deletes the two broken Pods `shop-web` and `shop-worker` in `lab-02`:

<!-- test: contains=deleted -->
```bash
kubectl delete pod shop-web shop-worker -n lab-02
```

The web Pod with the right tag (the broken file corrected on the fly), and the worker with its setting:

<!-- test: contains=created -->
```bash
sed 's/1.30-alpne/1.30-alpine/' labs/02-pod-debugging/broken/typo-image.yaml | kubectl apply -n lab-02 -f -
kubectl apply -f labs/02-pod-debugging/fixed-worker.yaml -n lab-02
grep -A3 'env:' labs/02-pod-debugging/fixed-worker.yaml
```

## Verification

<!-- test: contains=worker running in production mode -->
```bash
kubectl wait --for=condition=Ready pod/shop-web pod/shop-worker -n lab-02 --timeout=120s
kubectl get pods -n lab-02
kubectl logs shop-worker -n lab-02
```

Both `Running`, `RESTARTS 0`, and the worker says it runs in production mode.

## Cleanup

🧹 Delete the namespace `lab-02` and its two Pods:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-02
```
