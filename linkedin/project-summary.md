# Kubernetes Practical Course · project summary

**What:** a free, hands-on Kubernetes course from zero to practical, entirely on a local Minikube cluster: 29 lessons
(architecture, kubectl, namespaces, Pods, labels, ReplicaSets, Deployments, Services and DNS, ConfigMaps, Secrets,
storage, probes, resources, scheduling, Jobs, CronJobs, DaemonSets, StatefulSets, Ingress, networking,
NetworkPolicies, ServiceAccounts, RBAC, scaling, HPA, troubleshooting, Helm), 13 labs, 19 challenges and a
production-style capstone.

**Problem:** Kubernetes is usually learned as YAML to copy; the hard parts at work are the failures: Pods that never
schedule, crash loops, image pulls, Services without endpoints, lost data, failing probes, stuck rollouts, DNS and
NetworkPolicy problems. Those are rarely practised.

**Contents**
- 29 lessons, each: what it is, why it exists, how it works, an architecture diagram, the YAML explained field by
  field, a hands-on lab with expected results, inspect commands, an experiment, a failure made on purpose,
  troubleshooting, common mistakes, best practices, a challenge with a hidden solution, key takeaways and cleanup
- 13 labs with break/fix parts; the troubleshooting lab reproduces 14 failures in the format problem → symptoms →
  first command → investigation → root cause → fix → verification → lesson learned
- 19 challenges at three levels (beginner, intermediate, troubleshooting)
- a Helm chart for the course application with values per environment
- a capstone: Ingress → nginx frontend (non-root, read-only, ConfigMaps) → Go backend (probes, limits, HPA 2–5) →
  PostgreSQL StatefulSet on a PVC, a password Secret mounted as a file, a backup CronJob, default-deny NetworkPolicies,
  one ServiceAccount per component without API tokens, a read-only RBAC Role; rolling update and rollback; then six
  break/fix scenarios (image, Service, ConfigMap, probe, storage, NetworkPolicy); the same application as one Helm
  release
- a 17-video series (full and silent versions), a 117-page study guide PDF, 13 diagrams, a glossary,
  22 interview questions and a final knowledge checklist

**Engineering details**
- `tests/mdrun.py` runs every Bash block as a learner types it on a real Minikube cluster (Kubernetes 1.37, Calico),
  writes the real outputs back into the lessons and resets the cluster between lessons (course namespaces, the
  default namespace, labelled cluster-wide objects, node labels and taints); a sandbox home and kubeconfig keep the
  author's clusters untouched; hung commands are stopped after their timeout
- GitHub Actions runs all 750 blocks in four parallel groups on a fresh Minikube cluster, with the course
  images preloaded through a Docker Hub mirror; static checks validate every manifest and the rendered Helm chart
  against the Kubernetes 1.37 API (kubeconform), lint the chart, check links, ShellCheck the scripts and vet the Go code
- the videos are generated from the lessons: one per level, two narrator voices, real recorded outputs, original
  synthesised music and effects, captions, chapters and an audio-license register with timestamps

**Repository:** https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course
