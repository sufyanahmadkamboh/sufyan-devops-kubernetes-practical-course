# Glossary

Every Kubernetes term the course uses, in alphabetical order, with the lesson that explains it.

| Term | Meaning | Lesson |
|---|---|---|
| **Annotation** | a key/value note on an object for tools and people; unlike labels, never used to select objects | [07](07-labels-selectors/README.md) |
| **API server** | the front door of the cluster: every command and every component talks only to it | [02](02-architecture/README.md) |
| **ClusterIP** | the default Service type: a stable virtual IP reachable only inside the cluster | [10](10-services/README.md) |
| **ClusterRole / ClusterRoleBinding** | RBAC permissions (and their assignment) that apply to the whole cluster or to cluster-wide objects | [24](24-rbac/README.md) |
| **ConfigMap** | non-secret configuration stored in the cluster, given to Pods as environment variables or files | [11](11-configmaps/README.md) |
| **Container runtime** | the program on each node that actually runs containers (containerd in Minikube) | [02](02-architecture/README.md) |
| **Context** | a named kubeconfig entry: cluster + user + default namespace; `kubectl config current-context` | [04](04-kubectl/README.md) |
| **Controller manager** | runs the reconciliation loops that keep reality equal to the desired state | [02](02-architecture/README.md) |
| **CoreDNS** | the cluster's DNS server: resolves Service names such as `backend` or `backend.ns.svc.cluster.local` | [10](10-services/README.md) |
| **CronJob** | creates a Job on a schedule (cron syntax) | [17](17-jobs-cronjobs/README.md) |
| **DaemonSet** | runs one Pod on every (suitable) node: log and monitoring agents | [18](18-daemonsets/README.md) |
| **Deployment** | manages ReplicaSets to keep N identical Pods running, with rolling updates and rollbacks | [09](09-deployments/README.md) |
| **Desired state** | what you declared in YAML; Kubernetes continuously makes reality match it (reconciliation) | [01](01-kubernetes-introduction/README.md) |
| **emptyDir** | a volume that lives as long as its Pod: scratch space shared by the Pod's containers | [13](13-storage/README.md) |
| **Endpoints / EndpointSlice** | the list of Pod addresses behind a Service; empty when the selector matches no ready Pod | [10](10-services/README.md) |
| **etcd** | the key-value database that stores every object of the cluster | [02](02-architecture/README.md) |
| **Event** | a record of something that happened to an object (scheduled, pulled, failed…); `kubectl get events` | [27](27-troubleshooting/README.md) |
| **Headless Service** | a Service with `clusterIP: None`: DNS returns the Pods' own addresses (StatefulSets) | [19](19-statefulsets/README.md) |
| **Helm / chart / release** | the package manager for Kubernetes; a chart is a package of templates, a release one installation of it | [28](28-helm/README.md) |
| **HorizontalPodAutoscaler (HPA)** | changes a Deployment's replica count from metrics such as CPU | [26](26-hpa/README.md) |
| **Ingress / ingress controller** | HTTP routing rules (hosts, paths) to Services, applied by a controller such as ingress-nginx | [20](20-ingress/README.md) |
| **Job** | runs Pods until a task completes successfully | [17](17-jobs-cronjobs/README.md) |
| **kube-proxy** | makes Service virtual IPs work on every node | [02](02-architecture/README.md) |
| **kubeconfig** | the file (`~/.kube/config`) that tells kubectl which clusters exist and how to log in | [03](03-installation/README.md) |
| **kubectl** | the command-line client of the Kubernetes API | [04](04-kubectl/README.md) |
| **kubelet** | the agent on every node: starts a Pod's containers, runs its probes, reports its status | [02](02-architecture/README.md) |
| **Label / selector** | key/value tags on objects, and the queries that pick objects by them (Services, Deployments, policies) | [07](07-labels-selectors/README.md) |
| **Limit / request** | the most a container may use, and what the scheduler reserves for it (CPU, memory) | [15](15-resources/README.md) |
| **Liveness / readiness / startup probe** | restart if dead / send traffic only when ready / wait for a slow start | [14](14-health-checks/README.md) |
| **LoadBalancer** | a Service type that asks the infrastructure (cloud) for an external load balancer | [10](10-services/README.md) |
| **Minikube** | a local one-node Kubernetes cluster, running in Docker for this course | [03](03-installation/README.md) |
| **Namespace** | a named group of objects inside a cluster, for organisation, access control and quotas | [05](05-namespaces/README.md) |
| **NetworkPolicy** | firewall rules between Pods by label and namespace (enforced by the network plugin, Calico here) | [22](22-networkpolicies/README.md) |
| **Node** | a machine (VM or server) that runs Pods | [02](02-architecture/README.md) |
| **nodeSelector** | runs a Pod only on nodes with the given labels | [16](16-scheduling/README.md) |
| **NodePort** | a Service type that also opens a port (30000–32767) on every node | [10](10-services/README.md) |
| **OOMKilled** | the container exceeded its memory limit and the kernel killed it (exit code 137) | [15](15-resources/README.md) |
| **PersistentVolume (PV)** | a piece of storage in the cluster, created by an administrator or a provisioner | [13](13-storage/README.md) |
| **PersistentVolumeClaim (PVC)** | a Pod's request for storage; bound to a PV | [13](13-storage/README.md) |
| **Pod** | the smallest deployable unit: one or more containers sharing network and storage | [06](06-pods/README.md) |
| **RBAC** | role-based access control: Roles (what) bound to users or ServiceAccounts (who) | [24](24-rbac/README.md) |
| **Reconciliation** | the control loop "observe → compare with desired state → act", the core of Kubernetes | [01](01-kubernetes-introduction/README.md) |
| **ReplicaSet** | keeps N identical Pods running; normally managed by a Deployment | [08](08-replicasets/README.md) |
| **Role / RoleBinding** | permissions inside one namespace, and their assignment to a user, group or ServiceAccount | [24](24-rbac/README.md) |
| **Rolling update / rollback** | replacing Pods gradually with a new version / returning to a previous revision | [09](09-deployments/README.md) |
| **Scheduler** | picks a node for each new Pod, based on resources, selectors, taints and more | [02](02-architecture/README.md) |
| **Secret** | sensitive configuration (passwords, tokens); base64-encoded, **not** encrypted by default | [12](12-secrets/README.md) |
| **Service** | a stable name and virtual IP in front of a changing set of Pods | [10](10-services/README.md) |
| **ServiceAccount** | the identity of a workload (Pod) when it talks to the Kubernetes API | [23](23-serviceaccounts/README.md) |
| **Sidecar** | a helper container in the same Pod as the application (log shipper, proxy) | [06](06-pods/README.md) |
| **StatefulSet** | like a Deployment, but with stable Pod names, ordered start and one volume per Pod | [19](19-statefulsets/README.md) |
| **StorageClass** | a kind of storage and the provisioner that creates PVs for PVCs on demand | [13](13-storage/README.md) |
| **Taint / toleration** | a node repels Pods (taint) unless a Pod accepts it (toleration) | [16](16-scheduling/README.md) |
| **Static Pod** | a Pod the kubelet runs from a file on its node; how the control plane starts itself | [02](02-architecture/README.md) |
