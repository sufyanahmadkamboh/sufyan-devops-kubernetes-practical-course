# Troubleshooting challenges

Six broken setups without the answer next to them. Each file starts with a **Setup** block that creates the broken
objects in their own namespace (`tchallenge-NN`), then gives you the task, requirements and hints. Try to solve it with
the method of [lesson 27](../../docs/27-troubleshooting/README.md) before you open the solution.

| # | Symptom | Challenge |
|---|---|---|
| 01 | the Service has endpoints, but connections are refused | [The Service has endpoints, but refuses](01-service-target-port.md) |
| 02 | restarts every few seconds, clean logs | [Restarts every few seconds](02-liveness-restarts.md) |
| 03 | never starts, empty logs | [The container never starts](03-command-not-found.md) |
| 04 | a Job ends `Failed` | [The export Job gives up](04-job-backoff.md) |
| 05 | fewer Pods than replicas, none failing | [Only half of the replicas](05-quota-exceeded.md) |
| 06 | `Pending` on an idle node | [Pending on an empty cluster](06-node-selector.md) |

More guided practice: the fourteen problems of [lab 12](../../labs/12-troubleshooting/README.md).
