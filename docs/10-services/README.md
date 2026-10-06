# 10 · Services, service discovery and DNS

> Level 5 · Services · ⏱ 60 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **Service** gives a group of Pods **one stable address and name**, and spreads the traffic sent to it over all of
them. The Pods behind it are chosen with a label selector (lesson 07). Kubernetes' **DNS** turns the Service's name
(`backend-service`) into that address, so applications call each other by name.

Analogy: a company's switchboard number. Employees (Pods) come and go and change desks (IP addresses); customers
always dial the same number, and the switchboard connects them to whoever is available.

## Why do we need it?

**Pod IPs change.** Every Pod gets a new IP when it is recreated (a crash, a rolling update, scaling), and there are
several Pods. A frontend cannot keep a list of backend Pod IPs up to date. It needs one address that always leads to
the healthy backend Pods: a Service.

## How does it work?

```text
frontend Pod: wget http://backend-service
   │ 1. DNS (CoreDNS): backend-service → 10.96.x.y  (the Service's ClusterIP, stable)
   │ 2. kube-proxy rules on the node: 10.96.x.y:80 → one of the ready Pods, port 8080
   ▼
backend Pods 10.244.a.b:8080, 10.244.c.d:8080   ← kept up to date in EndpointSlices, from the selector
```

- The Service's **selector** finds the Pods; only **ready** Pods (readiness probe, lesson 14) receive traffic.
- The list of current Pod addresses is stored in **EndpointSlices**, updated continuously.
- **Types:**

| Type | Reachable from | Use |
|---|---|---|
| `ClusterIP` (default) | inside the cluster only | service-to-service traffic (the backend, the database) |
| `NodePort` | every node's IP, on a port 30000–32767 | simple external access, tests, labs |
| `LoadBalancer` | an external load balancer the cloud creates | public services in the cloud (Minikube simulates it with `minikube tunnel`) |

- **DNS names:** `backend-service` (same namespace), `backend-service.services-lab` (from another namespace),
  `backend-service.services-lab.svc.cluster.local` (full name).

## Architecture

```text
                 Service "backend-service"   ClusterIP 10.96.x.y   port 80
                 selector: app=backend
                          │  targetPort 8080
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
       Pod backend    Pod backend    (a Pod that is not ready gets no traffic)
       10.244.a.b     10.244.c.d

 frontend ──"backend-service"──▶ CoreDNS ──▶ 10.96.x.y ──▶ kube-proxy ──▶ a backend Pod
```

## YAML

<!-- test: contains=kind: Service -->
```bash
cat manifests/services/10-backend.yaml
```

| Field | Meaning |
|---|---|
| (first object) `kind: Deployment` | the backend of lesson 09, 2 replicas, labels `app: backend` |
| `kind: Service`, `apiVersion: v1` | a Service, core API |
| `metadata.name: backend-service` | its name, which is also its DNS name |
| `spec.type: ClusterIP` | an internal address (the default type) |
| `spec.selector.app: backend` | send traffic to the ready Pods with `app=backend` |
| `ports[].name: http` | a name for the port (useful when there are several) |
| `ports[].port: 80` | the port the Service listens on (clients use `http://backend-service`, port 80) |
| `ports[].targetPort: 8080` | the port on the Pods where traffic is sent (the backend listens on 8080) |

The frontend is a small Pod that calls the backend by name every 3 seconds and logs the answer:

<!-- test: contains=backend-service -->
```bash
cat manifests/services/10-frontend.yaml
```

## Hands-On Lab

<!-- test: contains=created -->
```bash
kubectl create namespace services-lab
kubectl config set-context --current --namespace=services-lab
```

**1. The backend and its Service:**

<!-- test: contains=successfully rolled out -->
```bash
kubectl apply -f manifests/services/10-backend.yaml
kubectl rollout status deployment/backend --timeout=120s
```

<!-- test: contains=backend-service; output -->
```bash
kubectl get service backend-service
kubectl get endpointslices -l kubernetes.io/service-name=backend-service
```

```text
NAME              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
backend-service   ClusterIP   10.108.94.241   <none>        80/TCP    1s
NAME                    ADDRESSTYPE   PORTS   ENDPOINTS                       AGE
backend-service-8cjfj   IPv4          8080    10.244.120.103,10.244.120.105   2s
```

The Service has a stable `CLUSTER-IP`; its EndpointSlice lists the two Pods' IPs, on port 8080.

**2. Service discovery:** the frontend calls `http://backend-service` by name.

<!-- test: contains=pod/frontend created -->
```bash
kubectl apply -f manifests/services/10-frontend.yaml
kubectl wait --for=condition=Ready pod/frontend --timeout=120s > /dev/null
```

<!-- test: contains=Hello from the backend; retry=10 -->
```bash
sleep 10
kubectl logs frontend --tail=4
```

**3. Load spreading:** which backend Pods answered?

<!-- test: contains=backend-; output -->
```bash
kubectl logs frontend --tail=30 | grep -o '"pod":"[^"]*"' | sort | uniq -c
```

```text
      2 "pod":"backend-6668bd5576-dvfgx"
      2 "pod":"backend-6668bd5576-pknng"
```

Usually both Pods appear: the Service spreads requests over its endpoints.

**4. DNS:** what the name resolves to, and how:

<!-- test: contains=backend-service.services-lab.svc.cluster.local; output -->
```bash
kubectl run dns --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c 'nslookup backend-service.services-lab.svc.cluster.local; grep -E "search|nameserver" /etc/resolv.conf' 2>&1 | grep -vE '^$|deleted'
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53
Name:	backend-service.services-lab.svc.cluster.local
Address: 10.108.94.241
search services-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
warning: couldn't attach to pod/dns, falling back to streaming logs: unable to upgrade connection: container dns not found in pod dns_services-lab
Server:		10.96.0.10
Address:	10.96.0.10:53
Name:	backend-service.services-lab.svc.cluster.local
Address: 10.108.94.241
search services-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
```

The address is the Service's ClusterIP. Every Pod's `/etc/resolv.conf` points at the cluster DNS (`10.96.0.10`) and
lists **search domains**: that is why the short name `backend-service` works inside `services-lab`.

**5. NodePort:** the same Pods on a port of the node.

<!-- test: contains=30080 -->
```bash
kubectl apply -f manifests/services/10-backend-nodeport.yaml
kubectl get service backend-nodeport
```

From inside the cluster, through the node's IP (`minikube ip`):

<!-- test: contains=Hello from the backend; retry=5 -->
```bash
node_ip=$(minikube ip)
kubectl run np --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 "http://$node_ip:30080/"
```

From your own computer, Minikube opens a tunnel to a NodePort (with the Docker driver on Windows and macOS the node is
not directly reachable). It keeps running until you press Ctrl+C:

<!-- test: skip -->
```bash
minikube service backend-nodeport -n services-lab --url
```

**LoadBalancer** (concept): in a cloud, `type: LoadBalancer` makes the cloud create an external load balancer with a
public IP. On Minikube, `minikube tunnel` (in a second terminal, needs administrator rights) plays that role and fills in
`EXTERNAL-IP`:

<!-- test: skip -->
```bash
kubectl expose deployment backend --name=backend-lb --type=LoadBalancer --port=80 --target-port=8080
minikube tunnel
```

## Expected Result

`backend-service` has a ClusterIP and two endpoints; the frontend logs answers from the backend Pods, by name; DNS
resolves the full name to the ClusterIP; the NodePort answers on the node's IP, port 30080.

## Inspect

Pod IPs change, the Service does not. Delete the backend Pods and compare:

<!-- test: contains=same ClusterIP -->
```bash
before_svc=$(kubectl get service backend-service -o jsonpath='{.spec.clusterIP}')
before_eps=$(kubectl get endpointslices -l kubernetes.io/service-name=backend-service -o jsonpath='{.items[0].endpoints[*].addresses[0]}')
kubectl delete pods -l app=backend --wait=true > /dev/null
kubectl rollout status deployment/backend --timeout=120s > /dev/null
kubectl wait --for=condition=Ready pods -l app=backend --timeout=120s > /dev/null
after_svc=$(kubectl get service backend-service -o jsonpath='{.spec.clusterIP}')
after_eps=$(kubectl get endpointslices -l kubernetes.io/service-name=backend-service -o jsonpath='{.items[0].endpoints[*].addresses[0]}')
echo "Pods before: $before_eps"
echo "Pods after:  $after_eps"
[ "$before_svc" = "$after_svc" ] && echo "same ClusterIP: $after_svc"
```

## Experiment

Scale the backend and watch the endpoints follow, with no change to the Service:

<!-- test: contains=4; retry=10 -->
```bash
kubectl scale deployment backend --replicas=4
kubectl rollout status deployment/backend --timeout=120s > /dev/null
kubectl get endpointslices -l kubernetes.io/service-name=backend-service -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}' | wc -l | tr -d ' '
```

## Break It

A colleague "tidies up" the Service and mistypes its selector:

<!-- test: contains=not reachable; retry=10; output=tail:2 -->
```bash
kubectl patch service backend-service -p '{"spec":{"selector":{"app":"backnd"}}}'
sleep 8
kubectl logs frontend --tail=2
```

```text
service/backend-service patched
backend-service not reachable
```

## Troubleshoot It

*What should happen?* The frontend gets answers. *What happened?* `backend-service not reachable`. *Which object
controls it?* The Service. Name and DNS still work (it exists), so check where it sends traffic:

<!-- test: contains=<unset>; output -->
```bash
kubectl get endpointslices -l kubernetes.io/service-name=backend-service
```

```text
NAME                    ADDRESSTYPE   PORTS     ENDPOINTS   AGE
backend-service-8cjfj   IPv4          <unset>   <unset>     31s
```

No endpoints: the selector matches no ready Pod. Compare the selector with the Pods' labels:

<!-- test: contains=backnd; contains=app=backend -->
```bash
kubectl get service backend-service -o jsonpath='selector: {.spec.selector}{"\n"}'
kubectl get pods -l app=backend --show-labels | head -2
```

Root cause: the selector says `app=backnd`, the Pods are labelled `app=backend` (lesson 07: an empty selection is
silent).

## Fix It

<!-- test: contains=Hello from the backend; retry=15 -->
```bash
kubectl patch service backend-service -p '{"spec":{"selector":{"app":"backend"}}}'
sleep 6
kubectl logs frontend --tail=4
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Selector does not match the Pod labels | no endpoints, timeouts | compare `spec.selector` with `--show-labels` |
| `targetPort` ≠ the port the app listens on | endpoints exist, `connection refused` | `targetPort` = `containerPort` |
| Calling a Pod IP | breaks at the next restart | always call the Service name |
| Short name from another namespace | `bad address` | `name.namespace` or the full name |
| Pods not ready | no endpoints although labels match | fix the readiness probe (lesson 14) |
| Expecting a NodePort on `localhost` with the Docker driver | connection refused | `minikube service NAME --url` |

## Best Practices

- One Service per component; clients use its DNS name, never IPs.
- Name ports (`http`, `metrics`); use ClusterIP inside the cluster and an Ingress (lesson 20) for HTTP from outside,
  rather than one NodePort per application.
- Readiness probes on every backend, so a Service only sends traffic to Pods that can answer.

## Challenge

**Task:** from a new namespace `clients`, call the backend with the shortest name that works, and prove that the
short name `backend-service` does **not** work there.

**Requirements:** a temporary busybox Pod in `clients`; two `wget` calls.

**Hints:** search domains contain the Pod's **own** namespace first.

**Expected Result:** `backend-service` fails (`bad address`), `backend-service.services-lab` answers.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=bad address; contains=Hello from the backend -->
```bash
kubectl create namespace clients
kubectl run c -n clients --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c 'wget -qO- -T 5 http://backend-service/; echo; wget -qO- -T 5 http://backend-service.services-lab/' 2>&1 | grep -v deleted
```

</details>

From `clients`, the search domains are `clients.svc.cluster.local`, `svc.cluster.local`, `cluster.local`: the short
name becomes `backend-service.clients.svc.cluster.local`, which does not exist. `backend-service.services-lab` +
`svc.cluster.local` is the real name.

## Key Takeaways

- A Service gives Pods a stable IP and DNS name and spreads traffic over the ready Pods it selects.
- `port` is what clients call, `targetPort` is where the Pods listen; EndpointSlices show where traffic goes.
- ClusterIP for inside, NodePort for simple external access, LoadBalancer in the cloud.
- DNS: `name` in the same namespace, `name.namespace` across namespaces.
- Real-world use: every microservice calls the others through Services; most "it cannot connect" problems are a
  selector, a port or a readiness problem.

## Cleanup

🧹 Delete the namespaces `services-lab` (backend, Services, frontend) and `clients`, and switch back to `default`:

<!-- test: contains=deleted -->
```bash
kubectl config set-context --current --namespace=default
kubectl delete namespace services-lab clients --ignore-not-found
```

Next: [11 · ConfigMaps](../11-configmaps/README.md)
