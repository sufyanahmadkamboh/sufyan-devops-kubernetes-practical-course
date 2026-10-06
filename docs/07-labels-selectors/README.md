# 07 · Labels, selectors and annotations

> Level 3 · Pods · ⏱ 30 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **label** is a key/value tag on an object: `app: web`, `environment: dev`, `tier: frontend`. A **selector** is a
question about labels: "all objects with `app=web` and `environment=prod`". An **annotation** is also a key/value pair,
but for information meant for people and tools, never for selecting (a description, a contact, a build number).

Analogy: labels are the coloured stickers on moving boxes ("kitchen", "fragile"); a selector is "bring me every box
with a kitchen sticker". Annotations are the notes written on the box: useful to read, never used to sort.

## Why do we need it?

This is the **most important idea for understanding how Kubernetes connects things**. Kubernetes objects do not
point at each other by name: a ReplicaSet does not keep a list of "its" Pods, a Service does not list "its" Pods. They
hold a **selector**, and whatever currently carries matching labels belongs to them. New Pods with the right labels
are picked up automatically; a Pod whose labels change drops out. Lessons 08, 09, 10, 22 and 24 all depend on it.

## How does it work?

```text
Labels           →   Selectors          →   matching objects
app=web               app=web                  web-dev, web-prod
environment=dev       environment in (dev)     web-dev, api-dev
tier=frontend         tier!=backend            web-dev, web-prod
```

- **Equality-based:** `app=web`, `environment!=prod`.
- **Set-based:** `environment in (dev,test)`, `tier notin (backend)`, `app` (has the key), `!app` (has not).
- Several conditions separated by commas must **all** match (AND).
- Keys may have a prefix (`app.kubernetes.io/name`); values are short strings (63 characters, letters, digits, `-`,
  `_`, `.`).

## Architecture

```text
   Service / ReplicaSet / NetworkPolicy
          selector: app=web
                │  "who matches?" (asked continuously)
     ┌──────────┼───────────────┐
     ▼          ▼               ✕
  Pod web-dev  Pod web-prod   Pod api-dev
  app=web      app=web        app=api
```

## YAML

<!-- test: contains=environment: dev -->
```bash
cat manifests/pods/07-labelled-pods.yaml
```

| Field | Meaning |
|---|---|
| `metadata.labels` | a map of key: value labels; here `app`, `environment`, `tier` |
| `{app: web, environment: dev}` | YAML "flow style": the same map written on one line |
| `metadata.annotations` | free-form information: `team`, `description`; never selected on |

## Hands-On Lab

<!-- test: contains=created -->
```bash
kubectl create namespace labels-lab
kubectl apply -f manifests/pods/07-labelled-pods.yaml -n labels-lab
kubectl wait --for=condition=Ready pods --all -n labels-lab --timeout=120s > /dev/null
```

**1. See the labels:**

<!-- test: contains=environment=dev; output -->
```bash
kubectl get pods -n labels-lab --show-labels
```

```text
NAME       READY   STATUS    RESTARTS   AGE   LABELS
api-dev    1/1     Running   0          2s    app=api,environment=dev,tier=backend
api-prod   1/1     Running   0          2s    app=api,environment=prod,tier=backend
web-dev    1/1     Running   0          2s    app=web,environment=dev,tier=frontend
web-prod   1/1     Running   0          2s    app=web,environment=prod,tier=frontend
```

`-L key` shows chosen labels as columns:

<!-- test: contains=TIER -->
```bash
kubectl get pods -n labels-lab -L environment,tier
```

**2. Select with equality:**

<!-- test: contains=web-prod; absent=api-prod; output -->
```bash
kubectl get pods -n labels-lab -l app=web,environment=prod
```

```text
NAME       READY   STATUS    RESTARTS   AGE
web-prod   1/1     Running   0          2s
```

**3. Select with sets:**

<!-- test: contains=api-dev; absent=prod -->
```bash
kubectl get pods -n labels-lab -l 'environment in (dev,test)'
kubectl get pods -n labels-lab -l 'tier notin (frontend),environment=dev'
```

**4. Change labels on a running object:**

<!-- test: contains=web-dev -->
```bash
kubectl label pod web-dev -n labels-lab release=canary
kubectl get pods -n labels-lab -l release=canary
kubectl label pod web-dev -n labels-lab release-
```

`release-` (a key followed by `-`) removes the label.

**5. Annotations:**

<!-- test: contains=web-team@example.com -->
```bash
kubectl annotate pod web-prod -n labels-lab description="nginx for production"
kubectl get pod web-dev -n labels-lab -o jsonpath='{.metadata.annotations.team}{"\n"}'
kubectl describe pod web-prod -n labels-lab | grep -A1 Annotations
```

## Expected Result

Four Pods; selectors return exactly the matching subset; labels and annotations can be added and removed on running
Pods.

## Inspect

The same selectors work for every kind and for deletion, which makes them powerful and dangerous:

<!-- test: contains=web-dev -->
```bash
kubectl get pods -n labels-lab -l tier=frontend -o name
kubectl delete pods -n labels-lab -l tier=frontend --dry-run=client
```

`--dry-run=client` shows what *would* be deleted, without deleting: always check a label-based delete this way first.

## Experiment

Kubernetes itself labels objects. Look at the control plane's labels, and select them:

<!-- test: contains=kube-apiserver -->
```bash
kubectl get pods -n kube-system -l tier=control-plane -L component
```

These are the labels lesson 02's challenge used.

## Break It

Look for the web Pods with a small typo in the value:

<!-- test: contains=No resources found; output -->
```bash
kubectl get pods -n labels-lab -l app=Web 2>&1
```

```text
No resources found in labels-lab namespace.
```

## Troubleshoot It

*What should happen?* Two `web` Pods. *What happened?* `No resources found`, with no error: a selector that matches
nothing is not an error, it is an empty answer. This is the silent failure behind many broken Services (lesson 10).
Compare the selector with the real labels:

<!-- test: contains=app=web -->
```bash
kubectl get pods -n labels-lab --show-labels | grep -o 'app=[a-z]*' | sort -u
```

Root cause: label values are **case-sensitive**; `Web` is not `web`.

## Fix It

<!-- test: contains=web-dev; contains=web-prod -->
```bash
kubectl get pods -n labels-lab -l app=web
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Typo or wrong case in a label | selector finds nothing, silently | compare with `--show-labels` |
| Using annotations to select | selectors ignore annotations | labels for selecting, annotations for information |
| Label-based delete without checking | more Pods deleted than intended | `--dry-run=client` first |
| Too many ad-hoc labels | nobody knows which ones matter | agree on a few: `app`, `environment`, `tier`, or the `app.kubernetes.io/*` recommended labels |

## Best Practices

- Use the recommended labels for applications: `app.kubernetes.io/name`, `app.kubernetes.io/instance`,
  `app.kubernetes.io/version`, `app.kubernetes.io/part-of`.
- Keep selector labels stable (what *is* the app), and put changing information (versions, build IDs) in labels you
  never select on, or in annotations.

## Challenge

**Task:** in `labels-lab`, list the Pods that are **not** in production and are **not** frontend, then label every
backend Pod with `owner=api-team` in one command.

**Requirements:** selectors only, no Pod names in the commands.

**Hints:** `environment!=prod`, `tier!=frontend`; `kubectl label pods -l SELECTOR KEY=VALUE`.

**Expected Result:** first command: `api-dev`; afterwards `kubectl get pods -l owner=api-team` lists `api-dev` and
`api-prod`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=api-prod; contains=api-dev -->
```bash
kubectl get pods -n labels-lab -l 'environment!=prod,tier!=frontend'
kubectl label pods -n labels-lab -l tier=backend owner=api-team
kubectl get pods -n labels-lab -l owner=api-team
```

</details>

Commas mean AND. Labelling (or deleting, or scaling) "everything that matches" is how operations are done on many
objects at once.

## Key Takeaways

- Labels tag objects; selectors find objects by labels; annotations hold information that is never selected.
- Services, ReplicaSets, Deployments and NetworkPolicies find their Pods with selectors, continuously.
- An empty selection is not an error: check labels with `--show-labels` when "nothing happens".
- Real-world use: every routing, scaling, policy and monitoring rule in Kubernetes is written as a label selector.

## Cleanup

🧹 Delete the namespace `labels-lab` and its four Pods:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace labels-lab
```

Next: [08 · ReplicaSets](../08-replicasets/README.md)
