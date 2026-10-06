# Problem 14 · NetworkPolicy blocks required traffic

> Lab 12 · Troubleshooting · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

## Problem

Security locked the backend down: "only the frontend may call it". Now the frontend cannot reach it either. Set it
up, with a client Pod labelled like the frontend (`app=frontend`):

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace trouble-14
kubectl apply -f labs/12-troubleshooting/manifests/14-networkpolicy.yaml -n trouble-14
kubectl rollout status deployment/backend -n trouble-14 --timeout=120s
```

## Symptoms

<!-- test: contains=timed out; output -->
```bash
kubectl run frontend -n trouble-14 --labels=app=frontend --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 http://backend 2>&1' || true
```

```text
wget: download timed out
pod trouble-14/frontend terminated (Error)
```

A **timeout**, not `Connection refused`: the packets are dropped silently. That is the signature of a NetworkPolicy
(with Calico, lesson 22), not of a missing endpoint (problem 05).

## First command to run

Which policies apply to the backend Pods?

<!-- test: contains=backend-allow-frontend; output -->
```bash
kubectl get networkpolicy -n trouble-14
```

```text
NAME                     POD-SELECTOR   AGE
backend-allow-frontend   app=backend    8s
backend-deny-all         app=backend    8s
```

## Investigation

`backend-deny-all` blocks all incoming traffic; `backend-allow-frontend` should open it for the frontend. Policies add
up: traffic is allowed if **any** policy allows it. Who does the allow rule select?

<!-- test: contains=role=frontend; output -->
```bash
kubectl describe networkpolicy backend-allow-frontend -n trouble-14 | grep -A6 'Allowing ingress'
```

```text
  Allowing ingress traffic:
    To Port: 8080/TCP
    From:
      PodSelector: role=frontend
  Not affecting egress traffic
  Policy Types: Ingress
```

The rule allows Pods labelled `role=frontend`. The frontend is labelled `app=frontend`. The Service and endpoints are
fine:

<!-- test: contains=Endpoints -->
```bash
kubectl describe service backend -n trouble-14 | grep '^Endpoints'
```

## Root cause

The allow rule selects the frontend by a label it does not have, so only `backend-deny-all` takes effect: every
caller, the frontend included, is dropped.

## Fix

<!-- test: contains=patched -->
```bash
kubectl patch networkpolicy backend-allow-frontend -n trouble-14 --type=json \
  -p '[{"op":"replace","path":"/spec/ingress/0/from/0/podSelector/matchLabels","value":{"app":"frontend"}}]'
```

## Verification

The frontend gets through; any other Pod is still blocked:

<!-- test: contains=Hello from the backend -->
```bash
kubectl run frontend2 -n trouble-14 --labels=app=frontend --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 10); do wget -qO- -T 5 http://backend && exit 0; sleep 2; done; exit 1'
```

<!-- test: contains=timed out -->
```bash
kubectl run stranger -n trouble-14 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 http://backend 2>&1' || true
```

## Lesson learned

- A timeout to a Service with endpoints = traffic dropped: suspect a NetworkPolicy.
- Policies are allow-lists that add up; a typo in a selector silently allows nothing.
- `kubectl describe networkpolicy` shows exactly whom a rule allows; compare it with `kubectl get pods --show-labels`.

## Cleanup

🧹 Delete the namespace `trouble-14` (Deployment, Service, both policies):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-14
```

Next: [Troubleshooting lab index](README.md)
