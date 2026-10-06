# 28 · Helm

> Level 15 · Helm · ⏱ 50 minutes · run every command from the course folder · cluster: minikube

## What is it?

**Helm** is the package manager of Kubernetes. A **chart** is a folder of YAML templates plus a file of default
settings (`values.yaml`); Helm fills the templates with the values and applies the result to the cluster as one unit,
a **release**. Every change to a release is numbered (a **revision**), so you can see the history and roll back.

If raw YAML files are a recipe written out for exactly four people, a chart is the recipe with blanks: "flour:
{{ guests × 100 }} g". You write it once and cook it for 2, 4 or 40 people by changing one number.

## Why do we need it?

By now the course application is a dozen YAML files: Deployments, Services, a ConfigMap, a Secret, a PVC. Running it
in **dev** and **test** means copying all of them and changing a few values in each copy, then keeping the copies in
sync forever. Helm replaces the copies with **one chart and one small values file per environment**, installs and
upgrades everything in one command, and remembers each version for rollbacks.

```text
Raw YAML                 → many files, copied per environment, edited by hand
Helm chart + values      → one set of templates; dev, test, prod differ only in a values file
helm upgrade / rollback  → versioned releases of the whole application
```

## How does it work?

```text
helm/learning-app/                   values-dev.yaml       values-test.yaml
├── Chart.yaml        (name, version)  backend.replicas: 1   backend.replicas: 2
├── values.yaml       (defaults)       message: DEV          database.enabled: true
└── templates/        (YAML with {{ }})
        │
        ▼  helm install shop helm/learning-app -f values-dev.yaml
Helm renders the templates with: values.yaml, then the -f file, then --set (later wins)
        │
        ▼
plain Kubernetes YAML ──▶ API server  (stored as release "shop", revision 1, in a Secret in the namespace)
```

| Word | Meaning |
|---|---|
| chart | the package: templates + default values + metadata |
| values | the settings that fill the templates (`values.yaml`, `-f file`, `--set key=value`) |
| release | one installation of a chart, with a name (`shop`), in a namespace |
| revision | one version of a release: install = 1, each upgrade or rollback adds one |

## Architecture

```text
                   ┌─────────────────────────────┐
  values-dev.yaml ─┤                             │      release "shop" (namespace helm-lab)
                   │  chart helm/learning-app    ├──▶   revision 1: backend 1.0.0, 1 replica
  values-test.yaml ┤  templates + values.yaml    │      revision 2: backend 2.0.0      ← helm upgrade
                   │                             │      revision 3: = revision 1       ← helm rollback 1
                   └─────────────────────────────┘
```

## YAML

The chart's defaults, then one template. Everything in `{{ }}` is filled in by Helm:

<!-- test: contains=backend:; contains=database: -->
```bash
cat helm/learning-app/values.yaml
```

<!-- test: contains=.Values.backend.replicas -->
```bash
sed -n '1,30p' helm/learning-app/templates/backend.yaml
```

| Template expression | Meaning |
|---|---|
| `{{ .Release.Name }}-backend` | object names start with the release name, so two releases never collide |
| `{{ .Values.backend.replicas }}` | a value from values.yaml, overridable per environment |
| `{{- if .Values.database.enabled }}` … `{{- end }}` | include a block only when a value is true (the database is optional) |
| `{{- include "learning-app.labels" . \| nindent 4 }}` | reuse a block of labels defined once in `_helpers.tpl` |
| `{{ .Values.backend.message \| quote }}` | a **function** (`quote`) applied to a value |

The two environment files only list what differs from the defaults:

<!-- test: contains=Hello from DEV; contains=enabled: true -->
```bash
cat helm/learning-app/values-dev.yaml helm/learning-app/values-test.yaml
```

## Hands-On Lab

**1. Install Helm** (Windows: `winget install Helm.Helm`; macOS: `brew install helm`; Linux: the install script on
helm.sh) and check it:

<!-- test: skip -->
```bash
winget install Helm.Helm
```

<!-- test: contains=v4 -->
```bash
helm version --short
```

**2. What `helm create` gives you.** Every new chart starts from this scaffold (created here in your home folder, to
look at, not to use):

<!-- test: contains=values.yaml; contains=deployment.yaml -->
```bash
(mkdir -p ~/helm-scaffold && cd ~/helm-scaffold && helm create mychart > /dev/null && find . -type f | sort && cd ~ && rm -rf ~/helm-scaffold)
```

The course chart, `helm/learning-app`, follows the same layout with templates for the course application.

**3. Check and preview the chart** before installing anything: `lint` finds mistakes, `template` prints the YAML
Helm would apply:

<!-- test: contains=0 chart(s) failed; contains=kind: Deployment; output=tail:6 -->
```bash
helm lint helm/learning-app -f helm/learning-app/values-dev.yaml
helm template shop helm/learning-app -f helm/learning-app/values-dev.yaml | grep -E '^kind:|replicas:'
```

```text
...
kind: Service
kind: Service
kind: Deployment
  replicas: 1
kind: Deployment
  replicas: 1
```

**4. Install the dev release:**

<!-- test: contains=STATUS: deployed; timeout=300; output -->
```bash
kubectl create namespace helm-lab > /dev/null
helm install shop helm/learning-app -n helm-lab -f helm/learning-app/values-dev.yaml --wait --timeout 3m
```

```text
NAME: shop
LAST DEPLOYED: Tue Oct  6 16:52:32 2026
NAMESPACE: helm-lab
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
TEST SUITE: None
NOTES:
shop is installed in the namespace helm-lab: backend 1.0.0 x1.

Try it:
  kubectl port-forward -n helm-lab svc/shop-frontend 8080:80
```

<!-- test: contains=Hello from DEV; contains=1.0.0 -->
```bash
helm list -n helm-lab
kubectl run client -n helm-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- http://shop-backend
```

**5. Upgrade** to backend 2.0.0. `--set` overrides one value on top of the files:

<!-- test: contains=REVISION: 2; timeout=300 -->
```bash
helm upgrade shop helm/learning-app -n helm-lab -f helm/learning-app/values-dev.yaml \
  --set backend.image.tag=2.0.0 --wait --timeout 3m | grep -E 'STATUS|REVISION'
```

<!-- test: contains="version":"2.0.0" -->
```bash
kubectl run client -n helm-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- http://shop-backend
```

**6. History and rollback:**

<!-- test: contains=Rollback was a success; timeout=300 -->
```bash
helm history shop -n helm-lab
helm rollback shop 1 -n helm-lab --wait --timeout 3m
```

<!-- test: contains="version":"1.0.0"; contains=Rollback to 1; output -->
```bash
helm history shop -n helm-lab
kubectl run client -n helm-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- http://shop-backend
```

```text
REVISION	UPDATED                 	STATUS    	CHART             	APP VERSION	DESCRIPTION     
1       	Tue Oct  6 16:52:32 2026	superseded	learning-app-0.1.0	1.0.0      	Install complete
2       	Tue Oct  6 16:52:38 2026	superseded	learning-app-0.1.0	1.0.0      	Upgrade complete
3       	Tue Oct  6 16:52:43 2026	deployed  	learning-app-0.1.0	1.0.0      	Rollback to 1   
{"message":"Hello from DEV","pod":"shop-backend-66555cc57d-kn4sm","version":"1.0.0"}
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_helm-lab
{"message":"Hello from DEV","pod":"shop-backend-66555cc57d-kn4sm","version":"1.0.0"}
```

A rollback is a new revision (3) with the content of revision 1: history only grows, so you can always see what
happened.

**7. The same chart, another environment.** The test values add a second backend replica and a PostgreSQL database
with a PersistentVolumeClaim, in a separate namespace:

<!-- test: contains=STATUS: deployed; timeout=420 -->
```bash
kubectl create namespace helm-test > /dev/null
helm install shop helm/learning-app -n helm-test -f helm/learning-app/values-test.yaml --wait --timeout 5m | grep -E 'STATUS|NOTES' -A1
```

<!-- test: contains="visits"; contains=Hello from TEST -->
```bash
kubectl get deployments,pvc -n helm-test
kubectl run client -n helm-test --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- http://shop-backend; echo; wget -qO- http://shop-backend/api/visits'
```

## Expected Result

Release `shop` in `helm-lab` at revision 3 (backend 1.0.0 after the rollback), and release `shop` in `helm-test` with
two backends, a database and a bound PVC: the same chart, two environments, two values files.

## Inspect

What Helm knows about a release: the values it was installed with, and the YAML it applied:

<!-- test: contains=Hello from DEV; contains=kind: Deployment -->
```bash
helm get values shop -n helm-lab
helm get manifest shop -n helm-lab | grep -E '^kind:|^  name:'
```

Helm stores each revision as a Secret in the release's namespace:

<!-- test: contains=sh.helm.release.v1.shop.v3 -->
```bash
kubectl get secrets -n helm-lab -l owner=helm
```

## Experiment

Preview the effect of a value without touching the cluster:

<!-- test: contains=replicas: 4 -->
```bash
helm template shop helm/learning-app --set backend.replicas=4 | grep 'replicas:'
```

## Break It

Release a backend version that does not exist, and let Helm wait for it:

<!-- test: fail; anyof=context deadline exceeded||timed out||failed; timeout=300; output=tail:2 -->
```bash
helm upgrade shop helm/learning-app -n helm-lab -f helm/learning-app/values-dev.yaml \
  --set backend.image.tag=9.9.9 --wait --timeout 40s 2>&1
```

```text
...
Error: UPGRADE FAILED: resource Deployment/helm-lab/shop-backend not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
```

## Troubleshoot It

*What should happen?* Revision 4, deployed. *What happened?* `UPGRADE FAILED`. Helm applied the new YAML, then waited
for the Deployments to become ready, and they did not. Helm's view first, then Kubernetes':

<!-- test: contains=failed; contains=ErrImagePull -->
```bash
helm history shop -n helm-lab | tail -2
kubectl get pods -n helm-lab -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,REASON:.status.containerStatuses[0].state.waiting.reason | grep -E 'NAME|9.9.9'
```

Revision 4 is `failed`; its new backend Pod cannot pull `learning-app/backend:9.9.9` (lab 12, problem 03). The old
Pod is still serving (a rolling update, lesson 09). Root cause: a value (`backend.image.tag`) that points at an image
which does not exist.

## Fix It

Roll back to the last good revision; the fix of the release itself (building 9.9.9, or using a real tag) comes after:

<!-- test: contains=Rollback was a success; timeout=300 -->
```bash
helm rollback shop 3 -n helm-lab --wait --timeout 3m
helm history shop -n helm-lab | tail -2
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Editing objects with `kubectl` after `helm install` | the next `helm upgrade` overwrites or conflicts with your change | change values and `helm upgrade`; the chart is the source of truth |
| Forgetting `-f values-dev.yaml` on upgrade | the release silently goes back to the defaults | pass the same values files every time (or `--reuse-values`, carefully) |
| `helm install` twice with the same name | `cannot re-use a name that is still in use` | `helm upgrade --install` installs or upgrades |
| No `--wait` | `STATUS: deployed` although the Pods crash | `--wait --timeout` makes Helm check readiness |
| Indentation errors in templates | `error converting YAML to JSON` | `helm template` and `helm lint` before every install |

## Best Practices

- One chart, one values file per environment; keep values files small (only what differs).
- Always `helm lint` and `helm template` (or `--dry-run`) before installing; always `--wait --timeout`.
- Never put real passwords in values files committed to Git: pass them with `--set` from a secret store or reference
  existing Secrets.
- Version the chart (`version` in Chart.yaml) when the templates change, the app (`appVersion`) when the image changes.

## Challenge

**Task:** add a **prod** environment: a values file that runs 3 backend replicas with the message "Hello from PROD",
and install it as release `shop` in a namespace `helm-prod`.

**Requirements:** a new values file (outside the chart is fine); `--wait`; the backend answers with the PROD message.

**Hints:** only `backend.replicas` and `backend.message` differ from the defaults; `-f -` reads a values file from a
pipe (a file such as `values-prod.yaml` next to the chart works the same).

**Expected Result:** `kubectl get deployment shop-backend -n helm-prod` shows `3/3`; the backend says "Hello from
PROD".

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=3/3; contains=Hello from PROD; timeout=420 -->
```bash
kubectl create namespace helm-prod > /dev/null
printf 'backend:\n  replicas: 3\n  message: "Hello from PROD"\n' |
  helm install shop helm/learning-app -n helm-prod -f - --wait --timeout 5m > /dev/null
kubectl get deployment shop-backend -n helm-prod
kubectl run client -n helm-prod --rm -i --quiet --restart=Never --image=busybox:1.37 -- wget -qO- http://shop-backend
```

</details>

Three environments now share one set of templates; prod differs from the defaults in two lines. A CI/CD pipeline would
run the same `helm upgrade --install … -f values-prod.yaml` with the image tag it just built.

## Key Takeaways

- A chart = templates + default values; a release = one installation; every change is a numbered revision.
- `helm install / upgrade / rollback / uninstall / list / history`; `lint` and `template` before installing.
- Values files per environment replace copies of YAML: dev, test and prod differ only in their values.
- `--wait --timeout` makes failures visible; `helm rollback` returns to any earlier revision.
- Real-world use: most third-party software (ingress controllers, databases, monitoring) is installed with Helm,
  and many teams package their own applications as charts that CI/CD pipelines upgrade.

## Cleanup

🧹 Uninstall the three releases (Helm deletes every object it created, the PVC too), then delete their namespaces:

<!-- test: contains=uninstalled -->
```bash
helm uninstall shop -n helm-lab
helm uninstall shop -n helm-test
helm uninstall shop -n helm-prod --ignore-not-found
kubectl delete namespace helm-lab helm-test helm-prod --ignore-not-found > /dev/null
```

Next: [29 · Capstone](../29-capstone/README.md)
