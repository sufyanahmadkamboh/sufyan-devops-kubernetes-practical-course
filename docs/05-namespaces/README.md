# 05 · Namespaces

> Level 2 · kubectl · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **namespace** is a named folder inside the cluster. Most objects (Pods, Deployments, Services, ConfigMaps…) live in
exactly one namespace, and their names only have to be unique inside it. One cluster can hold `dev`, `test` and
`prod` side by side, each with its own `web` Pod.

Analogy: one office building (the cluster), many companies on different floors (namespaces). Two companies can both
have a "Reception" room; everybody knows which one you mean by the floor.

## Why do we need it?

- **Organization:** a team, an application or an environment gets its own space; `kubectl get pods -n dev` shows only
  what belongs there.
- **Isolation of names:** two teams can both call something `web`.
- **Resource management and access control:** quotas (how much CPU and memory a namespace may use) and permissions
  (RBAC, lesson 24) are set per namespace.
- **Clean-up:** deleting a namespace deletes everything inside it, in one command.

## How does it work?

Every cluster starts with a few namespaces: `default` (where things go when you name none), `kube-system` (the
cluster's own components, lesson 02), `kube-public` and `kube-node-lease`. A **namespaced** object belongs to one
namespace; a **cluster-scoped** object (a Node, a Namespace itself, a StorageClass, a ClusterRole) belongs to the whole
cluster. kubectl uses the namespace you give with `-n`, or the default namespace of your context.

Namespaces separate *names and permissions*, not the network: by default a Pod in `dev` can reach a Pod in `prod`.
NetworkPolicies (lesson 22) add network isolation.

## Architecture

```text
                         cluster
 ┌───────────────┬───────────────┬───────────────┬────────────────┐
 │ namespace dev │ namespace test│ namespace prod│ kube-system    │
 │  pod/hello    │  pod/hello    │  pod/hello    │  kube-apiserver│
 │  svc/web      │               │               │  coredns …     │
 └───────────────┴───────────────┴───────────────┴────────────────┘
   cluster-scoped (no namespace): nodes, namespaces, storageclasses, clusterroles …
```

## YAML

<!-- test: contains=kind: Namespace -->
```bash
cat manifests/namespaces/05-environments.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: v1`, `kind: Namespace` | a Namespace is a core (`v1`) object |
| `metadata.name` | the namespace's name: lowercase letters, digits and `-` |
| `metadata.labels.environment` | a label, so namespaces can be selected (`-l environment=prod`) |
| `---` | separates several objects in one file |

A namespace has no `spec`: it is only a name. Objects choose their namespace with `metadata.namespace`, or with
`-n` on the command line (the Pod file `manifests/pods/05-hello-pod.yaml` has no namespace, so the same file can go
into any of them).

## Hands-On Lab

**1. The namespaces every cluster starts with:**

<!-- test: contains=kube-system; output -->
```bash
kubectl get namespaces
```

```text
NAME              STATUS   AGE
default           Active   26m
ingress-nginx     Active   9m16s
kube-node-lease   Active   26m
kube-public       Active   26m
kube-system       Active   26m
```

**2. Create one imperatively, then the three environments from the file:**

<!-- test: contains=namespace/sandbox created; contains=namespace/prod created -->
```bash
kubectl create namespace sandbox
kubectl apply -f manifests/namespaces/05-environments.yaml
```

**3. The same Pod in two namespaces**, under the same name:

<!-- test: contains=pod/hello created -->
```bash
kubectl apply -f manifests/pods/05-hello-pod.yaml -n dev
kubectl apply -f manifests/pods/05-hello-pod.yaml -n prod
kubectl wait --for=condition=Ready pod/hello -n dev --timeout=120s
kubectl wait --for=condition=Ready pod/hello -n prod --timeout=120s
```

**4. Look in one namespace, then in all of them:**

<!-- test: contains=hello; output -->
```bash
kubectl get pods -n dev
kubectl get pods -A -l app=hello
```

```text
NAME    READY   STATUS    RESTARTS   AGE
hello   1/1     Running   0          2s
NAMESPACE   NAME    READY   STATUS    RESTARTS   AGE
dev         hello   1/1     Running   0          2s
prod        hello   1/1     Running   0          1s
```

## Expected Result

`dev`, `test`, `prod` and `sandbox` exist; a Pod named `hello` runs in both `dev` and `prod`; `kubectl get pods -A`
shows the `NAMESPACE` column that tells them apart.

## Inspect

Which kinds of objects belong to a namespace, and which to the whole cluster?

<!-- test: contains=pods; contains=nodes -->
```bash
kubectl api-resources --namespaced=true -o name | head -8
echo "..."
kubectl api-resources --namespaced=false -o name | head -8
```

Select namespaces by their labels:

<!-- test: contains=prod -->
```bash
kubectl get namespaces -l environment --show-labels
kubectl get namespaces -l environment=prod
```

## Experiment

Make `dev` the default namespace of your context, so `-n dev` is no longer needed, then switch back:

<!-- test: contains=hello -->
```bash
kubectl config set-context --current --namespace=dev
kubectl get pods
kubectl config set-context --current --namespace=default
```

Every kubectl command now looked in `dev`. This is convenient, and dangerous: a later `kubectl delete` without `-n`
also acts in `dev`. Always switch back.

## Break It

Apply a Pod whose file names a namespace that does not exist:

<!-- test: fail; contains=not found; output -->
```bash
kubectl apply -f manifests/pods/05-hello-pod-qa.yaml 2>&1
```

```text
Error from server (NotFound): error when creating "manifests/pods/05-hello-pod-qa.yaml": namespaces "qa" not found
```

## Troubleshoot It

*What should happen?* A Pod `hello` in `qa`. *What happened?* `NotFound … namespaces "qa" not found`. Read which
object was not found: not the Pod, the **namespace**. Kubernetes never creates a namespace for you. Check:

<!-- test: contains=NotFound -->
```bash
grep namespace manifests/pods/05-hello-pod-qa.yaml
kubectl get namespace qa 2>&1 || true
```

Root cause: the file names `namespace: qa`, and `qa` was never created.

## Fix It

Create the namespace first, then apply the file again:

<!-- test: contains=pod/hello created -->
```bash
kubectl create namespace qa
kubectl apply -f manifests/pods/05-hello-pod-qa.yaml
```

Namespace files are applied before the objects that live in them (put them first in a folder, or in a file named
`00-namespace.yaml`).

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Forgetting `-n` | `No resources found in default namespace` | `-n NS`, or `-A` to search all namespaces |
| Applying objects before their namespace | `namespaces "x" not found` | create the namespace first |
| `kubectl delete namespace` to "clean a bit" | everything inside is deleted, irreversibly | delete individual objects; delete a namespace only when all of it should go |
| Expecting namespaces to block network traffic | Pods in `dev` reach Pods in `prod` | NetworkPolicies (lesson 22) |
| Putting your own objects in `kube-system` | mixed with cluster components, hard to clean | one namespace per application or environment |

## Best Practices

- One namespace per application and environment (`shop-dev`, `shop-prod`) or per team, never everything in `default`.
- Label namespaces (`environment`, `team`) so they can be selected and governed.
- In production, environments usually live in separate clusters; namespaces still separate applications and teams.

## Challenge

**Task:** create a namespace `team-a` with the label `owner=team-a`, run an `nginx:1.30-alpine` Pod named `web` in it,
then list all namespaces that have an `owner` label.

**Requirements:** the namespace from a YAML file you write (or `kubectl create namespace` + `kubectl label`); the Pod
in that namespace.

**Hints:** `kubectl label namespace NAME KEY=VALUE`; `kubectl get namespaces -l owner`.

**Expected Result:** `team-a` is listed with its label, and `kubectl get pods -n team-a` shows `web` running.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=team-a; contains=Running -->
```bash
kubectl create namespace team-a
kubectl label namespace team-a owner=team-a
kubectl run web --image=nginx:1.30-alpine -n team-a
kubectl wait --for=condition=Ready pod/web -n team-a --timeout=120s
kubectl get namespaces -l owner --show-labels
kubectl get pods -n team-a
```

</details>

Labels on namespaces work exactly like labels on Pods (lesson 07): any tool, policy or person can select "all
namespaces of team-a" without knowing their names.

## Key Takeaways

- A namespace is a named space for objects; names are unique inside it, not across the cluster.
- `-n NS` chooses the namespace, `-A` searches all; without them kubectl uses the context's default (`default`).
- Deleting a namespace deletes everything in it.
- Real-world use: separating applications, teams and environments, and attaching quotas and permissions to them.

## Cleanup

🧹 Delete the namespaces of this lesson and everything in them: `sandbox`, `dev`, `test`, `prod`, `qa`, `team-a`
(the `hello` and `web` Pods):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace sandbox dev test prod qa team-a --ignore-not-found
```

Next: [06 · Pods](../06-pods/README.md)
