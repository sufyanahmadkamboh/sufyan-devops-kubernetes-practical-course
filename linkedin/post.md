Most Kubernetes tutorials show you a YAML file and "kubectl apply". Then real work begins: a Pod stuck in Pending, a rollout that never finishes, a Service with no endpoints, a database that lost its data, a NetworkPolicy that blocks the one call you needed. So I built a free, hands-on Kubernetes course that teaches exactly those moments. ☸️👇

Think of Kubernetes as a restaurant manager: you write the order on the wall ("three cooks on the grill, always"), and the manager keeps it true, replacing a cook who goes home and opening more stations when it gets busy. Every lesson writes one kind of order, watches the manager follow it, then breaks it on purpose so you learn to read the manager's notes (the events) when something goes wrong.

That is the "Kubernetes Practical Course: Kubernetes From Zero to Practical":

📚 29 lessons on a local Minikube cluster: architecture, kubectl, namespaces, Pods, labels, ReplicaSets, Deployments, Services and DNS, ConfigMaps, Secrets, storage, probes, requests and limits, scheduling, Jobs, CronJobs, DaemonSets, StatefulSets, Ingress, NetworkPolicies, ServiceAccounts, RBAC, scaling, the HPA and Helm
🧯 a troubleshooting lab with 14 broken clusters (Pending, CrashLoopBackOff, ImagePullBackOff, OOMKilled, DNS, a stuck rollout, a blocking NetworkPolicy…): Problem → Symptoms → First command → Investigation → Root cause → Fix → Verification
🏗️ a capstone: Ingress → frontend → backend → PostgreSQL on a PVC, with probes, limits, an HPA, a backup CronJob, NetworkPolicies, ServiceAccounts and RBAC; then broken six ways and fixed

Every lesson follows the same path: Theory → Visual → YAML → kubectl → Deploy → Inspect → Experiment → Break it → Troubleshoot → Fix.

Things I learned while building and testing it:
🔹 a PVC that a finished Job's Pod still uses cannot be deleted: it waits in Terminating forever (pvc-protection)
🔹 runAsNonRoot fails with CreateContainerConfigError when the image's user is a name instead of a number
🔹 with the Docker driver, a Minikube node reports the host's CPUs and memory, not the --cpus and --memory you gave it
🔹 a readiness probe's default timeout is 1 second: an endpoint that checks a database can fail it while being healthy
🔹 Minikube's default network plugin ignores NetworkPolicies; the course starts the cluster with Calico so they are enforced

✅ Every lesson is also a test: __BLOCKS__ code blocks run automatically in GitHub Actions on a fresh Minikube cluster, and the outputs in the lessons are the real outputs. No cloud account, nothing to pay.

Also included: 13 hands-on labs, 19 challenges at three levels with hidden solutions, a Helm chart with values per environment, a __VIDEOS__-video series (__DURATION__ in total, full and silent versions), a __PAGES__-page study guide PDF, 13 diagrams, a glossary and 22 interview questions.

🔗 Repository: https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course
🌐 All my projects: https://sufyanahmadkamboh.github.io/

Which Kubernetes error cost you the most time? 💬

#Kubernetes #K8s #DevOps #CloudNative #Helm #PlatformEngineering #Containers #LearningDevOps #OpenSource
