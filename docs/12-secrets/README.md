# 12 · Secrets

> Level 6 · Configuration · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **Secret** is like a ConfigMap for sensitive values: passwords, API tokens, keys, certificates. Pods read it the
same two ways, as **environment variables** or as **files**. The difference is in how Kubernetes treats it: Secrets
are kept apart from ordinary configuration, can be protected separately with RBAC (lesson 24), are not printed by
`kubectl describe`, and are only sent to nodes that run a Pod that needs them.

## Why do we need it?

A password written in an image, a Git repository or a ConfigMap is readable by everyone who can read those. Secrets
give credentials their own object, so that access to them can be limited and audited, and so that the same image can
use different credentials per environment.

> ⚠️ **A Secret is encoded, not encrypted.** Its values are stored **base64-encoded**, which anyone can decode with
> one command. Out of the box, Kubernetes also stores Secrets **unencrypted in etcd**, its database; encryption at
> rest has to be switched on by the cluster administrator. Treat read access to Secrets like access to the passwords
> themselves, and never commit Secret files with real values to Git.

## How does it work?

```text
Secret db-credentials                         Pod
  username: YXBw          (base64 of "app")   ── env ──▶  DB_USER=app, DB_PASSWORD=example-password-change-me
  password: ZXhhbXBs…     (base64)            ── volume ─▶ /etc/db/password   (a file, kept in memory on the node)
```

- `stringData` lets you write plain text in the YAML; Kubernetes encodes it into `data` when it stores the Secret.
- **As a file** (a `secret` volume) is safer than **as a variable**: variables are inherited by child processes and
  often end up in crash reports and logs. Mounted Secrets live in a memory file system (tmpfs) on the node and are
  updated when the Secret changes.
- `kubectl describe secret` shows only the sizes of the values; `kubectl get secret -o yaml` shows them encoded.

## Architecture

```text
   kubectl apply ──▶ API server ──▶ etcd  (base64; plain on disk unless encryption at rest is enabled)
                                     │
                     only to the node that runs a Pod using it
                                     ▼
                     kubelet ──▶ tmpfs /etc/db/password  +  env DB_PASSWORD  ──▶ container
```

## YAML

<!-- test: contains=kind: Secret; contains=stringData -->
```bash
cat manifests/secrets/secrets-db-credentials.yaml
```

| Field | Meaning |
|---|---|
| `kind: Secret` | a core-API Secret |
| `type: Opaque` | arbitrary key–value data (other types: `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson`…) |
| `stringData` | values in plain text, encoded by Kubernetes on save (write-only: reading back shows `data`) |
| `data` | values already base64-encoded (what `kubectl get -o yaml` shows) |

<!-- test: contains=secretKeyRef; contains=secretName -->
```bash
cat manifests/secrets/secrets-backend-deployment.yaml
```

| Field | Meaning |
|---|---|
| `env[].valueFrom.secretKeyRef` | one variable from one key of a Secret |
| `volumes[].secret.secretName` | a volume made from the Secret; `items` chooses which keys become which files |
| `volumeMounts[].readOnly: true` | the container cannot change the files |
| `DB_PASSWORD_FILE` | the backend reads the password from this file (and prefers it to `DB_PASSWORD`) |

## Hands-On Lab

**1. The namespace, the Secret and the backend:**

<!-- test: contains=secret/db-credentials created; contains=successfully rolled out -->
```bash
kubectl create namespace secrets-lab
kubectl apply -n secrets-lab -f manifests/secrets/secrets-db-credentials.yaml -f manifests/secrets/secrets-backend-deployment.yaml
kubectl rollout status deployment/backend -n secrets-lab --timeout=120s
```

**2. A client Pod**, and the backend's view of its configuration (it shows the password only as "set"):

<!-- test: contains=set (from file); output=tail:1 -->
```bash
kubectl run client -n secrets-lab --image=busybox:1.37 -- sleep 3600
kubectl wait --for=condition=Ready pod/client -n secrets-lab --timeout=120s
ip=$(kubectl get pod -n secrets-lab -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n secrets-lab client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

```text
...
{"db_host":"(none)","db_password":"set (from file)","log_level":"info","message":"Hello from the backend"}
```

## Expected Result

The backend received the password both as a variable and as the file `/etc/db/password`, and reports
`set (from file)`: it never prints the value itself.

## Inspect

`describe` hides the values:

<!-- test: contains=26 bytes; output -->
```bash
kubectl describe secret db-credentials -n secrets-lab | tail -4
```

```text
Data
====
password:  26 bytes
username:  3 bytes
```

`get -o yaml` shows them, encoded, and base64 is reversible by anyone:

<!-- test: contains=example-password-change-me -->
```bash
kubectl get secret db-credentials -n secrets-lab -o jsonpath='{.data.password}{"\n"}'
kubectl get secret db-credentials -n secrets-lab -o jsonpath='{.data.password}' | base64 -d; echo
```

Who can read Secrets therefore matters as much as who can read the passwords (lesson 24 restricts it with RBAC).

## Experiment

See with your own eyes that the Secret is stored **unencrypted** in etcd. The etcd Pod contains `etcdctl`, the
database's client; Minikube keeps etcd's certificates in `/var/lib/minikube/certs/etcd`:

<!-- test: contains=example-password-change-me; output -->
```bash
kubectl exec -n kube-system etcd-minikube -- etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/var/lib/minikube/certs/etcd/ca.crt --cert=/var/lib/minikube/certs/etcd/server.crt \
  --key=/var/lib/minikube/certs/etcd/server.key \
  get /registry/secrets/secrets-lab/db-credentials --print-value-only | grep -a -o 'example-password-change-me'
```

```text
example-password-change-me
example-password-change-me
```

The password is in the database as plain text. Production clusters enable **encryption at rest** (managed clusters
such as EKS, AKS and GKE offer it, often with a cloud key service), and many teams keep the real values out of
Kubernetes entirely, in a vault, synced in by an operator. The concepts of this lesson stay the same.

## Break It

A typo in the Secret's name (`db-credential`, without the final `s`):

<!-- test: contains=pod/broken created -->
```bash
kubectl run broken -n secrets-lab --image=learning-app/backend:1.0.0 --restart=Never --overrides='
{"spec":{"containers":[{"name":"broken","image":"learning-app/backend:1.0.0",
 "env":[{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"db-credential","key":"password"}}}]}]}}'
```

<!-- test: retry=10; contains=CreateContainerConfigError; output -->
```bash
kubectl get pod broken -n secrets-lab
```

```text
NAME     READY   STATUS                       RESTARTS   AGE
broken   0/1     CreateContainerConfigError   0          2s
```

## Troubleshoot It

*What should happen?* The Pod runs. *What happened?* `CreateContainerConfigError`: the container was never created,
so `kubectl logs` has nothing. *Which object controls it?* The Pod's reference to a Secret. The events name the
missing object:

<!-- test: retry=5; contains=not found; output -->
```bash
kubectl describe pod broken -n secrets-lab | grep 'Error:' | tail -1
```

```text
  Warning  Failed     0s (x2 over 1s)  kubelet            spec.containers{broken}: Error: secret "db-credential" not found
```

<!-- test: contains=db-credentials -->
```bash
kubectl get secrets -n secrets-lab
```

Root cause: the Pod asks for `db-credential`; the Secret is `db-credentials`.

## Fix It

A Pod's containers cannot be changed after creation: delete it and create it with the right name.

<!-- test: contains=condition met -->
```bash
kubectl delete pod broken -n secrets-lab
kubectl run fixed -n secrets-lab --image=learning-app/backend:1.0.0 --restart=Never --overrides='
{"spec":{"containers":[{"name":"fixed","image":"learning-app/backend:1.0.0",
 "env":[{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"db-credentials","key":"password"}}}]}]}}'
kubectl wait --for=condition=Ready pod/fixed -n secrets-lab --timeout=120s
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Wrong Secret name or key | `CreateContainerConfigError`, `secret "x" not found` / `couldn't find key` | compare with `kubectl get secret -n NS` |
| Base64-encoding a value twice in `data` | the application gets gibberish | use `stringData`, or `echo -n value \| base64` (no newline) |
| Committing Secret YAML with real values | the password is in Git history forever | create Secrets from a vault or CI; commit examples only |
| Thinking base64 is encryption | false sense of security | restrict access (RBAC), enable encryption at rest |
| Expecting env vars to update after a change | the old password stays | mount as a file, or restart the Pods |

## Best Practices

- Mount Secrets as files when the application can read them; avoid printing environment variables in logs.
- Restrict `get`/`list` on Secrets with RBAC to the people and ServiceAccounts that need them.
- Enable encryption at rest on real clusters; rotate credentials; keep real values out of Git.

## Challenge

**Task:** give the backend the user `reporter` and the password `example-reporter-change-me` from a new Secret
`reporter-credentials`, created with one `kubectl create secret` command, mounted as a file.

**Requirements:** a Deployment `reporter` (image `learning-app/backend:1.0.0`) with `DB_PASSWORD_FILE=/etc/reporter/password`;
the backend's `/api/config` must say `set (from file)`.

**Hints:** `kubectl create secret generic NAME --from-literal=key=value`; copy the volume part of
`secrets-backend-deployment.yaml`.

**Expected Result:** `"db_password":"set (from file)"`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=set (from file) -->
```bash
kubectl create secret generic reporter-credentials -n secrets-lab --from-literal=username=reporter --from-literal=password=example-reporter-change-me
cat > reporter.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reporter
spec:
  replicas: 1
  selector:
    matchLabels: {app: reporter}
  template:
    metadata:
      labels: {app: reporter}
    spec:
      containers:
        - name: backend
          image: learning-app/backend:1.0.0
          env:
            - name: DB_PASSWORD_FILE
              value: /etc/reporter/password
          volumeMounts:
            - name: creds
              mountPath: /etc/reporter
              readOnly: true
      volumes:
        - name: creds
          secret:
            secretName: reporter-credentials
EOF
kubectl apply -n secrets-lab -f reporter.yaml
kubectl rollout status deployment/reporter -n secrets-lab --timeout=120s
ip=$(kubectl get pod -n secrets-lab -l app=reporter -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n secrets-lab client -- wget -qO- -T 5 "http://$ip:8080/api/config"
rm reporter.yaml
```

</details>

Without `items`, every key of the Secret (`username` and `password`) becomes a file in `/etc/reporter`; the
backend reads `password`. `kubectl create secret` never writes the value into a file you might commit.

## Key Takeaways

- Secrets hold sensitive configuration; Pods read them as variables or (better) as files.
- base64 is an encoding, not encryption; Secrets are unencrypted in etcd unless encryption at rest is enabled.
- Wrong name or key → `CreateContainerConfigError`; `kubectl describe pod` names what is missing.
- Real-world use: database passwords, API tokens, TLS certificates and registry credentials of every service, often
  synced from a vault and protected by RBAC.

## Cleanup

🧹 Delete the namespace `secrets-lab`: the Secrets, the Deployments and the Pods of this lesson:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace secrets-lab
```

Next: [13 · Storage: volumes, PV, PVC and StorageClasses](../13-storage/README.md)
