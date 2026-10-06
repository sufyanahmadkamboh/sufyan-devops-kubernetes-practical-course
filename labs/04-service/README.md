# Lab 04 · A Service that does not answer

> After lesson 10 · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## Objective

Put a Service in front of the backend, find out why it refuses every connection although the Pods are healthy and
the selector is right, and fix it. You will check the three things every Service depends on: **selector**, **endpoints**
and **ports**.

## Setup

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace lab-04
kubectl apply -f labs/04-service/backend.yaml -n lab-04
kubectl rollout status deployment/api -n lab-04 --timeout=120s
```

## Steps

**1. The backend Pods answer directly** (on their own IP, port 8080):

<!-- test: contains=Hello from the backend -->
```bash
ip=$(kubectl get pods -n lab-04 -l app=api -o jsonpath='{.items[0].status.podIP}')
kubectl run direct -n lab-04 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 "http://$ip:8080/"
```

## Break It

Create the Service from `labs/04-service/broken/service.yaml` and call it by name:

<!-- test: contains=refused; output -->
```bash
kubectl apply -f labs/04-service/broken/service.yaml -n lab-04
kubectl run client -n lab-04 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://api/ 2>&1 | grep -v deleted
```

```text
service/api created
wget: can't connect to remote host (10.97.247.22): Connection refused
pod lab-04/client terminated (Error)
```

## Troubleshoot It

*What should happen?* The same answer as step 1. *What happened?* `Connection refused` to the Service's IP. DNS worked
(the name became an IP), so the Service exists. Check the chain: does the selector find Pods?

<!-- test: contains=8081; output -->
```bash
kubectl get endpointslices -n lab-04 -l kubernetes.io/service-name=api
```

```text
NAME        ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
api-h6xf4   IPv4          8081    10.244.120.67,10.244.120.68   4s
```

Endpoints exist: the selector is fine and the Pods are ready. But look at the port column: **8081**. Where does the
application listen?

<!-- test: contains=8080 -->
```bash
kubectl get deployment api -n lab-04 -o jsonpath='containerPort: {.spec.template.spec.containers[0].ports[0].containerPort}{"\n"}'
kubectl get service api -n lab-04 -o jsonpath='Service port: {.spec.ports[0].port}, targetPort: {.spec.ports[0].targetPort}{"\n"}'
```

Root cause: `targetPort: 8081`, but the backend listens on 8080. Traffic reaches the right Pods on a port where
nothing listens, and the Pod's network answers "refused". (A selector mismatch would show no endpoints at all and a
timeout; a refused connection with endpoints points at the port.)

## Fix It

<!-- test: contains=configured -->
```bash
kubectl apply -f labs/04-service/service.yaml -n lab-04
```

## Verification

<!-- test: contains=Hello from the backend -->
```bash
kubectl get endpointslices -n lab-04 -l kubernetes.io/service-name=api -o jsonpath='endpoint port: {.items[0].ports[0].port}{"\n"}'
kubectl run client -n lab-04 --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://api/
```

Endpoint port 8080, and the backend answers through `http://api/`.

## Cleanup

🧹 Delete the namespace `lab-04` (the Deployment `api` and the Service `api`):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-04
```
