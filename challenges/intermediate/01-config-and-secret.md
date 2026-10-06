# Challenge 01 · Configure the backend from a ConfigMap and a Secret

> Intermediate · after lessons 11–12 · ⏱ 20 minutes · cluster: minikube

## Task

Run the backend so that its greeting comes from a ConfigMap and its database password from a Secret mounted as a
file, in a namespace `challenge-01`.

## Requirements

- ConfigMap `app-settings` with `MESSAGE=Configured, not built`.
- Secret `app-db` with `password=example-password-change-me`.
- Deployment `backend` (image `learning-app/backend:1.0.0`) with `envFrom` the ConfigMap and the Secret mounted at
  `/etc/db`, `DB_PASSWORD_FILE=/etc/db/password`.

## Hints

- `kubectl create configmap … --from-literal`, `kubectl create secret generic … --from-literal`.
- Lessons 11 and 12 show `envFrom` and a `secret` volume.

## Expected Result

The backend's `/api/config` returns `"message":"Configured, not built"` and `"db_password":"set (from file)"`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=Configured, not built; contains=set (from file) -->
```bash
kubectl create namespace challenge-01
kubectl create configmap app-settings -n challenge-01 --from-literal=MESSAGE='Configured, not built'
kubectl create secret generic app-db -n challenge-01 --from-literal=password=example-password-change-me
kubectl apply -n challenge-01 -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels: {app: backend}
  template:
    metadata:
      labels: {app: backend}
    spec:
      containers:
        - name: backend
          image: learning-app/backend:1.0.0
          envFrom:
            - configMapRef: {name: app-settings}
          env:
            - name: DB_PASSWORD_FILE
              value: /etc/db/password
          volumeMounts:
            - {name: db, mountPath: /etc/db, readOnly: true}
      volumes:
        - name: db
          secret: {secretName: app-db}
EOF
kubectl rollout status deployment/backend -n challenge-01 --timeout=120s > /dev/null
kubectl run client -n challenge-01 --image=busybox:1.37 -- sleep 3600 > /dev/null
kubectl wait --for=condition=Ready pod/client -n challenge-01 --timeout=120s > /dev/null
ip=$(kubectl get pod -n challenge-01 -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n challenge-01 client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

</details>

## Explanation

Non-secret settings and secrets travel separately: the ConfigMap can be shown in a code review, while access to the
Secret can be restricted with RBAC (lesson 24). The image is unchanged; another namespace (environment) would get
different values.

## Cleanup

🧹 Delete the namespace `challenge-01` and everything in it:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-01
```
