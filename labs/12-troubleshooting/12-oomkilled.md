# Problem 12 · Pod OOMKilled

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The nightly import Pod stops in the middle of its work. Its logs end without any error. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-12
kubectl apply -f labs/12-troubleshooting/manifests/12-oomkilled.yaml -n trouble-12
```

## Symptoms

<!-- test: contains=OOMKilled; retry=30; output -->
```bash
kubectl get pod import -n trouble-12
kubectl get pod import -n trouble-12 | grep -q OOMKilled
```

```text
NAME     READY   STATUS      RESTARTS   AGE
import   0/1     OOMKilled   0          5s
```

## First command to run

<!-- test: contains=loading; output -->
```bash
kubectl logs import -n trouble-12
```

```text
loading 100 MiB of records
```

The log stops after the first line: "import done" never appears, and there is no error message. Something stopped the
process from outside.

## Investigation

How did the container end?

<!-- test: contains=137; output -->
```bash
kubectl get pod import -n trouble-12 -o jsonpath='reason: {.status.containerStatuses[0].state.terminated.reason}, exit code {.status.containerStatuses[0].state.terminated.exitCode}{"\n"}'
kubectl get pod import -n trouble-12 -o jsonpath='memory limit: {.spec.containers[0].resources.limits.memory}{"\n"}'
```

```text
reason: OOMKilled, exit code 137
memory limit: 48Mi
```

`OOMKilled`, exit code 137 (128 + signal 9, SIGKILL): the kernel's out-of-memory killer stopped the process because
the container used more memory than its **limit**, 48 MiB. The program had no chance to log anything.

## Root cause

The import needs about 100 MiB but is limited to 48 MiB. A memory limit is a hard wall (lesson 15): crossing it kills
the process, it does not slow it down.

## Fix

Give the job the memory it needs (a Pod's resources cannot be changed in place, so recreate it):

<!-- test: contains=import done; timeout=300 -->
```bash
kubectl delete pod import -n trouble-12
sed 's/memory: 48Mi/memory: 192Mi/' labs/12-troubleshooting/manifests/12-oomkilled.yaml | kubectl apply -n trouble-12 -f -
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/import -n trouble-12 --timeout=120s > /dev/null
kubectl logs import -n trouble-12
```

## Verification

<!-- test: contains=Completed -->
```bash
kubectl get pod import -n trouble-12
```

## Lesson learned

- `OOMKilled` / exit code 137 / logs that just stop = the memory limit, not a bug in the logs.
- Set limits from measured usage plus headroom (`kubectl top pod` with metrics-server, lesson 26).
- If memory keeps growing until the kill, raising the limit only delays it: that is a leak to fix in the program.

## Cleanup

🧹 Delete the namespace `trouble-12`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-12
```

Next: [Problem 13 · DNS resolution failure](13-dns-failure.md)
