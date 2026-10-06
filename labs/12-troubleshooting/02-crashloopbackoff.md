# Problem 02 · CrashLoopBackOff

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The new queue worker was deployed this morning. Its Pod shows a restart count that keeps growing. Set it up:

<!-- test: contains=created -->
```bash
kubectl create namespace trouble-02
kubectl apply -f labs/12-troubleshooting/manifests/02-crashloop.yaml -n trouble-02
```

## Symptoms

<!-- test: contains=CrashLoopBackOff; retry=30; output -->
```bash
kubectl get pods -n trouble-02 | grep CrashLoopBackOff
```

```text
worker-5b6dd64668-nkhvt   0/1     CrashLoopBackOff   1 (2s ago)   4s
```

`CrashLoopBackOff`: the container starts, exits, is restarted, exits again; Kubernetes waits longer and longer
between attempts (10 s, 20 s, 40 s… up to 5 minutes).

## First command to run

The logs of the container that crashed. The current container may not have started yet, so ask for the **previous**
one:

<!-- test: contains=QUEUE_URL is not set; output -->
```bash
kubectl logs -n trouble-02 -l app=worker --previous
```

```text
fatal: QUEUE_URL is not set
worker starting
```

## Investigation

*What should happen?* A long-running worker. *What happened?* It exits during start-up. The exit code confirms that
the application itself chose to stop (code 1), as opposed to being killed (137, problem 12):

<!-- test: contains=exit code 1; output -->
```bash
kubectl get pods -n trouble-02 -l app=worker -o jsonpath='last state: {.items[0].status.containerStatuses[0].lastState.terminated.reason}, exit code {.items[0].status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

```text
last state: Error, exit code 1
```

Which environment variables does the container get?

<!-- test: absent=QUEUE_URL -->
```bash
kubectl get deployment worker -n trouble-02 -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

None at all.

## Root cause

The worker needs `QUEUE_URL` and refuses to start without it; the Deployment does not set it. Kubernetes restarts the
container exactly as configured, so it fails the same way every time.

## Fix

Give the container its configuration (in real life from a ConfigMap, lesson 11):

<!-- test: contains=successfully rolled out -->
```bash
kubectl set env deployment/worker -n trouble-02 QUEUE_URL=amqp://queue:5672
kubectl rollout status deployment/worker -n trouble-02 --timeout=120s
```

## Verification

<!-- test: contains=connected to amqp://queue:5672; retry=10 -->
```bash
kubectl logs -n trouble-02 -l app=worker
```

## Lesson learned

- `CrashLoopBackOff` is not the error; it is Kubernetes waiting between restarts. The error is in the logs.
- `kubectl logs --previous` shows the container that crashed; without it you may see an empty, just-started one.
- Exit code 1 (or any small number) = the application stopped itself; 137 = killed (out of memory, problem 12).

## Cleanup

🧹 Delete the namespace `trouble-02` and the worker in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-02
```

Next: [Problem 03 · ImagePullBackOff](03-imagepullbackoff.md)
