# 22 · NetworkPolicies

> Level 10 · Ingress & Networking · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **NetworkPolicy** is a firewall rule for Pods: "the database accepts connections **only** from the backend, on port
5432". It selects Pods by label and lists who may talk to them (ingress) or whom they may talk to (egress).

The analogy: by default every office in the building has its door open. NetworkPolicies are badge readers: once a door
has one, only the badges listed may enter.

## Why do we need it?

Lesson 21's model says every Pod can reach every Pod. That is convenient and dangerous: if an attacker takes over the
frontend (the part exposed to the Internet), they can connect straight to the database. NetworkPolicies enforce the
architecture you drew: frontend → backend → database, and nothing else.

```text
frontend → backend     allowed
backend  → database    allowed
frontend ✕ database    denied
```

## How does it work?

- A Pod is **isolated** for ingress as soon as **any** policy with `policyTypes: [Ingress]` selects it. From then on,
  only traffic allowed by some policy gets in. Pods selected by no policy stay open.
- Policies only **add** permissions; there is no "deny" rule. The usual pattern: one **default-deny** policy selecting
  every Pod (`podSelector: {}`), then small **allow** policies.
- `from` can select Pods by label (`podSelector`), namespaces (`namespaceSelector`) or IP ranges (`ipBlock`).
- The **network plugin** enforces them. This course's cluster runs Calico, which does; a plugin without
  NetworkPolicy support accepts the objects and silently ignores them (that is why lesson 03 starts Minikube with
  `--cni=calico`).

## Architecture

```text
 namespace netpol-lab, policies: default-deny-ingress + two allow rules

   frontend ──── TCP 8080 ✔ ───▶ backend ──── TCP 5432 ✔ ───▶ database
      │                          (allow-frontend-to-backend)   (allow-backend-to-database)
      └────────────────────── TCP 5432 ✕ ──────────────────────────┘   (no rule allows it)
```

## YAML

The application (`manifests/networking/netpol-app.yaml`): a `frontend` Pod (a shell to send requests from), the
course backend configured to use the database, and PostgreSQL. The policies:

<!-- test: contains=podSelector: {} -->
```bash
cat manifests/networking/netpol-default-deny.yaml
cat manifests/networking/netpol-allow-frontend-to-backend.yaml
```

| Field | Meaning |
|---|---|
| `kind: NetworkPolicy` (`networking.k8s.io/v1`) | a firewall rule for Pods |
| `spec.podSelector` | the Pods the policy applies to; `{}` = all Pods of the namespace |
| `policyTypes: [Ingress]` | the policy controls incoming traffic (add `Egress` to control outgoing) |
| `ingress[].from[].podSelector` | which Pods may connect (by label, in the same namespace) |
| `ingress[].ports` | which ports they may connect to |
| no `ingress` list at all | nothing is allowed: the default-deny policy |

`netpol-allow-backend-to-database.yaml` is the same pattern for `database` ← `backend` on 5432.

## Hands-On Lab

**1. Deploy the three tiers:**

<!-- test: contains=deployment.apps/database created; timeout=300 -->
```bash
kubectl create namespace netpol-lab
kubectl apply -f manifests/networking/netpol-app.yaml -n netpol-lab
kubectl rollout status deployment/database -n netpol-lab --timeout=180s
kubectl rollout status deployment/backend -n netpol-lab --timeout=180s
kubectl wait --for=condition=Ready pod/frontend -n netpol-lab --timeout=120s
```

**2. Before any policy, everything is open.** From the frontend: the backend answers, the backend reaches the database
(`/readyz` says `ready` only then), and the frontend can also open the database port directly:

<!-- test: retry=15; contains="status":"ready"; contains=database port: open; output -->
```bash
kubectl exec frontend -n netpol-lab -- wget -qO- -T 3 http://backend:8080/readyz
kubectl exec frontend -n netpol-lab -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "database port: open" || echo "database port: blocked"'
```

```text
{"status":"ready"}
database port: open
```

That last line is the problem: the frontend should never be able to talk to the database.

**3. Close every door:**

<!-- test: retry=10; contains=timed out; contains=database port: blocked; output -->
```bash
kubectl apply -f manifests/networking/netpol-default-deny.yaml -n netpol-lab > /dev/null
kubectl exec frontend -n netpol-lab -- sh -c 'wget -qO- -T 3 http://backend:8080/readyz 2>&1 || true'
kubectl exec frontend -n netpol-lab -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "database port: open" || echo "database port: blocked"'
```

```text
wget: download timed out
database port: blocked
```

**4. Open exactly the two paths of the architecture:**

<!-- test: retry=15; contains="status":"ready"; contains=database port: blocked; output -->
```bash
kubectl apply -f manifests/networking/netpol-allow-frontend-to-backend.yaml -n netpol-lab > /dev/null
kubectl apply -f manifests/networking/netpol-allow-backend-to-database.yaml -n netpol-lab > /dev/null
kubectl exec frontend -n netpol-lab -- wget -qO- -T 3 http://backend:8080/readyz
kubectl exec frontend -n netpol-lab -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "database port: open" || echo "database port: blocked"'
```

```text
{"status":"ready"}
database port: blocked
```

## Expected Result

frontend → backend works, backend → database works (the backend is `ready`), frontend → database is blocked.

## Inspect

<!-- test: contains=default-deny-ingress; contains=allow-backend-to-database -->
```bash
kubectl get networkpolicies -n netpol-lab
kubectl describe networkpolicy allow-backend-to-database -n netpol-lab
```

`describe` spells the rule out: which Pods it applies to, who may connect, on which port.

## Experiment

Which policy really keeps the frontend away from the database? Delete the default-deny policy and test again:

<!-- test: retry=10; contains=without default-deny: blocked -->
```bash
kubectl delete networkpolicy default-deny-ingress -n netpol-lab --ignore-not-found > /dev/null
kubectl exec frontend -n netpol-lab -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "without default-deny: open" || echo "without default-deny: blocked"'
kubectl apply -f manifests/networking/netpol-default-deny.yaml -n netpol-lab > /dev/null
```

Still blocked: the database is selected by `allow-backend-to-database`, and **being selected by any policy isolates a
Pod**. Only the sources listed in some policy get in. Default-deny matters for the Pods that **no** allow rule
selects (here the frontend itself, and every Pod added to the namespace later): without it they would be open.

## Break It

A colleague "tidies up" the frontend rule:

<!-- test: retry=10; contains=timed out; output -->
```bash
kubectl apply -f manifests/networking/netpol-allow-frontend-to-backend-broken.yaml -n netpol-lab > /dev/null
kubectl exec frontend -n netpol-lab -- sh -c 'wget -qO- -T 3 http://backend:8080/readyz 2>&1 || true'
```

```text
wget: download timed out
```

## Troubleshoot It

*What should happen?* `ready`. *What happened?* A timeout: no answer at all, the signature of dropped packets, so
suspect a NetworkPolicy. *Which policies select the backend, and whom do they allow?*

<!-- test: contains=fronted -->
```bash
kubectl describe networkpolicy allow-frontend-to-backend -n netpol-lab | grep -A6 'Allowing ingress'
kubectl get pods -n netpol-lab --show-labels
```

The policy allows Pods labelled `app=fronted`; the frontend is labelled `app=frontend`. No Pod matches, so the rule
allows nobody, and the default-deny policy blocks the frontend. Root cause: a typo in a label selector.

## Fix It

<!-- test: retry=15; contains="status":"ready" -->
```bash
kubectl apply -f manifests/networking/netpol-allow-frontend-to-backend.yaml -n netpol-lab
kubectl exec frontend -n netpol-lab -- wget -qO- -T 3 http://backend:8080/readyz
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| A network plugin without NetworkPolicy support | policies exist, nothing is blocked | use Calico/Cilium (`minikube start --cni=calico`) |
| A label typo in `podSelector` or `from` | timeouts, or nothing protected | `kubectl get pods --show-labels`; `describe networkpolicy` |
| Default-deny **egress** without allowing DNS | every name lookup fails | allow UDP/TCP 53 to `kube-system` CoreDNS |
| Forgetting the port | traffic still blocked | list the destination port in `ports` |
| Assuming policies are ordered | "deny" rules expected | policies only allow; isolation comes from being selected |

## Best Practices

- Start every namespace with a default-deny policy, then allow the paths of your architecture.
- Label Pods by role (`app`, `tier`) so policies stay readable.
- Test both directions: what must work **and** what must be blocked.

## Challenge

**Task:** the database should also accept connections from a backup job Pod labelled `app=backup` (and still not from
the frontend). Add that permission without changing the existing policies, and prove it.

**Requirements:** a new NetworkPolicy; test from a `busybox:1.37` Pod labelled `app=backup`.

**Hints:** a second policy selecting the database adds to the first; `kubectl run --labels=app=backup`.

**Expected Result:** `database port: open` from the backup Pod, `blocked` from the frontend.

## Solution

<details>
<summary>Solution</summary>

<!-- test: retry=10; contains=backup: open; contains=frontend: blocked -->
```bash
sed -e 's/allow-backend-to-database/allow-backup-to-database/' -e 's/app: backend           # who/app: backup            # who/' manifests/networking/netpol-allow-backend-to-database.yaml | kubectl apply -n netpol-lab -f - > /dev/null
kubectl run backup -n netpol-lab --labels=app=backup --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "backup: open" || echo "backup: blocked"'
kubectl exec frontend -n netpol-lab -- sh -c 'nc -w 3 database 5432 < /dev/null && echo "frontend: open" || echo "frontend: blocked"'
```

</details>

Policies add up: the database now accepts the backend **or** the backup Pod. Nothing had to be edited, so the change
is easy to review and to remove.

## Key Takeaways

- NetworkPolicies are label-based firewall rules for Pods; selected Pods accept only what some policy allows.
- Default-deny first, then explicit allow rules for the paths of the architecture.
- A blocked connection usually times out; check policies and labels.
- They need a network plugin that enforces them (Calico in this course).
- Real-world use: limiting the damage of a compromised Pod, separating teams and environments in shared clusters,
  meeting security requirements ("only the API may reach the database").

## Cleanup

🧹 Delete the namespace `netpol-lab` (the three tiers and all four policies):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace netpol-lab
```

Next: [23 · ServiceAccounts](../23-serviceaccounts/README.md)
