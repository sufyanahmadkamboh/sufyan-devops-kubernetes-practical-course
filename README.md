# Kubernetes Practical Course · Kubernetes From Zero to Practical

[![test-lessons](https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course/actions/workflows/test.yml/badge.svg)](https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course/actions/workflows/test.yml)

A complete, hands-on Kubernetes learning lab. You learn Kubernetes by **using** it on a cluster on your own computer:

```text
Learn → Deploy → Inspect → Break → Troubleshoot → Fix → Improve
```

29 lessons, 13 labs (one with 14 troubleshooting problems), challenges at three levels and a production-style
capstone, all on **Minikube**: no cloud account, nothing to pay. Every command in this course is run by CI on a fresh
cluster, and every output you see is the real output of that command.

> ⚠️ **Never run the commands of this course against a production or shared Kubernetes cluster.** They delete
> resources, stop components and break things on purpose. Before any `kubectl delete`, check:
> `kubectl config current-context` must print `minikube`.

## Who is it for?

Someone who knows basic Linux and Docker (images, containers, Dockerfiles) and has **never used Kubernetes**. You do
not need to be a programmer: the course application is ready-made, and exists only to make Kubernetes visible.

## What you will be able to do

Deploy and manage applications, expose them with Services and Ingress, configure them with ConfigMaps and Secrets,
give them persistent storage, add health checks and resource limits, scale them by hand and automatically, run Jobs,
CronJobs, DaemonSets and StatefulSets, secure them with NetworkPolicies, ServiceAccounts and RBAC, package them with
Helm, and troubleshoot the common failures on your own.

## The learning method

Every lesson walks the same path:

```text
Theory → Visual explanation → YAML → kubectl command → Deploy → Inspect → Experiment → Break it → Troubleshoot → Fix it
```

and has the same sections: What is it? · Why do we need it? · How does it work? · Architecture · YAML · Hands-On Lab ·
Expected Result · Inspect · Experiment · Break It · Troubleshoot It · Common Mistakes · Best Practices · Challenge ·
Solution · Key Takeaways · Cleanup.

## Roadmap

| Level | Topic | Lessons | Lab |
|---|---|---|---|
| 1 | Kubernetes fundamentals | [01 Introduction](docs/01-kubernetes-introduction/README.md) · [02 Architecture](docs/02-architecture/README.md) · [03 Installation](docs/03-installation/README.md) | |
| 2 | kubectl | [04 kubectl](docs/04-kubectl/README.md) · [05 Namespaces](docs/05-namespaces/README.md) | |
| 3 | Pods | [06 Pods](docs/06-pods/README.md) · [07 Labels and selectors](docs/07-labels-selectors/README.md) | [01 first Pod](labs/01-first-pod/README.md), [02 Pod debugging](labs/02-pod-debugging/README.md) |
| 4 | Deployments | [08 ReplicaSets](docs/08-replicasets/README.md) · [09 Deployments](docs/09-deployments/README.md) | [03 Deployment](labs/03-deployment/README.md) |
| 5 | Services | [10 Services and DNS](docs/10-services/README.md) | [04 Service](labs/04-service/README.md) |
| 6 | Configuration | [11 ConfigMaps](docs/11-configmaps/README.md) · [12 Secrets](docs/12-secrets/README.md) | [05 ConfigMap](labs/05-configmap/README.md), [06 Secret](labs/06-secret/README.md) |
| 7 | Storage | [13 Volumes, PV, PVC, StorageClass](docs/13-storage/README.md) | [07 storage](labs/07-storage/README.md) |
| 8 | Health checks | [14 Probes](docs/14-health-checks/README.md) | [08 probes](labs/08-probes/README.md) |
| 9 | Scaling and scheduling | [15 Requests and limits](docs/15-resources/README.md) · [16 Scheduling](docs/16-scheduling/README.md) · [25 Scaling](docs/25-scaling/README.md) · [26 HPA](docs/26-hpa/README.md) | [13 scaling](labs/13-scaling/README.md) |
| 10 | Ingress and networking | [20 Ingress](docs/20-ingress/README.md) · [21 Networking](docs/21-networking/README.md) · [22 NetworkPolicies](docs/22-networkpolicies/README.md) | [09 networking](labs/09-networking/README.md), [10 Ingress](labs/10-ingress/README.md) |
| 11 | Jobs and CronJobs | [17 Jobs and CronJobs](docs/17-jobs-cronjobs/README.md) · [18 DaemonSets](docs/18-daemonsets/README.md) | |
| 12 | Stateful applications | [19 StatefulSets](docs/19-statefulsets/README.md) | |
| 13 | Security and RBAC | [23 ServiceAccounts](docs/23-serviceaccounts/README.md) · [24 RBAC](docs/24-rbac/README.md) | [11 RBAC](labs/11-rbac/README.md) |
| 14 | Troubleshooting | [27 Troubleshooting](docs/27-troubleshooting/README.md) | [12 troubleshooting: 14 problems](labs/12-troubleshooting/README.md) |
| 15 | Helm | [28 Helm](docs/28-helm/README.md) | |
| 16 | Production-style capstone | [29 Capstone](docs/29-capstone/README.md) | [capstone/](capstone/) |

The lessons are numbered in the order to follow them (01 → 29); the table groups them by level. After each level,
try the [challenges](challenges/README.md): beginner, intermediate and troubleshooting.

## Setup

1. **Docker**: Docker Desktop (Windows, macOS) or Docker Engine (Linux), running, with at least 4 GB of memory for
   Docker.
2. **Minikube and kubectl**: [lesson 03](docs/03-installation/README.md) has the commands for every operating
   system. On Windows, use **Git Bash** and add `export MSYS_NO_PATHCONV=1` to your profile.
3. **This repository**:

```bash
git clone https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course.git kubernetes-practical-course
cd kubernetes-practical-course
minikube start --driver=docker --cni=calico --cpus=2 --memory=4g
bash scripts/build-images.sh
```

Run every command of the course **from the course folder**. Stop the cluster at the end of a session with
`minikube stop`; `minikube start` with the same flags brings everything back.

## The application

One small application grows through the course:

```text
User ─▶ Ingress ─▶ frontend (nginx) ─▶ backend (API) ─▶ database (PostgreSQL) ─▶ persistent volume
```

The backend ([apps/backend](apps/backend/)) is a tiny API built into Minikube by `scripts/build-images.sh`, in two
versions for rolling updates. It shows which version and which Pod answered, reads its configuration from the
environment and its password from a file, reports liveness and readiness, counts visits in the database and can burn
CPU on request for the autoscaler. You never need to change its code.

## Repository structure

```text
kubernetes-practical-course/
├── docs/          the 29 lessons (01-kubernetes-introduction … 29-capstone), one folder each
├── labs/          13 hands-on labs; labs/12-troubleshooting has 14 broken scenarios
├── manifests/     the YAML of the lessons, by kind (pods, deployments, services, configmaps, …)
├── challenges/    beginner, intermediate and troubleshooting challenges, solutions hidden
├── helm/          the course application as a Helm chart (lesson 28)
├── capstone/      the production-style application: namespace, frontend, backend, database, networking,
│                  storage, security, ingress, jobs, scaling, helm
├── apps/backend/  the course API (Go) and its Dockerfile
├── scripts/       build-images.sh
├── study/         the study guide (PDF)
└── tests/         the runner that executes every lesson exactly as written
```

## Labs, challenges and the capstone

- **Labs** practise one area each, with a break/fix part: objective, setup, steps, break it, troubleshoot it, fix
  it, verification, cleanup.
- **Challenges** give you a task, requirements and hints; the solution is folded away until you want it.
- **The capstone** ([lesson 29](docs/29-capstone/README.md)) deploys the whole application with everything the
  course taught, then breaks it six ways (image, Service, configuration, probe, storage, NetworkPolicy) for you to fix.

## Where Kubernetes fits

Kubernetes is the runtime of most container platforms. Around it, other tools build the images (CI), store them
(registries), describe infrastructure (Terraform), deliver changes from Git (GitOps tools) and watch everything
(Prometheus, Grafana). None of them is needed here: this course is about Kubernetes itself, and everything it teaches
works the same on a cloud cluster (EKS, AKS, GKE) as on Minikube.

## Final knowledge checklist

- [ ] I understand Kubernetes
- [ ] I understand Kubernetes architecture
- [ ] I can use kubectl
- [ ] I understand Pods
- [ ] I understand Deployments
- [ ] I understand ReplicaSets
- [ ] I understand Services
- [ ] I understand labels and selectors
- [ ] I can use ConfigMaps
- [ ] I can use Secrets
- [ ] I understand Kubernetes storage
- [ ] I understand PV/PVC
- [ ] I can configure health probes
- [ ] I understand requests and limits
- [ ] I understand basic scheduling
- [ ] I can use Jobs
- [ ] I can use CronJobs
- [ ] I understand DaemonSets
- [ ] I understand StatefulSets
- [ ] I understand Ingress
- [ ] I understand Kubernetes DNS
- [ ] I understand NetworkPolicies
- [ ] I understand ServiceAccounts
- [ ] I understand RBAC
- [ ] I can troubleshoot Pods
- [ ] I can troubleshoot Services
- [ ] I can troubleshoot Deployments
- [ ] I can troubleshoot storage
- [ ] I can troubleshoot networking
- [ ] I can perform rolling updates
- [ ] I can roll back deployments
- [ ] I can scale applications
- [ ] I understand HPA
- [ ] I understand Helm
- [ ] I can deploy a complete Kubernetes application

## How the course is tested

[tests/run.sh](tests/run.sh) runs every lesson as a learner types it: a sandbox home and kubeconfig, one Minikube
cluster started with the course's settings, a clean cluster before and after every lesson. The
[CI workflow](.github/workflows/test.yml) does the same on a fresh cluster for every change, and validates every
manifest against the Kubernetes 1.37 API. [docs/AUTHORING.md](docs/AUTHORING.md) describes the lesson format.

## License

[MIT](LICENSE)
