# 23 · ServiceAccounts

> Level 13 · Security & RBAC · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **ServiceAccount** is an identity for a **workload**: a Pod that talks to the Kubernetes API (to list Pods, read a
ConfigMap, create a Job) does it **as** a ServiceAccount. Kubernetes gives the Pod a short-lived token proving that
identity.

The analogy: people get a personal badge (a **user** account); the delivery robot in the building gets its own badge
too, with its own name, so the doors know it is the robot and not a person.

## Why do we need it?

Some applications need the Kubernetes API: a CI runner creating Pods, a monitoring agent reading nodes, an operator
managing a database, the ingress controller reading Ingresses (lesson 20). Each needs an identity, so that
permissions (lesson 24) can be given to **that** application only, and so the audit log shows which application did
what.

| | User | ServiceAccount |
|---|---|---|
| Who | a person (you, a colleague) | a workload (a Pod) |
| Created by | outside Kubernetes (certificates, an identity provider) | Kubernetes itself: `kind: ServiceAccount` |
| Scope | the cluster | one namespace |
| Name in permissions | `developer` | `system:serviceaccount:<namespace>:<name>` |

## How does it work?

- Every namespace has a ServiceAccount called `default`; a Pod that names none uses it.
- `spec.serviceAccountName` chooses another one. The kubelet mounts a token, the cluster's CA certificate and the
  namespace into `/var/run/secrets/kubernetes.io/serviceaccount/`; the token is short-lived and renewed automatically.
- The API server is reachable from every Pod at `https://kubernetes.default.svc`.
- A ServiceAccount starts with **no permissions** (beyond discovering the API): identity is not authorization.
  RoleBindings (lesson 24) grant permissions.
- `automountServiceAccountToken: false` keeps the token out of Pods that never call the API.

## Architecture

```text
 Pod "reporter"  (serviceAccountName: reporter)
   /var/run/secrets/kubernetes.io/serviceaccount/
     token  ca.crt  namespace
        │  Authorization: Bearer <token>
        ▼
 API server ── authentication: "this is system:serviceaccount:sa-lab:reporter"
            ── authorization (RBAC, lesson 24): "may it list Pods?" → no binding → 403 Forbidden
```

## YAML

<!-- test: contains=kind: ServiceAccount -->
```bash
cat manifests/security/sa-reporter.yaml
```

| Field | Meaning |
|---|---|
| `kind: ServiceAccount` (`v1`) | a workload identity; only a name is needed |
| `spec.serviceAccountName: reporter` | the identity this Pod uses for API calls |
| `alpine:3.23` | a small image with a shell and `wget`, to make an API call by hand |

`manifests/security/sa-no-token.yaml` adds `automountServiceAccountToken: false` to a Pod spec.

## Hands-On Lab

**1. Every namespace has a `default` ServiceAccount:**

<!-- test: contains=default -->
```bash
kubectl create namespace sa-lab
kubectl get serviceaccounts -n sa-lab
```

**2. Create the `reporter` ServiceAccount and a Pod that uses it:**

<!-- test: contains=serviceaccount/reporter created -->
```bash
kubectl apply -f manifests/security/sa-reporter.yaml -n sa-lab
kubectl wait --for=condition=Ready pod/reporter -n sa-lab --timeout=120s
```

**3. What the Pod received:**

<!-- test: contains=token; contains=sa-lab; output -->
```bash
kubectl get pod reporter -n sa-lab -o jsonpath='{.spec.serviceAccountName}{"\n"}'
kubectl exec reporter -n sa-lab -- ls /var/run/secrets/kubernetes.io/serviceaccount
kubectl exec reporter -n sa-lab -- cat /var/run/secrets/kubernetes.io/serviceaccount/namespace
```

```text
reporter
ca.crt
namespace
token
sa-lab
```

**4. Call the Kubernetes API from inside the Pod**, as `reporter`: list the Pods of its namespace. (`--no-check-certificate`
keeps the example short; a real client verifies the server with `ca.crt`.)

<!-- test: contains=403 Forbidden; output -->
```bash
kubectl exec reporter -n sa-lab -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  wget -qO- --no-check-certificate --header "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api/v1/namespaces/sa-lab/pods 2>&1 || true'
```

```text
wget: server returned error: HTTP/1.1 403 Forbidden
```

## Expected Result

The Pod runs as `reporter`, has a token, and the API **refuses** it with `403 Forbidden`: the API knows exactly who
is asking (authentication worked) but nothing allows it (authorization said no).

## Inspect

Ask the API server what a ServiceAccount may do, without running anything as it:

<!-- test: contains=no -->
```bash
kubectl auth can-i list pods -n sa-lab --as=system:serviceaccount:sa-lab:reporter || true
```

(`kubectl auth can-i` also answers with its exit code: 0 for yes, 1 for no, so scripts can use it.)

The token itself is a signed JSON Web Token; its middle part names the identity (here decoded only to look at it):

<!-- test: contains=system:serviceaccount:sa-lab:reporter -->
```bash
kubectl exec reporter -n sa-lab -- sh -c 'cut -d. -f2 /var/run/secrets/kubernetes.io/serviceaccount/token | tr "_-" "/+" | base64 -d 2> /dev/null' | grep -o '"sub":"[^"]*"'
```

## Experiment

A Pod that never talks to the API should not carry a token:

<!-- test: contains=no token mounted -->
```bash
kubectl apply -f manifests/security/sa-no-token.yaml -n sa-lab > /dev/null
kubectl wait --for=condition=Ready pod/no-token -n sa-lab --timeout=120s > /dev/null
kubectl exec no-token -n sa-lab -- sh -c 'ls /var/run/secrets/kubernetes.io/serviceaccount 2> /dev/null || echo "no token mounted"'
```

If an attacker takes over this Pod, there is no credential to steal.

## Break It

A Deployment names a ServiceAccount that does not exist:

<!-- test: contains=0/1; output -->
```bash
kubectl apply -f manifests/security/sa-deployment-broken.yaml -n sa-lab > /dev/null
sleep 5
kubectl get deployment exporter -n sa-lab
kubectl get pods -n sa-lab -l app=exporter
```

```text
NAME       READY   UP-TO-DATE   AVAILABLE   AGE
exporter   0/1     0            0           5s
No resources found in sa-lab namespace.
```

## Troubleshoot It

*What should happen?* One `exporter` Pod. *What happened?* `0/1` and **no Pod at all**: not even a failing one.
When a Pod does not exist, its events cannot help; the object that creates Pods is the ReplicaSet (lesson 08). Its
events:

<!-- test: contains=serviceaccount "exporter" not found; output=tail:1 -->
```bash
kubectl describe replicaset -n sa-lab -l app=exporter | grep FailedCreate | tail -1
```

```text
  Warning  FailedCreate  0s (x11 over 5s)  replicaset-controller  Error creating: pods "exporter-86d8cc87d6-" is forbidden: error looking up service account sa-lab/exporter: serviceaccount "exporter" not found
```

Root cause: the API server refuses to create a Pod whose ServiceAccount does not exist.

## Fix It

Create the ServiceAccount; the ReplicaSet keeps retrying and succeeds by itself:

<!-- test: contains=1/1 -->
```bash
kubectl create serviceaccount exporter -n sa-lab
kubectl rollout status deployment/exporter -n sa-lab --timeout=180s > /dev/null
kubectl get deployment exporter -n sa-lab
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Naming a missing ServiceAccount | Deployment `0/1`, no Pods, `FailedCreate` on the ReplicaSet | create it in the same namespace |
| Expecting a new ServiceAccount to have permissions | `403 Forbidden` | bind a Role to it (lesson 24) |
| Giving the `default` ServiceAccount permissions | every Pod in the namespace gets them | one ServiceAccount per application |
| Mounting tokens everywhere | a stolen Pod = a stolen credential | `automountServiceAccountToken: false` |
| Copying a token into a ConfigMap or an image | a long-lived secret leaks | use the mounted, auto-rotated token |

## Best Practices

- One ServiceAccount per application that needs the API; none for applications that do not (`automount…: false`).
- Grant the smallest permissions (lesson 24), in the application's own namespace.
- Name ServiceAccounts after the application, so audit logs are readable.

## Challenge

**Task:** find out which ServiceAccount every Pod in `sa-lab` uses, and which of them have a token mounted.

**Requirements:** one `kubectl get` command.

**Hints:** `.spec.serviceAccountName` and `.spec.automountServiceAccountToken` in `-o custom-columns`.

**Expected Result:** `reporter` → reporter, `no-token` → default with `false`, `exporter-…` → exporter.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=reporter; contains=false -->
```bash
kubectl get pods -n sa-lab -o custom-columns=POD:.metadata.name,SERVICEACCOUNT:.spec.serviceAccountName,AUTOMOUNT:.spec.automountServiceAccountToken
```

</details>

`<none>` in the last column means the default (mounted). A Pod spec without `serviceAccountName` shows `default`:
Kubernetes fills it in.

## Key Takeaways

- ServiceAccount = a namespaced identity for workloads; users are for people.
- Pods get a short-lived token at `/var/run/secrets/kubernetes.io/serviceaccount/token`; the API is at
  `https://kubernetes.default.svc`.
- Identity is not permission: a new ServiceAccount gets `403` until a RoleBinding allows it (lesson 24).
- Real-world use: CI/CD runners, operators, monitoring agents, ingress controllers and any app calling the API each run
  with their own ServiceAccount and the smallest permissions.

## Cleanup

🧹 Delete the namespace `sa-lab` (its ServiceAccounts, Pods and the `exporter` Deployment):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace sa-lab
```

Next: [24 · RBAC](../24-rbac/README.md)
