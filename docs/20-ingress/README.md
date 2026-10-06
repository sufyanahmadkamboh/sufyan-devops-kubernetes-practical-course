# 20 · Ingress

> Level 10 · Ingress & Networking · ⏱ 40 minutes · run every command from the course folder · cluster: minikube

## What is it?

An **Ingress** is a set of HTTP routing rules: "requests for `app.local` go to the frontend Service, requests for
`shop.local/api` go to the backend Service". An **ingress controller** is the program (a reverse proxy running in the
cluster) that reads those rules and actually routes the traffic.

The analogy: Services are the departments of a company; the Ingress is the reception desk with one public entrance,
reading the visitor's request ("I am here for accounting") and sending them to the right floor.

## Why do we need it?

Exposing every application with its own `NodePort` or `LoadBalancer` Service (lesson 10) does not scale: one random
high port or one paid cloud load balancer **per application**, no host names, no shared TLS certificate, no paths.
Web traffic wants one entrance (ports 80/443) and rules by **host name** and **path**. That is the Ingress.

## How does it work?

```text
Ingress object (rules)  ──read by──▶  ingress controller (a Deployment of reverse-proxy Pods, e.g. ingress-nginx)
                                             │  turns the rules into its proxy configuration
client ──HTTP Host: shop.local /api/x ──▶  controller ──▶ backend-service ──▶ backend Pods
```

- The Ingress object alone does nothing: without a controller, nobody reads it.
- A cluster can run several controllers; `ingressClassName` says which one handles an Ingress. Minikube's addon
  installs **ingress-nginx** with the class `nginx`. (The ingress-nginx project was retired upstream in 2026; other
  controllers such as Traefik, and the newer **Gateway API**, use the same ideas: host and path rules to Services.)
- The controller itself is reached from outside through a Service: on Minikube a NodePort on the node.
- Rules match the `Host` header first, then the **longest** matching path.

## Architecture

```text
                    Internet / your browser
                             │  http://shop.local/api/config
                             ▼
              ingress-nginx controller (namespace ingress-nginx)
                 │ host app.local, /          │ host shop.local, /api      │ host shop.local, /
                 ▼                            ▼                            ▼
         frontend-service              backend-service               frontend-service
                 │                            │                            │
          frontend Pods                 backend Pods                 frontend Pods
```

## YAML

The two applications are ordinary Deployments with **ClusterIP** Services (reachable only inside the cluster):
`manifests/ingress/ingress-apps.yaml`. The routing rules by host name:

<!-- test: contains=kind: Ingress -->
```bash
cat manifests/ingress/ingress-hosts.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: networking.k8s.io/v1`, `kind: Ingress` | HTTP routing rules |
| `ingressClassName: nginx` | the controller that must handle this Ingress |
| `rules[].host` | the host name the rule applies to (the HTTP `Host` header) |
| `paths[].path`, `pathType: Prefix` | the URL path; `Prefix` matches `/api`, `/api/`, `/api/config` (whole path segments) |
| `backend.service.name`, `port.number` | the Service (in the same namespace) and port that receive the request |

And by path, on one host:

<!-- test: contains=path: /api -->
```bash
cat manifests/ingress/ingress-paths.yaml
```

## Hands-On Lab

**1. Install the ingress controller** (Minikube's addon; once per cluster):

<!-- test: contains=enabled; timeout=600 -->
```bash
minikube addons enable ingress 2>&1 | tail -1
kubectl wait --for=condition=Ready pod -n ingress-nginx -l app.kubernetes.io/component=controller --timeout=300s
```

**2. The applications, in their own namespace:**

<!-- test: contains=deployment.apps/backend created -->
```bash
kubectl create namespace ingress-lab
kubectl apply -f manifests/ingress/ingress-apps.yaml -n ingress-lab
kubectl rollout status deployment/frontend -n ingress-lab --timeout=120s
kubectl rollout status deployment/backend -n ingress-lab --timeout=120s
```

**3. The host-based Ingress:**

<!-- test: contains=by-host -->
```bash
kubectl apply -f manifests/ingress/ingress-hosts.yaml -n ingress-lab
kubectl get ingress -n ingress-lab
```

**4. Send requests through the controller** with different `Host` headers. The test client runs inside the cluster
and calls the controller's Service; the `Host` header is what a browser would send for `app.local` or `api.local`:

<!-- test: retry=15; contains=Welcome to nginx; contains=Hello from the backend; output -->
```bash
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  wget -qO- -T 5 --header "Host: app.local" http://ingress-nginx-controller.ingress-nginx | grep -o "<title>.*</title>"
  wget -qO- -T 5 --header "Host: api.local" http://ingress-nginx-controller.ingress-nginx'
```

```text
<title>Welcome to nginx!</title>
{"message":"Hello from the backend","pod":"backend-6d67574bcc-ntnzg","version":"1.0.0"}
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_ingress-lab
<title>Welcome to nginx!</title>
{"message":"Hello from the backend","pod":"backend-6d67574bcc-ntnzg","version":"1.0.0"}
```

One entrance, two applications, chosen by host name.

**5. Path-based routing** on one host:

<!-- test: retry=15; contains="db_password"; contains=Welcome to nginx -->
```bash
kubectl apply -f manifests/ingress/ingress-paths.yaml -n ingress-lab > /dev/null
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx/api/config; echo
  wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx/ | grep -o "<title>.*</title>"'
```

From your own computer: on Linux, `curl --resolve shop.local:80:$(minikube ip) http://shop.local/api/config`; on
Windows and macOS the Minikube node is not directly reachable, so run `minikube tunnel` in a second terminal, add
`127.0.0.1 shop.local` to your hosts file and open <http://shop.local/>:

<!-- test: skip -->
```bash
minikube tunnel
```

## Expected Result

`app.local` returns the nginx page, `api.local` the backend's JSON; on `shop.local`, `/api/config` reaches the backend
and `/` the frontend.

## Inspect

How the controller understood the rules, and which Pods stand behind each Service:

<!-- test: contains=backend-service:8080 -->
```bash
kubectl describe ingress by-path -n ingress-lab | grep -A6 '^Rules'
kubectl get endpointslices -n ingress-lab
```

The controller's own Service and its logs (every request is logged with the Service it was sent to):

<!-- test: contains=ingress-nginx-controller -->
```bash
kubectl get service ingress-nginx-controller -n ingress-nginx
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=2
```

## Experiment

A host name with no rule: the controller answers with its **default backend**, a `404`.

<!-- test: contains=404 -->
```bash
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 --header "Host: unknown.local" http://ingress-nginx-controller.ingress-nginx 2>&1 || true'
```

## Break It

A colleague updates the path-based Ingress, with a typo in the backend's Service name:

<!-- test: contains=503; output -->
```bash
kubectl apply -f manifests/ingress/ingress-paths-broken.yaml -n ingress-lab > /dev/null
sleep 5
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx/api/config 2>&1 || true'
```

```text
wget: server returned error: HTTP/1.1 503 Service Temporarily Unavailable
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_ingress-lab
wget: server returned error: HTTP/1.1 503 Service Temporarily Unavailable
```

## Troubleshoot It

*What should happen?* JSON from the backend. *What happened?* `503 Service Temporarily Unavailable`, from the
ingress controller: it received the request but had nowhere to send it. *Which object controls the routing?* The
Ingress: describe it and read its backends:

<!-- test: contains=backend-svc; output -->
```bash
kubectl describe ingress by-path -n ingress-lab | grep -A5 '^Rules'
```

```text
Rules:
  Host        Path  Backends
  ----        ----  --------
  shop.local  
              /api   backend-svc:8080 (<error: services "backend-svc" not found>)
              /      frontend-service:80 (10.244.120.65:80)
```

The `/api` backend is an error: `services "backend-svc" not found`. The Service is `backend-service`
(`kubectl get svc -n ingress-lab`). Root cause: a wrong Service name; the controller has no Pods to send `/api` to.

## Fix It

<!-- test: retry=15; contains="db_password" -->
```bash
kubectl apply -f manifests/ingress/ingress-paths.yaml -n ingress-lab > /dev/null
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 --header "Host: shop.local" http://ingress-nginx-controller.ingress-nginx/api/config
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| No ingress controller installed | Ingress objects accepted, nothing answers | install one (`minikube addons enable ingress`) |
| Missing or wrong `ingressClassName` | the Ingress gets no address, requests 404 | `kubectl get ingressclass`; set the class |
| Wrong Service name or port | `503` from the controller; `<error: services ... not found>` in describe | match `kubectl get svc` |
| Service in another namespace | `not found` | an Ingress routes only to Services in its own namespace |
| Testing without the right `Host` header | `404` from the default backend | send the host name (`curl -H 'Host: …'`, hosts file, DNS) |
| Expecting a Pod-level fix to show at once | old errors for a few seconds | the controller reloads its config; retry |

## Best Practices

- One Ingress per application (or team), owned with the application's manifests.
- Terminate TLS at the Ingress (`spec.tls` with a certificate Secret; cert-manager automates it).
- Keep backend Services `ClusterIP`: the Ingress is the only door.
- For new platforms, look at the Gateway API, the successor of Ingress.

## Challenge

**Task:** add a third rule to the host-based Ingress: requests for `status.local` go to the **backend**, and prove it
by calling `/livez` through the controller.

**Requirements:** edit a copy of `ingress-hosts.yaml` (or use `kubectl patch`); test with a `Host: status.local` header.

**Hints:** a new entry in `spec.rules`; the backend answers `{"status":"alive"}` on `/livez`.

**Expected Result:** `{"status":"alive"}`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: retry=15; contains=alive -->
```bash
kubectl patch ingress by-host -n ingress-lab --type=json -p '[{"op":"add","path":"/spec/rules/-","value":{"host":"status.local","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"backend-service","port":{"number":8080}}}}]}}}]'
kubectl run client -n ingress-lab --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 --header "Host: status.local" http://ingress-nginx-controller.ingress-nginx/livez
```

</details>

Adding an application to the entrance is one more rule; the controller picks it up within seconds, without a restart.

## Key Takeaways

- Ingress = HTTP routing rules (host, path → Service); the ingress controller does the routing.
- One entrance for many applications: no NodePort per app.
- `503` from the controller → a backend Service is missing or has no ready Pods; `404` → no rule matched.
- Real-world use: every web application on Kubernetes is published through an Ingress or Gateway, usually with TLS,
  behind one cloud load balancer.

## Cleanup

🧹 Delete the namespace `ingress-lab` (both Ingresses, both applications and their Services). The ingress controller
stays: lesson 29 and the labs use it.

<!-- test: contains=deleted -->
```bash
kubectl delete namespace ingress-lab
```

Next: [21 · Kubernetes networking](../21-networking/README.md)
