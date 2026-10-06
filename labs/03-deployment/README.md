# Lab 03 · Running a Deployment

> After lesson 09 · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## Objective

Run a web shop as a Deployment, scale it, update it without downtime, then hit a rule many teams discover the hard
way: a Deployment's selector can never be changed.

## Setup

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace lab-03
kubectl apply -f labs/03-deployment/deployment.yaml -n lab-03
kubectl rollout status deployment/shop -n lab-03 --timeout=120s
```

## Steps

**1. Scale to 4 replicas** (more capacity for a busy day):

<!-- test: contains=4/4 -->
```bash
kubectl scale deployment shop -n lab-03 --replicas=4
kubectl rollout status deployment/shop -n lab-03 --timeout=120s > /dev/null
kubectl get deployment shop -n lab-03 -o jsonpath='{.status.readyReplicas}/{.spec.replicas} ready{"\n"}'
```

**2. Change a setting:** an environment variable is part of the Pod template, so changing it rolls out new Pods.

<!-- test: contains=successfully rolled out -->
```bash
kubectl set env deployment/shop -n lab-03 SHOP_THEME=autumn
kubectl rollout status deployment/shop -n lab-03 --timeout=120s
```

**3. Check every Pod has the setting, and the revision history:**

<!-- test: contains=SHOP_THEME=autumn -->
```bash
for p in $(kubectl get pods -n lab-03 -l app=shop -o name); do kubectl exec -n lab-03 "$p" -- printenv SHOP_THEME | sed "s|^|$p SHOP_THEME=|"; done
kubectl rollout history deployment/shop -n lab-03
```

## Break It

A colleague decides the label `app: shop` should become `app: shop-web` everywhere, and applies the change:

<!-- test: fail; contains=field is immutable; output -->
```bash
kubectl apply -f labs/03-deployment/broken/deployment-new-labels.yaml -n lab-03 2>&1
```

```text
The Deployment "shop" is invalid: spec.selector: Invalid value: {"matchLabels":{"app":"shop-web"}}: field is immutable
```

## Troubleshoot It

*What should happen?* The Deployment uses the new labels. *What happened?* `spec.selector … field is immutable`:
nothing changed. The selector is how the Deployment finds its ReplicaSets and Pods; changing it in place would orphan
every running Pod, so Kubernetes forbids it after creation.

<!-- test: contains=app=shop -->
```bash
kubectl get deployment shop -n lab-03 -o jsonpath='current selector: app={.spec.selector.matchLabels.app}{"\n"}'
```

Root cause: an attempt to change an immutable field.

## Fix It

Changing a selector means creating a new Deployment. The safe order: create the new one next to the old one, check it,
then delete the old one. Here the name stays the same, so the old one goes first. 🧹 This deletes the Deployment
`shop` in `lab-03` and its Pods (a short outage, acceptable in a lab; in production use a new name):

<!-- test: contains=successfully rolled out -->
```bash
kubectl delete deployment shop -n lab-03
kubectl apply -f labs/03-deployment/broken/deployment-new-labels.yaml -n lab-03
kubectl rollout status deployment/shop -n lab-03 --timeout=120s
```

## Verification

<!-- test: contains=app=shop-web; contains=2/2 -->
```bash
kubectl get deployment shop -n lab-03 -o jsonpath='{.status.readyReplicas}/{.spec.replicas} ready, selector app={.spec.selector.matchLabels.app}{"\n"}'
kubectl get pods -n lab-03 --show-labels
```

Two Pods labelled `app=shop-web`. Notice what was lost by recreating: the 4 replicas and the `SHOP_THEME` setting were
only in the cluster (imperative changes), never in the file. Files are the source of truth.

## Cleanup

🧹 Delete the namespace `lab-03` and the Deployment in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-03
```
