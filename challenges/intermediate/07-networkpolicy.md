# Challenge 07 · Only the API may reach the cache

> Lesson 22 · intermediate

## Task

In the namespace `ch07`, run a cache (`nginx:1.30-alpine`, label `app=cache`, port 80, Service `cache`). Only Pods
labelled `app=api` may connect to it; any other Pod must be blocked.

## Requirements

- One NetworkPolicy, selecting the cache, allowing `app=api` on TCP 80.
- Prove both cases with `busybox:1.37` client Pods.

## Hints

- `kubectl run --labels=app=api` gives a client Pod the right label.
- A blocked connection times out: use `wget -T 3`.

## Expected Result

`api: allowed`, `other: blocked`.

## Solution

<details>
<summary>Solution</summary>

The policy, in `challenges/intermediate/07-cache-policy.yaml`:

<!-- test: contains=cache-from-api-only -->
```bash
cat challenges/intermediate/07-cache-policy.yaml
kubectl create namespace ch07
kubectl create deployment cache --image=nginx:1.30-alpine -n ch07
kubectl expose deployment cache --port=80 -n ch07
kubectl rollout status deployment/cache -n ch07 --timeout=120s
kubectl apply -f challenges/intermediate/07-cache-policy.yaml -n ch07
```

<!-- test: retry=10; contains=api: allowed; contains=other: blocked -->
```bash
kubectl run api -n ch07 --labels=app=api --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 3 http://cache > /dev/null && echo "api: allowed" || echo "api: blocked"'
kubectl run other -n ch07 --labels=app=other --rm -i --quiet --restart=Never --image=busybox:1.37 -- \
  sh -c 'wget -qO- -T 3 http://cache > /dev/null && echo "other: allowed" || echo "other: blocked"'
```

</details>

## Explanation

`kubectl create deployment cache` labels its Pods `app=cache`, which the policy selects. Once selected, the cache
accepts only what the policy lists: Pods labelled `app=api`, on port 80. No default-deny is needed, because the
protected Pod is the one the policy selects.

## Cleanup

🧹 Delete the namespace `ch07`:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace ch07
```
