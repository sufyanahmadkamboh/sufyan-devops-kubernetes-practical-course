# Problem 04 · Container exits immediately

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The team wants a "toolbox" Pod with BusyBox to run debugging commands in. It keeps restarting, although nothing is
wrong in its logs. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-04
kubectl apply -f labs/12-troubleshooting/manifests/04-exits-immediately.yaml -n trouble-04
```

## Symptoms

<!-- test: anyof=Completed||CrashLoopBackOff; retry=30; output -->
```bash
kubectl get pods -n trouble-04 | grep -E 'Completed|CrashLoopBackOff'
```

```text
toolbox-65989c87c-xzkwn   0/1     Completed   0          2s
```

## First command to run

The logs first, as for any crash:

<!-- test: output -->
```bash
kubectl logs -n trouble-04 -l app=toolbox --previous 2>&1 | head -3
```

```text
```

Empty. Nothing was printed, so look at how the container ended:

<!-- test: contains=exit code 0; output -->
```bash
kubectl get pods -n trouble-04 -l app=toolbox -o jsonpath='last state: {.items[0].status.containerStatuses[0].lastState.terminated.reason}, exit code {.items[0].status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

```text
last state: Completed, exit code 0
```

## Investigation

Exit code 0, reason `Completed`: the container did not crash, it **finished successfully**. A container lives
exactly as long as its main process. Which process is that?

<!-- test: contains=command:; contains=busybox -->
```bash
kubectl get deployment toolbox -n trouble-04 -o jsonpath='command: {.spec.template.spec.containers[0].command}{"\n"}'
minikube image ls | grep busybox | head -1
```

No `command` in the Deployment, so the image's default runs: BusyBox's default command is `sh`. A shell without a
terminal (no `-it`) has nothing to read, so it exits at once with 0. A Deployment exists to keep a process
**running**, so it restarts the container, which exits again: `CrashLoopBackOff` with exit code 0.

## Root cause

The container has no long-running process. Deployments are for programs that run until stopped; a command that ends
belongs in a **Job** (lesson 17).

## Fix

Give the toolbox something that keeps running (here `sleep`), so the team can `kubectl exec` into it:

<!-- test: contains=successfully rolled out -->
```bash
kubectl patch deployment toolbox -n trouble-04 --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/command","value":["sleep","infinity"]}]'
kubectl rollout status deployment/toolbox -n trouble-04 --timeout=120s
```

## Verification

<!-- test: contains=BusyBox -->
```bash
kubectl get pods -n trouble-04
kubectl exec -n trouble-04 deploy/toolbox -- busybox | head -1
```

## Lesson learned

- A container runs as long as its main process; a Deployment restarts anything that ends, even successfully.
- `CrashLoopBackOff` with **exit code 0** and empty logs = the process simply finished: wrong command, or the work
  belongs in a Job.
- Check the image's default command (`ENTRYPOINT`/`CMD`) when a Pod spec sets none.

## Cleanup

🧹 Delete the namespace `trouble-04` and the toolbox in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-04
```

Next: [Problem 05 · Service cannot reach Pods](05-service-cannot-reach-pods.md)
