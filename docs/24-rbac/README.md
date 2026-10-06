# 24 · RBAC

> Level 13 · Security & RBAC · ⏱ 45 minutes · run every command from the course folder · cluster: minikube

## What is it?

**RBAC** (role-based access control) decides **who may do what** in a cluster. A **Role** lists permissions ("get,
list and watch Pods"); a **RoleBinding** gives a Role to someone (a user, a group, a ServiceAccount). Their
cluster-wide versions, **ClusterRole** and **ClusterRoleBinding**, cover objects without a namespace (nodes) or all
namespaces at once.

The analogy: a Role is a job description ("may read the patient files"), a RoleBinding is the signed contract that
gives that job to a person, in one department.

## Why do we need it?

Without authorization, anyone who can reach the API can delete production. Teams need rules like: developers may
look at Pods and logs in their namespace, but not delete them; the CI system may deploy to `staging` only; a
monitoring agent may read nodes everywhere. RBAC expresses exactly that, and `kubectl auth can-i` checks it.

## How does it work?

Every API request is checked in two steps:

```text
1. authentication  "who are you?"   certificate, token  → user "developer", or system:serviceaccount:ns:name
2. authorization   "may you?"       RBAC: is there a binding that gives this subject a role that allows
                                     VERB on RESOURCE (in NAMESPACE)?   yes → allowed, no → 403 Forbidden
```

- Permissions are **additive** and **deny by default**: no matching rule = forbidden. There are no "deny" rules.
- A rule = `apiGroups` (`""` for the core group: Pods, Services…; `apps` for Deployments…) + `resources` + `verbs`
  (`get`, `list`, `watch`, `create`, `update`, `patch`, `delete`).
- Role + RoleBinding = permissions in **one** namespace. ClusterRole + ClusterRoleBinding = everywhere, and for
  cluster-scoped objects (nodes, namespaces, PersistentVolumes). A RoleBinding may also point at a ClusterRole, to reuse
  a common role in one namespace (Kubernetes ships `view`, `edit`, `admin`).
- Kubernetes has no user database: users come from certificates or an identity provider. In this lab you **impersonate**
  a user with `--as developer` (allowed for the cluster administrator you are on Minikube).

## Architecture

```text
 User "developer" ─┐                   RoleBinding developer-views-pods (namespace rbac-lab)
 SA "reporter" ────┴─── subjects ───▶          │ roleRef
                                               ▼
                                     Role pod-viewer: pods, pods/log → get, list, watch

 User "developer" ─── ClusterRoleBinding ───▶ ClusterRole course-node-viewer: nodes → get, list

 developer: get pods in rbac-lab ✔   delete pods ✕   get nodes ✔   get pods in kube-system ✕
```

## YAML

<!-- test: contains=kind: Role; contains=kind: RoleBinding -->
```bash
cat manifests/security/rbac-pod-viewer.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: rbac.authorization.k8s.io/v1` | the RBAC API group |
| `kind: Role` | a set of permissions in one namespace |
| `rules[].apiGroups: [""]` | the core API group (Pods); Deployments would be `apps` |
| `resources: ["pods", "pods/log"]` | Pods and their logs (a **subresource**) |
| `verbs: [get, list, watch]` | read only |
| `kind: RoleBinding` | gives the Role to the `subjects`, in the binding's namespace |
| `subjects[]` | a `User` (`developer`) and a `ServiceAccount` (`reporter`, lesson 23) |
| `roleRef` | the Role being granted; it cannot be changed later (delete and re-create the binding) |

The cluster-wide pair, for nodes:

<!-- test: contains=kind: ClusterRole; contains=course: k8s-lab -->
```bash
cat manifests/security/rbac-node-viewer.yaml
```

## Hands-On Lab

**1. A namespace with something to look at:**

<!-- test: contains=pod/web created -->
```bash
kubectl create namespace rbac-lab
kubectl run web --image=nginx:1.30-alpine -n rbac-lab
kubectl wait --for=condition=Ready pod/web -n rbac-lab --timeout=120s
```

**2. Before any binding, the developer may do nothing:**

<!-- test: contains=no; output -->
```bash
kubectl auth can-i list pods -n rbac-lab --as developer || true
```

```text
no
```

**3. Give the developer the read-only Role in `rbac-lab`:**

<!-- test: contains=rolebinding.rbac.authorization.k8s.io/developer-views-pods created -->
```bash
kubectl create serviceaccount reporter -n rbac-lab
kubectl apply -f manifests/security/rbac-pod-viewer.yaml -n rbac-lab
```

**4. Check the permissions:** can view Pods, cannot delete them.

<!-- test: contains=list pods: yes; contains=delete pods: no; output -->
```bash
echo "list pods: $(kubectl auth can-i list pods -n rbac-lab --as developer)"
echo "read logs: $(kubectl auth can-i get pods --subresource=log -n rbac-lab --as developer)"
echo "delete pods: $(kubectl auth can-i delete pods -n rbac-lab --as developer)"
echo "list pods in kube-system: $(kubectl auth can-i list pods -n kube-system --as developer)"
```

```text
list pods: yes
read logs: yes
delete pods: no
list pods in kube-system: no
```

**5. Act as the developer:**

<!-- test: contains=web; contains=Forbidden; output -->
```bash
kubectl get pods -n rbac-lab --as developer
kubectl delete pod web -n rbac-lab --as developer 2>&1 || true
```

```text
NAME   READY   STATUS    RESTARTS   AGE
web    1/1     Running   0          2s
Error from server (Forbidden): pods "web" is forbidden: User "developer" cannot delete resource "pods" in API group "" in the namespace "rbac-lab"
```

The error says exactly which check failed: user, verb, resource, API group, namespace.

**6. Nodes have no namespace: a ClusterRole and ClusterRoleBinding:**

<!-- test: contains=nodes before: no; contains=nodes after: yes -->
```bash
echo "nodes before: $(kubectl auth can-i list nodes --as developer)"
kubectl apply -f manifests/security/rbac-node-viewer.yaml > /dev/null
echo "nodes after: $(kubectl auth can-i list nodes --as developer)"
kubectl get nodes --as developer
```

## Expected Result

The developer can list and read Pods (and their logs) in `rbac-lab`, list nodes, and nothing else: no deletes, no
other namespaces.

## Inspect

Everything the developer may do in the namespace, and who holds the bindings:

<!-- test: contains=pods; contains=developer -->
```bash
kubectl auth can-i --list -n rbac-lab --as developer | grep -E 'pods|nodes'
kubectl get rolebindings -n rbac-lab -o wide
```

## Experiment

The same binding names the ServiceAccount `reporter` from lesson 23. A Pod running as `reporter` can now list the
Pods of its namespace through the API (in lesson 23 it got `403`):

<!-- test: contains=PodList; retry=5 -->
```bash
kubectl run api-call -n rbac-lab --rm -i --quiet --restart=Never --image=alpine:3.23 \
  --overrides='{"spec":{"serviceAccountName":"reporter"}}' -- sh -c 'sleep 2
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  wget -qO- --no-check-certificate --header "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/api/v1/namespaces/rbac-lab/pods 2>&1 | head -c 60; echo'
```

## Break It

A tester should get the same read-only access; a colleague writes the binding:

<!-- test: contains=no; output -->
```bash
kubectl apply -f manifests/security/rbac-binding-broken.yaml -n rbac-lab > /dev/null
kubectl auth can-i list pods -n rbac-lab --as tester || true
```

```text
no - rbac: RBAC: role.rbac.authorization.k8s.io "pod-viewers" not found
```

## Troubleshoot It

*What should happen?* `yes`. *What happened?* `no`. Kubernetes accepted the binding without complaint. *Which
objects decide?* A RoleBinding and the Role it refers to. Read the binding:

<!-- test: contains=pod-viewers; output -->
```bash
kubectl describe rolebinding tester-views-pods -n rbac-lab
kubectl get roles -n rbac-lab
```

```text
Name:         tester-views-pods
Labels:       <none>
Annotations:  <none>
Role:
  Kind:  Role
  Name:  pod-viewers
Subjects:
  Kind  Name    Namespace
  ----  ----    ---------
  User  tester  
NAME         CREATED AT
pod-viewer   2026-10-06T16:33:52Z
```

The binding grants a Role called `pod-viewers`; the Role is `pod-viewer`. A binding to a Role that does not exist is
allowed (the Role could be created later), and grants nothing. Root cause: a typo in `roleRef.name`.

## Fix It

`roleRef` cannot be changed: delete the binding and create it again with the right name:

<!-- test: contains=yes -->
```bash
kubectl delete rolebinding tester-views-pods -n rbac-lab
kubectl create rolebinding tester-views-pods --role=pod-viewer --user=tester -n rbac-lab
kubectl auth can-i list pods -n rbac-lab --as tester
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| A typo in `roleRef` or subject name | `no` / `403`, no error when applying | `kubectl describe rolebinding`; compare with `kubectl get roles` |
| Binding in the wrong namespace | allowed in one namespace, forbidden in another | a RoleBinding works only in its own namespace |
| Wrong `apiGroups` | `403` for Deployments | Deployments are in `apps`, Ingresses in `networking.k8s.io` (`kubectl api-resources` shows the group) |
| Using a Role for nodes | `cannot list resource "nodes" ... at the cluster scope` | ClusterRole + ClusterRoleBinding |
| Giving `cluster-admin` "to make it work" | everything works, including deleting everything | grant only the verbs and resources needed |
| Granting `*` verbs or `*` resources | far more access than intended | list them explicitly |

## Best Practices

- Least privilege: read-only by default, write access only where needed, per namespace.
- Reuse the built-in ClusterRoles `view`, `edit`, `admin` through RoleBindings when they fit.
- Bind groups (from your identity provider), not individual users, in real clusters.
- Check with `kubectl auth can-i … --as …` after every change; keep RBAC manifests in version control.

## Challenge

**Task:** give a user `auditor` **read-only access to everything** in `rbac-lab` (Pods, Services, ConfigMaps,
Deployments…, but not Secrets) without writing a Role yourself.

**Requirements:** reuse a built-in ClusterRole; one command; prove it with `kubectl auth can-i`.

**Hints:** `kubectl get clusterroles view -o yaml`; `kubectl create rolebinding --clusterrole=...`.

**Expected Result:** `list deployments: yes`, `delete pods: no`, `get secrets: no`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=list deployments: yes; contains=delete pods: no; contains=get secrets: no -->
```bash
kubectl create rolebinding auditor-view --clusterrole=view --user=auditor -n rbac-lab
echo "list deployments: $(kubectl auth can-i list deployments.apps -n rbac-lab --as auditor)"
echo "delete pods: $(kubectl auth can-i delete pods -n rbac-lab --as auditor)"
echo "get secrets: $(kubectl auth can-i get secrets -n rbac-lab --as auditor)"
```

</details>

A RoleBinding can grant a **ClusterRole** inside one namespace: the built-in `view` role is defined once for the
whole cluster and reused per namespace. `view` deliberately excludes Secrets.

## Key Takeaways

- Authentication says who you are; RBAC authorization says what you may do; the default is deny.
- Role + RoleBinding = one namespace; ClusterRole + ClusterRoleBinding = cluster-wide and cluster-scoped objects.
- `kubectl auth can-i VERB RESOURCE -n NS --as SUBJECT` answers every RBAC question.
- Real-world use: giving teams access to their namespaces, limiting CI/CD to the environments it deploys to, granting
  agents read-only access, passing security audits.

## Cleanup

🧹 Delete the namespace `rbac-lab` (the Pod, the ServiceAccount, the Role and all RoleBindings) and the cluster-wide
node-viewer ClusterRole and ClusterRoleBinding:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace rbac-lab
kubectl delete -f manifests/security/rbac-node-viewer.yaml
```

Next: [25 · Scaling](../25-scaling/README.md)
