# Challenge 05 · A nightly report, tested now

> Lesson 17 · intermediate

## Task

Create a CronJob `nightly-report` in the namespace `ch05` that runs every day at 02:30, prints `report done`, keeps
two successful Jobs, and never runs twice at the same time. Prove that it works without waiting for 02:30.

## Requirements

- `busybox:1.37`; schedule 02:30 every day; `concurrencyPolicy: Forbid`; `successfulJobsHistoryLimit: 2`.
- A manual run from the CronJob's template prints `report done`.

## Hints

- Cron fields: minute, hour, day of month, month, day of week.
- `kubectl create job NAME --from=cronjob/CRONJOB`.

## Expected Result

`kubectl get cronjob` shows the schedule `30 2 * * *`; the manual Job is `Complete` and its log says `report done`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=30 2 * * * Forbid 2; contains=report done -->
```bash
kubectl create namespace ch05
kubectl create cronjob nightly-report -n ch05 --image=busybox:1.37 --schedule='30 2 * * *' --dry-run=client -o yaml -- sh -c 'echo report done' |
  sed 's/^spec:/spec:\n  concurrencyPolicy: Forbid\n  successfulJobsHistoryLimit: 2/' | kubectl apply -n ch05 -f -
kubectl get cronjob nightly-report -n ch05 -o jsonpath='{.spec.schedule} {.spec.concurrencyPolicy} {.spec.successfulJobsHistoryLimit}{"\n"}'
kubectl create job report-test --from=cronjob/nightly-report -n ch05
kubectl wait --for=condition=complete job/report-test -n ch05 --timeout=120s > /dev/null
kubectl logs job/report-test -n ch05
kubectl delete namespace ch05
```

</details>

## Explanation

`30 2 * * *` = minute 30 of hour 2, every day. CronJobs use the controller's time zone (UTC on most clusters) unless
`spec.timeZone` is set. Testing with `--from=cronjob` runs exactly the template the schedule will run.
