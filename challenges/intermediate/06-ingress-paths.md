# Challenge 06 · Two applications behind one host name

> Lesson 20 · intermediate

## Task

In the namespace `ch06`, run the backend (`learning-app/backend:1.0.0`, port 8080) and an nginx frontend (port 80),
each with a ClusterIP Service, and publish both on `portal.local`: `/api` to the backend, everything else to the
frontend.

## Requirements

- Two Deployments, two ClusterIP Services, one Ingress with class `nginx`.
- `/api/config` through the ingress controller returns the backend's JSON; `/` returns the nginx page.

## Hints

- `manifests/ingress/ingress-apps.yaml` and `ingress-paths.yaml` (lesson 20) are close to what you need.
- Test from a client Pod with `--header "Host: portal.local"` against `http://ingress-nginx-controller.ingress-nginx`.

## Expected Result

Two answers through one entrance: JSON with `db_password` for `/api/config`, `Welcome to nginx` for `/`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=created; timeout=600 -->
```bash
minikube addons enable ingress > /dev/null 2>&1
kubectl wait --for=condition=Ready pod -n ingress-nginx -l app.kubernetes.io/component=controller --timeout=300s > /dev/null
kubectl create namespace ch06
kubectl apply -f manifests/ingress/ingress-apps.yaml -n ch06
sed 's/host: shop.local/host: portal.local/' manifests/ingress/ingress-paths.yaml | kubectl apply -n ch06 -f -
kubectl rollout status deployment/backend -n ch06 --timeout=120s
kubectl rollout status deployment/frontend -n ch06 --timeout=120s
```

<!-- test: retry=15; contains="db_password"; contains=Welcome to nginx -->
```bash
kubectl run client -n ch06 --rm -i --quiet --restart=Never --image=busybox:1.37 -- sh -c '
  wget -qO- -T 5 --header "Host: portal.local" http://ingress-nginx-controller.ingress-nginx/api/config; echo
  wget -qO- -T 5 --header "Host: portal.local" http://ingress-nginx-controller.ingress-nginx/ | grep -o "<title>.*</title>"'
```

</details>

## Explanation

The Ingress picks the **longest** matching path: `/api/config` matches both `/api` and `/`, and `/api` wins. The first
requests after a change may fail for a few seconds while the controller loads the new rules.

## Cleanup

🧹 Delete the namespace `ch06`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace ch06
```
