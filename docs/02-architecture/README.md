# 02 · Kubernetes architecture

> Level 1 · Kubernetes Fundamentals · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## What is it?

A Kubernetes **cluster** is a group of machines (**nodes**) with one "brain", the **control plane**. The control plane
stores what you want, decides where things run and corrects anything that drifts. The **worker nodes** run your
containers. Every component is a separate program with one job, and they all talk through one door: the **API
server**.

Back to the restaurant from lesson 01: the control plane is the office (the order book, the person who assigns work,
the supervisors who check), and the nodes are the kitchens where the cooking happens.

## Why do we need it?

When something goes wrong in Kubernetes, the symptom tells you which component to look at, but only if you know what
each one does. A Pod that stays `Pending` forever, a Pod that is scheduled but never starts, a cluster where nothing
changes any more: each points at a different component. This lesson builds that map.

## How does it work?

| Component | Where | Its one job (beginner version) |
|---|---|---|
| **API server** (`kube-apiserver`) | control plane | the front door: every command (`kubectl`), every component, talks only to it |
| **etcd** | control plane | the database: stores the desired and current state of every object |
| **Scheduler** (`kube-scheduler`) | control plane | picks a node for every new Pod that has none |
| **Controller manager** (`kube-controller-manager`) | control plane | runs the reconciliation loops: "3 copies wanted, 2 running → create 1" |
| **kubelet** | every node | the node agent: starts the Pod's containers, reports their status |
| **kube-proxy** | every node | makes Service addresses (lesson 10) work on the node |
| **Container runtime** (containerd) | every node | actually runs containers (what Docker did on your laptop) |

What happens when you create a Pod:

```text
kubectl run web ─▶ API server ─▶ etcd           (stored: "Pod web, no node yet")
                        ▲
   scheduler ───────────┘  sees a Pod without a node, picks one, writes "node = minikube"
   kubelet on minikube ────  sees a Pod assigned to it, asks containerd to start the container,
                             reports "Running" back to the API server
```

Nobody gives orders directly: every component **watches** the API server for objects it cares about and acts. That
is why one missing component stops exactly one step of the chain.

## Architecture

```text
                    Kubernetes Cluster (Minikube: everything on one node)

                  +---------------------+
                  |    Control Plane    |
                  |                     |
                  | API Server  ◀───────┼──── kubectl
                  | Scheduler           |
                  | Controller Manager  |
                  | etcd                |
                  +----------+----------+
                             |
              +--------------+--------------+
              |                             |
       +------+-------+              +------+-------+
       | Worker Node  |              | Worker Node  |
       | kubelet      |              | kubelet      |
       | kube-proxy   |              | kube-proxy   |
       | containerd   |              | containerd   |
       | Pods         |              | Pods         |
       +--------------+              +--------------+
```

Minikube runs the control plane and the worker on **one** node (named `minikube`); production clusters keep them on
separate machines. The components are the same.

## YAML

The control-plane components themselves are described by YAML files: Minikube (like `kubeadm`) runs them as **static
Pods**, defined by files on the node in `/etc/kubernetes/manifests/`. The kubelet runs whatever it finds there, even
without the API server; that is how the API server itself can start. You will look at those files in the lab.

## Hands-On Lab

**1. Start the cluster.** Lesson 03 explains every flag and what to do when this fails; if you have not installed
Minikube and kubectl yet, do lesson 03's installation first and come back.

<!-- test: contains=Done!; timeout=900 -->
```bash
minikube start --driver=docker --cni=calico --cpus=2 --memory=4g 2>&1 | tail -1
```

**2. The node:**

<!-- test: contains=control-plane; output -->
```bash
kubectl get nodes -o wide
```

```text
NAME       STATUS   ROLES           AGE     VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE                         KERNEL-VERSION                              CONTAINER-RUNTIME
minikube   Ready    control-plane   7m34s   v1.37.0   192.168.49.2   <none>        Debian GNU/Linux 12 (bookworm)   6.6.114.1-microsoft-standard-WSL2 (amd64)   containerd://2.3.4
```

One node, `Ready`, with the role `control-plane`, running Kubernetes v1.37.0 with the `containerd` runtime.

**3. The components, as Pods in the `kube-system` namespace:**

<!-- test: contains=kube-scheduler-minikube; contains=etcd-minikube; output -->
```bash
kubectl get pods -n kube-system -o custom-columns=NAME:.metadata.name,STATUS:.status.phase
```

```text
NAME                                      STATUS
calico-kube-controllers-db57f7644-h6kbk   Running
calico-node-sv68s                         Running
coredns-559f6c778d-jqvxs                  Running
etcd-minikube                             Running
kube-apiserver-minikube                   Running
kube-controller-manager-minikube          Running
kube-proxy-2wnhg                          Running
kube-scheduler-minikube                   Running
storage-provisioner                       Running
```

The four control-plane components end in `-minikube` (the node they are pinned to). `kube-proxy` and `calico-node`
run on every node; `coredns` is the cluster's DNS (lesson 10); `calico` is the network plugin (lesson 21).

**4. The static Pod files** that start the control plane, on the node (`minikube ssh` runs a command inside the
Minikube node):

<!-- test: contains=kube-scheduler.yaml; output -->
```bash
minikube ssh -- ls /etc/kubernetes/manifests
```

```text
etcd.yaml	     kube-controller-manager.yaml
kube-apiserver.yaml  kube-scheduler.yaml
```

## Expected Result

A `Ready` node, the four control-plane components running as Pods in `kube-system`, and their four static Pod files
on the node.

## Inspect

Ask the API server whether it is healthy, and how many kinds of objects it knows:

<!-- test: contains=livez check passed -->
```bash
kubectl get --raw '/livez?verbose' | tail -1
kubectl api-resources --no-headers | wc -l
```

The containers behind the Pods, as the container runtime sees them (`crictl` is the runtime's own CLI):

<!-- test: contains=kube-apiserver -->
```bash
minikube ssh -- sudo crictl ps --name kube-apiserver
```

## Experiment

Delete the `coredns` Pod and watch who brings it back:

<!-- test: contains=coredns -->
```bash
kubectl delete pod -n kube-system -l k8s-app=kube-dns --wait=false
kubectl wait --for=condition=Ready pod -n kube-system -l k8s-app=kube-dns --timeout=120s
kubectl get pods -n kube-system -l k8s-app=kube-dns
```

A new `coredns` Pod (a new random suffix) is running within seconds: the **controller manager** saw "1 wanted, 0
running" and created one, the **scheduler** placed it, the **kubelet** started it. You just watched reconciliation.

## Break It

⚠️ This breaks a control-plane component on purpose. Do it only on your local Minikube cluster.

Move the scheduler's static Pod file away, so the kubelet stops the scheduler, then create a Pod:

<!-- test: contains=Pending; output -->
```bash
minikube ssh -- sudo mv /etc/kubernetes/manifests/kube-scheduler.yaml /etc/kubernetes/
for i in $(seq 1 30); do kubectl get pod -n kube-system kube-scheduler-minikube > /dev/null 2>&1 || break; sleep 2; done
kubectl run waiting --image=nginx:1.30-alpine > /dev/null
sleep 8
kubectl get pod waiting -o wide
```

```text
NAME      READY   STATUS    RESTARTS   AGE   IP       NODE     NOMINATED NODE   READINESS GATES
waiting   0/1     Pending   0          8s    <none>   <none>   <none>           <none>
```

## Troubleshoot It

*What should happen?* The Pod runs. *What happened?* It is `Pending`, with `NODE <none>`: nobody picked a node.
*Which component picks nodes?* The scheduler. Look at the Pod's events first (lesson 27 makes this a habit):

<!-- test: contains=<none>; output -->
```bash
kubectl describe pod waiting | grep -A3 '^Events'
```

```text
Events:                      <none>
```

No events at all: not even a "FailedScheduling" (which the scheduler would write if it had tried and found no
suitable node). Nobody is looking at this Pod. Is the scheduler there?

<!-- test: contains=No resources found -->
```bash
kubectl get pods -n kube-system -l component=kube-scheduler 2>&1
```

Root cause: the scheduler is not running, so every new Pod waits forever. Existing Pods keep running: they already
have a node.

## Fix It

Put the static Pod file back; the kubelet starts the scheduler again, and the scheduler places the waiting Pod:

<!-- test: contains=Scheduled; output=tail:2 -->
```bash
minikube ssh -- sudo mv /etc/kubernetes/kube-scheduler.yaml /etc/kubernetes/manifests/
kubectl wait --for=condition=Ready pod -n kube-system -l component=kube-scheduler --timeout=120s > /dev/null
kubectl wait --for=condition=Ready pod/waiting --timeout=120s > /dev/null
kubectl describe pod waiting | grep -E 'Scheduled|Started'
```

```text
...
  Normal  Scheduled  10s   default-scheduler  Successfully assigned default/waiting to minikube
  Normal  Started    10s   kubelet            spec.containers{waiting}: Container started
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Expecting `kubectl` to talk to the nodes | confusion when the API server is down: every command fails | everything goes through the API server: check it first (`kubectl get --raw /livez`) |
| Deleting a `kube-system` Pod to "restart" a static Pod | the Pod comes back unchanged | static Pods are owned by the kubelet: change the file in `/etc/kubernetes/manifests` |
| Reading `Pending` as "image is downloading" | wrong investigation | `Pending` with no node = scheduling; with a node = the kubelet (image pull, volumes) |

## Best Practices

- When something is stuck, ask "which component owns this step?" before searching the error text.
- On real clusters the control plane runs on dedicated nodes (or is managed by the cloud provider): you rarely touch
  it, but you read its effects in events all the time.

## Challenge

**Task:** find out which container image and version each control-plane component runs, using only `kubectl`.

**Requirements:** one command; the output lists the four components with their images.

**Hints:** the components carry the label `tier=control-plane`; `-o custom-columns` can print
`.spec.containers[0].image`.

**Expected Result:** four lines: etcd, kube-apiserver, kube-controller-manager, kube-scheduler, with their image tags.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=kube-apiserver; output -->
```bash
kubectl get pods -n kube-system -l tier=control-plane -o custom-columns=POD:.metadata.name,IMAGE:.spec.containers[0].image
```

```text
POD                                IMAGE
etcd-minikube                      registry.k8s.io/etcd:3.7.0-0
kube-apiserver-minikube            registry.k8s.io/kube-apiserver:v1.37.0
kube-controller-manager-minikube   registry.k8s.io/kube-controller-manager:v1.37.0
kube-scheduler-minikube            registry.k8s.io/kube-scheduler:v1.37.0
```

</details>

Every component is an ordinary container image, versioned with Kubernetes itself (etcd has its own versions).
Labels and `-o custom-columns` are the tools you will use most in this course (lessons 04 and 07).

## Key Takeaways

- Control plane: API server (front door), etcd (state), scheduler (where), controller manager (reconcile).
- Every node: kubelet (start containers), kube-proxy (Service networking), container runtime (containerd).
- Components watch the API server and act; a missing component stops one step: `Pending` without node → scheduler.
- Real-world use: reading which component failed from a symptom is the first skill of on-call Kubernetes work.

## Cleanup

🧹 Delete the `waiting` Pod of the Break It section:

<!-- test -->
```bash
kubectl delete pod waiting --ignore-not-found
```

Next: [03 · Installing Minikube](../03-installation/README.md)
