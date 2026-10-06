# Lab 12 · Troubleshooting

> Level 14 · Troubleshooting · ⏱ 2–3 hours · run every command from the course folder · cluster: minikube

Fourteen broken setups, each one a problem you will meet on a real cluster. Every problem file creates the broken
setup in its own namespace (`trouble-NN`), shows the real symptoms, and then works through:

```text
Problem → Symptoms → First command to run → Investigation → Root cause → Fix → Verification → Lesson learned
```

Try to find the root cause **yourself** after the "First command to run", before you read the Investigation. The
method behind every investigation is in [lesson 27](../../docs/27-troubleshooting/README.md):

```text
What is broken? → What should happen? → What actually happened? → Which object controls it?
→ inspect it → events → logs → configuration → root cause → fix → verify
```

## Problems by symptom

| # | Symptom you see | Problem |
|---|---|---|
| 01 | `Pending`, `NODE <none>` | [Pod stuck in Pending](01-pod-pending.md) |
| 02 | `CrashLoopBackOff`, restarts grow | [CrashLoopBackOff](02-crashloopbackoff.md) |
| 03 | `ErrImagePull`, `ImagePullBackOff` | [ImagePullBackOff](03-imagepullbackoff.md) |
| 04 | `Completed` / `CrashLoopBackOff`, empty logs, exit code 0 | [Container exits immediately](04-container-exits-immediately.md) |
| 05 | Service: `Connection refused`, `Endpoints: <none>` | [Service cannot reach Pods](05-service-cannot-reach-pods.md) |
| 06 | `Running` but `READY 0/1` | [Readiness probe failing](06-readiness-probe-failing.md) |
| 07 | `CreateContainerConfigError: couldn't find key` | [Wrong ConfigMap](07-wrong-configmap.md) |
| 08 | `CreateContainerConfigError: secret not found` | [Wrong Secret](08-wrong-secret.md) |
| 09 | PVC and Pod `Pending` | [PVC stuck in Pending](09-pvc-pending.md) |
| 10 | Ingress answers `503` | [Ingress not working](10-ingress-not-working.md) |
| 11 | `rollout status` never finishes | [Deployment rollout stuck](11-rollout-stuck.md) |
| 12 | `OOMKilled`, exit code 137, logs stop | [Pod OOMKilled](12-oomkilled.md) |
| 13 | `bad address` | [DNS resolution failure](13-dns-failure.md) |
| 14 | a Service with endpoints times out | [NetworkPolicy blocks traffic](14-networkpolicy-blocks-traffic.md) |

The broken manifests are in [manifests/](manifests/). More practice without the answers next to the problem:
[troubleshooting challenges](../../challenges/troubleshooting/README.md).

Next: [Lab 13 · Scaling](../13-scaling/README.md)
