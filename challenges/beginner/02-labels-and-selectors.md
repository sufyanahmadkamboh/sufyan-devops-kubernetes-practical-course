# Beginner challenge 02 · Find Pods by their labels

> After lesson 07 · ⏱ 15 minutes · run every command from the course folder · cluster: minikube

## Task

In a namespace `challenge-02`, start four nginx Pods with these labels, then answer three questions with **one
selector each**:

| Pod | `app` | `environment` |
|---|---|---|
| `shop-dev` | shop | dev |
| `shop-prod` | shop | prod |
| `blog-dev` | blog | dev |
| `blog-test` | blog | test |

1. Which Pods belong to the shop?
2. Which Pods are not in production?
3. Which blog Pods are in dev or test?

## Requirements

- Selectors only (`-l`): no Pod names, no `grep`.
- Image `nginx:1.30-alpine`.

## Hints

- `kubectl run NAME --image=… --labels=key=value,key=value` sets labels at creation.
- `!=` excludes a value; `in (a,b)` matches several; a comma means AND.

## Expected Result

1. `shop-dev`, `shop-prod`; 2. `shop-dev`, `blog-dev`, `blog-test`; 3. `blog-dev`, `blog-test`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=created -->
```bash
kubectl create namespace challenge-02
kubectl run shop-dev  -n challenge-02 --image=nginx:1.30-alpine --labels=app=shop,environment=dev
kubectl run shop-prod -n challenge-02 --image=nginx:1.30-alpine --labels=app=shop,environment=prod
kubectl run blog-dev  -n challenge-02 --image=nginx:1.30-alpine --labels=app=blog,environment=dev
kubectl run blog-test -n challenge-02 --image=nginx:1.30-alpine --labels=app=blog,environment=test
```

<!-- test: contains=shop-prod; contains=blog-test; output -->
```bash
echo "1:"; kubectl get pods -n challenge-02 -l app=shop -o name
echo "2:"; kubectl get pods -n challenge-02 -l 'environment!=prod' -o name
echo "3:"; kubectl get pods -n challenge-02 -l 'app=blog,environment in (dev,test)' -o name
```

```text
1:
pod/shop-dev
pod/shop-prod
2:
pod/blog-dev
pod/blog-test
pod/shop-dev
3:
pod/blog-dev
pod/blog-test
```

🧹 Clean up (deletes the namespace `challenge-02` and its four Pods):

<!-- test: contains=deleted -->
```bash
kubectl delete namespace challenge-02
```

</details>

## Explanation

Equality (`=`, `!=`) and set conditions (`in`, `notin`) can be combined with commas, which all must match. The same
selectors drive Services, Deployments and NetworkPolicies, so being fluent with them makes the rest of Kubernetes
easier to read.
