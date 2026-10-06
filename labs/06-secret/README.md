# Lab 06 · Secret: the file that never appeared

> ⏱ 20 minutes · after lesson 12 · run every command from the course folder · cluster: minikube

## Objective

Mount a database password from a Secret as a file, diagnose a Pod that is stuck while starting, and fix the mount.

## Setup

<!-- test: contains=secret/db-credentials created -->
```bash
kubectl create namespace lab-secret
kubectl apply -n lab-secret -f manifests/secrets/secrets-db-credentials.yaml
kubectl run client -n lab-secret --image=busybox:1.37 -- sleep 3600
kubectl wait --for=condition=Ready pod/client -n lab-secret --timeout=120s
```

## Steps

A colleague wrote this Deployment: the password should arrive as the file `/etc/db/password`.

<!-- test: contains=deployment.apps/backend created -->
```bash
kubectl apply -n lab-secret -f - <<'EOF'
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
          env:
            - name: DB_PASSWORD_FILE
              value: /etc/db/password
          volumeMounts:
            - name: creds
              mountPath: /etc/db
              readOnly: true
      volumes:
        - name: creds
          secret:
            secretName: db-credentials
            items:
              - key: db-password
                path: password
EOF
```

## Break It

The Deployment above is already broken. Watch its Pod:

<!-- test: retry=10; contains=ContainerCreating; output -->
```bash
kubectl get pods -n lab-secret -l app=backend
```

```text
NAME                       READY   STATUS              RESTARTS   AGE
backend-7b8596c798-z6tls   0/1     ContainerCreating   0          1s
```

## Troubleshoot It

*What is broken?* The Pod never leaves `ContainerCreating`. *What should happen?* `Running` in seconds. *Which
component is involved?* The kubelet prepares volumes before it starts the container: a stuck `ContainerCreating` is
usually a volume. Events:

<!-- test: retry=15; contains=db-password; output -->
```bash
kubectl get events -n lab-secret --field-selector reason=FailedMount -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
MountVolume.SetUp failed for volume "creds" : references non-existent secret key: db-password
```

<!-- test: contains=password -->
```bash
kubectl get secret db-credentials -n lab-secret -o jsonpath='{.data}' | tr ',' '\n'
```

Root cause: the volume asks for the key `db-password`; the Secret's keys are `password` and `username`.

## Fix It

<!-- test: contains=successfully rolled out -->
```bash
kubectl patch deployment backend -n lab-secret --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/volumes/0/secret/items/0/key","value":"password"}]'
kubectl rollout status deployment/backend -n lab-secret --timeout=120s
```

## Verification

<!-- test: contains=set (from file) -->
```bash
ip=$(kubectl get pod -n lab-secret -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n lab-secret client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

`"db_password":"set (from file)"`. Unlike the environment-variable mistake of lesson 12 (`CreateContainerConfigError`),
a wrong key in a **volume** shows as `ContainerCreating` with a `FailedMount` event: same root cause, different
symptom, which is why reading events beats guessing.

## Cleanup

🧹 Delete the namespace `lab-secret` with the Secret, the backend and the client:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-secret
```
