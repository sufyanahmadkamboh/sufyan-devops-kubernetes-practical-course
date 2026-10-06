# Kubernetes interview questions

Questions asked in junior and mid-level DevOps and platform interviews. Answer out loud first, then open the model
answer; the lesson link has the hands-on version.

**1. What problem does Kubernetes solve that Docker alone does not?**
<details><summary>Answer</summary>

Docker runs containers on one machine. Kubernetes manages containerized applications across many machines from a
declared desired state: it keeps the right number of copies running (self-healing), places them on nodes, gives them
stable addresses (Services), spreads traffic, scales them and updates them without downtime. → [01](01-kubernetes-introduction/README.md)
</details>

**2. Name the control-plane components and what each does.**
<details><summary>Answer</summary>

API server (the only entry point), etcd (the state store), scheduler (picks a node for new Pods), controller manager
(reconciliation loops). On every node: kubelet (runs the Pods), kube-proxy (Service networking), container runtime.
→ [02](02-architecture/README.md)
</details>

**3. A Pod stays `Pending`. How do you find out why?**
<details><summary>Answer</summary>

`kubectl describe pod` and read the Events: `FailedScheduling` with `Insufficient cpu/memory`, an untolerated taint,
a nodeSelector no node matches, or a PVC that is not bound. No events at all means nothing is scheduling (the
scheduler is down). → [27](27-troubleshooting/README.md), [02](02-architecture/README.md)
</details>

**4. What is the difference between a Pod, a ReplicaSet and a Deployment?**
<details><summary>Answer</summary>

A Pod runs containers. A ReplicaSet keeps N identical Pods running. A Deployment manages ReplicaSets so it can roll
out a new version (a new ReplicaSet) gradually and roll back to an old one. You normally create Deployments only.
→ [08](08-replicasets/README.md), [09](09-deployments/README.md)
</details>

**5. How does a Service find its Pods, and what happens when a Pod is replaced?**
<details><summary>Answer</summary>

By its label selector: every ready Pod whose labels match becomes an endpoint. A replaced Pod gets a new IP; the
Service's endpoints update automatically and the Service's name and IP stay the same. → [10](10-services/README.md)
</details>

**6. ClusterIP, NodePort, LoadBalancer, Ingress: when do you use which?**
<details><summary>Answer</summary>

ClusterIP for traffic inside the cluster (the default). NodePort to open a port on every node (testing, simple
setups). LoadBalancer for an external load balancer from the cloud, one per Service. Ingress for HTTP(S) routing of
many hosts/paths to many Services behind one entry point. → [10](10-services/README.md), [20](20-ingress/README.md)
</details>

**7. A Service has no endpoints. What are the usual causes?**
<details><summary>Answer</summary>

The selector does not match the Pods' labels (typo), the Pods are not ready (failing readiness probe), or they are in
another namespace. `kubectl get endpointslices`, `kubectl get pods --show-labels`, `kubectl describe pod`.
→ [10](10-services/README.md), [labs/12](../labs/12-troubleshooting/README.md)
</details>

**8. ConfigMap vs Secret: what is the difference, and is a Secret encrypted?**
<details><summary>Answer</summary>

Both hold configuration for Pods; Secrets are for sensitive values and are handled more carefully (RBAC, not shown by
default). By default a Secret is only base64-encoded, not encrypted: anyone who can read it, or read etcd, sees the
value. Encryption at rest, RBAC and external secret managers are needed for real protection. → [12](12-secrets/README.md)
</details>

**9. Liveness, readiness and startup probes: what does each one do when it fails?**
<details><summary>Answer</summary>

Liveness: the kubelet restarts the container. Readiness: the Pod is removed from its Services' endpoints (no traffic),
not restarted. Startup: liveness and readiness wait until it succeeds, for slow-starting applications.
→ [14](14-health-checks/README.md)
</details>

**10. What are requests and limits, and what happens when a container exceeds them?**
<details><summary>Answer</summary>

Requests are what the scheduler reserves for the container; limits are the maximum. Above the CPU limit the container
is throttled; above the memory limit it is OOMKilled (exit code 137) and restarted. → [15](15-resources/README.md)
</details>

**11. How does a rolling update work, and how do you roll back?**
<details><summary>Answer</summary>

The Deployment creates a new ReplicaSet and shifts Pods from the old one to the new one within `maxSurge` and
`maxUnavailable`, waiting for new Pods to be ready. `kubectl rollout status` follows it, `kubectl rollout undo`
returns to the previous revision. → [09](09-deployments/README.md)
</details>

**12. A rollout is stuck. What do you check?**
<details><summary>Answer</summary>

`kubectl rollout status` and the new Pods: `ImagePullBackOff` (wrong image or tag), `CrashLoopBackOff`, or a readiness
probe that never passes. The events and logs of the new Pod name the cause; `rollout undo` restores service.
→ [09](09-deployments/README.md), [29](29-capstone/README.md)
</details>

**13. PV, PVC and StorageClass: how do they relate?**
<details><summary>Answer</summary>

A Pod uses a PVC (a request for storage); the PVC binds to a PV (actual storage). With a StorageClass, a provisioner
creates the PV automatically when the PVC is created (dynamic provisioning). → [13](13-storage/README.md)
</details>

**14. Deployment vs StatefulSet?**
<details><summary>Answer</summary>

Deployment Pods are interchangeable (random names, shared or no storage). StatefulSet Pods have stable names
(`db-0`), start in order, keep their own PVC each and get stable DNS through a headless Service: databases and
clustered systems. → [19](19-statefulsets/README.md)
</details>

**15. Job, CronJob, DaemonSet: give one use for each.**
<details><summary>Answer</summary>

Job: a database migration that must complete once. CronJob: a nightly backup. DaemonSet: a log or monitoring agent on
every node. → [17](17-jobs-cronjobs/README.md), [18](18-daemonsets/README.md)
</details>

**16. How does service discovery work in Kubernetes?**
<details><summary>Answer</summary>

CoreDNS resolves `SERVICE` (same namespace), `SERVICE.NAMESPACE` and `SERVICE.NAMESPACE.svc.cluster.local` to the
Service's ClusterIP; Pods use the name, never Pod IPs. → [10](10-services/README.md), [21](21-networking/README.md)
</details>

**17. What does a NetworkPolicy do, and what is needed for it to work?**
<details><summary>Answer</summary>

It restricts which Pods (by label and namespace) may talk to which, on which ports. Once a Pod is selected by a policy,
everything not allowed is denied. It needs a network plugin that enforces policies (Calico, Cilium); otherwise it is
silently ignored. → [22](22-networkpolicies/README.md)
</details>

**18. How would you give a developer read-only access to one namespace?**
<details><summary>Answer</summary>

A Role with `get`, `list`, `watch` on the resources they need, and a RoleBinding to their user or group in that
namespace; verify with `kubectl auth can-i delete pods -n NS --as USER` → `no`. → [24](24-rbac/README.md)
</details>

**19. What is a ServiceAccount, and why disable its token when not needed?**
<details><summary>Answer</summary>

The identity of a Pod towards the Kubernetes API. Every Pod gets one; if the application never calls the API, setting
`automountServiceAccountToken: false` removes a credential an attacker could steal. → [23](23-serviceaccounts/README.md)
</details>

**20. How does the Horizontal Pod Autoscaler decide how many Pods to run?**
<details><summary>Answer</summary>

It reads metrics (CPU from metrics-server, relative to the Pods' requests) and computes
`desired = ceil(current × currentMetric / target)`, within min and max replicas, with a stabilization window before
scaling down. Without requests or metrics it cannot work. → [26](26-hpa/README.md)
</details>

**21. Why use Helm?**
<details><summary>Answer</summary>

To package an application's manifests as one versioned chart with values per environment, and to install, upgrade
and roll back the whole set as a release instead of applying many YAML files by hand. → [28](28-helm/README.md)
</details>

**22. Walk me through troubleshooting "the application does not respond".**
<details><summary>Answer</summary>

From the outside in: Ingress (rules, controller) → Service (endpoints, selector, ports) → Pods (status, restarts,
readiness) → events → logs (`--previous` after a crash) → configuration (ConfigMaps, Secrets) → dependencies (DNS,
database) → NetworkPolicies. Fix the source file, apply it, verify as the user.
→ [27](27-troubleshooting/README.md), [29](29-capstone/README.md)
</details>
