# 17 · Jobs and CronJobs

> Level 11 · Jobs & CronJobs · ⏱ 35 minutes · run every command from the course folder · cluster: minikube

## What is it?

A **Job** runs a task **until it succeeds, then stops**: a database migration, a report, an import. A **CronJob**
creates a Job **on a schedule**: every night at 2:00, every minute, every Monday.

The analogy: a Deployment is a shop that must stay open all day; a Job is a delivery that is done once the parcel
arrives; a CronJob is the delivery round that happens every morning.

## Why do we need it?

A Deployment restarts its Pods forever: if your backup script finishes and exits, the Deployment would start it again
and again. Some work has an end. A Job knows the difference between "finished successfully" and "crashed", retries
failures a limited number of times, and keeps the result (the Pod and its logs) for you to read.

```text
Deployment  → long-running application, always N copies running
Job         → one-time task: run until it succeeds, then stop
CronJob     → a Job on a schedule
```

## How does it work?

The Job controller creates Pods from the Job's template and watches how they end:

- exit code 0 → one **completion**; when `completions` are reached, the Job is `Complete`;
- non-zero exit → a failure; a new Pod is created, up to `backoffLimit` retries, with a growing delay
  (10 s, 20 s, 40 s…); after that the Job is `Failed` with the reason `BackoffLimitExceeded`.

`restartPolicy` must be `Never` (a failed Pod is replaced by a new one) or `OnFailure` (the container is restarted
inside the same Pod); never `Always`, which is for long-running Pods.

The CronJob controller checks the `schedule` every few seconds and creates a Job (named `CRONJOB-<number>`) when it is
due. Old Jobs are deleted according to the history limits.

## Architecture

```text
CronJob "report"  ── every minute ──▶ Job report-29365432 ──▶ Pod report-29365432-x7k2p  ──▶ exit 0 → Complete
                  ── every minute ──▶ Job report-29365433 ──▶ Pod ...                    ──▶ exit 0 → Complete

Job "import" ──▶ Pod #1 exit 1 ──▶ Pod #2 exit 1 ──▶ Pod #3 exit 1 ──▶ backoffLimit 2 reached → Failed
```

## YAML

<!-- test: contains=kind: Job -->
```bash
cat manifests/workloads/jobs-countdown.yaml
```

| Field | Meaning |
|---|---|
| `apiVersion: batch/v1` | Jobs and CronJobs belong to the `batch` API group |
| `kind: Job` | a task that runs to completion |
| `spec.backoffLimit: 2` | how many failed Pods are retried before the Job gives up |
| `spec.ttlSecondsAfterFinished: 600` | delete the finished Job and its Pods 10 minutes after it ends (housekeeping) |
| `spec.template` | the Pod to run, exactly like a Pod's `spec` (lesson 06) |
| `restartPolicy: Never` | do not restart the container in place; a failure means a new Pod |
| `command` | the task: count down, print `liftoff`, exit 0 |

The CronJob wraps a Job template in a schedule:

<!-- test: contains=kind: CronJob -->
```bash
cat manifests/workloads/cronjobs-report.yaml
```

| Field | Meaning |
|---|---|
| `schedule: "* * * * *"` | standard cron syntax: minute, hour, day of month, month, day of week; `*` = every. `"0 2 * * *"` = every day at 02:00 |
| `concurrencyPolicy: Forbid` | if a run is still going when the next one is due, skip the new one (`Allow` runs both, `Replace` stops the old one) |
| `successfulJobsHistoryLimit: 3` / `failedJobsHistoryLimit: 1` | how many finished Jobs to keep for their logs |
| `jobTemplate` | the Job created at every scheduled time |

## Hands-On Lab

**1. A namespace for this lesson:**

<!-- test: contains=created -->
```bash
kubectl create namespace jobs-lab
```

**2. Run the countdown Job and wait for it to finish:**

<!-- test: contains=condition met -->
```bash
kubectl apply -f manifests/workloads/jobs-countdown.yaml -n jobs-lab
kubectl wait --for=condition=complete job/countdown -n jobs-lab --timeout=120s
```

**3. Look at the result:**

<!-- test: contains=Complete; contains=liftoff; output -->
```bash
kubectl get job countdown -n jobs-lab
kubectl logs job/countdown -n jobs-lab
```

```text
NAME        STATUS     COMPLETIONS   DURATION   AGE
countdown   Complete   1/1           9s         9s
5
4
3
2
1
liftoff
```

**4. Start the CronJob, and trigger one run by hand** (`--from=cronjob/...` creates a Job from its template right
away, useful to test a CronJob without waiting for its schedule):

<!-- test: contains=job.batch/report-manual created -->
```bash
kubectl apply -f manifests/workloads/cronjobs-report.yaml -n jobs-lab
kubectl create job report-manual --from=cronjob/report -n jobs-lab
kubectl wait --for=condition=complete job/report-manual -n jobs-lab --timeout=120s
```

**5. Wait for the first scheduled run** (at the start of the next minute):

<!-- test: retry=45; contains=T -->
```bash
kubectl get cronjob report -n jobs-lab -o jsonpath='{.status.lastScheduleTime}{"\n"}' | grep T
```

## Expected Result

<!-- test: contains=report-manual; contains=report-; output -->
```bash
kubectl get cronjob,jobs -n jobs-lab
```

```text
NAME                   SCHEDULE    TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
cronjob.batch/report   * * * * *   <none>     False     1        0s              28s

NAME                        STATUS     COMPLETIONS   DURATION   AGE
job.batch/countdown         Complete   1/1           9s         37s
job.batch/report-29854920   Running    0/1           0s         0s
job.batch/report-manual     Complete   1/1           3s         28s
```

The CronJob has a last schedule time and created a Job named `report-` plus a number (the scheduled time in minutes);
every Job is `Complete`.

## Inspect

The Pods of a Job stay after it finishes (status `Completed`), so you can read their logs; each carries the label
`job-name`:

<!-- test: contains=Completed -->
```bash
kubectl get pods -n jobs-lab -l job-name=countdown
kubectl logs -n jobs-lab -l job-name=report-manual
```

<!-- test: contains=Successful -->
```bash
kubectl describe cronjob report -n jobs-lab | grep -A6 '^Events'
```

## Experiment

`completions` and `parallelism`: six work items, two at a time.

<!-- test: contains=6/6; output -->
```bash
kubectl apply -f manifests/workloads/jobs-batch.yaml -n jobs-lab
kubectl wait --for=condition=complete job/batch -n jobs-lab --timeout=180s > /dev/null
kubectl get job batch -n jobs-lab
```

```text
job.batch/batch created
NAME    STATUS     COMPLETIONS   DURATION   AGE
batch   Complete   6/6           16s        16s
```

Six Pods ran, never more than two at once, so the Job took about three rounds of a few seconds each. Try
`parallelism: 6` in a copy of the file: all six run together.

Pause the schedule without deleting the CronJob (useful during maintenance):

<!-- test: contains=true -->
```bash
kubectl patch cronjob report -n jobs-lab -p '{"spec":{"suspend":true}}'
kubectl get cronjob report -n jobs-lab -o jsonpath='suspended: {.spec.suspend}{"\n"}'
```

## Break It

An import task reads a file that does not exist:

<!-- test: contains=BackoffLimitExceeded; timeout=300; output -->
```bash
kubectl apply -f manifests/workloads/jobs-broken.yaml -n jobs-lab > /dev/null
kubectl wait --for=condition=failed job/import -n jobs-lab --timeout=240s > /dev/null
kubectl get job import -n jobs-lab
kubectl get job import -n jobs-lab -o jsonpath='{.status.conditions[?(@.type=="Failed")].reason}{"\n"}'
```

```text
NAME     STATUS   COMPLETIONS   DURATION   AGE
import   Failed   0/1           34s        34s
BackoffLimitExceeded
```

## Troubleshoot It

*What should happen?* `Complete 1/1`. *What happened?* `Failed`, reason `BackoffLimitExceeded`. *Which object
controls it?* The Job, through its Pods. How many Pods did it try, and how did they end?

<!-- test: contains=Error; output -->
```bash
kubectl get pods -n jobs-lab -l job-name=import
```

```text
NAME           READY   STATUS   RESTARTS   AGE
import-hgttp   0/1     Error    0          34s
import-rm4sf   0/1     Error    0          3s
import-sl4qs   0/1     Error    0          24s
```

Three Pods: the first try plus the two retries of `backoffLimit: 2`, all `Error`. The Job's events say the same; the
**logs** say why:

<!-- test: contains=No such file; output -->
```bash
kubectl logs -n jobs-lab -l job-name=import --tail=2 | head -2
```

```text
reading /data/prices.csv
cat: can't open '/data/prices.csv': No such file or directory
error: write /dev/stdout: The pipe is being closed.
```

Root cause: the task's input file is not there. Retrying could not help: a Job's retries are for temporary
failures (a database not reachable yet), not for a broken task.

## Fix It

A failed Job does not start again: fix the cause, delete the Job and create it again. Here the import should read a
file the Pod has (in a real Job you would mount it from a ConfigMap or a volume, lessons 11 and 13):

<!-- test: contains=Complete -->
```bash
kubectl delete job import -n jobs-lab
sed 's#cat /data/prices.csv#cat /etc/hostname#' manifests/workloads/jobs-broken.yaml | kubectl apply -n jobs-lab -f -
kubectl wait --for=condition=complete job/import -n jobs-lab --timeout=120s > /dev/null
kubectl get job import -n jobs-lab
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `restartPolicy: Always` in a Job | `Unsupported value: "Always"` when applying | `Never` or `OnFailure` |
| A Job's command that never exits | the Job runs forever, `COMPLETIONS 0/1` | the task must end; add `activeDeadlineSeconds` as a safety limit |
| Re-applying a changed Job | `field is immutable` | delete the Job and create it again (Jobs are run-once) |
| Wrong cron syntax or time zone | runs at the wrong time, or never | check with `kubectl get cronjob` (LAST SCHEDULE); set `timeZone: "Europe/Berlin"` if needed |
| No history limits / TTL | thousands of finished Jobs and Pods pile up | `successfulJobsHistoryLimit`, `failedJobsHistoryLimit`, `ttlSecondsAfterFinished` |

## Best Practices

- Make tasks **idempotent**: a retry, or two overlapping runs, must not do the work twice.
- Use `concurrencyPolicy: Forbid` for tasks that must not overlap (backups, reports).
- Set `backoffLimit` and `activeDeadlineSeconds` so a broken task fails fast and visibly.
- Test a CronJob with `kubectl create job NAME --from=cronjob/CRONJOB` instead of waiting for its schedule.

## Challenge

**Task:** create a CronJob `cleanup` in `jobs-lab` that runs **every 5 minutes**, prints `cleaning up`, keeps only
**one** successful Job in its history, and is never allowed to run twice at the same time. Then prove it works
without waiting five minutes.

**Requirements:** `busybox:1.37`; schedule every 5 minutes; history limit 1; no overlapping runs.

**Hints:** `*/5` in the minute field; `concurrencyPolicy`; `kubectl create job --from=cronjob/...`.

**Expected Result:** the CronJob exists with the schedule `*/5 * * * *`, and a manual Job printed `cleaning up`.

## Solution

<details>
<summary>Solution</summary>

<!-- test: contains=cleaning up; contains=*/5 * * * * -->
```bash
kubectl create cronjob cleanup -n jobs-lab --image=busybox:1.37 --schedule='*/5 * * * *' --dry-run=client -o yaml -- sh -c 'echo cleaning up' |
  sed 's/^spec:/spec:\n  concurrencyPolicy: Forbid\n  successfulJobsHistoryLimit: 1/' | kubectl apply -n jobs-lab -f -
kubectl create job cleanup-test --from=cronjob/cleanup -n jobs-lab
kubectl wait --for=condition=complete job/cleanup-test -n jobs-lab --timeout=120s > /dev/null
kubectl logs job/cleanup-test -n jobs-lab
kubectl get cronjob cleanup -n jobs-lab -o jsonpath='{.spec.schedule} {.spec.concurrencyPolicy} {.spec.successfulJobsHistoryLimit}{"\n"}'
```

</details>

`kubectl create cronjob ... --dry-run=client -o yaml` writes the skeleton; the two extra fields are added to `spec`
(in a real project, edit the file instead of using `sed`). `*/5` means "every minute divisible by 5".

## Key Takeaways

- Job = run to completion, retry failures up to `backoffLimit`; CronJob = a Job on a cron schedule.
- `completions` and `parallelism` split work across Pods.
- A failed Job's Pods keep their logs: `kubectl logs -l job-name=NAME`.
- Real-world use: database migrations before a release, nightly backups and reports, cleanup tasks, batch imports.

## Cleanup

🧹 Delete the namespace `jobs-lab` with its CronJobs, Jobs and their Pods:

<!-- test: contains=deleted -->
```bash
kubectl delete namespace jobs-lab
```

Next: [18 · DaemonSets](../18-daemonsets/README.md)
