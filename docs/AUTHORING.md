# Writing lessons for this course

Every lesson is one `README.md` that a learner follows from top to bottom on a local Minikube cluster, and that
`tests/run.sh` runs exactly as the learner types it. The lessons of `docs/01`–`docs/04` are the reference: copy their
structure, tone and level of detail.

## The learner

Knows basic Linux and Docker (images, containers, Dockerfiles). Has never used Kubernetes. Is not a programmer. Every
new word is explained the first time it appears; every YAML field the first time it is used.

## Lesson structure (`docs/NN-topic/README.md`)

The headings are fixed, in this order:

```text
# NN · Topic

> Level N · Level name · ⏱ NN minutes · run every command from the course folder · cluster: minikube

## What is it?                 simple explanation, an everyday analogy
## Why do we need it?          the real-world problem it solves
## How does it work?           beginner-friendly technical explanation
## Architecture                an ASCII diagram (```text)
## YAML                        the complete manifest (a file in manifests/, shown with cat), then a field-by-field table
## Hands-On Lab                numbered steps; every command tested
## Expected Result             what the learner sees (real recorded output)
## Inspect                     kubectl get/describe/logs/events commands to look inside
## Experiment                  something to change and observe
## Break It                    an intentional, realistic failure with its real output
## Troubleshoot It             the investigation, following the troubleshooting mindset
## Common Mistakes             a table: mistake → symptom → fix
## Best Practices              short, practical
## Challenge                   Task / Requirements / Hints / Expected Result (no solution here)
## Solution                    the tested solution inside <details><summary>Solution</summary> … </details>, then
                               an explanation
## Key Takeaways               3–6 bullets, ending with "Real-world use:" (where this is used in a DevOps job)
## Cleanup                     delete what the lesson created (mark it 🧹)

Next: [NN · Topic] → ../NN-topic/README.md
```

The troubleshooting mindset (every Troubleshoot It section and lab follows it):
*What is broken? → What should happen? → What actually happened? → Which object controls it? → inspect it → events →
logs → configuration → root cause → fix → verify.*

## YAML

- Manifests live in `manifests/<category>/<name>.yaml` (or a lab's own folder for broken variants). Lessons show them
  with `cat` and apply them with `kubectl apply -f manifests/...`, so the file on disk is exactly what is explained.
- After the manifest, a table explains the fields: `apiVersion`, `kind`, `metadata`, `spec`, then every field the
  lesson introduces.
- Every manifest must validate: `kubeconform -strict -kubernetes-version 1.37.0` (CI runs it on `manifests/`,
  `capstone/` and the Helm chart). Intentionally invalid YAML goes in a `broken/` folder and is said to be invalid.
- Pin every image with its tag: `nginx:1.30-alpine`, `busybox:1.37`, `alpine:3.23`, `postgres:18-alpine`,
  `learning-app/backend:1.0.0` / `2.0.0` (built inside Minikube by `scripts/build-images.sh`). Never `latest`.
- Cluster-wide objects a lesson creates (ClusterRole, ClusterRoleBinding, StorageClass, PersistentVolume,
  PriorityClass) carry the label `course: k8s-lab`, so a reset can find them.
- Lesson resources go in the namespace the lesson says (often its own, e.g. `pods-lab`); the lesson's Cleanup deletes
  them. `kubectl delete` lines are marked 🧹 in the text and say exactly what they delete.

## The application

`apps/backend` is the course's API (`learning-app/backend:1.0.0` and `2.0.0`): `/` (message, version, pod),
`/livez`, `/readyz` (checks the database when `DB_HOST` is set), `/api/config`, `/api/visits` (PostgreSQL counter),
`/api/burn?ms=N` (CPU load). Configuration: `PORT`, `MESSAGE`, `LOG_LEVEL`, `STARTUP_DELAY`, `DB_HOST`, `DB_PORT`,
`DB_USER`, `DB_NAME`, `DB_PASSWORD` / `DB_PASSWORD_FILE`. The frontend is `nginx:1.30-alpine` with its page and
configuration from ConfigMaps. The database is `postgres:18-alpine` (mount `/var/lib/postgresql`, not `.../data`).

## Test annotations

Every ```` ```bash ```` block runs, in order, in one shell session (the working directory carries over, variables do
not). Put an annotation on the line before a block:

| Annotation | Meaning |
|---|---|
| `<!-- test: contains=TEXT -->` | must succeed and print TEXT (`contains=a; contains=b` for several) |
| `<!-- test: anyof=A\|\|B -->` | output contains A or B |
| `<!-- test: fail; contains=TEXT -->` | must fail (Break It), printing TEXT |
| `<!-- test: absent=TEXT -->` | must not print TEXT (values are trimmed: `absent=NotReady`, never `contains= Ready`) |
| `<!-- test: output -->` | `--update` writes the real output into the ```` ```text ```` block that follows |
| `<!-- test: retry=N -->` | retry up to N times, 2 s apart |
| `<!-- test: timeout=S -->` | seconds before the block is stopped (default 600) |
| `<!-- test: skip -->` | never run (installation for other systems, illustrations, interactive commands) |

Rules:

- **Never write output by hand.** Add `output`, run `bash tests/run.sh --update FILE`, read what it recorded, and fix
  the text if it says something else.
- **Wait, don't sleep:** `kubectl wait --for=condition=Ready pod -l app=x --timeout=120s`,
  `kubectl rollout status deployment/x --timeout=120s`, `kubectl wait --for=condition=complete job/x`.
- `retry=N` reruns from the first probe line (`kubectl`, `curl`, `wget`, `minikube service`…) on; anything before it
  runs once. Keep retried blocks to checks; never put `kubectl create`/`run` in a retried block.
- To reach a Service from the test, run a client inside the cluster:
  `kubectl run client --rm -i --restart=Never --image=busybox:1.37 -- wget -qO- -T 5 http://web` (add `-n NS`).
  `kubectl port-forward` needs a background process: start it with `&`, save `$!`, `kill` it in the same block.
- A `kubectl run --rm -i` client can finish before kubectl attaches, and its output is lost (now and then on slow
  machines): the runner tries such blocks up to three times, so keep them repeatable (`create ... --dry-run=client
  -o yaml | kubectl apply -f -` instead of `create`).
- Never start a follower in the background and leave it (`kubectl logs -f`, `kubectl get -w`); use `--tail`,
  `--since`, `kubectl wait`.
- Blocks run with `bash -e`: capture an exit code with `code=0; cmd || code=$?`.
- Pod names are random: select by label (`kubectl logs -l app=web`, `kubectl get pods -l app=web -o name`) and use
  `-o jsonpath` / `-o custom-columns` instead of parsing tables.
- Host commands must work in Git Bash, macOS and Linux: `curl`, `grep`, `sed`, `head`, `tail`, `printf`. Avoid `jq`,
  `watch`, `timeout`. Never pass `/c/...` or `~/...` paths as arguments to native Windows programs.
- Never print kubeconfig contents, tokens or Secret values that are not obviously fake examples
  (`example-password-change-me`).

## Running the tests

```bash
bash tests/run.sh --update docs/06-pods/README.md       # one lesson, recording outputs
bash tests/run.sh docs/*/README.md labs/*/README.md     # many
```

One run at a time (`tests/.lock`): the cluster is shared and is reset between files. Commands you try by hand must
hold the same lock and use the course cluster: `bash tests/locked.sh bash -c 'kubectl get pods -A'`.

## Lesson map

| Dir | Topic | Spec sections |
|---|---|---|
| docs/01-kubernetes-introduction | what Kubernetes is, why, Kubernetes vs Docker | §1, §9 |
| docs/02-architecture | control plane, nodes, components | §8 |
| docs/03-installation | Minikube setup, first cluster, building the app images | §10 |
| docs/04-kubectl | kubectl fundamentals | §11, §52 |
| docs/05-namespaces | namespaces dev/test/prod | §12 |
| docs/06-pods | first Pod, Pod deep dive, multi-container Pods | §13–15 |
| docs/07-labels-selectors | labels, selectors, annotations | §16 |
| docs/08-replicasets | ReplicaSets, self-healing | §17 |
| docs/09-deployments | Deployments, rolling updates, rollbacks | §18–19 |
| docs/10-services | Services, ClusterIP/NodePort/LoadBalancer, discovery, DNS | §20–21 |
| docs/11-configmaps | ConfigMaps (env and files) | §22 |
| docs/12-secrets | Secrets | §23 |
| docs/13-storage | volumes, emptyDir, PV, PVC, StorageClass | §24–26 |
| docs/14-health-checks | liveness, readiness, startup probes | §27 |
| docs/15-resources | requests, limits, OOMKilled | §28 |
| docs/16-scheduling | nodeSelector, taints, tolerations | §29 |
| docs/17-jobs-cronjobs | Jobs, CronJobs | §30–31 |
| docs/18-daemonsets | DaemonSets | §32 |
| docs/19-statefulsets | StatefulSets, headless Services | §33 |
| docs/20-ingress | Ingress, ingress controller | §34 |
| docs/21-networking | the networking model | §35 |
| docs/22-networkpolicies | NetworkPolicies | §36 |
| docs/23-serviceaccounts | ServiceAccounts | §37 |
| docs/24-rbac | RBAC | §38 |
| docs/25-scaling | manual scaling | §43 |
| docs/26-hpa | Horizontal Pod Autoscaler | §44 |
| docs/27-troubleshooting | method, events, logs, exec | §39–42, §55 |
| docs/28-helm | Helm, values per environment | §45–46 |
| docs/29-capstone | the capstone walkthrough | §47–48 |

Labs (`labs/NN-name/README.md`, sections: Objective / Setup / Steps / Break It / Troubleshoot It / Fix It /
Verification / Cleanup): 01-first-pod, 02-pod-debugging, 03-deployment, 04-service, 05-configmap, 06-secret,
07-storage, 08-probes, 09-networking, 10-ingress, 11-rbac, 12-troubleshooting (14 problems, one file each, format:
Problem / Symptoms / First command to run / Investigation / Root cause / Fix / Verification / Lesson learned),
13-scaling.

Challenges (`challenges/<level>/NN-name.md`, sections: Task / Requirements / Hints / Expected Result / Solution (in
`<details>`) / Explanation): beginner, intermediate, troubleshooting.
