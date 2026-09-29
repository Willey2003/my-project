# Phase 25 - KCA: Kyverno Certified Associate

**Plan weeks:** Golden track G5, about 1.5 weeks at 28 h, exam target Wed 9 Jun 2027 · **Hours:** 40 · **Exam:** KCA, 90 min online-proctored multiple choice, USD 250, one free retake · **Lab:** `./lab.sh kind up`, `./lab.sh addon kyverno`, `lab/golden/kyverno/`

You met policy engines in KCSA/CKS (Gatekeeper + Pod Security Admission). Kyverno does the same job with policies written as Kubernetes YAML instead of Rego, and it goes further: it can **mutate**, **generate** and **clean up** resources and **verify image signatures**. The exam is multiple choice, but a third of it is "Writing Policies", so you need to read a policy and predict exactly what it does. Write every policy in `lab/golden/kyverno/policies/` once from memory.

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Architecture, webhooks, install/upgrade, ClusterPolicy vs Policy, match/exclude, validate (patterns, anchors, deny, podSecurity), audit vs enforce, PolicyReports, mutate, generate | `lab/golden/kyverno/up.sh` running; policies 01-06 working; every policy rewritten once from a blank file |
| 2 (3 days) | verifyImages, cleanup, preconditions + JMESPath, PolicyExceptions, kyverno CLI (`apply`, `test`, `jp`), Pod Security policy library, self-check, sit exam | Policies 07-08 working, one PolicyException by hand, `kyverno test lab/golden/kyverno/test` green, KCA |

## Domains (verify the current curriculum on training.linuxfoundation.org and github.com/cncf/curriculum)
| Domain | Weight | Your lab |
|---|---|---|
| Writing Policies | 32% | `lab/golden/kyverno/policies/` 01-08, rewrite each from a blank file |
| Fundamentals of Kyverno | 18% | Architecture section below, `kubectl -n kyverno get deploy` |
| Installation, Configuration and Upgrades | 18% | `./lab.sh addon kyverno`, Helm values, `kubectl get validatingwebhookconfigurations` |
| Kyverno CLI | 12% | `kyverno apply` / `kyverno test` on `lab/golden/kyverno/test/` |
| Applying Policies | 10% | Enforce vs Audit, background scans, policy status |
| Policy Management | 10% | PolicyReports, PolicyExceptions, `kubectl get polr -A` |

## Exam technique
- ~60 questions in 90 minutes: answer everything on the first pass, flag and revisit. No negative marking.
- Most questions show a YAML snippet. Read in this order: **kind** (ClusterPolicy or Policy, or a cleanup/exception kind) -> **match/exclude** (which resources, which operations) -> **rule type** (validate/mutate/generate/verifyImages) -> **failure action** (Audit or Enforce) -> the pattern itself.
- Know the anchors cold: `()` conditional, `=()` equality/optional, `+()` add-if-absent, `^()` global, `X()` negation, `<()` existence. Wrong answers often swap `=()` and `+()`.
- Know the API groups: `kyverno.io/v1` ClusterPolicy/Policy, `kyverno.io/v2` PolicyException + ClusterCleanupPolicy/CleanupPolicy, `wgpolicyk8s.io/v1alpha2` PolicyReport/ClusterPolicyReport, `cli.kyverno.io/v1alpha1` Test, `policies.kyverno.io` for the newer CEL-based kinds.
- While studying, keep a scratch terminal with:
```bash
alias k=kubectl
kyverno apply policies/02-disallow-latest-tag.yaml --resource /tmp/pod.yaml   # instant feedback, no cluster needed
k explain clusterpolicy.spec.rules.validate --recursive | less
```

## Week 1 - architecture and admission webhooks
Kyverno runs as a set of controllers in namespace `kyverno` (Helm chart `kyverno/kyverno`):
| Controller | Job |
|---|---|
| **admission controller** | Serves the mutating + validating webhooks; runs validate, mutate and verifyImages rules on API requests. Scale it (3 replicas) for HA |
| **background controller** | Generate rules and mutate-existing rules (asynchronous, via UpdateRequests) |
| **reports controller** | Background scans of existing resources, writes PolicyReports |
| **cleanup controller** | Runs CleanupPolicies on their cron schedule and TTL-label deletions |
- Flow of an API request: authn -> authz -> **mutating admission** (Kyverno mutate + verifyImages add digests) -> schema validation -> **validating admission** (Kyverno validate, verifyImages checks) -> etcd.
- Kyverno **manages its own webhook configurations** (`kyverno-resource-mutating-webhook-cfg`, `kyverno-resource-validating-webhook-cfg`, `kyverno-policy-validating-webhook-cfg` ...) and narrows them to the kinds your policies match. Do not edit them by hand.
- `failurePolicy`: per policy `spec.failurePolicy: Fail|Ignore` - what the API server does if Kyverno is unreachable. `Fail` is safer, `Ignore` keeps the cluster usable during a Kyverno outage. `webhookTimeoutSeconds` defaults to 10.
- Resource filters in the `kyverno` ConfigMap (`resourceFilters`) exclude noisy kinds/namespaces (e.g. `[Event,*,*]`, `[*,kube-system,*]`) from all policies.
- Install/upgrade: `helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace` (the lab does this via `./lab.sh addon kyverno`); HA values: `admissionController.replicas=3`, `backgroundController.replicas=2`, `cleanupController.replicas=2`, `reportsController.replicas=2`. Upgrades: read the release notes, upgrade CRDs with the chart, one minor at a time.
```bash
kubectl -n kyverno get deploy,svc ; kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations | grep kyverno
kubectl get crd | grep kyverno ; kubectl get cpol ; kubectl get pol -A
```

## Week 1 - policy anatomy: ClusterPolicy vs Policy, match/exclude
- **ClusterPolicy** (`cpol`) is cluster-scoped and can match resources in any namespace plus cluster-scoped kinds. **Policy** (`pol`) lives in a namespace and only ever applies to resources in that namespace (good for delegating to teams).
- A policy is a list of **rules**; each rule has exactly one of `validate`, `mutate`, `generate`, `verifyImages`.
- `match` / `exclude` use `any` (OR) or `all` (AND) of resource filters: `kinds`, `names`, `namespaces`, `selector`, `namespaceSelector`, `operations` (CREATE/UPDATE/DELETE/CONNECT), plus `subjects`, `roles`, `clusterRoles` (who made the request). Wildcards work in names/namespaces. `exclude` always wins over `match`.
- Kinds can be `Pod`, `apps/v1/Deployment`, `Pod/exec` (subresource) or `*`.
- **Auto-gen:** a rule that matches `Pod` is automatically rewritten for Deployment, DaemonSet, StatefulSet, ReplicaSet, Job, CronJob (rules named `autogen-...`) so users see errors at `kubectl apply deploy` time, not later in the ReplicaSet. Control it with the annotation `pod-policies.kyverno.io/autogen-controllers`.
- Other spec fields to know: `background: true` (also scan existing resources -> reports), `admission: true`, `failurePolicy`, `webhookTimeoutSeconds`, `useServerSideApply` (generate), `schemaValidation`.
```yaml
spec:
  background: true
  rules:
    - name: check-app-label
      match:   { any: [ { resources: { kinds: [Pod], namespaces: [kyverno-lab] } } ] }
      exclude: { any: [ { subjects: [ { kind: ServiceAccount, name: ci-bot, namespace: ci } ] } ] }
      validate:
        failureAction: Audit
        message: "label app.kubernetes.io/name is required"
        pattern: { metadata: { labels: { app.kubernetes.io/name: "?*" } } }
```

## Week 1 - validate rules and audit vs enforce
Five styles of validate:
| Style | Use | Example |
|---|---|---|
| `pattern` | Resource must match an overlay; `*` any, `?` one char, `?*` non-empty, `!` not, a pipe for OR, `>=`/`<` numbers and quantities | `image: "!*:latest"` |
| `anyPattern` | List of patterns, one must match | tag present OR digest present |
| `deny` + `conditions` | Deny when JMESPath conditions are true (operators `Equals`, `NotEquals`, `AnyIn`, `AllNotIn`, `GreaterThan`, `DurationLessThan` ...) | block `DELETE` of namespaces with label `protected=true` |
| `podSecurity` | Apply a Pod Security Standard level with optional `exclude` controls | `level: baseline, version: latest` |
| `cel` | CEL expressions (like ValidatingAdmissionPolicy) | `object.spec.replicas <= 5` |
- **Anchors** in patterns: `(name): "web*"` conditional (only check the rest if this matches), `=(hostPath)` "if present, must match", `^(containers)` global condition, `X(hostPath)` must not exist, `<(key)` existence anywhere in a list.
- **Enforce** blocks the request with the `message`. **Audit** admits it and records a `fail` result in a PolicyReport. Current syntax is per rule: `validate.failureAction: Audit|Enforce` (older policies use `spec.validationFailureAction`; `validationFailureActionOverrides` / `failureActionOverrides` switch the action per namespace).
- Roll-out pattern used in real clusters: deploy in **Audit**, read reports for a week, fix offenders, switch to **Enforce**.
- Lab: `./up.sh` in `lab/golden/kyverno/` applies the policies (07 once you paste a cosign key), sends the bad pods through the webhooks with `--dry-run=server` and creates a good one; read the denial messages and `kubectl -n kyverno-lab get polr`.

## Week 1 - PolicyReports
- `PolicyReport` (namespaced, `polr`) and `ClusterPolicyReport` (`cpolr`) follow the Policy WG API `wgpolicyk8s.io/v1alpha2`. One report per resource (named by UID), with results `pass`, `fail`, `warn`, `error`, `skip` and a `summary`.
- Produced by admission requests (Audit results) and by **background scans** (`background: true`, periodic, default every hour).
```bash
kubectl get polr -A ; kubectl -n kyverno-lab get polr -o wide
kubectl -n kyverno-lab get polr -o jsonpath='{range .items[*].results[?(@.result=="fail")]}{.policy}{" / "}{.rule}{": "}{.message}{"\n"}{end}'
```
- Policy Reporter (separate Helm chart) gives a UI and forwards results to Slack/Loki/etc. Know it exists.

## Week 1 - mutate rules
- `patchStrategicMerge`: overlay YAML merged into the resource. Anchor `+(field)` adds only if absent (never overwrites the user), `(name): "*"` conditional selects which list items to touch.
- `patchesJson6902`: RFC 6902 ops (`add`, `replace`, `remove`) on exact paths - use for list inserts and removals.
- `foreach`: iterate a list (`list: "request.object.spec.containers"`) and patch each element, with `{{element.name}}`.
- **mutateExisting**: `mutate.targets` + `mutateExistingOnPolicyUpdate: true` patches resources that already exist (background controller, needs RBAC).
- Mutation runs **before** validation, so a mutate policy can make a resource pass a validate policy.
```yaml
mutate:
  patchStrategicMerge:
    spec:
      securityContext: { +(runAsNonRoot): true, +(seccompProfile): { type: RuntimeDefault } }
      containers:
        - (name): "*"
          securityContext: { +(allowPrivilegeEscalation): false }
```
Lab: `policies/03-add-default-securitycontext.yaml`; `kubectl -n kyverno-lab get pod good-pod -o yaml | grep -A4 securityContext`.

## Week 1 - generate rules
- Create a resource when a trigger resource appears: `generate: {apiVersion, kind, name, namespace, data: {...}}` or `clone: {namespace, name}` (copy an existing Secret/ConfigMap) or `cloneList` (many, by selector).
- `synchronize: true` keeps the generated resource in line with the policy (edits are reverted, deletion is re-created; deleting the trigger deletes it). `false` = create once and leave it alone.
- `generateExisting: true` also generates for triggers that existed before the policy.
- The **background controller** creates the resource, so its ServiceAccount needs RBAC for that kind - add a ClusterRole labelled `rbac.kyverno.io/aggregate-to-background-controller: "true"` (see `policies/04-generate-default-networkpolicy.yaml`).
- Classic uses: default-deny NetworkPolicy, ResourceQuota/LimitRange, image pull Secret per namespace, RoleBinding for a team.

## Week 2 - verifyImages
- Checks image signatures and attestations (Sigstore cosign keys or keyless, Notary v2) at admission. Attestors: `keys` (public key, KMS), `keyless` (issuer + subject, Rekor transparency log), `certificates`.
- `imageReferences: ["ghcr.io/myorg/*"]` selects images; `attestations` checks in-toto predicates (SBOM, SLSA provenance, vuln scan) with conditions.
- `mutateDigest: true` rewrites `image:tag` to `image@sha256:...` so the verified image is exactly what runs; `verifyDigest: true` requires a digest; `required: true` fails unsigned images.
- Results are cached (`imageVerifyCache`) and the verified digest is recorded in the `kyverno.io/verify-images` annotation.
- `failureAction: Audit` for rollout, then `Enforce`. Lab file `policies/07-verify-images.yaml` ships in Audit with a placeholder key - generate your own with `cosign generate-key-pair` (the CKS lab `lab/security/supply-chain.sh` already does this) and paste `cosign.pub` in.

## Week 2 - cleanup policies and TTL
- `ClusterCleanupPolicy` / `CleanupPolicy` (`kyverno.io/v2`): `schedule` (cron), `match`/`exclude`, `conditions` (JMESPath on `target.*`). The cleanup controller deletes matching resources on schedule.
- **TTL label**: put `cleanup.kyverno.io/ttl: 2h` (or an absolute time) on any resource and the cleanup controller deletes it when it expires - no policy needed, but the controller needs delete RBAC for that kind.
- RBAC again: aggregate delete permissions to the cleanup controller with a ClusterRole labelled `rbac.kyverno.io/aggregate-to-cleanup-controller: "true"` (see `policies/08-cleanup-bare-pods.yaml`).

## Week 2 - preconditions, variables and JMESPath
- **Variables**: `{{request.object.metadata.name}}`, `{{request.operation}}`, `{{request.userInfo.username}}`, `{{serviceAccountName}}`, `{{request.namespace}}`, `{{images.containers.*.tag}}`, `{{element}}` in foreach, `{{target}}` in cleanup/mutateExisting.
- **context** entries load extra data into variables: `configMap` (from a ConfigMap), `apiCall` (Kubernetes API GET, with `jmesPath`), `service` (external HTTP call), `imageRegistry` (read image config/manifest), `variable` (compute a value once).
- **preconditions**: `any`/`all` conditions that decide whether the rule runs at all (a failed precondition = `skip`, not `fail`). Use them to skip DELETE requests, system users, or resources without a given label.
- **JMESPath** functions to recognise: `length()`, `contains()`, `to_string()`, `starts_with()`, `split()`, `regex_match()`, `lookup()`, `base64_decode()`, `time_since()`, `truncate()`; default values with `||` (`{{ request.object.metadata.labels.team || 'none' }}`).
- Try expressions offline: `kyverno jp query -i pod.json "spec.containers[].image"`.
```yaml
preconditions:
  all:
    - key: "{{ request.operation || 'BACKGROUND' }}"
      operator: AnyIn
      value: [CREATE, UPDATE]
    - key: "{{ request.object.metadata.labels.\"lab.devops/skip\" || '' }}"
      operator: NotEquals
      value: "true"
```

## Week 2 - PolicyExceptions
- `PolicyException` (`kyverno.io/v2`) exempts specific resources from specific rules without editing the policy: `spec.exceptions: [{policyName, ruleNames}]` + `spec.match` (+ optional `conditions`, and `podSecurity` control exemptions).
- Disabled or restricted by default depending on version: enable with Helm `features.policyExceptions.enabled=true` and limit where they may live with `features.policyExceptions.namespace=<ns>` so random users cannot exempt themselves. Guard creation with RBAC (and, ideally, with a Kyverno policy on PolicyException itself).
```yaml
apiVersion: kyverno.io/v2
kind: PolicyException
metadata: { name: legacy-app-latest, namespace: kyverno }
spec:
  exceptions: [ { policyName: disallow-latest-tag, ruleNames: [validate-image-tag, autogen-validate-image-tag] } ]
  match: { any: [ { resources: { kinds: [Pod, Deployment], namespaces: [kyverno-lab], names: ["legacy-*"] } } ] }
```

## Week 2 - kyverno CLI
```bash
kyverno version
kyverno apply policies/ --resource test/resources-bad.yaml          # evaluate without a cluster
kyverno apply policies/02-disallow-latest-tag.yaml --cluster -n kyverno-lab   # against live resources
kyverno apply policies/03-add-default-securitycontext.yaml -r pod.yaml -o /tmp/mutated/   # see the mutated output
kyverno test lab/golden/kyverno/test                               # runs every kyverno-test.yaml under the path
kyverno test . --detailed-results ; kyverno test . --fail-only
kyverno create test -p policy.yaml -r resource.yaml                # scaffold a test file
kyverno jp query -i pod.json 'metadata.labels'                     # JMESPath playground
```
- `kyverno-test.yaml` (`cli.kyverno.io/v1alpha1`, kind `Test`): `policies`, `resources`, optional `variables` (values file for context/namespace labels), and `results` with `policy`, `rule`, `resources`, `kind`, `result: pass|fail|skip` (mutate tests add `patchedResources`, generate tests `generatedResource`).
- Put `kyverno test` in CI next to the policies so every change is tested before Argo CD syncs it (Phase 17 GitOps).

## Week 2 - Pod Security policy library
- https://kyverno.io/policies lists 300+ ready policies; `github.com/kyverno/policies` has them as Kustomize/Helm (`kyverno/kyverno-policies` chart, `podSecurityStandard: baseline|restricted`, `validationFailureAction: Audit|Enforce`).
- The Pod Security set mirrors PSS one policy per control: baseline (`disallow-privileged-containers`, `disallow-host-namespaces`, `disallow-host-path`, `disallow-capabilities` ...) and restricted (`require-run-as-nonroot`, `restrict-seccomp-strict`, `disallow-privilege-escalation`, `restrict-volume-types` ...).
- Shortcut: one rule with `validate.podSecurity: {level: restricted, version: latest}` plus `exclude` entries for controls you must relax (e.g. `controlName: Capabilities`, `images: [...]`).
- Compared with built-in Pod Security Admission: PSA is namespace-level and all-or-nothing per level; Kyverno adds granular exclusions, audit reports per resource, mutation to *fix* pods, and works together with PSA.
```bash
helm upgrade --install kyverno-policies kyverno/kyverno-policies -n kyverno --set podSecurityStandard=baseline --set validationFailureAction=Audit
kubectl get cpol ; kubectl get polr -A | head
```

## Self-check
1. Which Kyverno controller handles generate rules, and which one serves the admission webhooks?
2. In what order do Kyverno mutate and validate rules run for one API request, and why does it matter?
3. A `Policy` in namespace `team-a` matches `kinds: [Pod]` with no namespace filter. Which pods does it affect?
4. What does `exclude` do when a resource matches both `match` and `exclude`?
5. `any` vs `all` under `match`: what is the difference?
6. What is auto-gen, and how do you turn it off for one policy?
7. Explain the difference between `=(hostPath)` and `+(hostPath)`.
8. What does the pattern `image: "!*:latest"` allow and reject?
9. A validate rule has `failureAction: Audit`. A non-compliant pod is created. What happens and where do you see it?
10. What happens to API requests if all Kyverno admission pods are down and the policy has `failurePolicy: Fail`?
11. Name three `context` entry types and what each loads.
12. A precondition evaluates to false. What result does the rule record?
13. What does `synchronize: true` change on a generate rule?
14. A generate rule for NetworkPolicy is accepted but nothing is created. What is the most likely cause?
15. What does `mutateDigest: true` do in a verifyImages rule?
16. Which kind and API group deletes resources on a cron schedule, and what is the no-policy alternative?
17. Which two Helm settings govern PolicyExceptions, and why restrict the namespace?
18. What goes in a `kyverno-test.yaml` result entry?
19. `kyverno apply` vs `kyverno test`: when do you use each?
20. How would you enforce the PSS `restricted` level except the capabilities control, in one rule?

<details><summary>Answers</summary>

1. Generate (and mutate-existing): the **background controller**. Webhooks (validate, mutate, verifyImages): the **admission controller**.
2. Mutating webhook first, validating second. A mutate policy can fix a resource (e.g. add a securityContext) so it then passes validation.
3. Only pods in `team-a` - a namespaced Policy can never reach other namespaces.
4. Exclude wins: the rule does not apply to that resource.
5. `any` = the rule matches if at least one resource filter matches (OR); `all` = every filter must match (AND).
6. Kyverno copies Pod rules to Deployment/DaemonSet/StatefulSet/Job/CronJob etc. (`autogen-` rules). Turn off with annotation `pod-policies.kyverno.io/autogen-controllers: none`.
7. `=(hostPath)` is an equality anchor: if the field exists it must match the pattern (validate). `+(hostPath)` is add-if-absent (mutate): set it only when the user has not.
8. Rejects any image ending in `:latest`; allows everything else - including images with no tag at all, which is why `02-disallow-latest-tag.yaml` also has a `*:*` rule.
9. It is admitted; a `fail` result for that rule appears in the namespace's PolicyReport (`kubectl get polr`) and an event is emitted.
10. They are rejected (the API server cannot call the webhook). With `Ignore` they would be admitted unchecked.
11. Any three: `configMap` (ConfigMap data), `apiCall` (a Kubernetes API GET, filtered by `jmesPath`), `service` (external HTTP call), `imageRegistry` (image manifest/config), `variable` (computed value).
12. `skip` - the rule did not apply; it is neither pass nor fail.
13. Kyverno keeps the generated resource in sync: manual edits are reverted, deletion is re-created, policy changes propagate, and deleting the trigger removes the generated resource.
14. Missing RBAC: the background controller ServiceAccount cannot create NetworkPolicies. Aggregate a ClusterRole with `rbac.kyverno.io/aggregate-to-background-controller: "true"`.
15. Replaces the image tag with the verified `@sha256:` digest in the pod spec, so the running image cannot change behind a mutable tag.
16. `ClusterCleanupPolicy` / `CleanupPolicy` in `kyverno.io/v2` (schedule + match + conditions). Alternative: the `cleanup.kyverno.io/ttl` label on the resource.
17. `features.policyExceptions.enabled` and `features.policyExceptions.namespace`. Restricting the namespace (plus RBAC) stops any user who can create objects from exempting their own workloads.
18. `policy`, `rule`, `resources` (names), `kind`, `result` (pass/fail/skip); plus `patchedResources` for mutate or `generatedResource` for generate.
19. `apply`: ad-hoc evaluation of policies against local files or a live cluster (`--cluster`), prints results/mutations. `test`: declarative, repeatable assertions of expected results - for CI.
20. `validate: {podSecurity: {level: restricted, version: latest, exclude: [{controlName: Capabilities, images: ["*"]}]}}`.
</details>

## Resources
https://kyverno.io/docs (read Writing Policies end to end), https://kyverno.io/policies (library - read 20 policies and predict what each does before opening the YAML), https://github.com/cncf/curriculum (KCA PDF), https://playground.kyverno.io (browser playground for policies + resources), Kyverno CLI docs for `apply`/`test`, `lab/golden/kyverno/README.md`
