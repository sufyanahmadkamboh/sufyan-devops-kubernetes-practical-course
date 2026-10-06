# Lab 10 · Ingress: 503 from the entrance

> Lesson 20 · ⏱ 20 minutes · run every command from the course folder · cluster: minikube

## Objective

The backend is published on `api.lab10.local` through an Ingress. After a change to the Ingress, every request gets
`503`. Find out why from the Ingress and the Service, and fix it.

## Setup

The ingress controller (lesson 20), then the application:

<!-- test: contains=ingress.networking.k8s.io/api created; timeout=600 -->
```bash
minikube addons enable ingress 2>&1 | tail -1
kubectl wait --for=condition=Ready pod -n ingress-nginx -l app.kubernetes.io/component=controller --timeout=300s > /dev/null
kubectl create namespace lab10
kubectl apply -f labs/10-ingress/app.yaml -n lab10
kubectl rollout status deployment/backend -n lab10 --timeout=120s
```

## Steps

Through the entrance, with the host name:

<!-- test: retry=15; contains=Hello from the backend -->
```bash
kubectl run client -n lab10 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 --header "Host: api.lab10.local" http://ingress-nginx-controller.ingress-nginx/
```

## Break It

Someone "standardised" the Ingress to port 80:

<!-- test: retry=10; contains=503; output -->
```bash
kubectl apply -f labs/10-ingress/ingress-broken.yaml -n lab10 > /dev/null
kubectl run client -n lab10 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 5 --header "Host: api.lab10.local" http://ingress-nginx-controller.ingress-nginx/ 2>&1 || true'
```

```text
wget: server returned error: HTTP/1.1 503 Service Temporarily Unavailable
warning: couldn't attach to pod/client, falling back to streaming logs: unable to upgrade connection: container client not found in pod client_lab10
wget: server returned error: HTTP/1.1 503 Service Temporarily Unavailable
```

## Troubleshoot It

*Who answered?* The ingress controller (a `503` page): the request reached the entrance and matched a rule, but had
nowhere to go. *Which object maps the rule to Pods?* The Ingress, then the Service:

<!-- test: contains=backend:80; output -->
```bash
kubectl describe ingress api -n lab10 | grep -A4 '^Rules' | tail -1
kubectl get service backend -n lab10
```

```text
                   /   backend:80 (10.244.120.88:8080)
NAME      TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
backend   ClusterIP   10.97.44.110   <none>        8080/TCP   17s
```

The Ingress sends to port `80` of the Service; the Service only has port `8080`. No port 80, so no endpoints for the
controller. Root cause: the Ingress backend port must be a port **of the Service** (not of the container, not "the
usual web port").

## Fix It

<!-- test: retry=15; contains=Hello from the backend -->
```bash
kubectl apply -f labs/10-ingress/app.yaml -n lab10 > /dev/null
kubectl run client -n lab10 --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 --header "Host: api.lab10.local" http://ingress-nginx-controller.ingress-nginx/
```

## Verification

<!-- test: contains=backend:8080 -->
```bash
kubectl describe ingress api -n lab10 | grep -A4 '^Rules' | tail -1
```

The rule points to `backend:8080` with a Pod address in brackets, and the request returns the backend's JSON.

## Cleanup

🧹 Delete the namespace `lab10` (the backend, its Service and the Ingress). The ingress controller stays.

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab10
```
