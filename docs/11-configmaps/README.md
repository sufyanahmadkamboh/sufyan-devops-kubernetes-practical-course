# 11 · ConfigMaps

> Level 6 · Configuration · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **ConfigMap** is a Kubernetes object that holds configuration as key–value pairs: a greeting, a log level, a whole
configuration file. Pods read it as **environment variables** or as **files** mounted into the container. The image
stays the same; only the ConfigMap changes between environments.

An analogy: the image is a printed book, the ConfigMap is the sticky note you put inside the cover ("today's special:
soup"). Changing the note does not mean printing a new book.

## Why do we need it?

If configuration lives inside the image, every change (a URL, a feature switch, a log level) needs a new build, and the
same image cannot run in `dev` and `prod` with different settings. The twelve-factor rule "store config in the
environment" is what ConfigMaps implement in Kubernetes: build once, configure per environment.

## How does it work?

```text
ConfigMap backend-config            Pod
  MESSAGE:   "Hello from…"   ──env──▶  $MESSAGE, $LOG_LEVEL          (read once, when the container starts)
  LOG_LEVEL: "debug"

ConfigMap frontend-files            Pod
  index.html:   "<!doctype…" ──volume──▶ /usr/share/nginx/html/index.html   (files; updated in place after a change)
  default.conf: "server {…"  ──volume──▶ /etc/nginx/conf.d/default.conf
```

- **As environment variables** (`env.valueFrom.configMapKeyRef` for one key, `envFrom.configMapRef` for all keys): the
  values are copied when the container starts. A later change to the ConfigMap is **not** seen until the Pod restarts.
- **As files** (a `configMap` volume): every key becomes a file. The kubelet updates the files when the ConfigMap
  changes (within about a minute), but the application must reread them.
- A ConfigMap lives in a namespace, and the Pod must be in the same namespace. Size limit: 1 MiB. Not for secrets:
  that is lesson 12.

## Architecture

```text
                 ┌─────────────────────┐
                 │ ConfigMap           │
                 │  backend-config     │
                 └──────────┬──────────┘
            env (at start)  │   volume (files, kept up to date)
              ┌─────────────┴──────────────┐
              ▼                            ▼
      ┌──────────────┐             ┌──────────────┐
      │ backend Pod  │             │ frontend Pod │
      │ $MESSAGE     │             │ index.html   │
      │ $LOG_LEVEL   │             │ default.conf │
      └──────────────┘             └──────────────┘
```

## YAML

The ConfigMap:

<!-- test: contains=kind: ConfigMap -->
```bash
cat manifests/configmaps/configmaps-backend-config.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: v1`, `kind: ConfigMap` | a core-API ConfigMap |
| `metadata.name` | the name Pods refer to |
| `data` | the key–value pairs; values are always strings (quote numbers and `true`) |

The backend Deployment that reads it:

<!-- test: contains=configMapKeyRef -->
```bash
cat manifests/configmaps/configmaps-backend-deployment.yaml
```

| Field | Meaning |
|---|---|
| `env[].valueFrom.configMapKeyRef` | one variable (`MESSAGE`) from one key (`MESSAGE`) of the ConfigMap `backend-config` |
| `envFrom[].configMapRef` | every key of the ConfigMap becomes a variable of the same name |

The frontend's files:

<!-- test: contains=default.conf -->
```bash
cat manifests/configmaps/configmaps-frontend-config.yaml manifests/configmaps/configmaps-frontend-pod.yaml
```

| Field | Meaning |
|---|---|
| `data.index.html: \|` | a multi-line value (YAML `\|` keeps the line breaks): a whole file |
| `volumes[].configMap.name` | a volume made from the ConfigMap |
| `items[].key` / `items[].path` | which key becomes which file name (without `items`, every key becomes a file) |
| `volumeMounts[].mountPath` | the folder the files appear in, inside the container |

## Hands-On Lab

**1. A namespace, the ConfigMaps and the Pods:**

<!-- test: contains=configmap/backend-config created; contains=pod/frontend created -->
```bash
kubectl create namespace config-lab
kubectl apply -n config-lab -f manifests/configmaps/configmaps-backend-config.yaml \
  -f manifests/configmaps/configmaps-backend-deployment.yaml \
  -f manifests/configmaps/configmaps-frontend-config.yaml \
  -f manifests/configmaps/configmaps-frontend-pod.yaml
kubectl rollout status deployment/backend -n config-lab --timeout=120s
kubectl wait --for=condition=Ready pod/frontend -n config-lab --timeout=120s
```

**2. A client Pod** to call the others from inside the cluster (`sleep` keeps it running; `exec` runs commands in it):

<!-- test: contains=condition met -->
```bash
kubectl run client -n config-lab --image=busybox:1.37 -- sleep 3600
kubectl wait --for=condition=Ready pod/client -n config-lab --timeout=120s
```

**3. The backend reports the configuration it received** (its `/api/config` endpoint):

<!-- test: contains=Hello from a ConfigMap; contains="log_level":"debug"; output -->
```bash
backend_ip=$(kubectl get pod -n config-lab -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n config-lab client -- wget -qO- -T 5 "http://$backend_ip:8080/api/config"
```

```text
{"db_host":"(none)","db_password":"not set","log_level":"debug","message":"Hello from a ConfigMap"}
```

**4. The frontend serves the page from the ConfigMap:**

<!-- test: contains=Served from a ConfigMap; output -->
```bash
frontend_ip=$(kubectl get pod frontend -n config-lab -o jsonpath='{.status.podIP}')
kubectl exec -n config-lab client -- wget -qO- -T 5 "http://$frontend_ip/"
```

```text
<!doctype html>
<html><head><title>Learning app</title></head>
<body><h1>Served from a ConfigMap</h1></body></html>
```

## Expected Result

The backend says `Hello from a ConfigMap` with log level `debug`, values it never had in its image; the frontend
serves the HTML page and uses the Nginx configuration from the ConfigMap `frontend-files`.

## Inspect

<!-- test: contains=MESSAGE; contains=backend-config -->
```bash
kubectl get configmap -n config-lab
kubectl describe configmap backend-config -n config-lab
```

The variables inside the backend container, and the mounted files inside the frontend:

<!-- test: contains=backend-config; contains=default.conf -->
```bash
kubectl get pod -n config-lab -l app=backend -o jsonpath='{.items[0].spec.containers[0].envFrom}{"\n"}'
kubectl exec -n config-lab frontend -- ls /usr/share/nginx/html /etc/nginx/conf.d
kubectl exec -n config-lab frontend -- head -3 /etc/nginx/conf.d/default.conf
```

(The backend image has no shell, so `env` cannot run inside it: the Pod spec and the ConfigMap show what it got.)

## Experiment

Create a ConfigMap from the command line instead of a file, and see the YAML kubectl would send:

<!-- test: contains=COLOR: blue -->
```bash
kubectl create configmap colors -n config-lab --from-literal=COLOR=blue --dry-run=client -o yaml
```

Now change the backend's message and watch when the change arrives:

<!-- test: contains=Hello from a ConfigMap -->
```bash
kubectl patch configmap backend-config -n config-lab --type=merge -p '{"data":{"MESSAGE":"Changed in the ConfigMap"}}'
backend_ip=$(kubectl get pod -n config-lab -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n config-lab client -- wget -qO- -T 5 "http://$backend_ip:8080/api/config"
```

Still the old message: environment variables are copied when the container starts. Restart the Pods so they read the
ConfigMap again:

<!-- test: contains=Changed in the ConfigMap; output -->
```bash
kubectl rollout restart deployment/backend -n config-lab
kubectl rollout status deployment/backend -n config-lab --timeout=120s
backend_ip=$(kubectl get pod -n config-lab -l app=backend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].status.podIP}')
kubectl exec -n config-lab client -- wget -qO- -T 5 "http://$backend_ip:8080/api/config"
```

```text
deployment.apps/backend restarted
Waiting for deployment "backend" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "backend" rollout to finish: 1 old replicas are pending termination...
deployment "backend" successfully rolled out
{"db_host":"(none)","db_password":"not set","log_level":"debug","message":"Changed in the ConfigMap"}
```

## Break It

A Pod that asks for a key the ConfigMap does not have (`GREETING` instead of `MESSAGE`):

<!-- test: contains=pod/greeter created -->
```bash
kubectl create configmap greeter-config -n config-lab --from-literal=MESSAGE=hi
kubectl run greeter -n config-lab --image=learning-app/backend:1.0.0 --restart=Never --overrides='
{"spec":{"containers":[{"name":"greeter","image":"learning-app/backend:1.0.0",
 "env":[{"name":"MESSAGE","valueFrom":{"configMapKeyRef":{"name":"greeter-config","key":"GREETING"}}}]}]}}'
```

<!-- test: retry=10; contains=CreateContainerConfigError; output -->
```bash
kubectl get pod greeter -n config-lab
```

```text
NAME      READY   STATUS                       RESTARTS   AGE
greeter   0/1     CreateContainerConfigError   0          2s
```

## Troubleshoot It

*What should happen?* The Pod runs. *What happened?* `CreateContainerConfigError`: the kubelet could not build the
container's configuration, so the container was never created (no logs to read). *Which object controls it?* The Pod
spec and the ConfigMap it refers to. The events say exactly what is missing:

<!-- test: retry=5; contains=couldn't find key GREETING; output -->
```bash
kubectl describe pod greeter -n config-lab | grep "couldn't find key" | tail -1
```

```text
  Warning  Failed     1s (x3 over 2s)  kubelet            spec.containers{greeter}: Error: couldn't find key GREETING in ConfigMap config-lab/greeter-config
```

Compare with the keys the ConfigMap really has:

<!-- test: contains=MESSAGE -->
```bash
kubectl get configmap greeter-config -n config-lab -o jsonpath='{.data}{"\n"}'
```

Root cause: the Pod refers to key `GREETING`; the ConfigMap only has `MESSAGE`.

## Fix It

Add the missing key (or correct the reference in the Pod). The kubelet retries on its own, and the Pod starts:

<!-- test: contains=Running; retry=15 -->
```bash
kubectl patch configmap greeter-config -n config-lab --type=merge -p '{"data":{"GREETING":"hi"}}' > /dev/null
kubectl get pod greeter -n config-lab
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Key name differs between Pod and ConfigMap | `CreateContainerConfigError`, `couldn't find key` | `kubectl get cm NAME -o jsonpath='{.data}'` and compare |
| ConfigMap in another namespace | `configmap "x" not found` | create it in the Pod's namespace |
| Expecting env vars to update | the old value stays | `kubectl rollout restart deployment/NAME` |
| Mounting a volume over a folder the image needs | the image's other files in that folder disappear | mount single files with `items` into an empty folder, or use `subPath` |
| Putting passwords in a ConfigMap | anyone who can read ConfigMaps sees them | Secrets (lesson 12) |

## Best Practices

- One ConfigMap per application (and per environment); name it after the application.
- Prefer files for whole configuration files, variables for single values.
- Apply ConfigMaps from version-controlled files, and restart the Deployment as part of the same change.

## Challenge

**Task:** run the backend with the message `Hello from dev` and log level `warn`, both from a new ConfigMap
`backend-dev`, created with one `kubectl create configmap` command.

**Requirements:** one Deployment `backend-dev` (image `learning-app/backend:1.0.0`) using `envFrom`; prove the values
with the backend's `/api/config`.

**Hints:** `--from-literal` can be repeated; `kubectl create deployment --dry-run=client -o yaml` gives you a starting
file; add `envFrom` under the container.

**Expected Result:** `/api/config` shows `"log_level":"warn"` and `"message":"Hello from dev"`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=Hello from dev; contains="log_level":"warn" -->
```bash
kubectl create configmap backend-dev -n config-lab --from-literal=MESSAGE='Hello from dev' --from-literal=LOG_LEVEL=warn
kubectl create deployment backend-dev -n config-lab --image=learning-app/backend:1.0.0 --dry-run=client -o yaml > backend-dev.yaml
kubectl apply -n config-lab -f backend-dev.yaml
kubectl set env deployment/backend-dev -n config-lab --from=configmap/backend-dev
kubectl rollout status deployment/backend-dev -n config-lab --timeout=120s
ip=$(kubectl get pod -n config-lab -l app=backend-dev --field-selector=status.phase=Running -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n config-lab client -- wget -qO- -T 5 "http://$ip:8080/api/config"
rm backend-dev.yaml
```

</details>

`kubectl set env --from=configmap/NAME` adds one `valueFrom` entry per key to the Deployment and triggers a new
rollout, so the Pods start with the values. Writing `envFrom` into the YAML by hand gives the same result and is
better for files you keep.

## Key Takeaways

- ConfigMaps keep configuration out of images: the same image runs everywhere with different settings.
- As variables: copied at container start (restart to pick up changes). As files: kept up to date by the kubelet.
- A wrong key or name gives `CreateContainerConfigError`; `kubectl describe pod` names the missing key.
- Real-world use: URLs of other services, feature switches, log levels and whole configuration files (Nginx,
  application YAML) for every service of a company, per environment.

## Cleanup

🧹 Delete the namespace `config-lab`: the ConfigMaps, the backend and frontend Pods, the client and the broken Pod:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace config-lab
```

Next: [12 · Secrets](../12-secrets/README.md)
