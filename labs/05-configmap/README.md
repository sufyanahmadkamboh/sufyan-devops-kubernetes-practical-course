# Lab 05 · ConfigMap: the change that did not arrive

> ⏱ 20 minutes · after lesson 11 · run every command from the course folder · cluster: minikube

## Objective

Change an application's configuration in a ConfigMap, find out why the running application still uses the old
value, and roll the change out properly.

## Setup

<!-- test: contains=successfully rolled out -->
```bash
kubectl create namespace lab-configmap
kubectl apply -n lab-configmap -f manifests/configmaps/configmaps-backend-config.yaml -f manifests/configmaps/configmaps-backend-deployment.yaml
kubectl rollout status deployment/backend -n lab-configmap --timeout=120s
kubectl run client -n lab-configmap --image=busybox:1.37 -- sleep 3600
kubectl wait --for=condition=Ready pod/client -n lab-configmap --timeout=120s
```

## Steps

1. Check what the backend received:

<!-- test: contains="log_level":"debug" -->
```bash
ip=$(kubectl get pod -n lab-configmap -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n lab-configmap client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

## Break It

The team lowers the log level to `warn` in the ConfigMap, the way a colleague would during an incident:

<!-- test: contains=patched -->
```bash
kubectl patch configmap backend-config -n lab-configmap --type=merge -p '{"data":{"LOG_LEVEL":"warn"}}'
```

<!-- test: contains="log_level":"debug"; output -->
```bash
ip=$(kubectl get pod -n lab-configmap -l app=backend -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n lab-configmap client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

```text
{"db_host":"(none)","db_password":"not set","log_level":"debug","message":"Hello from a ConfigMap"}
```

Still `debug`.

## Troubleshoot It

*What is broken?* The new log level is not in effect. *What should happen?* `warn`. *Which object controls it?* The
ConfigMap and the way the Pod reads it. Compare the ConfigMap with the Pod's age:

<!-- test: contains=warn -->
```bash
kubectl get configmap backend-config -n lab-configmap -o jsonpath='LOG_LEVEL={.data.LOG_LEVEL}{"\n"}'
kubectl get pods -n lab-configmap -l app=backend -o custom-columns=POD:.metadata.name,STARTED:.status.startTime
kubectl get deployment backend -n lab-configmap -o jsonpath='{.spec.template.spec.containers[0].envFrom}{"\n"}'
```

The ConfigMap says `warn`; the Pod started before the change and reads the ConfigMap through `envFrom`, i.e. as
environment variables, which are copied once, when the container starts. Root cause: the Pod never restarted.

## Fix It

<!-- test: contains=successfully rolled out -->
```bash
kubectl rollout restart deployment/backend -n lab-configmap
kubectl rollout status deployment/backend -n lab-configmap --timeout=120s
```

## Verification

<!-- test: contains="log_level":"warn"; retry=5 -->
```bash
ip=$(kubectl get pod -n lab-configmap -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].status.podIP}')
kubectl exec -n lab-configmap client -- wget -qO- -T 5 "http://$ip:8080/api/config"
```

`"log_level":"warn"`: the new Pods read the new value. In real teams the ConfigMap change and the restart go
together, in the same deployment step (Helm, lesson 28, does it automatically with a checksum annotation).

## Cleanup

🧹 Delete the namespace `lab-configmap` with the ConfigMap, the backend and the client:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace lab-configmap
```
