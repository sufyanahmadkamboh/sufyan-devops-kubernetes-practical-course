# Troubleshooting challenge 06 · Pending on an empty cluster

> After lessons 16 and 27 · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

Set up the cache:

<!-- test: contains=created -->
```bash
kubectl create namespace tchallenge-06
kubectl apply -f challenges/troubleshooting/manifests/06-node-selector.yaml -n tchallenge-06
sleep 5
```

## Task

The cache Pod stays `Pending`, although the node has plenty of free CPU and memory. Find the cause and get it running,
**without** changing the Deployment.

## Requirements

- Do not edit the Deployment; change the cluster so the Pod can be scheduled.
- The Pod is `Running`.

## Hints

- `Pending` → the `FailedScheduling` event.
- `nodeSelector` only matches nodes that carry the label (lesson 16). `kubectl get nodes --show-labels`.

## Expected Result

```text
NAME                     READY   STATUS    RESTARTS   AGE
cache-…                  1/1     Running   0          …
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=FailedScheduling; output -->
```bash
kubectl describe pod -n tchallenge-06 -l app=cache | grep -m1 FailedScheduling
```

```text
  Warning  FailedScheduling  5s    default-scheduler  0/1 nodes are available: 1 node(s) didn't match Pod's node affinity/selector. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

<!-- test: contains=Running -->
```bash
kubectl label node minikube disktype=ssd
kubectl wait --for=condition=Ready pod -n tchallenge-06 -l app=cache --timeout=120s > /dev/null
kubectl get pods -n tchallenge-06
```

</details>

## Explanation

The Deployment only accepts nodes labelled `disktype=ssd`; no node had that label, so the scheduler found no match
(`didn't match Pod's node affinity/selector`), whatever the free resources. Labelling the node told Kubernetes "this
node has an SSD". On a real cluster you would label only the nodes that really have one; removing the `nodeSelector`
would be the fix if the requirement was a mistake.

## Cleanup

🧹 Delete the namespace `tchallenge-06` and remove the label from the node (`disktype-` removes it):

<!-- test: contains=deleted -->
```bash
kubectl label node minikube disktype-
kubectl delete namespace tchallenge-06
```
