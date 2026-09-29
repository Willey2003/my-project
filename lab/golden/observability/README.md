# Golden Kubestronaut - observability labs (PCA + OTCA)

Hands-on material for `study-guides/22-pca-prometheus.md` and `study-guides/23-otca-opentelemetry.md`.

## Prerequisites
```bash
./lab.sh kind up                  # kind cluster "lab" + local registry localhost:5001
./lab.sh addon monitoring         # kube-prometheus-stack (release kps, ns monitoring): Prometheus Operator CRDs, Prometheus, Alertmanager, Grafana
lab/golden/observability/up.sh    # or: up.sh pca | up.sh otel | up.sh down
```
`up.sh` needs `kubectl`; the `otel` part also needs `docker` (and `kind` if the local registry is not running).

## Layout
| Path | Namespace | What |
|---|---|---|
| `pca/namespace.yaml` | `prom-lab` (`lab.devops/component: pca`) | namespace |
| `pca/app.py`, `pca/app.yaml` | prom-lab | `shop-api`: Python + prometheus_client (counter, histogram, gauges, info), 2 replicas, self-generated traffic; code mounted from a ConfigMap, no image build |
| `pca/servicemonitor.yaml` | prom-lab | ServiceMonitor (active, `release: kps`) and an equivalent PodMonitor (disabled via `release: disabled`) |
| `pca/rules.yaml` | - | plain rule file for `promtool check rules` |
| `pca/prometheusrule.yaml` | prom-lab | the same groups as a PrometheusRule CR (recording rules + 5 alerts) |
| `pca/alertmanager.yaml` | - | raw Alertmanager config (routing tree, `continue`, inhibition, time intervals) for `amtool` |
| `pca/alertmanagerconfig.yaml` | prom-lab | AlertmanagerConfig CR + `alert-sink` webhook echo server |
| `pca/promql-exercises.md` | - | 25 PromQL tasks with answers |
| `otel/namespace.yaml` | `otel-lab` (`lab.devops/component: otca`) | namespace |
| `otel/collector-config.yaml`, `otel/collector.yaml` | otel-lab | Collector (contrib) gateway: OTLP in -> debug + Prometheus exporter (:8889) + Jaeger (OTLP); ServiceMonitor for :8889 and self-metrics :8888 |
| `otel/jaeger.yaml` | otel-lab | Jaeger v2 all-in-one (in-memory) |
| `otel/app/` | otel-lab | Flask demo run with `opentelemetry-instrument` (Dockerfile, requirements, Deployment + load generator) |
| `otel/otel-exercises.md` | - | 20 OTel tasks with answers |

Both directories are kustomizations (`kubectl apply -k pca`, `kubectl apply -k otel`); the ConfigMaps for `app.py` and `collector-config.yaml` are generated with a hash suffix, so editing those files and re-applying rolls the pods.

## Notes
- The kps Prometheus only selects ServiceMonitors/PrometheusRules labelled `release: kps` - that is why every CR here carries it. Remove the label and the target/rules vanish (a good exam-style debugging drill).
- `up.sh` merge-patches the kps Alertmanager CR so it reads AlertmanagerConfig from all namespaces (only if the selectors are unset). A `helm upgrade` of the addon may revert it - just re-run `up.sh pca`.
- The operator adds a `namespace="prom-lab"` matcher to the AlertmanagerConfig route, so the rules keep `namespace` in every aggregation.
- Keep `rules.yaml` and `prometheusrule.yaml` in sync. To regenerate the CR from the plain file:
  ```bash
  cd lab/golden/observability/pca && python3 - <<'PY'
  import yaml; g = yaml.safe_load(open("rules.yaml"))["groups"]
  d = yaml.safe_load(open("prometheusrule.yaml")); d["spec"]["groups"] = g
  open("prometheusrule.yaml", "w").write(yaml.safe_dump(d, sort_keys=False, width=200))
  PY
  ```
  (this drops the header comment - re-add it if you care).
- Validation used for this directory:
  ```bash
  python3 -c 'import sys,yaml; [list(yaml.safe_load_all(open(f))) for f in sys.argv[1:]]' $(find lab/golden/observability -name '*.yaml')
  promtool check rules lab/golden/observability/pca/rules.yaml
  amtool check-config lab/golden/observability/pca/alertmanager.yaml
  python3 -m py_compile lab/golden/observability/pca/app.py lab/golden/observability/otel/app/app.py
  bash -n lab/golden/observability/up.sh
  ```
- Image tags are pinned (Collector 0.135.0, Jaeger 2.10.0, Python 3.12, OTel Python 1.37.0/0.58b0); bump them together when the exam curriculum moves.

## Cleanup
`lab/golden/observability/up.sh down` (deletes both namespaces; the monitoring addon stays).
