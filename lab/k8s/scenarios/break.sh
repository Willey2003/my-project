#!/usr/bin/env bash
# CKA troubleshooting drills (30% of the exam). Each command injects one fault into the kind cluster.
# Diagnose with ONLY: kubectl get/describe/logs/events, crictl/journalctl inside nodes
# (docker exec -it lab-worker bash). Time-box each to 8 minutes.
#
#   ./break.sh list | <scenario> | random | hint <scenario> | reset
set -euo pipefail
NS=trouble
CLUSTER=${CLUSTER:-lab}
k() { kubectl -n $NS "$@"; }
ns() { kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f - >/dev/null; }

declare -A HINT=(
  [crashloop]="kubectl logs --previous; what env var does the command expect?"
  [imagepull]="describe the pod: look at the Events section and the exact image name"
  [pending]="describe the pod: FailedScheduling. Compare requests with 'kubectl describe node | grep -A5 Allocatable'"
  [no-endpoints]="kubectl get endpointslices -n trouble; compare Service selector with pod labels"
  [bad-probe]="restart count climbing but logs look fine? Check the probe port against the containerPort"
  [pvc-pending]="kubectl get sc ; the PVC asks for a class that does not exist"
  [dns]="pods cannot resolve names: kubectl -n kube-system get deploy coredns"
  [scheduler]="new pods stay Pending with NO events: who assigns nodes? docker exec ${CLUSTER}-control-plane ls /etc/kubernetes/manifests"
  [node-notready]="kubectl get nodes; docker exec -it ${CLUSTER}-worker2 bash; systemctl status kubelet; journalctl -u kubelet"
  [netpol]="curl from the client pod times out: kubectl get netpol -n trouble"
  [rbac]="kubectl auth can-i list pods -n trouble --as system:serviceaccount:trouble:reader"
)

inject() {
case "$1" in
  crashloop)
    ns; k create deploy crash --image=busybox:1.36 -- sh -c 'test -n "$DB_HOST" || { echo "FATAL: DB_HOST not set"; exit 1; }; sleep 3600' ;;
  imagepull)
    ns; k create deploy web --image=nginx:1.27-alpinee ;;
  pending)
    ns; k create deploy hungry --image=nginx:stable-alpine
    k set resources deploy hungry --requests=cpu=64,memory=1Gi ;;
  no-endpoints)
    ns; k create deploy shop --image=nginx:stable-alpine --replicas=2
    k create service clusterip shop --tcp=80:80 --dry-run=client -o yaml \
      | sed 's/app: shop/app: shop-frontend/' | kubectl apply -f - ;;
  bad-probe)
    ns; kubectl apply -n $NS -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: { name: probed }
spec:
  selector: { matchLabels: { app: probed } }
  template:
    metadata: { labels: { app: probed } }
    spec:
      containers:
        - name: nginx
          image: nginx:stable-alpine
          ports: [{ containerPort: 80 }]
          livenessProbe:
            httpGet: { path: /, port: 8080 }
            periodSeconds: 3
            failureThreshold: 2
YAML
    ;;
  pvc-pending)
    ns; kubectl apply -n $NS -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: data }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: fast-ssd
  resources: { requests: { storage: 1Gi } }
---
apiVersion: v1
kind: Pod
metadata: { name: db }
spec:
  containers:
    - name: db
      image: busybox:1.36
      command: ["sleep", "3600"]
      volumeMounts: [{ name: data, mountPath: /data }]
  volumes:
    - name: data
      persistentVolumeClaim: { claimName: data }
YAML
    ;;
  dns)
    kubectl -n kube-system scale deploy coredns --replicas=0
    ns; k run client --image=busybox:1.36 -- sleep 3600 ;;
  scheduler)
    docker exec "${CLUSTER}-control-plane" mv /etc/kubernetes/manifests/kube-scheduler.yaml /root/kube-scheduler.yaml
    sleep 10; ns; k create deploy after-break --image=nginx:stable-alpine ;;
  node-notready)
    docker exec "${CLUSTER}-worker2" systemctl stop kubelet
    docker exec "${CLUSTER}-worker2" systemctl disable kubelet >/dev/null 2>&1 ;;
  netpol)
    ns; k create deploy api --image=nginx:stable-alpine; k expose deploy api --port 80
    k run client --image=busybox:1.36 -- sleep 3600
    kubectl apply -n $NS -f - <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: lockdown }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: [Ingress]
  ingress:
    - from: [{ podSelector: { matchLabels: { role: frontend } } }]
YAML
    echo "task: 'client' must reach api:80 without deleting the policy (needs an enforcing CNI: kind up cilium)" ;;
  rbac)
    ns; k create sa reader
    k create role pod-reader --verb=get --resource=pods
    k create rolebinding reader --role=pod-reader --serviceaccount=$NS:reader
    echo "task: reader must be able to 'kubectl get pods' (list) in $NS and nothing more" ;;
  *) echo "unknown scenario $1"; exit 1 ;;
esac
echo "fault '$1' injected. Go fix it. (./break.sh hint $1 if stuck > 8 min)"
}

reset() {
  kubectl delete ns $NS --ignore-not-found --wait=false
  kubectl -n kube-system scale deploy coredns --replicas=2 >/dev/null
  docker exec "${CLUSTER}-control-plane" sh -c 'test -f /root/kube-scheduler.yaml && mv /root/kube-scheduler.yaml /etc/kubernetes/manifests/ || true'
  docker exec "${CLUSTER}-worker2" sh -c 'systemctl enable --now kubelet' >/dev/null 2>&1 || true
  echo "cluster reset"
}

case "${1:-list}" in
  list)   printf '%s\n' "${!HINT[@]}" | sort ;;
  hint)   echo "${HINT[${2:?scenario}]}" ;;
  reset)  reset ;;
  random) mapfile -t all < <(printf '%s\n' "${!HINT[@]}"); inject "${all[RANDOM % ${#all[@]}]}" ;;
  *)      inject "$1" ;;
esac
