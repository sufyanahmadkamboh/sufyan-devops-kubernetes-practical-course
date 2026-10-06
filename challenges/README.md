# Challenges

Each challenge gives you a task, requirements and hints; the solution is folded away under the task. Try first, look
afterwards. Every solution is tested on the course cluster.

## Beginner (after levels 1–5)

| # | Challenge | Practises |
|---|---|---|
| 01 | [A Pod in its own namespace](beginner/01-namespace-and-pod.md) | namespaces, Pods |
| 02 | [Find Pods by their labels](beginner/02-labels-and-selectors.md) | labels, selectors |
| 03 | [A well-formed Deployment](beginner/03-deployment.md) | Deployments, requests, limits, readiness |
| 04 | [Release, notice, roll back](beginner/04-rolling-update-and-rollback.md) | rolling updates, rollbacks |
| 05 | [Expose the backend and call it by name](beginner/05-service-discovery.md) | Services, DNS |

## Intermediate (after levels 6–13)

| # | Challenge | Practises |
|---|---|---|
| 01 | [Configure the backend from a ConfigMap and a Secret](intermediate/01-config-and-secret.md) | ConfigMaps, Secrets |
| 02 | [A database that keeps its data](intermediate/02-persistent-database.md) | PVCs, storage |
| 03 | [Health checks for a slow backend](intermediate/03-probes.md) | startup, liveness, readiness probes |
| 04 | [A guaranteed Pod on a labelled node](intermediate/04-resources-and-scheduling.md) | requests, limits, scheduling |
| 05 | [A nightly report, tested now](intermediate/05-cronjob.md) | CronJobs, Jobs |
| 06 | [Two applications behind one host name](intermediate/06-ingress-paths.md) | Ingress |
| 07 | [Only the API may reach the cache](intermediate/07-networkpolicy.md) | NetworkPolicies |
| 08 | [A read-only identity for a dashboard](intermediate/08-rbac-serviceaccount.md) | ServiceAccounts, RBAC |

## Troubleshooting (after level 15)

| # | Challenge | The symptom |
|---|---|---|
| 01 | [The Service has endpoints, but refuses](troubleshooting/01-service-target-port.md) | connection refused |
| 02 | [Restarts every few seconds](troubleshooting/02-liveness-restarts.md) | restart count climbing |
| 03 | [The container never starts](troubleshooting/03-command-not-found.md) | `RunContainerError` |
| 04 | [The export Job gives up](troubleshooting/04-job-backoff.md) | `BackoffLimitExceeded` |
| 05 | [Only half of the replicas](troubleshooting/05-quota-exceeded.md) | a Deployment short of Pods |
| 06 | [Pending on an empty cluster](troubleshooting/06-node-selector.md) | `FailedScheduling` |

The [troubleshooting challenges' own README](troubleshooting/README.md) explains how to start each broken setup.
