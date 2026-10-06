# Problem 01 · Pod stuck in Pending

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

A colleague deployed the nightly report service. Hours later it still has not run once. "The Pod is just waiting",
they say. Set up their Deployment:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-01
kubectl apply -f labs/12-troubleshooting/manifests/01-pending.yaml -n trouble-01
sleep 5
```

## Symptoms

<!-- test: contains=Pending; output -->
```bash
kubectl get pods -n trouble-01 -o wide
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   IP       NODE     NOMINATED NODE   READINESS GATES
report-bb7b9fdb9-z6plb   0/1     Pending   0          5s    <none>   <none>   <none>           <none>
```

`Pending` and `NODE <none>`: the Pod has not been placed on any node yet.

## First command to run

The Pod's events: the scheduler writes there why it could not place a Pod.

<!-- test: contains=FailedScheduling; output -->
```bash
kubectl describe pod -n trouble-01 -l app=report | grep -A4 '^Events'
```

```text
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  5s    default-scheduler  0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

## Investigation

*What is broken?* The Pod is never scheduled. *Which object controls this?* The scheduler, using the Pod's resource
**requests** and what each node can still offer. The event names the reason: `Insufficient cpu`. Compare what the
Pod asks for with what the node has:

<!-- test: contains=64; output -->
```bash
kubectl get pods -n trouble-01 -l app=report -o jsonpath='requests: {.items[0].spec.containers[0].resources.requests}{"\n"}'
kubectl get node minikube -o jsonpath='allocatable cpu: {.status.allocatable.cpu}{"\n"}'
```

```text
requests: {"cpu":"64","memory":"32Mi"}
allocatable cpu: 14
```

## Root cause

The Pod requests `cpu: "64"`, 64 whole CPUs (the author meant `64m`, 64 millicores). No node can offer that, so the
scheduler leaves the Pod `Pending` forever. Nothing is "slow": it will never start.

## Fix

Request what the application really needs. Fix the manifest and apply it; the Deployment replaces the Pod:

<!-- test: contains=successfully rolled out -->
```bash
sed 's/cpu: "64"          # 64 whole CPUs/cpu: 100m/' labs/12-troubleshooting/manifests/01-pending.yaml | kubectl apply -n trouble-01 -f -
kubectl rollout status deployment/report -n trouble-01 --timeout=120s
```

## Verification

<!-- test: contains=Running -->
```bash
kubectl get pods -n trouble-01 -o wide
```

The Pod is `Running` on `minikube`.

## Lesson learned

- `Pending` + `NODE <none>` = a scheduling problem: read the `FailedScheduling` event first.
- The scheduler plans with **requests**, not with real usage: an impossible request blocks a Pod even on an idle node.
- `64` is 64 CPUs; `64m` is 0.064 of a CPU. Units matter (lesson 15).

## Cleanup

🧹 Delete the namespace `trouble-01` and the report Deployment in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-01
```

Next: [Problem 02 · CrashLoopBackOff](02-crashloopbackoff.md)
