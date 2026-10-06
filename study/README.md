# How to use this study guide

This guide is the revision companion to the course. Every lesson is condensed to what it is, why it exists, its
architecture diagram and its key takeaways, level by level. The full lessons, with every manifest, every command, its
real output, the labs, the challenges and their solutions, live in the repository: each summary links to its lesson.

## How to study

1. **Do the lesson first, read the summary afterwards.** Kubernetes is learned with your hands: apply every manifest,
   run every command, break the lesson the way its *Break It* section does, and read the real events before you read
   the explanation.
2. **Events first.** When something is wrong, `kubectl describe` and `kubectl get events` almost always name the cause:
   `FailedScheduling`, `ImagePullBackOff`, `Readiness probe failed`, `OOMKilled`. The course teaches you to trust them.
3. **Follow the chain.** Ingress → Service → endpoints → Pods → events → logs → configuration → dependencies →
   policies. Most problems are one wrong link in that chain.
4. **Do the lab of each level**, and the challenges, before reading their solutions.
5. **Finish with the troubleshooting lab and the capstone.** The capstone breaks a complete application six ways.

## A study plan

| Week | Levels | Goal |
|---|---|---|
| 1 | 1–4 | a cluster, kubectl, Pods, labels, ReplicaSets, Deployments, rolling updates |
| 2 | 5–8 | Services and DNS, ConfigMaps and Secrets, storage, health checks |
| 3 | 9–13 | resources, scheduling, Jobs, DaemonSets, StatefulSets, Ingress, NetworkPolicies, RBAC |
| 4 | 14–16 | scaling and the HPA, troubleshooting, Helm, the capstone |

One hour a day is enough: a lesson takes 20–45 minutes, plus its challenge.
