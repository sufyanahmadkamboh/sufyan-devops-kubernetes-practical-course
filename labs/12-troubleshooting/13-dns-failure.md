# Problem 13 · DNS resolution failure

> Lab 12 · Troubleshooting · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

## Problem

The reporting team's Pod, in its own namespace, must call the backend. "It works from the backend's namespace but not
from ours." Set up the backend in `trouble-13` and a client namespace `trouble-13-client`:

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace trouble-13
kubectl create namespace trouble-13-client
kubectl apply -f labs/12-troubleshooting/manifests/13-dns.yaml
kubectl rollout status deployment/backend -n trouble-13 --timeout=120s
```

## Symptoms

<!-- test: contains=bad address; output -->
```bash
kubectl run client -n trouble-13-client --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 http://backend 2>&1' || true
```

```text
wget: bad address 'backend'
pod trouble-13-client/client terminated (Error)
```

`bad address`: the name `backend` did not resolve to any address.

## First command to run

Is the cluster DNS working at all? Resolve a name that must exist, the API server's Service:

<!-- test: contains=kubernetes.default.svc.cluster.local; output -->
```bash
kubectl run dns -n trouble-13-client --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  nslookup kubernetes.default.svc.cluster.local 2>&1 | grep -A1 '^Name'
```

```text
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
--
Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

DNS works. So the problem is the **name**.

## Investigation

A short Service name is completed with the **caller's** namespace (the `search` line of the Pod's `/etc/resolv.conf`):

<!-- test: contains=trouble-13-client.svc.cluster.local; output -->
```bash
kubectl run resolv -n trouble-13-client --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  grep search /etc/resolv.conf
```

```text
search trouble-13-client.svc.cluster.local svc.cluster.local cluster.local
warning: couldn't attach to pod/resolv, falling back to streaming logs: unable to upgrade connection: container resolv not found in pod resolv_trouble-13-client
search trouble-13-client.svc.cluster.local svc.cluster.local cluster.local
```

From `trouble-13-client`, `backend` means `backend.trouble-13-client.svc.cluster.local`, which does not exist. The
backend Service lives in `trouble-13`:

<!-- test: contains=trouble-13 -->
```bash
kubectl get services -A --field-selector metadata.name=backend
```

## Root cause

The client uses the short name `backend` from another namespace. Short names only work inside the Service's own
namespace (lesson 10).

## Fix

Use the Service's name with its namespace (`backend.trouble-13`), or the full name
(`backend.trouble-13.svc.cluster.local`):

<!-- test: contains=Hello from the backend -->
```bash
kubectl run client2 -n trouble-13-client --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 http://backend.trouble-13
```

## Verification

<!-- test: contains=Hello from the backend -->
```bash
kubectl run client3 -n trouble-13-client --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 http://backend.trouble-13.svc.cluster.local
```

## Lesson learned

- `bad address` / `Name or service not known` = DNS; first prove DNS works with `kubernetes.default`, then check the
  name.
- `SERVICE` works in the same namespace; `SERVICE.NAMESPACE` across namespaces; the full name everywhere.
- In configuration (ConfigMaps), prefer `SERVICE.NAMESPACE` for anything another team owns.

## Cleanup

🧹 Delete the namespaces `trouble-13` and `trouble-13-client`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace trouble-13 trouble-13-client
```

Next: [Problem 14 · NetworkPolicy blocks traffic](14-networkpolicy-blocks-traffic.md)
