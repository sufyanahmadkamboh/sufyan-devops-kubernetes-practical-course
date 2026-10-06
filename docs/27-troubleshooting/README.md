# 27 · Troubleshooting Kubernetes

> Level 14 · Troubleshooting · ⏱ 45 minutes · run every command from the course folder · cluster: minikube

## What is it?

Troubleshooting is finding out **why** the cluster does not do what you asked, with a method instead of guesses.
Kubernetes is unusually good at telling you what is wrong: every object has a status, every important step leaves an
**event**, every container keeps its **logs**, and you can step **inside** a running Pod. The skill is knowing which of
these to read first.

A doctor does not start with surgery: they ask what hurts, take your temperature, look at the test results, and only
then decide. Here the symptoms are `kubectl get`, the temperature is `kubectl describe` and the events, the test
results are the logs, and the examination is `kubectl exec` and `kubectl debug`.

## Why do we need it?

Something always breaks: a typo in a label, an image tag that does not exist, a memory limit that is too small, a
policy that blocks a port. Copying the error text into a search engine finds other people's problems. Following the
same questions every time finds yours, usually in a few minutes. Lab 12 gives you fourteen real problems to practise
on; this lesson gives you the method and the tools.

## How does it work?

The troubleshooting mindset, in order:

```text
What is broken?                       "the backend does not answer"
        ↓
What should happen?                   "3 Pods ready behind the Service"
        ↓
What actually happened?               kubectl get: 0/1 READY, CrashLoopBackOff, Pending, …
        ↓
Which Kubernetes object controls it?  Pod? Deployment? Service? PVC? Ingress? NetworkPolicy?
        ↓
Inspect the object                    kubectl describe / kubectl get -o yaml
        ↓
Check events                          kubectl get events, the Events section of describe
        ↓
Check logs                            kubectl logs (--previous, -c)
        ↓
Check configuration                   env, ConfigMaps, Secrets, probes, selectors, resources
        ↓
Find the root cause → Fix → Verify    and verify with the same command that showed the problem
```

The status of a Pod already narrows it down:

| You see | It means | Look at |
|---|---|---|
| `Pending` | not scheduled, or waiting for a volume | events (`FailedScheduling`), the PVC |
| `ContainerCreating` for long | image pull, volume mount, network setup | events |
| `ErrImagePull` / `ImagePullBackOff` | the image cannot be downloaded | the `Failed to pull image` event |
| `CreateContainerConfigError` | a ConfigMap, Secret or key is missing | the `Error:` event |
| `CrashLoopBackOff` | the container keeps exiting | `kubectl logs --previous`, exit code |
| `Running`, `0/1 READY` | the readiness probe fails | the `Unhealthy` event |
| `OOMKilled`, exit 137 | over the memory limit | limits, `kubectl top` |
| everything Running, still no answer | Service, DNS, Ingress, NetworkPolicy | endpoints, `wget` from a Pod |

## Architecture

```text
                       ┌───────────── kubectl get ─────────────┐   status: what is happening
                       │                                       │
   you ──▶ API server ─┼──── kubectl describe / get events ────┤   events: what happened and why
                       │                                       │
                       ├──── kubectl logs [-c] [--previous] ───┤   logs: what the program said
                       │                                       │
                       └──── kubectl exec / kubectl debug ─────┘   inside: env, files, network, processes
                                        │
                                        ▼
                              Pod ── container(s) ── ephemeral debug container
```

## YAML

Two Pods to practise on. A Pod that fails at start-up:

<!-- test: contains=exit 1 -->
```bash
cat manifests/workloads/troubleshoot-crasher.yaml
```

And the backend with a second container, a "log shipper" that writes its own logs:

<!-- test: contains=log-shipper -->
```bash
cat manifests/workloads/troubleshoot-two-containers.yaml
```

| Field | Meaning |
|---|---|
| `command: ["sh", "-c", "…; exit 1"]` | the crasher prints two lines and exits with code 1, like a program that cannot find its configuration |
| two entries under `containers` | one Pod, two containers: they share the network (`localhost`) and have separate logs (lesson 06) |

## Hands-On Lab

**1. Create the crashing Pod and look at it:**

<!-- test: contains=created -->
```bash
kubectl create namespace debug-lab
kubectl apply -f manifests/workloads/troubleshoot-crasher.yaml -n debug-lab
```

<!-- test: contains=CrashLoopBackOff; retry=20; output -->
```bash
kubectl get pod crasher -n debug-lab
kubectl get pod crasher -n debug-lab | grep -q CrashLoopBackOff
```

```text
NAME      READY   STATUS             RESTARTS     AGE
crasher   0/1     CrashLoopBackOff   1 (3s ago)   5s
```

**2. Events.** Every namespace keeps a short history of what happened to its objects (about an hour). They are the
first place to look, because they come from the components that did the work (scheduler, kubelet, controllers):

<!-- test: contains=BackOff; output -->
```bash
kubectl get events -n debug-lab --sort-by=.lastTimestamp
```

```text
LAST SEEN   TYPE      REASON      OBJECT        MESSAGE
5s          Normal    Scheduled   pod/crasher   Successfully assigned debug-lab/crasher to minikube
3s          Normal    Pulled      pod/crasher   Container image "busybox:1.37" already present on machine and can be accessed by the pod
3s          Normal    Created     pod/crasher   Container created
3s          Normal    Started     pod/crasher   Container started
1s          Warning   BackOff     pod/crasher   Back-off restarting failed container app in pod crasher_debug-lab(d095573c-6cac-45a0-a1c8-bcc1f6dfde17)
```

Only the warnings, across all namespaces, is a good habit when you do not know where to look yet:

<!-- test: contains=BackOff -->
```bash
kubectl get events -A --field-selector type=Warning
```

**3. The Events section of `describe`** shows the same events for one object, under its configuration and state:

<!-- test: contains=Last State; contains=Exit Code -->
```bash
kubectl describe pod crasher -n debug-lab | grep -E 'State:|Reason:|Exit Code:|Restart Count:'
```

**4. Logs.** The current container may have just restarted; the crashed one is `--previous`:

<!-- test: contains=no such file; output -->
```bash
kubectl logs crasher -n debug-lab --previous
```

```text
error: /etc/app/app.conf: no such file
starting the report service
```

Logs contain both standard output and standard error. Useful options: `--tail=50` (last lines), `--since=10m`,
`--timestamps`, `-f` (follow live, stop with Ctrl+C).

**5. Logs of a Pod with several containers:**

<!-- test: contains=log-shipper: shipped batch; retry=10 -->
```bash
kubectl apply -f manifests/workloads/troubleshoot-two-containers.yaml -n debug-lab > /dev/null
kubectl wait --for=condition=Ready pod/api-with-sidecar -n debug-lab --timeout=120s > /dev/null
sleep 6
kubectl logs api-with-sidecar -n debug-lab -c log-shipper --tail=2
```

Without `-c`, kubectl picks the first container and says so; `--all-containers --prefix` shows them all:

<!-- test: contains=log-shipper; contains=backend; output -->
```bash
kubectl logs api-with-sidecar -n debug-lab --all-containers --prefix --tail=1
```

```text
[pod/api-with-sidecar/backend] {"time":"2026-10-06T14:23:12.267162093Z","level":"INFO","msg":"listening","port":"8080","version":"1.0.0","pod":"api-with-sidecar"}
[pod/api-with-sidecar/log-shipper] log-shipper: shipped batch 2
```

**6. Inside a container with `kubectl exec`:** environment, processes, files, network and DNS, from the Pod's point
of view. The log shipper has a shell (BusyBox), and it shares the Pod's network with the backend, so `localhost:8080`
is the backend:

<!-- test: contains=alive; contains=Name; output -->
```bash
kubectl exec api-with-sidecar -n debug-lab -c log-shipper -- sh -c '
  echo "--- hostname: $(hostname)"
  echo "--- processes:"; ps | head -3
  echo "--- the backend through localhost:"; wget -qO- http://localhost:8080/livez; echo
  echo "--- DNS:"; nslookup kubernetes.default.svc.cluster.local | grep -A1 "^Name"'
```

```text
--- hostname: api-with-sidecar
--- processes:
PID   USER     TIME  COMMAND
    1 root      0:00 sh -c i=0; while true; do i=$((i+1)); echo "log-shipper: shipped batch $i"; sleep 5; done
    8 root      0:00 sleep 5
--- the backend through localhost:
{"status":"alive"}

--- DNS:
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

## Expected Result

The crasher in `CrashLoopBackOff` with its error in `--previous` logs; the two-container Pod `2/2` ready, with separate
logs per container, and a shell in the sidecar that reaches the backend on `localhost`.

## Inspect

The exit code tells you **how** a container ended:

<!-- test: contains=exit code 1 -->
```bash
kubectl get pod crasher -n debug-lab -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}, exit code {.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
```

| Exit code | Meaning |
|---|---|
| 0 | the process finished successfully (a Deployment restarts it anyway, lab 12 problem 04) |
| 1, 2, … small numbers | the application stopped itself: read its logs |
| 126 / 127 | the command is not executable / not found (wrong `command`) |
| 137 | killed with SIGKILL: out of memory (`OOMKilled`), or a liveness probe gave up |
| 143 | terminated with SIGTERM: a normal stop |

## Experiment

The Pod's previous logs are kept only for the **last** crashed container. Delete the Pod and they are gone; a
Deployment's replacement Pod starts with empty logs. Read logs before you delete anything:

<!-- test: contains=not found -->
```bash
kubectl delete pod crasher -n debug-lab --wait=true > /dev/null
kubectl logs crasher -n debug-lab --previous 2>&1 || true
```

## Break It

The backend container has no shell: its image is "distroless" (only the program, nothing else). Try to look inside:

<!-- test: fail; contains=executable file not found; output -->
```bash
kubectl exec api-with-sidecar -n debug-lab -c backend -- sh -c 'ps' 2>&1
```

```text
error: Internal error occurred: Internal error occurred: error executing command in container: failed to exec in container: failed to start exec "2d7c9e01d59392517e1888df1fc5c6fafe23e9ea025ec3ec36a36d8360e69170": OCI runtime exec failed: exec failed: unable to start container process: exec: "sh": executable file not found in $PATH
```

## Troubleshoot It

*What should happen?* A process list. *What happened?* `exec: "sh": executable file not found`: kubectl reached the
container, but there is no `sh` in it. `kubectl exec` can only run programs that exist **inside the image**, and
minimal images (distroless, scratch) have no shell, `ps` or `wget`, on purpose: fewer programs, fewer
vulnerabilities. Which programs does the image have?

<!-- test: contains=backend -->
```bash
kubectl get pod api-with-sidecar -n debug-lab -o jsonpath='{.spec.containers[?(@.name=="backend")].image}{"\n"}'
```

Only `/backend`. The tools have to come from somewhere else.

## Fix It

`kubectl debug` adds an **ephemeral container** to the running Pod, from any image you choose. With `--target`, it
shares the target container's process namespace, so it sees the backend's processes, and it shares the Pod's network:

<!-- test: contains=/backend; contains=alive; timeout=180; output -->
```bash
kubectl debug api-with-sidecar -n debug-lab -c debugger --image=busybox:1.37 --target=backend -- \
  sh -c 'ps; wget -qO- http://localhost:8080/livez; echo' > /dev/null
kubectl wait --for=jsonpath='{.status.ephemeralContainerStatuses[0].state.terminated.reason}'=Completed \
  pod/api-with-sidecar -n debug-lab --timeout=120s > /dev/null
kubectl logs api-with-sidecar -n debug-lab -c debugger
```

```text
PID   USER     TIME  COMMAND
    1 65532     0:00 /backend
   19 root      0:00 sh -c ps; wget -qO- http://localhost:8080/livez; echo
   25 root      0:00 ps
{"status":"alive"}
```

PID 1 is `/backend`, running as user 65532 (`nonroot`): you are looking at the backend's processes from a container
that has the tools. Interactively, the same command with `-it` and without the `sh -c` part opens a shell. Ephemeral
containers cannot be removed from a Pod; they disappear when the Pod is replaced.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Reading `kubectl logs` of a restarted container | empty or unrelated logs | `--previous` |
| Forgetting `-c` on a multi-container Pod | logs of the wrong container | `-c NAME` or `--all-containers --prefix` |
| Deleting a broken Pod "to see if it helps" | the evidence (logs, events) is gone, the new Pod fails the same way | read events and logs first, then fix the cause |
| Expecting a shell in every image | `executable file not found` | `kubectl debug` with a tools image |
| Searching the error text first | other people's problems | follow the method: object → events → logs → configuration |

## Best Practices

- Start with `kubectl get` (status), then `kubectl describe` (events), then `kubectl logs` (application).
- Keep a "debug" toolbox image you trust (BusyBox, or a larger one with `curl`, `dig`, `tcpdump`) for `kubectl debug`.
- Applications should log to stdout/stderr with clear messages; that is what `kubectl logs` and every log system read.
- Verify a fix with the same command that showed the problem.

## Challenge

**Task:** a Pod `mystery` runs a web server that does not start. Find out why, using only the commands of this lesson.

<!-- test: contains=created -->
```bash
kubectl run mystery -n debug-lab --image=nginx:1.30-alpine --restart=Never -- nginx -g 'daemon off; worker_processes nope;'
```

**Requirements:** name the exact line of configuration that is wrong, from the logs.

**Hints:** the Pod does not restart (`--restart=Never`), so its logs stay readable; nginx prints a precise error.

**Expected Result:** one sentence naming the setting and the value.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=worker_processes; retry=15; output -->
```bash
kubectl get pod mystery -n debug-lab
kubectl logs mystery -n debug-lab | grep -i emerg
```

```text
NAME      READY   STATUS   RESTARTS   AGE
mystery   0/1     Error    0          3s
2026/10/06 14:23:22 [emerg] 1#1: "worker_processes" directive invalid value in command line
nginx: [emerg] "worker_processes" directive invalid value in command line
```

</details>

The status `Error` says the process ended with a non-zero code; the logs say why: `worker_processes` needs a number
or `auto`, and `nope` is neither. Status → logs → the exact line, without guessing.

## Key Takeaways

- Method: what is broken → expected vs actual → which object → describe/events → logs → configuration → fix → verify.
- Events (`kubectl get events --sort-by=.lastTimestamp`, `describe`) explain most problems at once.
- `kubectl logs --previous` for crashes, `-c` for multi-container Pods; exit codes tell how a container ended.
- `kubectl exec` runs tools that exist in the image; `kubectl debug --target` brings your own.
- Real-world use: on-call engineers follow exactly this order on production clusters, often under time pressure;
  the method keeps them from guessing.

## Cleanup

🧹 Delete the namespace `debug-lab` (the crasher, the two-container Pod with its debug container, and `mystery`):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace debug-lab
```

Next: [28 · Helm](../28-helm/README.md)
