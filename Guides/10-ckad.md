---
tags: [devops-prep, guide]
---
# Phase 10 - CKAD: Certified Kubernetes Application Developer

**Plan weeks:** 30-31 · **Hours:** 56 · **Exam:** 2 h performance-based · **Lab:** `./lab.sh kind up`, `lab/k8s/manifests/pod-patterns.yaml`, `lab/golden/ckad/`

CKA already gave you the cluster side. CKAD is narrower but faster: roughly 15-20 tasks in 2 hours, all about getting workloads, config and networking right inside a namespace. Speed with imperative commands matters more than depth.

| Week | Focus | Deliverable |
|---|---|---|
| 30 | Design & build (multi-container, init/sidecar, Jobs/CronJobs, volumes, images) + deployment (rollouts, blue/green, canary, Helm, Kustomize) | All 12 tasks in `lab/golden/ckad/` solved from a blank namespace, twice |
| 31 | Observability, config & security (probes, ConfigMap/Secret, SecurityContext, SA, quotas, RBAC, CRDs), Services/Ingress/NetworkPolicy, killer.sh mocks, sit exam | killer.sh score >= 80%, then CKAD |

## Domains (verify the current curriculum on training.linuxfoundation.org)
| Domain | Weight | Your lab |
|---|---|---|
| Application Design and Build | 20% | `k8s/manifests/pod-patterns.yaml`, golden tasks 1-4 |
| Application Deployment | 20% | golden tasks 5-6, Helm + Kustomize drills |
| Application Observability and Maintenance | 15% | golden task 7, `./lab.sh break` (app-level ones) |
| Application Environment, Configuration and Security | 25% | golden tasks 8-10 |
| Services and Networking | 20% | golden tasks 11-12, `./lab.sh kind up cilium` for NetworkPolicy |

## Exam technique
```bash
alias k=kubectl ; export do="--dry-run=client -o yaml" ; export now="--force --grace-period 0"
source <(kubectl completion bash) ; complete -o default -F __start_kubectl k
k config use-context <ctx> ; k config set-context --current --namespace=<ns>   # read the task header
k explain deploy.spec.strategy --recursive | less
```
- Generate, don't type: `k run web --image=nginx $do > t1.yaml`, edit, `k apply -f t1.yaml`.
- Namespace is part of the answer. A correct object in the wrong namespace scores zero. Set it per context or pass `-n` every time.
- Budget ~6 minutes per task. Skip anything that stalls you, flag it, come back.
- Verify each task: `k get`, `k describe`, `k logs`, or a throwaway curl pod (`k run t --rm -it --image=curlimages/curl --restart=Never -- curl -s svc:80`).
- vim: `set ts=2 sw=2 et` in `~/.vimrc`; `:set paste` before pasting YAML from the docs.
- Allowed docs: kubernetes.io/docs, kubernetes.io/blog, helm.sh/docs. Bookmark nothing you can't find by search in 20 s.

## Application Design and Build

### Multi-container pods, init and sidecar containers
- **Init containers** run to completion, in order, before app containers start. Use them to wait for a dependency or pre-populate a volume.
- **Native sidecars** (stable since 1.33): an init container with `restartPolicy: Always`. It starts before the app, keeps running, and stops after it. Before that, sidecars were just a second entry in `containers`.
- Containers in a pod share network (localhost) and any mounted volume. They do not share a filesystem by default.

```yaml
apiVersion: v1
kind: Pod
metadata: { name: web-sidecar }
spec:
  initContainers:
    - name: seed
      image: busybox:1.36
      command: ["sh", "-c", "echo hello > /work/index.html"]
      volumeMounts: [{ name: html, mountPath: /work }]
    - name: tailer                    # native sidecar
      image: busybox:1.36
      restartPolicy: Always
      command: ["sh", "-c", "touch /logs/access.log; tail -F /logs/access.log"]
      volumeMounts: [{ name: logs, mountPath: /logs }]
  containers:
    - name: nginx
      image: nginx:1.27
      volumeMounts:
        - { name: html, mountPath: /usr/share/nginx/html }
        - { name: logs, mountPath: /var/log/nginx }
  volumes:
    - { name: html, emptyDir: {} }
    - { name: logs, emptyDir: {} }
```
Check: `k get pod web-sidecar -o jsonpath='{.status.initContainerStatuses[*].name}'`, `k logs web-sidecar -c tailer`.

### Jobs and CronJobs
```bash
k create job pi --image=busybox:1.36 $do -- sh -c 'echo 3.14' > job.yaml
k create cronjob tick --image=busybox:1.36 --schedule='*/5 * * * *' $do -- date > cj.yaml
k create job manual-run --from=cronjob/tick      # trigger a CronJob now
k get jobs -w ; k logs job/pi
```
Fields to know by heart: `completions`, `parallelism`, `backoffLimit`, `activeDeadlineSeconds`, `ttlSecondsAfterFinished` (Job); `concurrencyPolicy` (Allow/Forbid/Replace), `successfulJobsHistoryLimit`, `failedJobsHistoryLimit`, `startingDeadlineSeconds`, `suspend` (CronJob). Pod template `restartPolicy` must be `Never` or `OnFailure`.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata: { name: report }
spec:
  schedule: "0 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      completions: 3
      parallelism: 1
      backoffLimit: 2
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - { name: report, image: busybox:1.36, command: ["sh", "-c", "date; echo done"] }
```

### Volumes
- `emptyDir` (pod lifetime; `medium: Memory` for tmpfs), `configMap`/`secret`/`projected`, `hostPath` (avoid), `persistentVolumeClaim`.
- PVC in the app namespace; the pod references `claimName`. Access modes RWO/ROX/RWX/RWOP.
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: data }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 1Gi } }
```
Mount with `volumes: [{name: data, persistentVolumeClaim: {claimName: data}}]` and a matching `volumeMounts` entry. `subPath` mounts one key/file instead of the whole directory.

### Building images
You may be asked to build or export an image with docker or podman on the exam host.
```bash
cat > Dockerfile <<'DF'
FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/
USER 101
DF
podman build -t localhost/web:v2 .            # or docker build
podman save localhost/web:v2 -o /root/web-v2.tar   # "export as OCI/docker archive" tasks
kind load image-archive /root/web-v2.tar      # lab only: make it visible to kind nodes
```
Know: multi-stage builds (`FROM ... AS build` then `COPY --from=build`), small base images, non-root `USER`, pin tags, never bake secrets into layers.

## Application Deployment

### Rolling update and rollback
```bash
k create deploy web --image=nginx:1.26 --replicas=4
k set image deploy/web nginx=nginx:1.27 ; k rollout status deploy/web
k annotate deploy/web kubernetes.io/change-cause="bump to 1.27"
k rollout history deploy/web ; k rollout history deploy/web --revision=2
k rollout undo deploy/web --to-revision=1
k rollout pause deploy/web ; k rollout resume deploy/web ; k rollout restart deploy/web
k scale deploy/web --replicas=6 ; k autoscale deploy/web --min=2 --max=5 --cpu-percent=70
```
```yaml
spec:
  strategy:
    type: RollingUpdate          # or Recreate (all old pods die first)
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  minReadySeconds: 5
  revisionHistoryLimit: 5
```

### Blue/green and canary with plain Deployments
The Service selector is the switch. Both patterns need nothing beyond Deployments, labels and one Service.
- **Blue/green:** `web-blue` (labels `app=web,version=blue`) and `web-green` (`version=green`) run side by side. Service selects `app=web,version=blue`. Cut over with one patch, roll back the same way:
  ```bash
  k patch svc web -p '{"spec":{"selector":{"app":"web","version":"green"}}}'
  ```
- **Canary:** Service selects only `app=web`. Run `web-stable` with 4 replicas and `web-canary` with 1. Roughly 20% of connections hit the canary. Shift weight with `k scale`. Promote by updating stable's image and scaling canary to 0.
```yaml
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  selector: { app: web }          # add version: blue for blue/green
  ports: [{ port: 80, targetPort: 80 }]
```
Verify the split: `for i in $(seq 20); do k exec t -- curl -s web; done | sort | uniq -c`.

### Helm
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami ; helm repo update
helm search repo nginx ; helm show values bitnami/nginx | less
helm install web bitnami/nginx -n web --create-namespace --set replicaCount=2
helm upgrade web bitnami/nginx -n web -f my-values.yaml --reuse-values
helm list -A ; helm history web -n web ; helm rollback web 1 -n web
helm get values web -n web ; helm template web bitnami/nginx | less ; helm uninstall web -n web
```

### Kustomize
```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [../../base]
namespace: prod
namePrefix: prod-
labels:
  - pairs: { env: prod }
images:
  - { name: nginx, newTag: "1.27" }
replicas:
  - { name: web, count: 3 }
configMapGenerator:
  - { name: web-config, literals: [MODE=prod] }
```
`k kustomize overlays/prod` (render) then `k apply -k overlays/prod`. Generators append a content hash to names, so a config change rolls the Deployment.

## Application Observability and Maintenance

### Probes
- **startupProbe** holds off the other probes until the app has started (slow boot).
- **livenessProbe** failure restarts the container.
- **readinessProbe** failure removes the pod from Service endpoints. It does not restart the container.
- Handlers: `httpGet`, `tcpSocket`, `exec`, `grpc`. Tune `initialDelaySeconds`, `periodSeconds`, `failureThreshold`, `timeoutSeconds`.
```yaml
containers:
  - name: web
    image: nginx:1.27
    startupProbe: { httpGet: { path: /, port: 80 }, failureThreshold: 30, periodSeconds: 2 }
    readinessProbe: { httpGet: { path: /, port: 80 }, periodSeconds: 5 }
    livenessProbe: { tcpSocket: { port: 80 }, periodSeconds: 10, failureThreshold: 3 }
```

### Logs and debugging
```bash
k logs pod/x -c sidecar --previous --tail=50 -f ; k logs deploy/web --all-containers
k logs -l app=web --prefix --max-log-requests=10
k describe pod x | sed -n '/Events/,$p' ; k get events --sort-by=.lastTimestamp
k get pod x -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'   # OOMKilled?
k exec -it x -c app -- sh ; k port-forward svc/web 8080:80
k debug -it x --image=busybox:1.36 --target=app     # ephemeral container sharing the process namespace
k debug x -it --copy-to=x-dbg --container=app -- sh  # copy of the pod with a shell instead of the entrypoint
k top pod --containers                               # needs metrics-server (./lab.sh addon metrics)
```
Triage order: `get` (status/restarts) -> `describe` (events) -> `logs --previous` -> `exec`/`debug`.

### API deprecations
```bash
k api-resources | grep -i cronjob ; k api-versions | grep batch
k explain cronjob --api-version=batch/v1
k get --raw /metrics | grep apiserver_requested_deprecated_apis   # what clients still call
kubectl convert -f old.yaml --output-version apps/v1               # kubectl-convert plugin
```
Know the removals that still show up in old manifests: `extensions/v1beta1` Deployment/Ingress -> `apps/v1` / `networking.k8s.io/v1`, `batch/v1beta1` CronJob -> `batch/v1`, `policy/v1beta1` PodSecurityPolicy removed (use Pod Security Admission). The fix is usually: change `apiVersion`, then add now-required fields (for example `spec.selector` on apps/v1 Deployments, `pathType` on v1 Ingress).

## Application Environment, Configuration and Security

### ConfigMap and Secret
```bash
k create cm app-cfg --from-literal=MODE=dev --from-file=app.properties
k create secret generic db --from-literal=user=app --from-literal=pass='s3cr3t'
k create secret tls web-tls --cert=tls.crt --key=tls.key
k create secret docker-registry regcred --docker-server=r.example.com --docker-username=u --docker-password=p
k get secret db -o jsonpath='{.data.pass}' | base64 -d      # base64 is encoding, not encryption
```
```yaml
containers:
  - name: app
    image: busybox:1.36
    envFrom: [{ configMapRef: { name: app-cfg } }]
    env:
      - name: DB_PASS
        valueFrom: { secretKeyRef: { name: db, key: pass } }
    volumeMounts: [{ name: cfg, mountPath: /etc/app, readOnly: true }]
volumes:
  - name: cfg
    configMap: { name: app-cfg, items: [{ key: MODE, path: mode.txt }] }
```
Env vars are read once at start; mounted volumes update in place (not with `subPath`). `immutable: true` blocks edits.

### SecurityContext
```yaml
spec:
  securityContext: { runAsNonRoot: true, runAsUser: 1000, fsGroup: 2000, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: app
      image: busybox:1.36
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: [ALL], add: [NET_BIND_SERVICE] }
```
Pod-level fields apply to all containers; container-level overrides. Capabilities exist only at container level. Check: `k exec x -- id`.

### ServiceAccount
```bash
k create sa app-sa ; k set serviceaccount deploy/web app-sa
k create token app-sa --duration=1h          # short-lived token for testing
```
Set `automountServiceAccountToken: false` on the SA or pod when the app never calls the API.

### Resources, ResourceQuota, LimitRange
```yaml
apiVersion: v1
kind: ResourceQuota
metadata: { name: team-quota }
spec:
  hard: { requests.cpu: "2", requests.memory: 2Gi, limits.cpu: "4", limits.memory: 4Gi, pods: "10" }
---
apiVersion: v1
kind: LimitRange
metadata: { name: defaults }
spec:
  limits:
    - type: Container
      default: { cpu: 200m, memory: 128Mi }          # limits when none given
      defaultRequest: { cpu: 100m, memory: 64Mi }
      max: { cpu: "1", memory: 512Mi }
```
`k set resources deploy/web --requests=cpu=100m,memory=64Mi --limits=cpu=200m,memory=128Mi`. Once a quota covers CPU/memory, pods without requests/limits are rejected unless a LimitRange fills them in. `k describe quota` shows used vs hard.

### RBAC basics
```bash
k create role pod-reader --verb=get,list,watch --resource=pods
k create rolebinding app-sa-reads --role=pod-reader --serviceaccount=ckad-lab:app-sa
k auth can-i list pods --as=system:serviceaccount:ckad-lab:app-sa -n ckad-lab     # yes
k auth can-i delete pods --as=system:serviceaccount:ckad-lab:app-sa -n ckad-lab   # no
```

### CRDs and custom resources
```bash
k get crd ; k api-resources --api-group=stable.example.com
k explain crontabs.spec ; k get crontabs -A
```
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata: { name: crontabs.stable.example.com }
spec:
  group: stable.example.com
  scope: Namespaced
  names: { plural: crontabs, singular: crontab, kind: CronTab, shortNames: [ct] }
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties: { cronSpec: { type: string }, image: { type: string } }
```
An operator is a controller that watches a CRD and reconciles it; the exam usually asks you to create or edit an instance, not write the controller.

## Services and Networking

### Services
```bash
k expose deploy web --port=80 --target-port=8080 --type=ClusterIP     # NodePort | LoadBalancer
k create svc nodeport web --tcp=80:8080 --node-port=30080 $do
k get endpointslices -l kubernetes.io/service-name=web                # empty = selector/labels mismatch
k run t --rm -it --image=curlimages/curl --restart=Never -- curl -s web.ckad-lab.svc.cluster.local
```
`port` = Service port, `targetPort` = container port (name or number), `nodePort` = 30000-32767. Headless (`clusterIP: None`) returns pod IPs from DNS.

### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: { name: web }
spec:
  ingressClassName: nginx
  tls: [{ hosts: [web.lab.local], secretName: web-tls }]
  rules:
    - host: web.lab.local
      http:
        paths:
          - { path: /, pathType: Prefix, backend: { service: { name: web, port: { number: 80 } } } }
          - { path: /api, pathType: Prefix, backend: { service: { name: api, port: { number: 8080 } } } }
```
`k create ingress web --class=nginx --rule="web.lab.local/*=web:80"`. Lab: `./lab.sh addon ingress`, then `curl -H 'Host: web.lab.local' localhost`.

### NetworkPolicy
Once any policy selects a pod for a direction, only what is explicitly allowed passes. Policies are additive. Remember DNS egress.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: api-allow-frontend }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: [Ingress, Egress]
  ingress:
    - from: [{ podSelector: { matchLabels: { role: frontend } } }]
      ports: [{ protocol: TCP, port: 8080 }]
  egress:
    - ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
```
Two entries under `from` = OR; `namespaceSelector` and `podSelector` in the same entry = AND. kind's default CNI does not enforce policies: use `./lab.sh kind up cilium`.

## Timed self-check (20 questions, 30 minutes, answer without the docs)
1. An init container with `restartPolicy: Always` behaves how?
2. Two containers in one pod need to exchange files. What do you add?
3. Create a Job that must succeed 5 times, 2 pods at a time, and give up after 3 failures.
4. A CronJob must never run two instances at once. Which field and value?
5. Run a CronJob `backup` right now without waiting for its schedule.
6. Roll `deploy/web` back to revision 2.
7. Which strategy settings give zero-downtime rollouts with one extra pod at a time?
8. Blue/green cutover with plain Kubernetes: what exactly do you change?
9. You need ~10% canary traffic without a service mesh. How?
10. Upgrade a Helm release but keep the values from the last install, changing only `image.tag`.
11. Render a Kustomize overlay without applying it.
12. A pod keeps restarting under load, but only because a slow endpoint times out. Which probe is wrong?
13. Get the logs of the crashed previous instance of container `app` in pod `x`.
14. A manifest uses `apiVersion: batch/v1beta1` for CronJob. What do you do?
15. Mount only key `nginx.conf` of ConfigMap `web-cfg` at `/etc/nginx/nginx.conf`.
16. Make container `app` run as UID 1000, block privilege escalation, drop all capabilities.
17. After creating a ResourceQuota with `requests.cpu`, new pods are rejected. Why, and the fix?
18. Check whether SA `builder` in ns `ci` can create Deployments.
19. A Service returns connection refused. Endpoints list is empty. First suspect?
20. Deny all ingress to every pod in ns `ckad-lab` in one short manifest.

<details><summary>Answers</summary>

1. Native sidecar: starts before app containers, runs for the pod's lifetime, is stopped after them, does not block pod completion.
2. A shared `emptyDir` volume mounted in both containers.
3. `k create job j --image=busybox:1.36 $do -- true`, then set `completions: 5`, `parallelism: 2`, `backoffLimit: 3`.
4. `spec.concurrencyPolicy: Forbid`.
5. `k create job backup-now --from=cronjob/backup`.
6. `k rollout undo deploy/web --to-revision=2`.
7. `type: RollingUpdate`, `maxSurge: 1`, `maxUnavailable: 0` (plus a readinessProbe so "ready" means ready).
8. The Service `selector` (for example `version: blue` -> `version: green`) via `k patch svc` or `k edit svc`.
9. Two Deployments sharing the Service's selector label, replicas 9:1 (stable:canary).
10. `helm upgrade <rel> <chart> --reuse-values --set image.tag=<tag>`.
11. `k kustomize <dir>` (or `kustomize build <dir>`).
12. The livenessProbe: too strict (timeout/threshold) or pointed at the slow endpoint. Readiness should handle "busy", liveness only "dead".
13. `k logs x -c app --previous`.
14. Change to `batch/v1` (check `k api-resources | grep cronjob`), re-apply.
15. `volumeMounts: [{name: cfg, mountPath: /etc/nginx/nginx.conf, subPath: nginx.conf}]` with a `configMap` volume `web-cfg`.
16. Container `securityContext: {runAsUser: 1000, allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}}`.
17. Pods without a CPU request are rejected under a quota that tracks it. Add requests, or a LimitRange with `defaultRequest`.
18. `k auth can-i create deployments --as=system:serviceaccount:ci:builder -n ci`.
19. Service selector does not match pod labels (or pods not Ready). Compare `k get svc -o wide` with `k get pod --show-labels`.
20. `kind: NetworkPolicy`, `spec: {podSelector: {}, policyTypes: [Ingress]}`.
</details>

## Resources
https://kubernetes.io/docs (allowed in the exam; practise finding pages by search), https://helm.sh/docs, https://killercoda.com/killer-shell-ckad, killer.sh (2 sessions with the exam), `lab/golden/ckad/README.md` (12 timed tasks; redo until each is < 6 minutes).


---
[[Home]] · [[Schedule]]
