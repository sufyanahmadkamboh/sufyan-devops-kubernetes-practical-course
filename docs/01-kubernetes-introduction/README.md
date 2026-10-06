# 01 · What is Kubernetes?

> Level 1 · Kubernetes Fundamentals · ⏱ 20 minutes · run every command from the course folder · needs: Docker

## What is it?

Kubernetes is a system that **runs and looks after containerized applications for you**, on one or many machines.
You tell it *what you want* ("three copies of my web server, reachable on one address, always running") and it
works continuously to make reality match: it starts the containers, restarts them when they crash, replaces them when
a machine dies, spreads traffic across them and updates them without downtime.

An analogy: Docker is a skilled cook who can prepare any dish (container) you ask for. Kubernetes is the **restaurant
manager**: it decides which cook prepares what, notices when a cook goes home sick and hands the work to another,
opens more stations when the restaurant is busy, and keeps the menu (your desired state) written on the wall.

## Why do we need it?

With one container on one machine, Docker is enough. Applications rarely stay that small:

```text
1 container                  →  docker run is enough
many containers              →  which ones are running? which crashed?
multiple machines            →  which machine runs what? what if one dies?
scaling                      →  start 5 more copies, spread the traffic
self-healing                 →  restart what crashed, without a human awake at 3 a.m.
rolling deployments          →  update to v2 with no downtime, go back to v1 if v2 is broken
                             →  Kubernetes
```

Doing all of that by hand, with scripts around `docker run`, is exactly the work Kubernetes automates.

## How does it work?

You never start containers yourself. You **describe the desired state** in YAML files and send them to Kubernetes:

```text
you                          Kubernetes                              machines (nodes)
"3 copies of web:1.0"  ───▶  stores the desired state          ───▶  starts 3 containers
                             compares it with reality, forever       one crashes ───┐
                             "only 2 running, I want 3"        ◀────────────────────┘
                             starts a replacement              ───▶  3 running again
```

This loop (desired state → observe → correct) is called **reconciliation**, and it is the core idea of Kubernetes.
Everything in this course is a variation of it.

| | Docker | Kubernetes |
|---|---|---|
| What it does | **runs** containers | **manages** containerized applications |
| Unit | a container | a Pod (one or more containers, lesson 06) |
| Scope | one machine | a cluster of machines |
| You say | "run this container now" | "this is how it should be; keep it that way" |
| When a container dies | it stays dead (unless a restart policy on that machine) | it is replaced, on any healthy machine |
| Scaling | start more containers yourself, each on its own port | `replicas: 5` |
| Updates | stop old, start new (downtime) | rolling update, rollback |

Kubernetes does not replace Docker images: it runs the **same images** you build with Docker.

## Architecture

```text
            You
             │  kubectl apply -f app.yaml        ("I want 3 copies of web")
             ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    Kubernetes cluster                       │
   │   ┌──────────────────┐                                      │
   │   │  Control plane   │  stores the desired state, decides,  │
   │   │  (the "brain")   │  watches, corrects                   │
   │   └────────┬─────────┘                                      │
   │            │                                                │
   │   ┌────────┴─────────┐      ┌──────────────────┐            │
   │   │  Node 1          │      │  Node 2          │            │
   │   │  [web] [web]     │      │  [web]           │  ◀── the   │
   │   └──────────────────┘      └──────────────────┘   machines │
   └─────────────────────────────────────────────────────────────┘
```

Lesson 02 opens the brain and the nodes, one component at a time.

## YAML

You will write YAML from lesson 06 on. Here is what "3 copies of web" looks like, so you can recognise it later
(lesson 09 explains every line):

```text
apiVersion: apps/v1
kind: Deployment             # "keep this application running"
metadata:
  name: web
spec:
  replicas: 3                # the desired state: three copies
  selector:
    matchLabels: {app: web}
  template:                  # what each copy looks like
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: web
          image: nginx:1.30-alpine
```

## Hands-On Lab

Before Kubernetes, feel the problem it solves, with plain Docker.

**1. Run a web server with Docker:**

<!-- test: contains=Welcome to nginx -->
```bash
docker run -d --name web -p 8080:80 nginx:1.30-alpine > /dev/null
sleep 2
curl -s http://localhost:8080 | grep -o '<title>.*</title>'
```

**2. Simulate a crash:** `docker kill` stops the container abruptly, as a crash or an out-of-memory kill would.

<!-- test: contains=Exited; output -->
```bash
docker kill web > /dev/null
docker ps -a --filter name=web --format '{{.Names}}: {{.Status}}'
```

```text
web: Exited (137) Less than a second ago
```

## Expected Result

The web server answered once, then the container is `Exited` and stays that way: nothing notices, nothing restarts
it. On a real server that is an outage until a person reacts.

## Inspect

<!-- test: contains=no answer -->
```bash
curl -s -m 3 http://localhost:8080 || echo "no answer on port 8080"
docker inspect web --format 'exit code {{.State.ExitCode}}, restart policy: {{.HostConfig.RestartPolicy.Name}}'
```

Exit code 137 means the process was killed (128 + signal 9). The restart policy is `no`: Docker was never told what
the container *should* be doing, only to start it once.

## Experiment

Docker can restart containers on the same machine with a restart policy. Try it:

<!-- test: contains=running -->
```bash
docker rm -f web > /dev/null
docker run -d --name web --restart always -p 8080:80 nginx:1.30-alpine > /dev/null
docker exec web kill 1
sleep 3
docker ps --filter name=web --format '{{.Names}}: {{.State}}'
```

It came back. But a restart policy only works **on that machine**: if the machine itself fails, nothing moves the
container elsewhere; and it does nothing for scaling, traffic spreading or updates. Those need an orchestrator.

## Break It

Scale by hand: a second copy of the web server on the same port.

<!-- test: fail; contains=port is already allocated; output=tail:1 -->
```bash
docker run -d --name web-2 -p 8080:80 nginx:1.30-alpine 2>&1
```

```text
...
Run 'docker run --help' for more information
```

## Troubleshoot It

*What should happen?* Two copies serving the same site. *What happened?* `port is already allocated`: a host port
belongs to one container. With plain Docker you would pick a second port (8081), then put a load balancer in front,
then keep a list of which copy runs where, and update it whenever one dies. That bookkeeping is exactly what
Kubernetes does: a **Service** (lesson 10) gives all copies one address and spreads traffic, and a **Deployment**
(lesson 09) keeps the right number of copies running.

## Common Mistakes

| Mistake | What happens | Instead |
|---|---|---|
| Thinking Kubernetes replaces Docker images | confusion about where images come from | Kubernetes runs the same images you build with Docker |
| Thinking you need Kubernetes for one container | a lot of complexity for nothing | one container on one machine: Docker (or Compose) is enough |
| Starting containers by hand on a cluster | Kubernetes does not know them, will not heal them | describe the desired state; let Kubernetes start them |

## Best Practices

- Learn Kubernetes on a local cluster (Minikube, this course) before touching a shared or production cluster.
- Think in **desired state**: "what should be true?", not "which command do I run?".

## Challenge

**Task:** in your own words, list three things that happened (or did not happen) in the lab that a Kubernetes
Deployment with a Service would have done differently.

**Requirements:** one sentence each; name the Kubernetes feature.

**Hints:** look at the Expected Result and the Break It sections.

**Expected Result:** three sentences.

## Solution

<details>
<summary>Solution</summary>

1. When the container was killed it stayed dead: a Deployment would have started a replacement (**self-healing**).
2. A second copy could not use the same port: a Deployment runs many copies and a **Service** gives them one
   address and spreads the traffic.
3. A restart policy only restarts on the same machine: Kubernetes **reschedules** work on another node when a node
   fails.

</details>

The point is not the commands but the shift: Docker executes instructions; Kubernetes keeps a promise.

## Key Takeaways

- Docker runs containers; Kubernetes manages containerized applications across machines.
- You describe the desired state; Kubernetes reconciles reality with it, continuously.
- Self-healing, scaling, one address for many copies and zero-downtime updates are what you get.
- Real-world use: almost every company that runs many services in containers runs them on Kubernetes, in the cloud
  (EKS, AKS, GKE) or in its own data center; the concepts in this course are the same everywhere.

## Cleanup

🧹 Delete the two Docker containers of this lesson (`web`, and `web-2` if it was created):

<!-- test -->
```bash
docker rm -f web web-2 > /dev/null 2>&1 || true
```

Next: [02 · Kubernetes architecture](../02-architecture/README.md)
