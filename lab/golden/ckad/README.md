# CKAD golden exercises (weeks 30-31)

12 timed tasks that cover every CKAD domain. Reference solutions are in `exercises.yaml`.
Solve each task yourself first (imperative commands + `$do`, then edit), then diff against the reference.
Target: every task under 6 minutes, twice in a row.

Setup:
```bash
./lab.sh kind up            # use ./lab.sh kind up cilium for task 12 (NetworkPolicy enforcement)
./lab.sh addon ingress      # task 11
alias k=kubectl ; export do="--dry-run=client -o yaml"
k create ns ckad-lab && k label ns ckad-lab lab.devops/component=ckad
k config set-context --current --namespace=ckad-lab
```
To load all reference solutions at once: `kubectl apply -f lab/golden/ckad/exercises.yaml`.

All objects live in namespace `ckad-lab`. Images used: `busybox:1.36`, `nginx:1.26`, `nginx:1.27`, `curlimages/curl:8.10.1`.

| # | Domain | Task | Verify |
|---|---|---|---|
| 1 | Design & Build | Pod `t1-sidecar`: init container `seed` writes `index.html` into an emptyDir; native sidecar `log-tailer` (init container with `restartPolicy: Always`) tails nginx's access log from a shared emptyDir; main container `web` is nginx. | `k exec t1-sidecar -c log-tailer -- wget -qO- localhost` -> `ckad t1`; then `k logs t1-sidecar -c log-tailer` shows the request |
| 2 | Design & Build | Job `t2-job`: 4 completions, parallelism 2, backoffLimit 2, deleted 10 min after finishing. | `k get job t2-job` shows `4/4`; `k logs -l job-name=t2-job` |
| 3 | Design & Build | CronJob `t3-cron` every 2 min, `concurrencyPolicy: Forbid`, history 2 succeeded / 1 failed. Trigger it once manually. | `k create job t3-manual --from=cronjob/t3-cron && k logs job/t3-manual` |
| 4 | Design & Build | PVC `t4-data` (100Mi, RWO) mounted at `/data` in pod `t4-writer`, which appends the date every 10 s. | `k get pvc t4-data` is `Bound`; `k exec t4-writer -- tail -2 /data/out.log` |
| 5 | Deployment | Deployment `t5-web` (3 replicas, nginx:1.26, maxSurge 1, maxUnavailable 0). Update to nginx:1.27 with a change-cause, then roll back to revision 1. | `k rollout history deploy/t5-web`; `k get deploy t5-web -o jsonpath='{.spec.template.spec.containers[0].image}'` -> `nginx:1.26` after the undo |
| 6 | Deployment | Blue/green: `t6-blue` (nginx:1.26) and `t6-green` (nginx:1.27) behind Service `t6-web`. Cut over to green by patching the selector. | `k patch svc t6-web -p '{"spec":{"selector":{"app":"t6","version":"green"}}}'`; `k get endpointslices -l kubernetes.io/service-name=t6-web -o wide` shows the green pod IPs |
| 7 | Observability | Pod `t7-probes`: nginx with startup (HTTP /), readiness (HTTP /) and liveness (TCP 80) probes. Then break readiness (edit path to `/nope` in a copy) and explain what happens. | `k describe pod t7-probes \| grep -E 'Liveness\|Readiness\|Startup'`; `k get pod t7-probes` is `1/1 Running`, 0 restarts |
| 8 | Config | ConfigMap `t8-config` (`MODE`, `app.properties`) and Secret `t8-secret` (`DB_PASSWORD`); pod `t8-config-pod` reads MODE and DB_PASSWORD as env and mounts `app.properties` at `/etc/app`. | `k logs t8-config-pod`; `k exec t8-config-pod -- printenv DB_PASSWORD` |
| 9 | Security | ServiceAccount `t9-app` without token automount; pod `t9-secure` runs as UID 1000/GID 3000, fsGroup 2000, read-only root FS, no privilege escalation, all capabilities dropped, writable `/tmp` emptyDir. | `k logs t9-secure` shows `uid=1000 gid=3000` and `tmp-writable`; `k exec t9-secure -- touch /x` fails; `k exec t9-secure -- ls /var/run/secrets/kubernetes.io` fails |
| 10 | Config / RBAC | ResourceQuota `t10-quota` + LimitRange `t10-defaults`; SA `t10-reader` bound to Role `t10-pod-reader` (get/list/watch pods and pods/log). | `k describe quota t10-quota`; `k auth can-i list pods --as=system:serviceaccount:ckad-lab:t10-reader` -> yes; same with `delete pods` -> no |
| 11 | Networking | Deployment `t11-api` (2 replicas), ClusterIP Service `t11-api` port 8080 -> named port `http`, Ingress `t11-ingress` for host `ckad.lab.local`. | `k run t --rm -it --image=curlimages/curl:8.10.1 --restart=Never -- curl -s t11-api:8080`; `curl -H 'Host: ckad.lab.local' http://localhost/` from the host |
| 12 | Networking | NetworkPolicy `t12-api-allow-frontend`: only pods labelled `role=frontend` may reach `t11-api` on TCP 80. Test from `t12-frontend` (allowed) and `t12-intruder` (blocked). | `k exec t12-frontend -- curl -s -m 3 t11-api:8080` succeeds; `k exec t12-intruder -- curl -s -m 3 t11-api:8080` times out (Cilium profile only) |

Notes:
- Task 1: the verify step uses busybox `wget` from the sidecar because containers in a pod share localhost; it avoids depending on tools inside the nginx image.
- Task 10: once the quota exists, pods without requests/limits are only admitted because the LimitRange fills in defaults. Delete the LimitRange and try `k run nolimits --image=nginx:1.27` to see the rejection.
- Task 12: kind's default CNI (kindnet) does not enforce NetworkPolicy, so both curls succeed there.

Cleanup:
```bash
kubectl delete ns ckad-lab
kubectl config set-context --current --namespace=default
```
