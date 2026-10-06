# 21 · Kubernetes networking

> Level 10 · Ingress & Networking · ⏱ 35 minutes · run every command from the course folder · cluster: minikube

## What is it?

The Kubernetes **networking model** is a short list of promises every cluster keeps, whatever network plugin it uses:

```text
Pod → Pod          every Pod has its own IP; every Pod can reach every other Pod directly, without NAT
Pod → Service      a Service has a stable virtual IP and a DNS name; traffic is spread over its ready Pods
Pod → Internet     Pods can reach the outside world (through the node)
External → Service a NodePort, LoadBalancer or Ingress lets outside traffic in
```

## Why do we need it?

Every "it cannot connect" problem is one of these four paths. Knowing which path a request takes, and which part of
the cluster is responsible for it, turns guessing into a short investigation: is it the Pod, the Service, DNS, a
NetworkPolicy (lesson 22), or the way in from outside?

## How does it work?

| Piece | What it does | Where |
|---|---|---|
| **CNI plugin** (Calico here) | gives every Pod an IP from the Pod network (`10.244.x.x`) and routes between them | a DaemonSet (`calico-node`) |
| **kube-proxy** | turns every Service IP into rules that forward to the Pods behind it | a DaemonSet on every node |
| **CoreDNS** | answers names: `web` → the Service IP; `web.net-lab.svc.cluster.local` | Pods in `kube-system` |
| **NodePort / LoadBalancer / Ingress** | the doors from outside | Services, ingress controller (lesson 20) |

Each Pod's `/etc/resolv.conf` points at CoreDNS and lists **search domains** (`<namespace>.svc.cluster.local`, …), so
a short name like `web` is completed with the Pod's **own** namespace.

## Architecture

```text
                 outside ──▶ node:30080 (NodePort) ──┐
                                                     ▼
 client Pod 10.244.0.20 ──── http://web ─▶ CoreDNS: web = 10.103.0.10 (Service IP)
        │                                            │ kube-proxy rules
        │  Pod → Pod (direct, no NAT)                ▼
        └──────────────▶ web Pod 10.244.0.11    web Pod 10.244.0.12
        │
        └─▶ Internet (through the node's address)
```

## YAML

<!-- test: contains=type: NodePort -->
```bash
cat manifests/networking/networking-web.yaml
```

| Field | Meaning |
|---|---|
| Deployment `web`, `replicas: 2` | two Pods, each with its own IP |
| Service `web`, `type: ClusterIP` | a stable virtual IP, reachable only inside the cluster, DNS name `web` |
| Service `web-nodeport`, `type: NodePort` | the same Pods, also reachable on a port of every node |
| `nodePort: 30080` | the port on the node (range 30000–32767; omit it to get a random one) |
| `port` / `targetPort` | the Service's port / the container's port |

## Hands-On Lab

**1. Deploy:**

<!-- test: contains=deployment.apps/web created -->
```bash
kubectl create namespace net-lab
kubectl apply -f manifests/networking/networking-web.yaml -n net-lab
kubectl rollout status deployment/web -n net-lab --timeout=120s
```

**2. Pod → Pod.** Every Pod has its own IP; a client Pod reaches one of them directly by IP:

<!-- test: contains=Welcome to nginx -->
```bash
kubectl get pods -n net-lab -l app=web -o custom-columns=NAME:.metadata.name,IP:.status.podIP
ip=$(kubectl get pods -n net-lab -l app=web -o jsonpath='{.items[0].status.podIP}')
kubectl run client -n net-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 "http://$ip" | grep -o '<title>.*</title>'
```

**3. Pod → Service**, by name. The Service has its own stable IP; DNS maps the name to it:

<!-- test: contains=Welcome to nginx; contains=web.net-lab.svc.cluster.local -->
```bash
kubectl get service web -n net-lab
kubectl run client -n net-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  wget -qO- -T 5 http://web | grep -o "<title>.*</title>"
  nslookup web.net-lab.svc.cluster.local | grep -A1 "^Name"'
```

**4. DNS settings inside a Pod:**

<!-- test: contains=search net-lab.svc.cluster.local; output -->
```bash
kubectl run client -n net-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- cat /etc/resolv.conf
```

```text
search net-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_net-lab
search net-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

`10.96.0.10` is CoreDNS's Service; the first search domain is the Pod's own namespace.

**5. Pod → Internet:**

<!-- test: retry=5; contains=Example Domain -->
```bash
kubectl run client -n net-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 10 http://example.com | grep -o '<title>.*</title>'
```

**6. External → Service** through the NodePort, from the Minikube node itself (on Linux you can also open
`http://$(minikube ip):30080` from your computer; on Windows and macOS use `minikube service web-nodeport -n net-lab
--url`, which opens a tunnel):

<!-- test: retry=5; contains=Welcome to nginx -->
```bash
minikube ssh -- curl -s http://localhost:30080 | grep -o '<title>.*</title>'
```

## Expected Result

The same nginx page reached four ways: a Pod IP, the Service name, the NodePort; and the client Pod reached the
Internet. Pod IPs are `10.244.x.x`, Service IPs `10.96–10.111.x.x`.

## Inspect

Which Pod IPs stand behind the Service (kube-proxy forwards to these):

<!-- test: contains=web -->
```bash
kubectl get endpointslices -n net-lab -l kubernetes.io/service-name=web
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
```

## Experiment

Delete one web Pod. Its replacement has a **new** IP; the Service IP and name do not change, and clients never notice:

<!-- test: contains=Welcome to nginx -->
```bash
kubectl get pods -n net-lab -l app=web -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}'
kubectl delete pod -n net-lab -l app=web > /dev/null
kubectl rollout status deployment/web -n net-lab --timeout=120s > /dev/null
kubectl wait --for=condition=Ready pod -n net-lab -l app=web --timeout=120s > /dev/null
kubectl get pods -n net-lab -l app=web -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}'
kubectl run client -n net-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://web | grep -o '<title>.*</title>'
```

Never hard-code Pod IPs: use Service names.

## Break It

A client in **another** namespace uses the same short name:

<!-- test: fail; contains=bad address; output -->
```bash
kubectl create namespace other --dry-run=client -o yaml | kubectl apply -f - > /dev/null
kubectl run client -n other --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://web 2>&1
```

```text
wget: bad address 'web'
pod other/client terminated (Error)
```

## Troubleshoot It

*What should happen?* The web page. *What happened?* `bad address 'web'`: the **name** did not resolve, so the
request never left the Pod. It is a DNS question. Which names does this Pod try?

<!-- test: contains=search other.svc.cluster.local -->
```bash
kubectl run client -n other --rm -i --quiet --restart=Never --image=busybox:1.37 -- grep search /etc/resolv.conf
```

The search list starts with `other.svc.cluster.local`: the short name `web` becomes `web.other.svc.cluster.local`,
and there is no Service `web` in `other`. Root cause: the Service lives in `net-lab`; short names only work inside the
same namespace.

## Fix It

Use the name with the namespace (`web.net-lab`), or the full name (`web.net-lab.svc.cluster.local`):

<!-- test: contains=Welcome to nginx -->
```bash
kubectl run client -n other --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://web.net-lab | grep -o '<title>.*</title>'
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Hard-coding a Pod IP | works until the Pod is replaced | always use a Service name |
| Short name across namespaces | `bad address` / `Name or service not known` | `service.namespace` |
| Expecting to `ping` a Service IP | no reply | Service IPs are virtual: they forward TCP/UDP ports, not ICMP; test with the port |
| Using `targetPort` from outside | connection refused | from outside use the `nodePort` (or Ingress), inside the Service `port` |
| Using `localhost` to reach another Pod | connection refused | `localhost` is the Pod itself (shared only between containers of one Pod, lesson 06) |

## Best Practices

- Clients address Services by name; configure the name (ConfigMap, lesson 11), not an IP.
- Expose web applications through an Ingress (lesson 20) rather than a NodePort per application.
- When a connection fails, separate the steps: does the name resolve? Is the Service IP reachable? Does a Pod IP
  answer directly? Is a NetworkPolicy in the way (lesson 22)?

## Challenge

**Task:** from a client Pod in `other`, find the **IP address** CoreDNS returns for the Service `web` in `net-lab`,
and check that it is the same as the Service's `CLUSTER-IP`.

**Requirements:** use `nslookup` with the full name; compare with `kubectl get service`.

**Hints:** the full name is `web.net-lab.svc.cluster.local`.

**Expected Result:** the same IP twice.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=same IP -->
```bash
svc=$(kubectl get service web -n net-lab -o jsonpath='{.spec.clusterIP}')
dns=$(kubectl run client -n other --rm -i --quiet --restart=Never --image=busybox:1.37 -- nslookup web.net-lab.svc.cluster.local | grep -A1 'Name:' | grep -o 'Address: .*' | head -1)
echo "Service IP: $svc / DNS: $dns"
[ "$dns" = "Address: $svc" ] && echo "same IP"
```

</details>

DNS returns the Service's virtual IP, not a Pod IP: the spreading over Pods happens afterwards, in kube-proxy's rules.
(A **headless** Service, lesson 19, is the exception: there DNS returns the Pod IPs.)

## Key Takeaways

- Every Pod has an IP and reaches every other Pod directly; Pod IPs change.
- Services give a stable IP and DNS name; kube-proxy forwards to the ready Pods.
- Short names resolve in the Pod's own namespace; use `name.namespace` across namespaces.
- NodePort / LoadBalancer / Ingress are the ways in from outside.
- Real-world use: "service A cannot reach service B" is among the most common incidents; walking the four paths finds
  the broken step quickly.

## Cleanup

🧹 Delete the namespaces `net-lab` (the web Deployment and both Services) and `other`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace net-lab other
```

Next: [22 · NetworkPolicies](../22-networkpolicies/README.md)
