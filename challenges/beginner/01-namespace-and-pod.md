# Beginner challenge 01 · A Pod in its own namespace

> After lessons 05–06 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

## Task

Create a namespace `challenge-01` and, inside it, a Pod `greeter` from a YAML manifest you write yourself. The Pod
runs `busybox:1.37` and prints `hello from challenge 01` once, then stays alive.

## Requirements

- The Pod is described in YAML (applied with `kubectl apply`), not created with `kubectl run`.
- The Pod carries the label `challenge: "01"`.
- `kubectl logs greeter -n challenge-01` prints the greeting.
- The Pod is `Running`, with 0 restarts.

## Hints

- A container that should stay alive needs a command that does not end: `sleep 3600` after the `echo`.
- In YAML, a label value made only of digits must be quoted (`"01"`), because labels are strings.
- `kubectl apply -f - <<'EOF' … EOF` reads a manifest from the terminal.

## Expected Result

```text
NAME      READY   STATUS    RESTARTS   AGE
greeter   1/1     Running   0          …
hello from challenge 01
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=hello from challenge 01; contains=Running -->
```bash
kubectl create namespace challenge-01
kubectl apply -n challenge-01 -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: greeter
  labels:
    challenge: "01"
spec:
  containers:
    - name: greeter
      image: busybox:1.37
      command: ["sh", "-c", "echo 'hello from challenge 01'; sleep 3600"]
EOF
kubectl wait --for=condition=Ready pod/greeter -n challenge-01 --timeout=120s > /dev/null
kubectl get pod greeter -n challenge-01
kubectl logs greeter -n challenge-01
```

🧹 Clean up (deletes the namespace `challenge-01` and the Pod):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-01
```

</details>

## Explanation

`command` replaces the image's default command; `sh -c` runs a small script: print, then sleep, so the main process
keeps running and the Pod stays `Running`. Without the `sleep` the container would exit with 0, the Pod would show
`Completed`, then be restarted again and again (`CrashLoopBackOff`), because a Pod's `restartPolicy` is `Always`.
