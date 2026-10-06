# 04 · kubectl fundamentals

> Level 2 · kubectl · ⏱ 45 minutes · run every command from the course folder · cluster: minikube

## What is it?

`kubectl` ("kube control") is the command-line client of Kubernetes. Every kubectl command becomes a request to the
API server: *list these objects*, *create this one*, *show me its logs*. Learning kubectl is learning to ask the
cluster questions and to read its answers.

## Why do we need it?

Kubernetes has no screen of its own; the API is the only way in. kubectl is the tool every Kubernetes engineer uses
daily, on every cluster, cloud or local. The same twenty commands cover almost all of the work: looking (get,
describe, logs, events), changing (apply, delete, edit, scale) and debugging (exec, port-forward).

## How does it work?

```text
kubectl get pods -n kubectl-lab
   │  reads ~/.kube/config: which cluster (context), which user, which namespace by default
   ▼
HTTPS GET /api/v1/namespaces/kubectl-lab/pods   ──▶ API server ──▶ etcd
   ◀── JSON list of Pods
   │  formats it: a table (default), wide, yaml, json, jsonpath, custom-columns
   ▼
NAME   READY   STATUS    RESTARTS   AGE
```

The pattern is always `kubectl VERB [TYPE] [NAME] [flags]`: `kubectl get pod web -n kubectl-lab -o yaml`.

## Architecture

```text
   kubectl ──▶ kubeconfig (~/.kube/config) ──▶ context = cluster + user + namespace
                                                  │
                                                  ▼
                                      Kubernetes API (API server)
                                                  │
                                                  ▼
                                          the cluster's objects
```

## YAML

kubectl can create objects from flags (**imperative**: `kubectl create deployment api --image=...`) or from files
(**declarative**: `kubectl apply -f file.yaml`, "make the cluster look like this file"). The course uses files,
because files can be reviewed, versioned and applied again. This lesson's file:

<!-- test: contains=kind: Pod -->
```bash
cat manifests/pods/web-pod.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: v1` | which version of the Kubernetes API defines this kind (`v1` = the core API) |
| `kind: Pod` | which kind of object to create |
| `metadata.name`, `metadata.labels` | its name, and labels to find it by (lesson 07) |
| `spec` | the desired state: here, one container from `nginx:1.30-alpine` listening on port 80 |

## Hands-On Lab

Every command below comes with its purpose, syntax and the options you will use most.

**1. A namespace for this lesson** (`create`; namespaces are lesson 05):

<!-- test: contains=created -->
```bash
kubectl create namespace kubectl-lab
```

**2. `kubectl apply`**: create or update objects from a file.

| | |
|---|---|
| Purpose | make the cluster match a file (create if missing, update if different) |
| Syntax | `kubectl apply -f FILE_OR_FOLDER [-n NAMESPACE]` |
| Common options | `-f folder/` (every file in it), `--dry-run=server` (validate without changing), `-R` (recursive) |
| Troubleshooting | `the path ... does not exist` (wrong path), `error validating data` (a field is misspelled) |

<!-- test: contains=pod/web created -->
```bash
kubectl apply -f manifests/pods/web-pod.yaml -n kubectl-lab
kubectl wait --for=condition=Ready pod/web -n kubectl-lab --timeout=120s
```

**3. `kubectl get`**: list objects.

| | |
|---|---|
| Purpose | the one-line state of objects |
| Syntax | `kubectl get TYPE [NAME] [-n NS \| -A] [-o FORMAT] [-l LABEL=VALUE]` |
| Common options | `-o wide` (more columns: IP, node), `-o yaml` / `-o json` (the full object), `-A` (all namespaces), `-l app=web` (by label), `--show-labels`, `-w` (watch for changes) |
| Troubleshooting | `No resources found in default namespace` → wrong namespace; `the server doesn't have a resource type` → typo in TYPE |

<!-- test: contains=Running; output -->
```bash
kubectl get pods -n kubectl-lab
kubectl get pods -n kubectl-lab -o wide
```

```text
NAME   READY   STATUS    RESTARTS   AGE
web    1/1     Running   0          1s
NAME   READY   STATUS    RESTARTS   AGE   IP               NODE       NOMINATED NODE   READINESS GATES
web    1/1     Running   0          1s    10.244.120.116   minikube   <none>           <none>
```

`-o wide` adds the Pod's IP address and the node it runs on. `READY 1/1`: one of one containers is ready.
`-o yaml` shows everything Kubernetes knows about the object, including fields it filled in itself:

<!-- test: contains=nginx:1.30-alpine -->
```bash
kubectl get pod web -n kubectl-lab -o yaml | grep -E '^  (name|namespace|uid):|image:|phase:|podIP:'
```

**4. `kubectl describe`**: a readable report, with the object's **events** at the end.

| | |
|---|---|
| Purpose | explain an object: configuration, state, and what happened to it (events) |
| Syntax | `kubectl describe TYPE NAME [-n NS]` |
| Troubleshooting | the Events section is where Kubernetes says *why* something is wrong (lesson 27) |

<!-- test: contains=Started; retry=10; output -->
```bash
kubectl describe pod web -n kubectl-lab | grep -A8 '^Events'
```

```text
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  2s    default-scheduler  Successfully assigned kubectl-lab/web to minikube
  Normal  Pulled     1s    kubelet            spec.containers{web}: Container image "nginx:1.30-alpine" already present on machine and can be accessed by the pod
  Normal  Created    1s    kubelet            spec.containers{web}: Container created
  Normal  Started    1s    kubelet            spec.containers{web}: Container started
```

The whole life of the Pod in four lines: the scheduler placed it, the kubelet found the image, created and started
the container.

**5. `kubectl logs`**: what the container writes to stdout/stderr.

| | |
|---|---|
| Syntax | `kubectl logs POD [-c CONTAINER] [-n NS]` |
| Common options | `--tail=20`, `--since=5m`, `-f` (follow), `--previous` (the crashed container before the restart), `-l app=web` (by label) |

<!-- test: contains=start worker -->
```bash
kubectl logs web -n kubectl-lab --tail=2
```

**6. `kubectl exec`**: run a command inside a running container.

| | |
|---|---|
| Syntax | `kubectl exec POD [-c CONTAINER] -- COMMAND [ARGS]` (`-it POD -- sh` for an interactive shell) |
| Troubleshooting | `executable file not found` → the image has no such program (many images have no shell, lesson 27) |

<!-- test: contains=nginx version -->
```bash
kubectl exec web -n kubectl-lab -- nginx -v
```

**7. `kubectl port-forward`**: reach a Pod (or Service) from your computer, through the API server.

| | |
|---|---|
| Syntax | `kubectl port-forward pod/web LOCAL:REMOTE` (or `svc/NAME`) |
| Note | it runs until you stop it (Ctrl+C); here it runs in the background and is stopped with `kill` |

<!-- test: contains=Welcome to nginx -->
```bash
kubectl port-forward -n kubectl-lab pod/web 18081:80 > /dev/null 2>&1 &
pf=$!
sleep 3
curl -s http://localhost:18081 | grep -o '<title>.*</title>'
kill $pf
```

**8. `kubectl explain`**: the API documentation, built in.

<!-- test: contains=Container image name -->
```bash
kubectl explain pod.spec.containers.image
```

**9. `kubectl create`** (imperative) and **`kubectl get all`**:

<!-- test: contains=deployment.apps/api -->
```bash
kubectl create deployment api --image=learning-app/backend:1.0.0 -n kubectl-lab
kubectl rollout status deployment/api -n kubectl-lab --timeout=120s
kubectl get all -n kubectl-lab
```

`get all` lists the common workload kinds (Pods, Services, Deployments, ReplicaSets…): one command created a
Deployment, which created a ReplicaSet, which created a Pod (lessons 08–09).

**10. `kubectl get events`**: everything that happened in a namespace, newest last.

<!-- test: contains=ScalingReplicaSet; retry=10 -->
```bash
kubectl get events -n kubectl-lab --sort-by=.lastTimestamp | grep -E 'deployment/|replicaset/|pod/api'
```

**11. `kubectl edit`** opens the live object in an editor and applies your changes when you save. It is interactive,
so the course uses its scriptable equivalent, `kubectl patch`, to change the same field:

<!-- test: skip -->
```bash
kubectl edit deployment api -n kubectl-lab
```

<!-- test: contains=patched -->
```bash
kubectl patch deployment api -n kubectl-lab --type=json -p '[{"op":"replace","path":"/spec/replicas","value":2}]'
kubectl rollout status deployment/api -n kubectl-lab --timeout=120s
```

**12. `kubectl config`**: which cluster, user and namespace kubectl uses.

<!-- test: contains=minikube; output -->
```bash
kubectl config get-contexts
kubectl config current-context
```

```text
CURRENT   NAME       CLUSTER    AUTHINFO   NAMESPACE
*         minikube   minikube   minikube   default
minikube
```

## Expected Result

A `web` Pod `Running` in the namespace `kubectl-lab`, reachable through `port-forward`; a Deployment `api` with 2 Pods;
the context `minikube`.

## Inspect

<!-- test: contains=web; contains=api -->
```bash
kubectl get pods -n kubectl-lab -o custom-columns=NAME:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName,IMAGE:.spec.containers[0].image
kubectl get pods -n kubectl-lab --show-labels
```

`-o custom-columns` prints exactly the fields you ask for (paths into the object, as in `-o yaml`); `-o jsonpath` does
the same for scripts.

## Experiment

`--dry-run=client -o yaml` turns any imperative command into a YAML file you can keep:

<!-- test: contains=kind: Deployment; contains=replicas: 3 -->
```bash
kubectl create deployment demo --image=nginx:1.30-alpine --replicas=3 --dry-run=client -o yaml
```

Nothing was created; kubectl only printed the object it would send. This is the fastest way to start a new manifest.

## Break It

Look for the Pod without saying which namespace:

<!-- test: fail; contains=NotFound; output -->
```bash
kubectl get pod web 2>&1
```

```text
Error from server (NotFound): pods "web" not found
```

## Troubleshoot It

*What should happen?* The `web` Pod you created. *What happened?* `NotFound`. Did it disappear, or are you looking
in the wrong place? kubectl uses the context's default namespace when you give none:

<!-- test: contains=default -->
```bash
kubectl config view --minify -o jsonpath='namespace: {..namespace}{"\n"}'
kubectl get pods 2>&1 | head -1
kubectl get pods -A -l app=web
```

The context has no namespace set, which means `default`, and `default` has no Pod called `web`. `-A` (all namespaces)
finds it in `kubectl-lab`. Root cause: wrong namespace, the most common kubectl "error" of all.

## Fix It

Give the namespace, or make `kubectl-lab` the default for the current context:

<!-- test: contains=web -->
```bash
kubectl get pod web -n kubectl-lab
kubectl config set-context --current --namespace=kubectl-lab
kubectl get pod web
kubectl config set-context --current --namespace=default
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Forgetting `-n` | `NotFound`, `No resources found in default namespace` | `-n NS`, `-A` to search everywhere, or set the context's namespace |
| `kubectl create -f` twice | `AlreadyExists` | `kubectl apply -f` creates or updates |
| Wrong context | commands hit another cluster | `kubectl config current-context` before every `delete` |
| Typo in a field | `unknown field "imgae"` | `kubectl explain` the path; `--dry-run=server` checks before applying |
| Parsing tables in scripts | breaks when columns change | `-o jsonpath`, `-o custom-columns`, `-o json` |

## Best Practices

- `apply -f` files for everything that should last; imperative commands for quick experiments.
- `describe` and `get events` first when something is wrong, before searching the internet.
- Keep `-n` explicit in scripts; never rely on the context's default namespace.

## Challenge

**Task:** list the name, image and node of every Pod in the cluster, in all namespaces, sorted by node.

**Requirements:** one kubectl command; no `grep`, `awk` or `sort`.

**Hints:** `-A`, `-o custom-columns`, `--sort-by`; the namespace is `.metadata.namespace`.

**Expected Result:** a table with the system Pods, `web` and the two `api` Pods.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=kubectl-lab; contains=kube-system -->
```bash
kubectl get pods -A --sort-by=.spec.nodeName -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,IMAGE:.spec.containers[0].image,NODE:.spec.nodeName
```

</details>

`custom-columns` paths are the same paths you see in `-o yaml`; `--sort-by` takes one of them. On a single-node
cluster every Pod is on `minikube`; on a real cluster this shows at once how Pods are spread.

## Key Takeaways

- `kubectl VERB TYPE NAME -n NS -o FORMAT`: get, describe, logs, exec, apply, delete, explain, port-forward, config.
- `apply -f` is declarative ("make it so"); `create` is imperative ("do this once").
- `describe` + `get events` explain problems; `-o wide/yaml/custom-columns/jsonpath` show exactly what you need.
- Real-world use: kubectl is the daily tool of every Kubernetes engineer, for deploying, inspecting and debugging.

## Cleanup

🧹 Delete the namespace `kubectl-lab` and everything in it (the `web` Pod and the `api` Deployment):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace kubectl-lab
```

Next: [05 · Namespaces](../05-namespaces/README.md)
