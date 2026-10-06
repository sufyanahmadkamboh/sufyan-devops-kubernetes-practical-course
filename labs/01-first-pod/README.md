# Lab 01 · Your first Pod

> After lesson 06 · ⏱ 20 minutes · run every command from the course folder · cluster: minikube

## Objective

Create a Pod from a file you understand line by line, look inside it from every angle (state, events, logs, a shell
command, the network), break the file on purpose and repair it.

## Setup

<!-- test: contains=created -->
```bash
kubectl create namespace lab-01
cat labs/01-first-pod/pod.yaml
```

Every line of this file is explained in lesson 06: `apiVersion` and `kind` say *what*, `metadata` says *who*, `spec`
says *how it should be*.

## Steps

**1. Create the Pod and wait until it is ready:**

<!-- test: contains=condition met -->
```bash
kubectl apply -f labs/01-first-pod/pod.yaml -n lab-01
kubectl wait --for=condition=Ready pod/my-first-pod -n lab-01 --timeout=120s
```

**2. Its state, its node and its IP:**

<!-- test: contains=Running -->
```bash
kubectl get pod my-first-pod -n lab-01 -o wide
```

**3. Its story (events):**

<!-- test: contains=Started -->
```bash
kubectl describe pod my-first-pod -n lab-01 | grep -A8 '^Events'
```

**4. Its logs, and a command inside it:**

<!-- test: contains=nginx version -->
```bash
kubectl logs my-first-pod -n lab-01 --tail=2
kubectl exec my-first-pod -n lab-01 -- nginx -v
```

**5. Its web page, from another Pod, through its IP:**

<!-- test: contains=Welcome to nginx -->
```bash
ip=$(kubectl get pod my-first-pod -n lab-01 -o jsonpath='{.status.podIP}')
kubectl run client -n lab-01 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 "http://$ip" | grep -o '<title>.*</title>'
```

## Break It

A colleague wrote the same Pod by hand. Apply their version (in `labs/01-first-pod/broken/`):

<!-- test: fail; contains=no kind "pod"; output -->
```bash
kubectl apply -f labs/01-first-pod/broken/pod.yaml -n lab-01 2>&1
```

```text
Error from server (BadRequest): error when creating "labs/01-first-pod/broken/pod.yaml": pod in version "v1" cannot be handled as a Pod: no kind "pod" is registered for version "v1" in scheme "pkg/api/legacyscheme/scheme.go:30"
```

## Troubleshoot It

*What should happen?* The Pod is created (or reported unchanged). *What happened?* `BadRequest`, and nothing was
created: the API server rejected the file before doing anything. Read the message slowly: `no kind "pod" is
registered for version "v1"`. Kinds are names of types, and they are **case-sensitive**. Compare the two files:

<!-- test: contains=kind: pod -->
```bash
diff labs/01-first-pod/pod.yaml labs/01-first-pod/broken/pod.yaml || true
```

Root cause: `kind: pod` instead of `kind: Pod`. (Its missing labels are allowed, just less useful.)

## Fix It

Correct the kind and apply again (`sed` changes the line, `kubectl apply -f -` reads the result):

<!-- test: contains=pod/colleague-pod created -->
```bash
sed 's/^kind: pod$/kind: Pod/' labs/01-first-pod/broken/pod.yaml | kubectl apply -n lab-01 -f -
kubectl wait --for=condition=Ready pod/colleague-pod -n lab-01 --timeout=120s
```

## Verification

<!-- test: contains=my-first-pod; contains=Running -->
```bash
kubectl get pods -n lab-01
kubectl get pod my-first-pod -n lab-01 -o jsonpath='phase: {.status.phase}{"\n"}'
```

You should see `my-first-pod` `Running` and nothing else.

## Cleanup

🧹 Delete the namespace `lab-01` and the Pod in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-01
```
