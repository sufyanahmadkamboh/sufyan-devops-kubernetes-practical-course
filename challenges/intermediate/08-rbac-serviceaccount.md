# Challenge 08 · A read-only identity for a dashboard

> Lessons 23, 24 · intermediate

## Task

A dashboard in the namespace `ch08` must read Pods, Services and Deployments of its namespace, and nothing else. Create
its ServiceAccount `dashboard` and the permissions, and prove what it can and cannot do.

## Requirements

- A ServiceAccount, a Role and a RoleBinding (write the Role yourself).
- `list pods`, `list services`, `list deployments`: yes. `delete pods`, `list secrets`, `list pods` in `default`: no.

## Hints

- Deployments are in the `apps` API group, Pods and Services in `""`.
- `kubectl auth can-i VERB RESOURCE -n NS --as=system:serviceaccount:NS:NAME`.

## Expected Result

Three `yes`, three `no`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=list deployments: yes; contains=delete pods: no; contains=list secrets: no; contains=pods in default: no -->
```bash
kubectl create namespace ch08
kubectl create serviceaccount dashboard -n ch08
kubectl create role dashboard-read -n ch08 --verb=get,list,watch --resource=pods,services,deployments.apps
kubectl create rolebinding dashboard-read -n ch08 --role=dashboard-read --serviceaccount=ch08:dashboard
sa=system:serviceaccount:ch08:dashboard
echo "list pods: $(kubectl auth can-i list pods -n ch08 --as=$sa)"
echo "list services: $(kubectl auth can-i list services -n ch08 --as=$sa)"
echo "list deployments: $(kubectl auth can-i list deployments.apps -n ch08 --as=$sa)"
echo "delete pods: $(kubectl auth can-i delete pods -n ch08 --as=$sa)"
echo "list secrets: $(kubectl auth can-i list secrets -n ch08 --as=$sa)"
echo "pods in default: $(kubectl auth can-i list pods -n default --as=$sa)"
```

</details>

## Explanation

`kubectl create role --resource=deployments.apps` writes the right API group for you. The RoleBinding gives the Role
to the ServiceAccount (`--serviceaccount=NAMESPACE:NAME`) in `ch08` only, so the same identity has no rights in
`default`, and Secrets were never listed.

## Cleanup

🧹 Delete the namespace `ch08`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace ch08
```
