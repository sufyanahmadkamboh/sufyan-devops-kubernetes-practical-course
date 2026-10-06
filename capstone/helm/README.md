# Capstone with Helm

> Capstone · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

The capstone of [docs/29](../../docs/29-capstone/README.md) applies one YAML file per object. The same application
can be installed as **one Helm release** from the course chart of [lesson 28](../../docs/28-helm/README.md):
[helm/learning-app](../../helm/learning-app) with the values in [values-capstone.yaml](values-capstone.yaml)
(frontend, two backend replicas, PostgreSQL with a PersistentVolumeClaim and a password Secret).

## Install

The challenge of docs/29: the release in its own namespace `learning-app-helm`, with **three** backend replicas set on
the command line (`--set` wins over the values file):

<!-- test: contains=STATUS: deployed; timeout=600 -->
```bash
helm lint helm/learning-app -f capstone/helm/values-capstone.yaml > /dev/null
helm install capstone helm/learning-app -n learning-app-helm --create-namespace \
  -f capstone/helm/values-capstone.yaml --set backend.replicas=3 --wait --timeout 5m | grep -E 'STATUS|REVISION'
```

## Verify

<!-- test: contains=deployed; contains=3/3; output -->
```bash
helm list -n learning-app-helm
kubectl get deployments,pvc -n learning-app-helm
```

```text
NAME    	NAMESPACE        	REVISION	UPDATED                               	STATUS  	CHART             	APP VERSION
capstone	learning-app-helm	1       	2026-10-06 16:56:26.2102696 +0200 CEST	deployed	learning-app-0.1.0	1.0.0      
NAME                                READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/capstone-backend    3/3     3            3           8s
deployment.apps/capstone-database   1/1     1            1           8s
deployment.apps/capstone-frontend   1/1     1            1           8s

NAME                                      STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/capstone-database   Bound    pvc-7799737f-ff96-4359-91ad-7e3edb32587a   1Gi        RWO            standard       <unset>                 8s
```

The application answers through the frontend (which proxies `/api/` to the backend) and counts visits in PostgreSQL:

<!-- test: contains=Hello from the capstone; contains="visits" -->
```bash
kubectl run client -n learning-app-helm --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- http://capstone-frontend/api/; echo; wget -qO- http://capstone-frontend/api/api/visits'
```

## Compare with the YAML capstone

| | `capstone/` (kubectl apply) | Helm release |
|---|---|---|
| Install | many `kubectl apply -f` | one `helm install` |
| Change replicas | edit the Deployment file | `--set backend.replicas=3` or a values file |
| History and rollback | `kubectl rollout undo` per Deployment | `helm rollback` for the whole application |
| Remove | `kubectl delete namespace learning-app` | `helm uninstall` (and the namespace) |

The chart is simpler than the hand-written capstone: it has no NetworkPolicies, Ingress, RBAC or CronJob. Adding them
as templates (each behind a value, like `database.enabled`) is a good exercise.

## Cleanup

🧹 Uninstall the release (its Deployments, Services, ConfigMap, Secret and PVC) and delete the namespace:

<!-- test: contains=uninstalled -->
```bash
helm uninstall capstone -n learning-app-helm
kubectl delete namespace learning-app-helm > /dev/null
```
