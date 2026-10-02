#!/usr/bin/env bash
# Week 39 / EX280: HTPasswd identity provider + RBAC. Run as kubeadmin (oc login -u kubeadmin ...).
set -euo pipefail
htpasswd -c -B -b /tmp/users.htpasswd admin redhat123
htpasswd -B -b /tmp/users.htpasswd developer developer
htpasswd -B -b /tmp/users.htpasswd auditor auditor
oc create secret generic htpass-secret --from-file=htpasswd=/tmp/users.htpasswd -n openshift-config \
  --dry-run=client -o yaml | oc apply -f -
oc apply -f - <<'YAML'
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
    - name: lab-htpasswd
      mappingMethod: claim
      type: HTPasswd
      htpasswd:
        fileData:
          name: htpass-secret
YAML
oc adm policy add-cluster-role-to-user cluster-admin admin
oc adm groups new dev-team developer || true
oc new-project team-a || oc project team-a
oc policy add-role-to-group edit dev-team -n team-a
oc adm policy add-cluster-role-to-user cluster-reader auditor
# Exam classic: stop everyone from creating projects except admins
oc adm policy remove-cluster-role-from-group self-provisioner system:authenticated:oauth
echo "wait ~2 min for oauth pods to roll (oc get pods -n openshift-authentication -w), then: oc login -u developer -p developer"
