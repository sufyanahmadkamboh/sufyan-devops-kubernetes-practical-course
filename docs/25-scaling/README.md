# 25 · Scaling

> Level 9 · Scaling & Scheduling · ⏱ 25 minutes · run every command from the course folder · cluster: minikube

## What is it?

**Scaling** means changing how many copies (**replicas**) of an application run. With Kubernetes you do not start or
stop containers yourself: you change one number on the Deployment, `replicas`, and the Deployment's ReplicaSet
creates or deletes Pods until reality matches it. The Service in front of the Pods notices the change on its own and
spreads requests over however many Pods are ready.

Think of a supermarket: when the queues get long, the manager opens more tills; the customers do not need to know
which till is open, they just join "the checkout".

## Why do we need it?

One Pod has limits: one container's CPU and memory, and when it restarts, nobody is served. More replicas mean more
capacity (more requests per second) and availability (one Pod can die while the others keep serving). Fewer replicas
save resources when traffic is low. Scaling by hand is the first step; lesson 26 lets Kubernetes do it automatically.

## How does it work?

```text
kubectl scale deployment backend --replicas=3
        │
        ▼
Deployment: spec.replicas = 3 ──▶ ReplicaSet: "3 wanted, 1 running" ──▶ 2 new Pods
                                                                           │ ready (readiness probe passes)
                                                                           ▼
Service "backend" ─▶ EndpointSlice: the IPs of the 3 ready Pods ─▶ kube-proxy spreads connections over them
```

- `kubectl scale` only changes `spec.replicas`; the rest is the reconciliation you saw in lessons 08–09.
- A new Pod receives traffic only once its readiness probe passes (lesson 14): scaling never sends requests to a Pod
  that is still starting.
- The Service does not count Pods: its **EndpointSlice** lists the addresses of the ready Pods matching its selector,
  and kube-proxy picks one of them for every new connection.

## Architecture

```text
 1 Pod                     3 Pods                         5 Pods
 ┌────────┐                ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
 │backend │                │backend │ │backend │ │backend │ │backend │ │backend │ │backend │ │backend │ │backend │ │backend │
 └───▲────┘                └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘ └───▲────┘
     │                         └──────────┼──────────┘          └──────────┴─────┬─────┴──────────┴──────────┘
 Service backend           Service backend                      Service backend
```

## YAML

The Deployment and Service of this lesson:

<!-- test: contains=kind: Deployment; contains=kind: Service -->
```bash
cat manifests/scaling/scaling-backend.yaml
```

| Field | Meaning |
|---|---|
| `spec.replicas: 1` | the desired number of Pods; `kubectl scale` changes this value |
| `resources.requests` | what each Pod reserves on the node (lesson 15): more replicas reserve more |
| `readinessProbe` | a Pod receives traffic only when `/readyz` answers 200 (lesson 14) |
| Service `selector: app: backend` | the Service sends traffic to every ready Pod with this label, however many there are |

The declarative way to scale is to change `replicas:` in the file and `kubectl apply` it again; `kubectl scale` is
the quick, imperative way (the next `apply` of the file sets the number back).

## Hands-On Lab

**1. One backend Pod behind a Service:**

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace scaling-lab
kubectl apply -f manifests/scaling/scaling-backend.yaml -n scaling-lab
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s
```

**2. Scale to 3:**

<!-- test: contains=3/3 -->
```bash
kubectl scale deployment backend -n scaling-lab --replicas=3
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s
kubectl get deployment backend -n scaling-lab
```

**3. Who answers?** The backend says which Pod answered (`"pod"`). A client Pod inside the cluster calls the Service
30 times; every call opens a new connection, so kube-proxy picks a Pod each time:

<!-- test: contains=backend-; output -->
```bash
kubectl run client -n scaling-lab --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 30); do wget -qO- http://backend; echo; done' > /dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/client -n scaling-lab --timeout=120s > /dev/null
kubectl logs client -n scaling-lab | grep -o '"pod":"[^"]*"' | sort | uniq -c
```

```text
     11 "pod":"backend-5f65986b87-7wrbs"
     10 "pod":"backend-5f65986b87-8vt4r"
      9 "pod":"backend-5f65986b87-t9wx6"
```

**4. Scale to 5**, and see the Service's list of addresses grow:

<!-- test: contains=5/5 -->
```bash
kubectl scale deployment backend -n scaling-lab --replicas=5
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s
kubectl get deployment backend -n scaling-lab
```

## Expected Result

Three Pods shared the 30 requests (the split is random, not exactly equal); after scaling to 5 the Deployment shows
`5/5` and the Service knows 5 addresses.

## Inspect

The Service's EndpointSlice lists the IP of every ready Pod:

<!-- test: contains=8080; output -->
```bash
kubectl get endpointslices -n scaling-lab -l kubernetes.io/service-name=backend
kubectl get pods -n scaling-lab -l app=backend -o custom-columns=NAME:.metadata.name,IP:.status.podIP
```

```text
NAME            ADDRESSTYPE   PORTS   ENDPOINTS                                                 AGE
backend-jrjp5   IPv4          8080    10.244.120.74,10.244.120.123,10.244.120.121 + 2 more...   8s
NAME                       IP
backend-5f65986b87-7wrbs   10.244.120.121
backend-5f65986b87-8vt4r   10.244.120.74
backend-5f65986b87-kw6c9   10.244.120.96
backend-5f65986b87-nhtvj   10.244.120.70
backend-5f65986b87-t9wx6   10.244.120.123
```

The ReplicaSet's events show every scaling step:

<!-- test: contains=Scaled up -->
```bash
kubectl get events -n scaling-lab --field-selector involvedObject.kind=Deployment -o custom-columns=MESSAGE:.message
```

## Experiment

Scale down from 5 to 2 and watch which Pods go: the ReplicaSet deletes the youngest, not-ready or unbalanced Pods
first, and the Service stops sending them traffic as soon as they start terminating.

<!-- test: contains=2/2 -->
```bash
kubectl scale deployment backend -n scaling-lab --replicas=2
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s
kubectl get deployment backend -n scaling-lab
```

## Break It

Someone "saves resources" by scaling to zero:

<!-- test: contains=Connection refused; output -->
```bash
kubectl scale deployment backend -n scaling-lab --replicas=0
kubectl wait --for=delete pod -l app=backend -n scaling-lab --timeout=120s > /dev/null
kubectl run client2 -n scaling-lab --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://backend > /dev/null
kubectl wait --for=jsonpath='{.status.phase}'=Failed pod/client2 -n scaling-lab --timeout=60s > /dev/null
kubectl logs client2 -n scaling-lab
```

```text
deployment.apps/backend scaled
wget: can't connect to remote host (10.102.151.108): Connection refused
```

## Troubleshoot It

*What should happen?* The client gets an answer. *What happened?* `Connection refused` from the Service's address.
The name resolved (DNS works, the Service exists), but nothing accepted the connection. *Which object decides where
Service traffic goes?* The EndpointSlice:

<!-- test: contains=<unset>; output -->
```bash
kubectl get endpointslices -n scaling-lab -l kubernetes.io/service-name=backend
kubectl get deployment backend -n scaling-lab
```

```text
NAME            ADDRESSTYPE   PORTS     ENDPOINTS   AGE
backend-jrjp5   IPv4          <unset>   <unset>     14s
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
backend   0/0     0            0           14s
```

No endpoints, because the Deployment wants `0/0` Pods. A Service with no endpoints rejects connections. Root cause:
`replicas: 0`. The same symptom appears when no Pod matches the selector or no Pod is ready (labs 04 and 12).

## Fix It

<!-- test: contains=backend- -->
```bash
kubectl scale deployment backend -n scaling-lab --replicas=2
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s > /dev/null
kubectl run client3 -n scaling-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'for i in $(seq 1 10); do wget -qO- -T 5 http://backend && exit 0; sleep 2; done; exit 1'
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `kubectl scale`, then `kubectl apply` of the old file | replicas jump back to the file's value | change `replicas:` in the file (the source of truth) |
| Scaling a Deployment that an HPA manages | the HPA overrides your number within seconds (lab 13) | change the HPA's `minReplicas`/`maxReplicas` instead |
| Scaling up without resource requests | Pods crowd one node, or the node runs out of memory | set requests (lesson 15) so the scheduler can plan |
| Scaling to 0 "temporarily" | `Connection refused` for every client | check `kubectl get deploy` first when a Service refuses connections |
| Expecting equal traffic per Pod | one Pod gets more | spreading is per connection and random; long-lived connections stick to one Pod |

## Best Practices

- Run at least 2 replicas of anything users depend on, so one Pod can restart without an outage.
- Keep the replica count in Git (the manifest); use `kubectl scale` for emergencies and experiments.
- Scale on evidence (CPU, latency, queue length), and let the HPA (lesson 26) do it for regular traffic changes.

## Challenge

**Task:** make the backend run 4 replicas **declaratively**, so that applying the file again keeps 4.

**Requirements:** do not use `kubectl scale`; the Deployment shows `4/4`.

**Hints:** change one field of the manifest and `kubectl apply` it; `sed` can edit the file on its way to
`kubectl apply -f -` (`-f -` reads the manifest from the pipe).

**Expected Result:** `kubectl get deployment backend -n scaling-lab` shows `4/4`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=4/4 -->
```bash
sed 's/replicas: 1/replicas: 4/' manifests/scaling/scaling-backend.yaml | kubectl apply -n scaling-lab -f -
kubectl rollout status deployment/backend -n scaling-lab --timeout=120s > /dev/null
kubectl get deployment backend -n scaling-lab
```

</details>

`kubectl apply` compares the file with the live object and changes only what differs: here `spec.replicas`. Because
the number now lives in the file, every later `apply` keeps 4, which is exactly what a CI/CD pipeline or GitOps tool
does.

## Key Takeaways

- Scaling = changing `spec.replicas`; the ReplicaSet creates or deletes Pods to match.
- The Service follows automatically: its EndpointSlice lists every ready Pod, kube-proxy spreads connections.
- `Connection refused` on a Service usually means no endpoints: 0 replicas, a wrong selector, or no ready Pod.
- Real-world use: scaling up before a known traffic peak, scaling down at night, and running enough replicas to
  survive the loss of a Pod or a node.

## Cleanup

🧹 Delete the namespace `scaling-lab` (the backend Deployment, its Service and the client Pods):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace scaling-lab
```

Next: [26 · Horizontal Pod Autoscaler](../26-hpa/README.md)
