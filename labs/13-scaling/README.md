# Lab 13 · Scaling under an autoscaler

> Level 9 · Scaling & Scheduling · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## Objective

Scale the backend by hand, put it under a HorizontalPodAutoscaler, and then meet the most common surprise of real
teams: a manual `kubectl scale` that the autoscaler quietly undoes. Afterwards you can explain who owns `replicas` and
change the scaling range the right way.

Prerequisites: [lesson 25](../../docs/25-scaling/README.md) and [lesson 26](../../docs/26-hpa/README.md)
(metrics-server enabled).

## Setup

<!-- test: contains=successfully rolled out; timeout=600 -->
```bash
minikube addons enable metrics-server 2>&1 | tail -1
kubectl wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=300s > /dev/null
kubectl create namespace lab13
kubectl apply -f manifests/scaling/scaling-backend.yaml -n lab13
kubectl rollout status deployment/backend -n lab13 --timeout=120s
```

## Steps

**1. Scale by hand to 3** and check that all three Pods receive requests:

<!-- test: contains=3/3 -->
```bash
kubectl scale deployment backend -n lab13 --replicas=3
kubectl rollout status deployment/backend -n lab13 --timeout=120s > /dev/null
kubectl get deployment backend -n lab13
```

<!-- test: contains=backend-; output -->
```bash
kubectl run client -n lab13 --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 30); do wget -qO- http://backend; echo; done' > /dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/client -n lab13 --timeout=120s > /dev/null
kubectl logs client -n lab13 | grep -o '"pod":"[^"]*"' | sort | uniq -c
```

```text
     16 "pod":"backend-5f65986b87-679lh"
     14 "pod":"backend-5f65986b87-jgg8r"
```

**2. Hand scaling over to an autoscaler** (1 to 5 Pods, 50 % CPU, lesson 26):

<!-- test: contains=created -->
```bash
kubectl apply -f manifests/scaling/hpa-backend.yaml -n lab13
```

Without load the HPA soon decides that one Pod is enough:

<!-- test: contains=replicas: 1; retry=60; timeout=300 -->
```bash
echo "replicas: $(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')"
[ "$(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')" = 1 ]
```

## Break It

A big sale starts tomorrow. Someone prepares by running four backends:

<!-- test: contains=scaled -->
```bash
kubectl scale deployment backend -n lab13 --replicas=4
```

A minute later:

<!-- test: contains=replicas: 1; retry=60; timeout=300; output -->
```bash
echo "replicas: $(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')"
[ "$(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')" = 1 ]
```

```text
replicas: 1
```

## Troubleshoot It

*What should happen?* Four Pods until after the sale. *What happened?* Back to one. *Which object changes
`replicas`?* Look at the Deployment's events and at what manages it:

<!-- test: contains=Scaled; output -->
```bash
kubectl get events -n lab13 --field-selector involvedObject.kind=Deployment -o custom-columns=MESSAGE:.message | tail -3
kubectl get hpa -n lab13
```

```text
Scaled down replica set backend-5f65986b87 from 3 to 1
Scaled up replica set backend-5f65986b87 from 1 to 4
Scaled down replica set backend-5f65986b87 from 4 to 1
NAME      REFERENCE            TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
backend   Deployment/backend   cpu: 1%/50%   1         5         4          2m32s
```

An HPA targets this Deployment. It recalculates every 15 seconds; with almost no CPU used its answer is the minimum,
1, and it overwrites whatever the Deployment says once its stabilization window (30 s here) has passed. Root cause:
`kubectl scale` changed a number the HPA owns.

## Fix It

Change the autoscaler's floor for the sale; the HPA itself then keeps at least 4 Pods:

<!-- test: contains=patched -->
```bash
kubectl patch hpa backend -n lab13 -p '{"spec":{"minReplicas":4}}'
```

## Verification

The HPA raises the Deployment to 4 and keeps it there:

<!-- test: contains=replicas: 4; retry=60; timeout=300 -->
```bash
echo "replicas: $(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')"
[ "$(kubectl get deployment backend -n lab13 -o jsonpath='{.spec.replicas}')" = 4 ]
```

<!-- test: contains=MINPODS; contains=4 -->
```bash
sleep 40
kubectl get hpa backend -n lab13
kubectl get deployment backend -n lab13
```

After the sale, the same patch with `"minReplicas":1` hands the decision back to the CPU measurement.

## Cleanup

🧹 Delete the namespace `lab13` (backend, autoscaler, client Pod):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab13
```

Next: [Challenges](../../challenges/troubleshooting/README.md)
