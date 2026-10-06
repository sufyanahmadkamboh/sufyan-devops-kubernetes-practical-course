# Troubleshooting challenge 05 · Only half of the replicas

> After lessons 05, 08 and 27 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

Set up the team's namespace and its web Deployment:

<!-- test: contains=created -->
```bash
kubectl create namespace tchallenge-05
kubectl apply -f challenges/troubleshooting/manifests/05-quota.yaml -n tchallenge-05
sleep 10
```

## Task

The Deployment asks for 4 replicas, but only 2 Pods exist, and no Pod is `Pending` or failing. Find out what stops
the other two, and get all 4 running.

## Requirements

- `kubectl get deployment web -n tchallenge-05` shows `4/4`.
- Explain which object limited the Pods.

## Hints

- If no Pod is failing, look at the object that **creates** the Pods: the ReplicaSet, and its events.
- Namespaces can have limits of their own (`kubectl get resourcequota`).

## Expected Result

```text
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    4/4     4            4           …
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=exceeded quota; output -->
```bash
kubectl get deployment web -n tchallenge-05
kubectl describe replicaset -n tchallenge-05 -l app=web | grep -m1 'exceeded quota'
```

```text
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    2/4     2            2           11s
  Warning  FailedCreate      11s               replicaset-controller  Error creating: pods "web-75fbf879df-7hkms" is forbidden: exceeded quota: team-quota, requested: pods=1, used: pods=2, limited: pods=2
```

<!-- test: contains=4/4 -->
```bash
kubectl patch resourcequota team-quota -n tchallenge-05 -p '{"spec":{"hard":{"pods":"6"}}}'
for i in $(seq 1 30); do [ "$(kubectl get deployment web -n tchallenge-05 -o jsonpath='{.status.readyReplicas}')" = 4 ] && break; sleep 3; done
kubectl get deployment web -n tchallenge-05
```

</details>

## Explanation

A **ResourceQuota** caps what a namespace may use: here at most 2 Pods. The ReplicaSet tried to create Pods 3 and 4
and the API server refused them, so they never existed; that is why no Pod looked broken. The refusal is an event on
the ReplicaSet (`FailedCreate … exceeded quota`). Raising the quota (or asking whoever owns it) lets the ReplicaSet
create the missing Pods on its next retry. Quotas are how cluster administrators share a cluster between teams.

## Cleanup

🧹 Delete the namespace `tchallenge-05` (Deployment and quota):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace tchallenge-05
```
