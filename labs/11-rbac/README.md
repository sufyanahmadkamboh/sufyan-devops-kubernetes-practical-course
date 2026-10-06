# Lab 11 · RBAC: the pipeline may not deploy

> Lessons 23, 24 · ⏱ 20 minutes · run every command from the course folder · cluster: minikube

## Objective

A CI pipeline deploys to the namespace `lab11` as the ServiceAccount `ci-deployer`. Its permissions were written
"to allow Deployments", yet every deployment is forbidden. Find the mistake with `kubectl auth can-i` and fix it.

## Setup

The permissions as first written:

<!-- test: contains=serviceaccount/ci-deployer created -->
```bash
kubectl create namespace lab11
kubectl apply -f labs/11-rbac/ci-access-broken.yaml -n lab11
```

## Steps

What the pipeline does, run with its identity (`--as` impersonates the ServiceAccount):

<!-- test: contains=forbidden; output -->
```bash
kubectl create deployment web --image=nginx:1.30-alpine -n lab11 --as=system:serviceaccount:lab11:ci-deployer 2>&1 || true
```

```text
error: failed to create deployment: deployments.apps is forbidden: User "system:serviceaccount:lab11:ci-deployer" cannot create resource "deployments" in API group "apps" in the namespace "lab11"
```

## Break It

The setup above is the broken state: the pipeline cannot deploy.

## Troubleshoot It

The error names every part of the check: user, verb `create`, resource `deployments`, **API group `apps`**,
namespace. Confirm with `can-i`, then read the Role:

<!-- test: contains=no; contains=apiGroups -->
```bash
kubectl auth can-i create deployments.apps -n lab11 --as=system:serviceaccount:lab11:ci-deployer || true
kubectl get role deployer -n lab11 -o yaml | grep -A6 '^rules'
kubectl api-resources --api-group=apps | grep deployments
```

The Role allows `deployments` in the API group `""` (the core group); Deployments live in the group `apps`. A rule for
a resource in the wrong group matches nothing. Root cause: the wrong `apiGroups`.

## Fix It

<!-- test: contains=yes -->
```bash
kubectl apply -f labs/11-rbac/ci-access.yaml -n lab11
kubectl auth can-i create deployments.apps -n lab11 --as=system:serviceaccount:lab11:ci-deployer
```

## Verification

The pipeline deploys, and still cannot do what it should not:

<!-- test: contains=deployment.apps/web created; contains=delete deployments: no -->
```bash
kubectl create deployment web --image=nginx:1.30-alpine -n lab11 --as=system:serviceaccount:lab11:ci-deployer
echo "delete deployments: $(kubectl auth can-i delete deployments.apps -n lab11 --as=system:serviceaccount:lab11:ci-deployer)"
echo "read secrets: $(kubectl auth can-i get secrets -n lab11 --as=system:serviceaccount:lab11:ci-deployer)"
```

## Cleanup

🧹 Delete the namespace `lab11` (the ServiceAccount, Role, RoleBinding and the `web` Deployment):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab11
```
