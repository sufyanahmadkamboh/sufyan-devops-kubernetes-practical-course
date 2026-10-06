# 03 · Installing Minikube

> Level 1 · Kubernetes Fundamentals · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## What is it?

**Minikube** creates a real Kubernetes cluster on your computer: one node, running inside a Docker container. It is
the same Kubernetes as in production (the same API server, scheduler, kubelet…), just small. **kubectl** is the
command-line client you use to talk to any Kubernetes cluster, including this one.

## Why do we need it?

You learn Kubernetes by using it, and you need a cluster you can break without consequences, without a cloud account
and without paying anything. Minikube is that cluster; every lesson of this course runs on it.

> ⚠️ **Do not run the commands of this course against a production or shared cluster.** They delete things, stop
> components and break them on purpose. Always check which cluster kubectl talks to: `kubectl config current-context`
> must print `minikube`.

## How does it work?

```text
your computer
├── Docker (Docker Desktop on Windows/macOS, Docker Engine on Linux)
│   └── container "minikube"            ← the Kubernetes node, a small Linux system
│       ├── containerd                  ← the container runtime inside the node
│       ├── kubelet, control plane      ← Kubernetes itself
│       └── your Pods                   ← containers started by Kubernetes
├── minikube    ← creates, starts, stops and deletes that node
└── kubectl     ← talks to the API server inside it; minikube writes the address into ~/.kube/config
```

Alternatives exist (kind, k3d, Docker Desktop's Kubernetes); they all give you a local cluster. This course uses
Minikube everywhere, with one set of settings, so every output you see matches yours.

## Architecture

```text
 kubectl ──▶ ~/.kube/config ──▶ https://127.0.0.1:PORT ──▶ API server ┐
                (context "minikube")                                  │  inside the
 minikube ──▶ Docker ──▶ container "minikube" (the node) ─────────────┘  "minikube" container
```

## YAML

No YAML yet: the cluster is created by `minikube start`. The settings you choose there decide what the cluster can
do, so the course always uses the same command:

| Flag | Meaning | Why this course uses it |
|---|---|---|
| `--driver=docker` | run the node as a Docker container | works the same on Windows, macOS and Linux |
| `--cni=calico` | the network plugin, Calico | it enforces NetworkPolicies (lesson 22); the default plugin ignores them |
| `--cpus=2` | CPUs given to the node | enough for every lesson, including the autoscaler |
| `--memory=4g` | memory given to the node | enough for the capstone (database, backend, frontend) |

## Hands-On Lab

**1. Install Docker, Minikube and kubectl.** Docker: Docker Desktop (Windows, macOS) or Docker Engine (Linux), running.
Then, on Windows (PowerShell):

<!-- test: skip -->
```bash
winget install Kubernetes.minikube
winget install Kubernetes.kubectl
```

On macOS:

<!-- test: skip -->
```bash
brew install minikube kubectl
```

On Linux (x86-64):

<!-- test: skip -->
```bash
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl && rm kubectl
```

On Windows, run the course in **Git Bash**. One Git Bash habit to know now: it rewrites arguments that look like
Linux paths (`/etc/hosts`) into Windows paths before kubectl sees them; set `export MSYS_NO_PATHCONV=1` in your Git
Bash profile so `kubectl exec POD -- cat /etc/hosts` works as written.

**2. Check the tools:**

<!-- test: contains=v1.39; contains=Client Version -->
```bash
minikube version --short
kubectl version --client
```

**3. Create the cluster.** The first start downloads about 500 MB (the node image and Kubernetes); later starts take
less than a minute:

<!-- test: contains=Done!; timeout=900 -->
```bash
minikube start --driver=docker --cni=calico --cpus=2 --memory=4g 2>&1 | tail -2
```

**4. Talk to it:**

<!-- test: contains=Server Version; contains=control plane is running; output -->
```bash
kubectl version
kubectl cluster-info
```

```text
Client Version: v1.37.1
Kustomize Version: v5.8.1
Server Version: v1.37.0
Kubernetes control plane is running at https://127.0.0.1:59829
CoreDNS is running at https://127.0.0.1:59829/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

<!-- test: contains=Ready; output -->
```bash
kubectl get nodes
```

```text
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   12m   v1.37.0
```

| Command | What it tells you |
|---|---|
| `kubectl version` | the client's version and the cluster's (server) version: they should be within one minor version |
| `kubectl cluster-info` | where the API server is: `127.0.0.1` and a port, forwarded into the Minikube container |
| `kubectl get nodes` | the machines of the cluster and whether they are `Ready` to run Pods |

**5. Build the course application** inside the cluster, so Kubernetes finds its images without a registry:

<!-- test: contains=learning-app/backend:1.0.0; contains=learning-app/backend:2.0.0; timeout=900 -->
```bash
bash scripts/build-images.sh
```

## Expected Result

`kubectl get nodes` shows one node, `minikube`, `Ready`; `kubectl version` shows a server version v1.37.0; the two
backend images are built.

## Inspect

Which cluster does kubectl talk to? (Always check before running anything that deletes.)

<!-- test: contains=minikube -->
```bash
kubectl config current-context
minikube status
```

The images inside the node:

<!-- test: contains=learning-app/backend -->
```bash
minikube image ls | grep learning-app
```

## Experiment

Ask for more memory than the computer has, in a second cluster (a **profile**, `-p`) so the course cluster is not
touched:

<!-- test: contains=RSRC_OVER_ALLOC_MEM; output -->
```bash
minikube start -p too-big --driver=docker --memory=64g 2>&1 | grep -E 'Exiting|Suggestion'
```

```text
X Exiting due to RSRC_OVER_ALLOC_MEM: Requested memory allocation 65536MB is more than your system limit 32220MB.
* Suggestion: Start minikube with less memory allocated: 'minikube start --memory=8000mb'
```

Minikube checks resources before creating anything and suggests a value. (On Docker Desktop the limit is the memory
given to Docker Desktop in its settings.)

## Break It

Stop the cluster, then use kubectl as usual:

<!-- test: fail; contains=refused; output=tail:1 -->
```bash
minikube stop 2>&1 | tail -1
kubectl get nodes 2>&1
```

```text
...
Unable to connect to the server: dial tcp [::1]:8080: connectex: No connection could be made because the target machine actively refused it.
```

## Troubleshoot It

*What should happen?* A list of nodes. *What happened?* `Unable to connect to the server … localhost:8080 … refused`.
Two clues: kubectl did not even try the Minikube address, it fell back to `localhost:8080`, the default when it has
**no** cluster configured. *Which component is involved?* Not Kubernetes: kubectl's configuration and the node
itself. Ask Minikube:

<!-- test: contains=Stopped; contains=exit code 7; output -->
```bash
code=0; minikube status 2>&1 || code=$?
echo "exit code $code"
```

```text
minikube
type: Control Plane
host: Stopped
kubelet: Stopped
apiserver: Stopped
kubeconfig: Stopped

exit code 7
```

`minikube status` also says it with its exit code: 0 when everything runs, non-zero (7 here) when something is
stopped, so scripts can check it. Root cause: the node is stopped, and `minikube stop` also removed its address from the kubeconfig, which is why
kubectl tried `localhost:8080`. Nothing is lost: a stopped cluster keeps everything.

## Fix It

<!-- test: contains=Ready; timeout=900 -->
```bash
minikube start --driver=docker --cni=calico --cpus=2 --memory=4g 2>&1 | tail -1
kubectl get nodes
```

## Common Mistakes

| Problem | Symptom | Fix |
|---|---|---|
| Docker is not running | `PROVIDER_DOCKER_NOT_RUNNING` or `Cannot connect to the Docker daemon` | start Docker Desktop / `sudo systemctl start docker`, then `minikube start` again |
| Docker driver problems | `minikube start` hangs or fails at "Creating docker container" | `minikube delete`, check `docker info` works, start again; on Linux your user must be in the `docker` group |
| kubectl cannot connect | `connection refused` / `localhost:8080` | `minikube status`; if running, `minikube update-context` rewrites the kubeconfig entry |
| The cluster is stopped | every kubectl command fails | `minikube start` with the same flags |
| Insufficient resources | `RSRC_OVER_ALLOC_MEM`, or Pods `Pending` with `Insufficient memory` later | lower `--memory`/`--cpus`, or give Docker Desktop more in its settings |
| kubectl points to another cluster | commands hit a work cluster | `kubectl config current-context` must say `minikube`; `kubectl config use-context minikube` |

## Best Practices

- Keep one Minikube cluster for the whole course; `minikube stop` at the end of a session, `minikube start` the next
  day: everything is still there.
- Check `kubectl config current-context` before any `delete`.
- Recreate rather than repair when the cluster itself is broken: `minikube delete` then `minikube start` takes a minute.

## Challenge

**Task:** find out how many CPUs and how much memory your Minikube node reports to Kubernetes, and compare them
with what you asked for (`--cpus=2 --memory=4g`).

**Requirements:** use only kubectl.

**Hints:** a node reports its `capacity` and its `allocatable` resources; `kubectl get node minikube -o jsonpath=...`
or `kubectl describe node minikube`.

**Expected Result:** two numbers, and an explanation of why they are not 2 and 4 GiB.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=cpu=; output -->
```bash
kubectl get node minikube -o jsonpath='cpu={.status.capacity.cpu} memory={.status.capacity.memory}{"\n"}'
```

```text
cpu=14 memory=16099924Ki
```

</details>

Not 2 and 4 GiB: with the Docker driver, `--cpus` and `--memory` limit the node **container** (Docker enforces them),
but the kubelet inside it reads the CPUs and memory of the machine that runs Docker (on Docker Desktop, its virtual
machine) and reports those as the node's `capacity`. The scheduler (lesson 16) therefore believes the node is
bigger than it really is; Pods asking for more than 4 GiB in total would be scheduled and then run out of memory.
`allocatable` is the capacity minus what the system reserves; lesson 15 uses these numbers.

## Key Takeaways

- Minikube = a real one-node Kubernetes cluster inside a Docker container; kubectl = the client for any cluster.
- The course cluster: `minikube start --driver=docker --cni=calico --cpus=2 --memory=4g`.
- `minikube status` and `kubectl config current-context` are the first checks when kubectl cannot connect.
- Real-world use: every DevOps engineer keeps a local cluster to try manifests, upgrades and failures before they
  reach a shared cluster.

## Cleanup

🧹 Delete the `too-big` profile of the Experiment (it was never created, but Minikube keeps an invalid profile entry).
The course cluster stays: every next lesson uses it.

<!-- test -->
```bash
minikube delete -p too-big 2>&1 | tail -1
```

Next: [04 · kubectl fundamentals](../04-kubectl/README.md)
