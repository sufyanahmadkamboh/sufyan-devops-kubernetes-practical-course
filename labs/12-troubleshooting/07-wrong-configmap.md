# Problem 07 · Wrong ConfigMap

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The backend's configuration moved into a ConfigMap. Since then its Pod never starts. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-07
kubectl apply -f labs/12-troubleshooting/manifests/07-configmap.yaml -n trouble-07
```

## Symptoms

<!-- test: contains=CreateContainerConfigError; retry=20; output -->
```bash
kubectl get pods -n trouble-07 | grep CreateContainerConfigError
```

```text
backend-69d5b6f5d4-2tz86   0/1     CreateContainerConfigError   0          2s
```

`CreateContainerConfigError`: the image is there, but the kubelet cannot even create the container, because part of
its configuration is missing.

## First command to run

<!-- test: contains=couldn't find key; output -->
```bash
kubectl describe pod -n trouble-07 -l app=backend | grep -m1 'Error:'
```

```text
  Warning  Failed     0s (x3 over 2s)  kubelet            spec.containers{backend}: Error: couldn't find key log_level in ConfigMap trouble-07/backend-config
```

## Investigation

The ConfigMap exists, but the key the Deployment asks for does not. Which keys does it have?

<!-- test: contains=LOG_LEVEL; output -->
```bash
kubectl get configmap backend-config -n trouble-07 -o jsonpath='{.data}{"\n"}'
```

```text
{"LOG_LEVEL":"info","MESSAGE":"Hello from the ConfigMap"}
```

Keys are case-sensitive: the ConfigMap has `LOG_LEVEL`, the Deployment asks for `log_level`.

## Root cause

The Deployment refers to a ConfigMap key that does not exist. A missing key (or ConfigMap) blocks the container from
starting, unless the reference is marked `optional: true`.

## Fix

Point the reference at the real key:

<!-- test: contains=successfully rolled out -->
```bash
kubectl patch deployment backend -n trouble-07 --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/env/1/valueFrom/configMapKeyRef/key","value":"LOG_LEVEL"}]'
kubectl rollout status deployment/backend -n trouble-07 --timeout=120s
```

## Verification

The backend shows the configuration it received:

<!-- test: contains=Hello from the ConfigMap -->
```bash
ip=$(kubectl get pod -n trouble-07 -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl run client -n trouble-07 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- "http://$ip:8080/api/config"
```

## Lesson learned

- `CreateContainerConfigError` = a ConfigMap, Secret or key the Pod needs is missing: the event names it exactly.
- ConfigMap keys are case-sensitive; `kubectl get configmap NAME -o jsonpath='{.data}'` lists them.
- References are checked when the container starts, not when you apply the Deployment.

## Cleanup

🧹 Delete the namespace `trouble-07`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-07
```

Next: [Problem 08 · Wrong Secret](08-wrong-secret.md)
