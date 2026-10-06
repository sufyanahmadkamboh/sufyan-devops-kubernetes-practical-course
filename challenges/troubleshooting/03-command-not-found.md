# Troubleshooting challenge 03 · The container never starts

> After lessons 06 and 27 · ⏱ 10 minutes · run every command from the course folder · cluster: minikube

Set up the broken toolbox:

<!-- test: contains=created -->
```bash
kubectl create namespace tchallenge-03
kubectl apply -f challenges/troubleshooting/manifests/03-command.yaml -n tchallenge-03
```

## Task

The toolbox Pod never runs. `kubectl logs` shows nothing. Find the cause and fix it.

## Requirements

- The toolbox Pod is `Running` with 0 new restarts.
- Fix the Deployment, not the image.

## Hints

- When logs are empty, the container may never have started at all: read the Pod's status and events.
- Exit code 127 / 128 and the words "executable file not found" point at the **command**.

## Expected Result

```text
NAME                       READY   STATUS    RESTARTS   AGE
toolbox-…                  1/1     Running   0          …
```

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=executable file not found; retry=30; output -->
```bash
kubectl describe pod -n tchallenge-03 -l app=toolbox | grep -m1 'executable file not found'
```

```text
  Warning  Failed     1s    kubelet            spec.containers{toolbox}: Error: failed to create containerd task: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: exec: "slep": executable file not found in $PATH
```

<!-- test: contains=Running -->
```bash
kubectl patch deployment toolbox -n tchallenge-03 --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command/0","value":"sleep"}]'
kubectl rollout status deployment/toolbox -n tchallenge-03 --timeout=120s > /dev/null
kubectl get pods -n tchallenge-03
```

</details>

## Explanation

The command is `slep`, a typo: the container runtime cannot find such a program in the image, so the container is
never created and there is nothing to log. The event quotes the exact program name. The status for this case is
`RunContainerError` or `StartError`, then `CrashLoopBackOff` as the kubelet keeps retrying.

## Cleanup

🧹 Delete the namespace `tchallenge-03`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace tchallenge-03
```
