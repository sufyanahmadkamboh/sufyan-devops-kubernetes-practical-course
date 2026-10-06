# 06 · Pods

> Level 3 · Pods · ⏱ 45 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **Pod** is the smallest thing Kubernetes runs: one or more containers that always run **together, on the same
node**, sharing one network address and, optionally, storage. Kubernetes never runs a container on its own; it runs
Pods, and a Pod runs containers.

Analogy: a container is a person; a Pod is a small apartment. Most apartments have one resident. Sometimes two people
live together because they work closely: they share the address (network), the kitchen (volumes) and they move in
and out together.

## Why do we need it?

Some processes belong together: a web server and a helper that refreshes its files, an application and an agent that
ships its logs. They must run on the same machine, talk over `localhost` and share files. The Pod is the unit that
guarantees this. It is also the unit Kubernetes schedules, gives an IP address, restarts and reports on.

## How does it work?

- **Pod IP:** every Pod gets its own IP address inside the cluster; all its containers share it (and its ports).
- **Shared network namespace:** containers in a Pod reach each other on `localhost`; two containers in one Pod cannot
  both listen on the same port.
- **Shared volumes:** a volume declared in the Pod can be mounted into several of its containers.
- **Lifecycle (phase):** `Pending` (accepted, not running yet: scheduling, image download) → `Running` (at least one
  container running) → `Succeeded` (all containers exited with 0) or `Failed`. The kubelet restarts crashed
  containers according to `restartPolicy` (`Always` by default).
- **Pods are mortal:** a Pod is never moved or resurrected. If it is deleted, or its node dies, it is gone; something
  else (a ReplicaSet, lesson 08) must create a new one, with a new name and a new IP. That is why you rarely create
  bare Pods in real life.

## Architecture

```text
 Pod "web-with-sidecar"   IP 10.244.x.y   (on one node)
 ┌───────────────────────────────────────────────────────┐
 │  ┌──────────────────┐        ┌──────────────────────┐ │
 │  │ container "web"  │        │ container "sidecar"  │ │
 │  │ nginx :80        │◀──────▶│ busybox              │ │   shared network:
 │  └────────┬─────────┘localhost└─────────┬───────────┘ │   both see localhost:80
 │           │ /usr/share/nginx/html       │ /html       │
 │           └──────────┬──────────────────┘             │   shared storage:
 │                volume "html" (emptyDir)               │   the same files
 └───────────────────────────────────────────────────────┘
```

## YAML

The first Pod:

<!-- test: contains=kind: Pod -->
```bash
cat manifests/pods/06-nginx-pod.yaml
```

| Line | Meaning |
|---|---|
| `apiVersion: v1` | Pods are part of the core API, version `v1` |
| `kind: Pod` | create a Pod |
| `metadata:` | identity of the object |
| `  name: nginx` | its name, unique in its namespace |
| `spec:` | the desired state |
| `  containers:` | the list of containers in the Pod (a list: each item starts with `-`) |
| `    - name: nginx` | the container's name inside the Pod (used by `logs -c`, `exec -c`) |
| `      image: nginx:1.30-alpine` | the image, always with a tag |

The two-container Pod adds two ideas:

<!-- test: contains=emptyDir -->
```bash
cat manifests/pods/06-sidecar-pod.yaml
```

| Field | Meaning |
|---|---|
| `spec.volumes[].name: html`, `emptyDir: {}` | a volume that lives as long as the Pod: an empty folder shared by its containers (lesson 13) |
| `containers[].volumeMounts` | where each container sees that volume: `/usr/share/nginx/html` for nginx, `/html` for the sidecar |
| `containers[].command` | the command the container runs, replacing the image's default (`CMD`) |
| `ports[].containerPort: 80` | documents the port nginx listens on (it does not publish anything) |

## Hands-On Lab

A namespace for this lesson:

<!-- test: contains=created -->
```bash
kubectl create namespace pods-lab
kubectl config set-context --current --namespace=pods-lab
```

**1. Create the first Pod and watch it start:**

<!-- test: contains=pod/nginx created -->
```bash
kubectl apply -f manifests/pods/06-nginx-pod.yaml
kubectl wait --for=condition=Ready pod/nginx --timeout=120s
```

<!-- test: contains=Running; output -->
```bash
kubectl get pods -o wide
```

```text
NAME    READY   STATUS    RESTARTS   AGE   IP               NODE       NOMINATED NODE   READINESS GATES
nginx   1/1     Running   0          1s    10.244.120.111   minikube   <none>           <none>
```

**2. Describe it and read its logs:**

<!-- test: contains=Started; output -->
```bash
kubectl describe pod nginx | grep -E '^(Status|IP|Node):|Started'
```

```text
Node:             minikube/192.168.49.2
Status:           Running
IP:               10.244.120.111
      Started:      Tue, 06 Oct 2026 03:27:03 +0200
  Normal  Started    0s    kubelet            spec.containers{nginx}: Container started
```

<!-- test: contains=start worker -->
```bash
kubectl logs nginx --tail=3
```

**3. The Pod's own IP is reachable from inside the cluster** (here from a temporary Pod, removed afterwards with
`--rm`):

<!-- test: contains=Welcome to nginx -->
```bash
ip=$(kubectl get pod nginx -o jsonpath='{.status.podIP}')
kubectl run client --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 "http://$ip" | grep -o '<title>.*</title>'
```

**4. A Pod with two containers:**

<!-- test: contains=pod/web-with-sidecar created; output=tail:1 -->
```bash
kubectl apply -f manifests/pods/06-sidecar-pod.yaml
kubectl wait --for=condition=Ready pod/web-with-sidecar --timeout=120s > /dev/null
kubectl get pod web-with-sidecar
```

```text
...
web-with-sidecar   2/2     Running   0          1s
```

`READY 2/2`: two containers, both ready.

**5. Shared storage:** the page nginx serves was written by the other container:

<!-- test: contains=page written by the sidecar; retry=5 -->
```bash
kubectl exec web-with-sidecar -c web -- cat /usr/share/nginx/html/index.html
```

**6. Shared network:** from the sidecar container, `localhost:80` is nginx in the *other* container:

<!-- test: contains=page written by the sidecar -->
```bash
kubectl exec web-with-sidecar -c sidecar -- wget -qO- http://localhost:80
```

## Expected Result

`nginx` is `Running` with its own IP; `web-with-sidecar` is `2/2 Running`; nginx serves a page that the sidecar keeps
rewriting, and the sidecar reaches nginx on `localhost`.

## Inspect

<!-- test: contains=web; contains=sidecar -->
```bash
kubectl get pod web-with-sidecar -o jsonpath='{range .spec.containers[*]}{.name}{"  "}{.image}{"\n"}{end}'
kubectl logs web-with-sidecar -c web --tail=2
kubectl get pod nginx -o jsonpath='phase={.status.phase} ip={.status.podIP} node={.spec.nodeName}{"\n"}'
```

With more than one container, `logs` and `exec` need `-c NAME`; without it kubectl picks the first container and
says so.

## Experiment

Delete the bare Pod and see what happens:

<!-- test: contains=No resources found; output -->
```bash
kubectl delete pod nginx
kubectl get pods -l '!app' 2>&1
```

```text
pod "nginx" deleted from pods-lab namespace
No resources found in pods-lab namespace.
```

Gone for good: nobody recreates a bare Pod. Lesson 08 adds the object that does.

## Break It

A Pod whose container exits with an error right after starting:

<!-- test: contains=pod/crasher created -->
```bash
kubectl apply -f manifests/pods/06-crashing-pod.yaml
```

<!-- test: contains=CrashLoopBackOff; retry=30; output -->
```bash
kubectl get pod crasher
```

```text
NAME      READY   STATUS             RESTARTS     AGE
crasher   0/1     CrashLoopBackOff   1 (4s ago)   4s
```

## Troubleshoot It

*What should happen?* A running container. *What happened?* `CrashLoopBackOff` and a growing `RESTARTS` count: the
container starts, exits, is restarted, exits again, and the kubelet waits longer each time (the "back-off").
*Which object controls it?* The Pod's container: its command and its logs. Events first:

<!-- test: contains=Back-off -->
```bash
kubectl describe pod crasher | grep -E 'Last State|Exit Code|Back-off' | head -4
```

The exit code is 1: the program itself failed (an image problem would show `ErrImagePull` instead). The logs of the
last run say why:

<!-- test: contains=giving up; retry=10 -->
```bash
kubectl logs crasher --previous
```

Root cause: the command ends with `exit 1` ("missing configuration"). Kubernetes is doing its job, restarting it, but
cannot fix the program.

## Fix It

A Pod's containers cannot be changed in place: delete the Pod and create it with a command that keeps running.

<!-- test: contains=Running -->
```bash
kubectl delete pod crasher
kubectl run crasher --image=busybox:1.37 -- sh -c 'echo starting; echo "configuration found"; sleep 3600'
kubectl wait --for=condition=Ready pod/crasher --timeout=120s > /dev/null
kubectl get pod crasher
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| A container whose command ends | `Completed`, then `CrashLoopBackOff` | the main process must keep running (a server, not a script) |
| Two containers on the same port in one Pod | the second one fails: `address already in use` | different ports; they share one network |
| `logs`/`exec` without `-c` on a multi-container Pod | the wrong container | `-c NAME` |
| Editing a Pod's image or command in place | `Forbidden: pod updates may not change fields` | delete and recreate, or use a Deployment (lesson 09) |
| Creating bare Pods for applications | a deleted Pod never comes back | Deployments (lessons 08–09) |

## Best Practices

- One main process per container, one main container per Pod; add sidecars only for helpers that must share its
  network or files.
- Do not create bare Pods for applications; Deployments create them for you.
- Always pin image tags; keep `-c NAME` in scripts.

## Challenge

**Task:** create a Pod `talkers` with two `busybox:1.37` containers: `server` runs `nc -lk -p 9000 -e echo hello`, and
`client` runs `sleep 3600`. Prove from `client` that `server` answers on `localhost:9000`.

**Requirements:** one YAML manifest (`kubectl apply -f -` reads it from standard input); the test from the `client` container with `kubectl exec`.

**Hints:** in YAML a command is a list: `command: ["sh", "-c", "..."]`; `nc localhost 9000` connects and prints
what the server sends.

**Expected Result:** `hello`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=hello; retry=10 -->
```bash
kubectl apply -f - > /dev/null <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: talkers
spec:
  containers:
    - name: server
      image: busybox:1.37
      command: ["sh", "-c", "nc -lk -p 9000 -e echo hello"]
    - name: client
      image: busybox:1.37
      command: ["sh", "-c", "sleep 3600"]
EOF
kubectl wait --for=condition=Ready pod/talkers --timeout=120s > /dev/null
kubectl exec talkers -c client -- sh -c 'nc localhost 9000 < /dev/null'
```

</details>

Both containers share the Pod's network namespace, so `localhost:9000` in `client` is the `server` container's port:
no Service, no IP address needed inside a Pod.

## Key Takeaways

- A Pod is one or more containers on one node, sharing an IP (localhost) and volumes.
- Phases: Pending → Running → Succeeded/Failed; `CrashLoopBackOff` = the container keeps exiting.
- `describe` (events, exit code) and `logs --previous` explain crashes.
- Bare Pods are never recreated; controllers (ReplicaSets, Deployments) manage Pods for you.
- Real-world use: sidecars ship logs, refresh certificates or proxy traffic next to the main application.

## Cleanup

🧹 Delete the namespace `pods-lab` (the Pods `web-with-sidecar`, `crasher`, `talkers`) and switch kubectl back to
`default`:

<!-- test: contains=deleted -->
```bash
kubectl config set-context --current --namespace=default
kubectl delete namespace pods-lab
```

Next: [07 · Labels and selectors](../07-labels-selectors/README.md)
