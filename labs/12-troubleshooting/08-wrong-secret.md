# Problem 08 · Wrong Secret

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The database password was put into a Secret, and the backend was told to read it. The backend never starts. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-08
kubectl apply -f labs/12-troubleshooting/manifests/08-secret.yaml -n trouble-08
```

## Symptoms

<!-- test: contains=CreateContainerConfigError; retry=20; output -->
```bash
kubectl get pods -n trouble-08 | grep CreateContainerConfigError
```

```text
backend-7864884799-64qqz   0/1     CreateContainerConfigError   0          3s
```

## First command to run

<!-- test: contains=not found; output -->
```bash
kubectl describe pod -n trouble-08 -l app=backend | grep -m1 'Error:'
```

```text
  Warning  Failed     1s (x3 over 2s)  kubelet            spec.containers{backend}: Error: secret "db-secret" not found
```

## Investigation

Which Secrets exist in the namespace? (Listing Secrets shows their names, never their values.)

<!-- test: contains=db-credentials; output -->
```bash
kubectl get secrets -n trouble-08
```

```text
NAME             TYPE     DATA   AGE
db-credentials   Opaque   1      3s
```

The Secret is called `db-credentials`; the Deployment asks for `db-secret`. Secrets are also namespaced: a Secret with
the right name in another namespace would not help either.

## Root cause

The Deployment references a Secret name that does not exist in its namespace, so the kubelet cannot build the
container's environment.

## Fix

<!-- test: contains=successfully rolled out -->
```bash
kubectl patch deployment backend -n trouble-08 --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/env/0/valueFrom/secretKeyRef/name","value":"db-credentials"}]'
kubectl rollout status deployment/backend -n trouble-08 --timeout=120s
```

## Verification

The backend reports that it received a password, without showing it:

<!-- test: contains=set (from environment) -->
```bash
ip=$(kubectl get pod -n trouble-08 -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl run client -n trouble-08 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- "http://$ip:8080/api/config"
```

## Lesson learned

- `secret "X" not found` = a wrong name or the wrong namespace; `couldn't find key` = a wrong key (problem 07).
- `kubectl get secrets -n NS` lists names safely; never print a Secret's values while troubleshooting.
- Keep Secret names in one place (a Helm value, lesson 28) so the Secret and its users cannot drift apart.

## Cleanup

🧹 Delete the namespace `trouble-08` (Deployment and Secret):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-08
```

Next: [Problem 09 · PVC stuck in Pending](09-pvc-pending.md)
