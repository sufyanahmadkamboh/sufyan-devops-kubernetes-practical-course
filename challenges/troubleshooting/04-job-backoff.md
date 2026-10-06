# Troubleshooting challenge 04 · The export Job gives up

> After lessons 13, 17 and 27 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

Set up the broken Job:

<!-- test: contains=created -->
```bash
kubectl create namespace tchallenge-04
kubectl apply -f challenges/troubleshooting/manifests/04-job.yaml -n tchallenge-04
```

## Task

The nightly export Job ends as `Failed`. Find out why, fix it, and run it again until it completes.

## Requirements

- The Job named `export` reaches `Complete`.
- Its log ends with `done`.
- The export writes into a directory that the Pod can actually write to.

## Hints

- A Job keeps its failed Pods (up to `backoffLimit`): their logs are readable.
- `mkdir` cannot create a directory whose parent does not exist. Which volume type gives a Pod an empty, writable
  folder (lesson 13)?
- Most fields of a Job's Pod template cannot be changed: delete the Job and apply a fixed one.

## Expected Result

```text
NAME     STATUS     COMPLETIONS   DURATION   AGE
export   Complete   1/1           …          …
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=BackoffLimitExceeded; retry=60; timeout=300; output -->
```bash
kubectl get job export -n tchallenge-04 -o jsonpath='{.status.conditions[?(@.type=="Failed")].reason}{"\n"}'
kubectl get job export -n tchallenge-04 -o jsonpath='{.status.conditions[?(@.type=="Failed")].reason}' | grep -q BackoffLimitExceeded
```

```text
BackoffLimitExceeded
```

<!-- test: contains=No such file or directory; output -->
```bash
kubectl logs -n tchallenge-04 -l job-name=export --tail=2 | tail -2
```

```text
exporting to /exports
mkdir: can't create directory '/exports/today': No such file or directory
```

<!-- test: contains=done -->
```bash
kubectl delete job export -n tchallenge-04 > /dev/null
kubectl apply -n tchallenge-04 -f - <<'EOF'
apiVersion: batch/v1
kind: Job
metadata:
  name: export
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: export
          image: busybox:1.37
          command: ["sh", "-c", "echo 'exporting to /exports'; mkdir /exports/today && echo done"]
          volumeMounts:
            - name: exports
              mountPath: /exports
          resources:
            requests: {cpu: 10m, memory: 8Mi}
            limits: {cpu: 50m, memory: 16Mi}
      volumes:
        - name: exports
          emptyDir: {}
EOF
kubectl wait --for=condition=complete job/export -n tchallenge-04 --timeout=120s > /dev/null
kubectl get job export -n tchallenge-04
kubectl logs -n tchallenge-04 job/export
```

</details>

## Explanation

The Job retried twice (`backoffLimit: 2`), then stopped with `BackoffLimitExceeded`. Each attempt failed the same
way: `/exports` does not exist in the image, so `mkdir /exports/today` fails. Mounting a volume at `/exports` (here an
`emptyDir`; in real life a PVC so the export survives) gives the job a writable folder. Retries only help with
temporary failures; a configuration error fails every time.

## Cleanup

🧹 Delete the namespace `tchallenge-04` (the Job and its Pods):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace tchallenge-04
```
