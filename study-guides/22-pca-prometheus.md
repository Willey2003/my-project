# Phase 22 - PCA: Prometheus Certified Associate

**Golden track step:** G2 · 23 Apr-6 May 2027 (see schedule) · **Hours:** 56 · **Exam:** PCA, 90 min online proctored, multiple choice (~60 questions), USD 250, one free retake · **Lab:** `./lab.sh addon monitoring`, `lab/golden/observability/up.sh pca`

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Architecture, data model, PromQL (selectors, rate/irate/increase, aggregation, histograms, joins, subqueries), exporters, service discovery, relabelling | `pca/promql-exercises.md` 1-25 solved without peeking; notes page of PromQL gotchas |
| 2 | Recording/alerting rules, Alertmanager routing and inhibition, instrumentation libraries, Grafana dashboards, federation/remote write, mocks, sit exam | PrometheusRule + Alertmanager config reviewed with `promtool`/`amtool`; a Grafana dashboard JSON in your repo; PCA |

## Domains (sheet weights; verify the current curriculum on training.linuxfoundation.org)
| Domain | Weight | Your lab |
|---|---|---|
| PromQL | 28% | `pca/promql-exercises.md` in the Prometheus UI (`:9090/graph`) |
| Observability Concepts | 18% | this page, "Concepts" section |
| Prometheus Fundamentals | 20% | `kubectl -n monitoring get prometheus -o yaml`, `/targets`, `/config`, `/tsdb-status` |
| Alerting & Dashboarding | 18% | `pca/prometheusrule.yaml`, `pca/alertmanager.yaml`, Grafana on `:3000` |
| Instrumentation & Exporters | 16% | `pca/app.py` (prometheus_client), node-exporter and blackbox |

The exam is theory plus reading PromQL and YAML. You will not type into a live cluster, but the fastest way to answer "what does this query return" is to have run hundreds of queries yourself.

## Exam technique
- Read the query twice: range vector vs instant vector is the most common trap (`rate()` needs a range vector; `sum()` needs an instant vector; you cannot graph a range vector).
- Eliminate answers that break type rules first: `rate(sum(x)[5m])` is invalid, `sum(rate(x[5m]))` is correct ("rate then sum").
- Counters only go up (resets are handled by `rate`/`increase`); gauges go up and down; never `rate()` a gauge - use `deriv()` or `delta()`.
- Know which component does what: Prometheus scrapes + evaluates rules + sends alerts; Alertmanager groups, dedups, silences, inhibits, routes, notifies. Prometheus never sends email.
- Flag and move on; 90 minutes for ~60 questions is 1.5 min each. Leave nothing blank (no negative marking).

## Concepts - observability and Prometheus architecture
- **Three pillars:** metrics (cheap aggregates, alerting), logs (events, context), traces (request paths). Prometheus is metrics only. SLI/SLO/SLA and error budgets; RED (Rate, Errors, Duration) for services, USE (Utilisation, Saturation, Errors) for resources.
- **Pull model:** Prometheus scrapes HTTP `/metrics` on targets every `scrape_interval` (default 1m, commonly 15-30s). Push only via **Pushgateway** for short-lived batch jobs (it never forgets a series - delete it yourself; not for service-level metrics).
- **Components:** Prometheus server (retrieval, TSDB, rule engine, HTTP API/UI), exporters, client libraries, Pushgateway, Alertmanager, service discovery, Grafana (visualisation, not part of Prometheus).
- **TSDB:** 2 h in-memory head block + WAL, compacted to on-disk blocks; retention by `--storage.tsdb.retention.time` (default 15d) or `.size`. Local storage is not clustered or replicated - HA means two identical Prometheus servers scraping the same targets, Alertmanager dedups their alerts.
- **Staleness:** a series missing from a scrape is marked stale; instant queries look back 5 minutes (`--query.lookback-delta`).
- **Synthetic series per target:** `up` (1 scraped OK / 0 failed), `scrape_duration_seconds`, `scrape_samples_scraped`, `scrape_series_added`.
- Config reload: `SIGHUP` or `POST /-/reload` (needs `--web.enable-lifecycle`). Validate first: `promtool check config prometheus.yml`.

## Data model and labels
```
http_requests_total{job="shop-api", instance="10.0.0.7:8000", method="GET", code="200"}  1027 @1727600000
<metric name>       <label set: key="value" ...>                                             <float64> <ms timestamp>
```
- A **time series** is identified by metric name + full label set; the name is itself the label `__name__`. Change any label value = new series.
- Naming: `snake_case`, a unit suffix in base units (`_seconds`, `_bytes`, `_ratio`), counters end in `_total`, `_info` for metadata gauges set to 1.
- **Cardinality:** every unique label combination is a series in memory. Never put user IDs, emails, full URLs or request IDs in labels. Check with `topk(10, count by (__name__)({__name__=~".+"}))` and `/tsdb-status`.
- Target labels added at scrape: `job` (from the scrape config) and `instance` (host:port). `honor_labels: true` keeps the target's own values on conflict (needed for Pushgateway and federation).
- **Metric types:**

| Type | Behaviour | Typical query |
|---|---|---|
| Counter | monotonically increasing, resets to 0 on restart | `rate(x_total[5m])` |
| Gauge | arbitrary value, up and down | `x`, `avg_over_time(x[10m])`, `deriv(x[10m])` |
| Histogram | `_bucket{le="..."}` (cumulative), `_sum`, `_count`; aggregatable across instances | `histogram_quantile(0.95, sum by (le) (rate(x_bucket[5m])))` |
| Summary | client-side `{quantile="0.99"}`, `_sum`, `_count`; quantiles cannot be aggregated | `x{quantile="0.99"}` |
| Native histogram | sparse exponential buckets in one series (feature flag in 2.x, stable-ish in 3.x) | `histogram_quantile(0.95, sum(rate(x[5m])))` |

## PromQL
**Selectors and matchers:** `=`, `!=`, `=~` (fully anchored RE2), `!~`. `http_requests_total{code=~"5.."}`. A selector must have at least one matcher that does not match the empty string. Range selector `[5m]`; `offset 1h`; `@ 1727600000` or `@ end()`.

**Counters:**
- `rate(x[5m])` per-second average over the window, extrapolated to the window edges, handles counter resets. Use for alerts and graphs.
- `irate(x[5m])` uses only the last two samples - spiky, for fast-moving graphs, never in alerts or recording rules.
- `increase(x[1h])` = `rate(x[1h]) * 3600`; can return non-integers due to extrapolation.
- Window rule of thumb: at least 4 x `scrape_interval`. Always apply `rate` before `sum` (rate-then-sum), otherwise counter resets are lost.

**Aggregation:** `sum`, `avg`, `min`, `max`, `count`, `count_values`, `group`, `stddev`, `stdvar`, `topk`, `bottomk`, `quantile`, `limitk`/`limit_ratio` (3.x, experimental). `by (a,b)` keeps only those labels; `without (a)` drops them. `topk(3, ...)` keeps original labels and can return more than 3 series on a graph (per step).
```promql
sum by (code) (rate(lab_http_requests_total[5m]))                       # req/s per status code
sum(rate(lab_http_requests_total{code=~"5.."}[5m])) / sum(rate(lab_http_requests_total[5m]))   # error ratio
count by (job) (up == 0)                                                 # down targets per job
avg_over_time(lab_queue_jobs[10m])  max_over_time(...)  quantile_over_time(0.9, ...)  # _over_time = per series over a range
```

**Histograms:**
```promql
histogram_quantile(0.95, sum by (le) (rate(lab_http_request_duration_seconds_bucket[5m])))            # p95 overall
histogram_quantile(0.95, sum by (le, path) (rate(lab_http_request_duration_seconds_bucket[5m])))      # p95 per path - keep le!
sum(rate(lab_http_request_duration_seconds_sum[5m])) / sum(rate(lab_http_request_duration_seconds_count[5m]))  # mean latency
sum(rate(lab_http_request_duration_seconds_bucket{le="0.25"}[5m])) / sum(rate(lab_http_request_duration_seconds_count[5m])) # % under 250 ms (Apdex-style SLI)
```
The quantile is linearly interpolated inside a bucket, so its accuracy depends on bucket boundaries. If the quantile falls in the `+Inf` bucket, the result is the upper bound of the highest finite bucket.

**Binary operators and vector matching:**
- Arithmetic `+ - * / % ^`, comparison `== != > < >= <=` (filter; add `bool` to return 0/1), logical/set `and`, `or`, `unless`.
- One-to-one matching needs identical label sets on both sides; adjust with `on(labels)` (match only on these) or `ignoring(labels)` (match on all but these).
- Many-to-one / one-to-many: `group_left(extra_labels)` / `group_right` - the "many" side is the one named. Classic join to copy a label from an `_info` metric:
```promql
sum by (pod) (rate(lab_http_requests_total[5m]))
  * on (pod) group_left (version) lab_build_info                         # attach version label to each pod's rate
rate(errors_total[5m]) / ignoring (code) group_left rate(requests_total[5m])
up == 0 unless on (instance) maintenance_mode == 1                        # alert only when not in maintenance
```
- Operator precedence (high to low): `^`, `* / % atan2`, `+ -`, comparisons, `and unless`, `or`.

**Subqueries:** `<instant query>[<range>:<resolution>]` produces a range vector from an expression, e.g. max 5m-rate seen in the last hour:
```promql
max_over_time(rate(lab_http_requests_total[5m])[1h:1m])
deriv(sum(lab_queue_jobs)[30m:1m]) > 0                                  # queue trend over 30 min
```
Subqueries are expensive; prefer recording rules for anything used repeatedly.

**Other functions to know:** `absent(x)` / `absent_over_time(x[10m])` (alert on missing series), `predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0`, `delta`, `deriv`, `changes`, `resets`, `clamp_min/max`, `label_replace(v, "dst", "$1", "src", "(.*):.*")`, `label_join`, `time()`, `timestamp()`, `vector(0)`, `scalar()`, `sort`/`sort_desc`, `round`, `ceil`, `floor`, `abs`, `ln`, `exp`.

## Recording and alerting rules
```yaml
groups:
- name: shop-api.rules
  interval: 30s                        # optional, defaults to global evaluation_interval
  rules:
  - record: job:lab_http_requests:rate5m          # level:metric:operations naming
    expr: sum by (job) (rate(lab_http_requests_total[5m]))
  - alert: ShopApiHighErrorRate
    expr: job:lab_http_errors:ratio_rate5m > 0.05
    for: 5m                            # pending -> firing only after 5m continuously true
    keep_firing_for: 2m                # avoid flapping on resolve (2.42+)
    labels: { severity: warning }
    annotations:
      summary: "{{ $labels.job }} 5xx ratio is {{ $value | humanizePercentage }}"
      runbook_url: https://example.com/runbooks/shop-api
```
- Rules in a group run sequentially (a recording rule can feed a later one); groups run in parallel.
- Alert states: **inactive -> pending -> firing**. The series `ALERTS{alertname,alertstate}` and `ALERTS_FOR_STATE` exist for inspection.
- Validate and test: `promtool check rules rules.yaml`; unit tests with `promtool test rules tests.yaml` (`input_series`, `alert_rule_test`, `promql_expr_test`).
- In Kubernetes (prometheus-operator) rules are `PrometheusRule` CRs selected by label (`release: kps` for the lab's kube-prometheus-stack). Lab: `lab/golden/observability/pca/prometheusrule.yaml`.

## Alertmanager
Pipeline: receive -> **inhibit** -> **silence** -> **route** -> **group** -> dedup -> notify (with retries).
- **Routing tree:** top-level `route` is the default; child `routes` match with `matchers: ['severity="critical"', 'team=~"shop|pay"']`; first match wins unless `continue: true`.
- **Grouping:** `group_by: [alertname, namespace]` batches alerts; `group_wait` (first notification delay, default 30s), `group_interval` (new alerts into an existing group, 5m), `repeat_interval` (re-send unchanged, 4h). `group_by: ['...']` disables grouping.
- **Inhibition:** mute target alerts while a source alert fires, where `equal` labels match - e.g. critical mutes warning for the same `alertname`, or `ClusterDown` mutes everything in that cluster.
- **Silences:** time-bound matcher sets created in the UI or `amtool silence add alertname=Foo --duration=2h -c "deploy"`.
- Receivers: email, Slack, PagerDuty, Opsgenie, webhook, MS Teams, Telegram, SNS... `time_intervals` + `mute_time_intervals` / `active_time_intervals` for business hours.
- HA: run 3 replicas in a gossip cluster (`--cluster.peer`); Prometheus sends to all of them; they dedup.
- Validate: `amtool check-config alertmanager.yaml`; test a route: `amtool config routes test --config.file=alertmanager.yaml severity=critical team=shop`.
- Lab: `pca/alertmanager.yaml` (raw config for amtool) and `pca/alertmanagerconfig.yaml` (namespaced `AlertmanagerConfig` CR).

## Exporters
- **node_exporter** (port 9100): host metrics - `node_cpu_seconds_total{mode}`, `node_memory_MemAvailable_bytes`, `node_filesystem_avail_bytes`, `node_network_receive_bytes_total`, `node_load1`. Textfile collector (`--collector.textfile.directory`) for cron job results. Runs as a DaemonSet in kube-prometheus-stack.
  ```promql
  1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))            # CPU utilisation
  1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes                  # memory utilisation
  predict_linear(node_filesystem_avail_bytes{fstype!="tmpfs"}[6h], 24*3600) < 0     # disk full within a day
  ```
- **blackbox_exporter** (port 9115): probes from the outside - `http_2xx`, `tcp_connect`, `icmp`, `dns` modules. Prometheus passes the target as a URL param using relabelling (`__address__ -> __param_target`, then `__address__` = the exporter). Key metrics: `probe_success`, `probe_duration_seconds`, `probe_http_status_code`, `probe_ssl_earliest_cert_expiry`.
- Others: kube-state-metrics (object state: `kube_pod_status_phase`, `kube_deployment_status_replicas_available`), cAdvisor via kubelet (`container_cpu_usage_seconds_total`), mysqld, postgres, redis, snmp, JMX exporters. Exporter ports are registered on the Prometheus wiki "default port allocations".
- Choose: instrument your own code directly; use an exporter only for third-party software you cannot change.

## Service discovery and relabelling
- SD mechanisms: `static_configs`, `file_sd_configs` (JSON/YAML, re-read on change), `kubernetes_sd_configs` (roles `node`, `pod`, `service`, `endpoints`, `endpointslice`, `ingress`), `consul_sd_configs`, `ec2_sd_configs`, `dns_sd_configs`, `http_sd_configs`...
- Discovery produces `__meta_*` labels plus `__address__`, `__scheme__`, `__metrics_path__`, `__param_<name>`. Labels starting with `__` are dropped after relabelling.
- **`relabel_configs`** run before the scrape on target labels (choose targets, set `job`/`instance`/extra labels). **`metric_relabel_configs`** run after the scrape on every sample (drop expensive series, rename). `write_relabel_configs` apply per remote write.
- Actions: `replace` (default), `keep`, `drop`, `keepequal`/`dropequal`, `labelmap`, `labeldrop`, `labelkeep`, `hashmod`, `lowercase`/`uppercase`.
```yaml
relabel_configs:
- source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
  action: keep
  regex: "true"
- source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
  regex: '([^:]+)(?::\d+)?;(\d+)'
  replacement: '$1:$2'
  target_label: __address__
- action: labelmap
  regex: __meta_kubernetes_pod_label_(.+)
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'go_gc_.*'
  action: drop
```
- In the operator world you write `ServiceMonitor` (scrape Service endpoints) or `PodMonitor` (scrape pods directly), with `relabelings` and `metricRelabelings` fields; the operator generates the scrape config. `ScrapeConfig` CR covers static/file/http SD. Blackbox via the `Probe` CR.

## Instrumentation with client libraries
- Official: Go, Java/Scala, Python, Ruby, Rust (plus many third party). Python lab app: `lab/golden/observability/pca/app.py`.
```python
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
REQS = Counter("lab_http_requests", "HTTP requests", ["method", "path", "code"])   # exposed as lab_http_requests_total
LAT  = Histogram("lab_http_request_duration_seconds", "Latency", ["path"], buckets=(.05, .1, .25, .5, 1, 2.5))
INFL = Gauge("lab_inflight_requests", "In-flight requests")
with LAT.labels(path="/cart").time(): ...     # or @LAT.time() decorator; INFL.inc()/dec() or .track_inprogress()
REQS.labels("GET", "/cart", "200").inc()
start_http_server(8000)
```
- Exposition formats: Prometheus text format (`# HELP`, `# TYPE`, samples) and **OpenMetrics** (`# EOF` terminator, `_created` series, exemplars). Content negotiation via `Accept` header. Check with `curl -s :8000/metrics | promtool check metrics`.
- Initialise label combinations you know about (so series exist at 0), keep label values bounded, measure in base units, prefer histograms over summaries when you need to aggregate across replicas.
- Short-lived jobs: push to Pushgateway at the end (`push_to_gateway`), alert on `time() - last_success_timestamp_seconds > 3600`.

## Dashboards in Grafana
- Add Prometheus as a data source (kube-prometheus-stack pre-provisions it plus ~30 dashboards). Panels: Time series, Stat, Gauge, Bar gauge, Table, Heatmap (for histogram buckets: format "Heatmap", query `sum by (le) (rate(x_bucket[$__rate_interval]))`).
- Use `$__rate_interval` instead of hard-coded `[5m]` in panel queries, template variables (`label_values(up, job)`, `query_result(...)`), `Legend: {{path}}`, units, thresholds.
- Dashboards as code: export JSON, provision via ConfigMap with label `grafana_dashboard: "1"` (the kps sidecar picks it up), or Grafana's Git sync / Terraform.
- Grafana alerting exists too, but on the exam "alerting" means Prometheus rules + Alertmanager.

## Scaling: federation and remote write
- **Federation:** a global Prometheus scrapes `/federate?match[]={__name__=~"job:.*"}` of lower-level servers with `honor_labels: true` - pull aggregated (recorded) series, not everything. Hierarchical federation for multi-DC; cross-service federation to join data.
- **Remote write:** Prometheus streams samples (WAL-based queue, `queue_config` for shards/batching) to a remote endpoint - Thanos Receive, Cortex, Mimir, VictoriaMetrics, Grafana Cloud, or another Prometheus with `--web.enable-remote-write-receiver`. **Remote read** queries back. Remote Write 2.0 adds metadata, exemplars, native histograms and string interning.
- **Agent mode** (`--agent`): scrape + remote write only, no local query/rules - for edge clusters.
- Long-term storage/HA: Thanos (sidecar uploads blocks to object storage, querier dedups replicas by `replica` external label), Cortex/Mimir (horizontally scalable, multi-tenant). Set `external_labels` (`cluster`, `replica`) on every server.

## Labs (kind cluster `lab`)
```bash
./lab.sh kind up && ./lab.sh addon monitoring          # kube-prometheus-stack as release "kps" in ns monitoring
lab/golden/observability/up.sh pca                      # ns prom-lab: sample app, ServiceMonitor, PrometheusRule, AlertmanagerConfig
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090 &   # svc name: kubectl -n monitoring get svc
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-alertmanager 9093 &
kubectl -n monitoring port-forward svc/kps-grafana 3000:80 &                           # admin/admin
```
1. **Targets and SD (day 1):** open `:9090/targets`, find `serviceMonitor/prom-lab/shop-api/0`; `:9090/service-discovery` shows discovered vs dropped labels. Break it: change the ServiceMonitor `port` name and watch the target disappear; fix it.
2. **Raw metrics:** `kubectl -n prom-lab port-forward svc/shop-api 8000 & curl -s localhost:8000/metrics | grep -E '^(# (HELP|TYPE)|lab_)' | head -40`; pipe it to `promtool check metrics`.
3. **PromQL drills (days 2-5):** work through `pca/promql-exercises.md` (25 tasks). Time yourself; redo the ones you missed two days later.
4. **Rules:** `promtool check rules lab/golden/observability/pca/rules.yaml` (the plain rule file mirrored in the PrometheusRule). Open `:9090/rules` and `:9090/alerts`; raise the error rate with `kubectl -n prom-lab set env deploy/shop-api ERROR_RATE=0.3` and watch `ShopApiHighErrorRate` go pending -> firing.
5. **Alertmanager:** `amtool check-config pca/alertmanager.yaml`; `amtool config routes test --config.file=pca/alertmanager.yaml severity=critical namespace=prom-lab`; in `:9093` create a silence for the firing alert, then expire it. Observe that `ShopApiHighErrorRateCritical` inhibits the warning one.
6. **Exporters:** query `node_*` metrics from the kps node-exporter DaemonSet. Install blackbox (`helm upgrade --install bb prometheus-community/prometheus-blackbox-exporter -n monitoring`) and write a `Probe` CR against `http://shop-api.prom-lab:8000/healthz`; alert on `probe_success == 0`.
7. **Relabelling:** add `metricRelabelings` to the ServiceMonitor dropping `python_gc_.*`; confirm with `count({__name__=~"python_gc.*", namespace="prom-lab"})` returning empty.
8. **Grafana:** build a RED dashboard for shop-api (rate, error ratio, p50/p95/p99 heatmap) with a `$path` variable; export JSON into `pca/`.
9. **Federation/remote write (reading level):** run a second Prometheus in Docker with `--web.enable-remote-write-receiver` and add a `remoteWrite` entry to the kps Prometheus via `helm upgrade ... --set prometheus.prometheusSpec.remoteWrite[0].url=http://<host>:9091/api/v1/write`; query the copy.

## Week plan (28 h each)
- **Week 1:** days 1-2 concepts + data model + labs 1-2; days 3-5 PromQL (lab 3), histograms and joins twice; day 6 exporters + SD/relabelling (labs 6-7); day 7 review weak areas.
- **Week 2:** days 1-2 rules + Alertmanager (labs 4-5); day 3 instrumentation (read `app.py`, add a new metric); day 4 Grafana (lab 8); day 5 federation/remote write/Thanos reading + lab 9; day 6 two timed mock exams; day 7 sit PCA.

## Self-check
1. What is the difference between `rate()` and `irate()`, and which belongs in an alerting rule?
2. Why is `rate(sum(http_requests_total)[5m:])` worse than `sum(rate(http_requests_total[5m]))`?
3. Write the p99 latency per `path` from histogram `lab_http_request_duration_seconds`.
4. A summary exposes `{quantile="0.99"}` on 5 replicas. Can you average them to get the service p99?
5. What does `up == 0` tell you, and which component creates the `up` series?
6. When is Pushgateway appropriate, and what is its main pitfall?
7. What does `for: 10m` do on an alerting rule? What are the three alert states?
8. Name the recording-rule naming convention and give an example.
9. `group_wait`, `group_interval`, `repeat_interval` - what does each control?
10. Write an inhibition rule: `severity=critical` mutes `severity=warning` with the same `alertname` and `namespace`.
11. Difference between `relabel_configs` and `metric_relabel_configs`?
12. How does blackbox_exporter get told which URL to probe?
13. Join: attach the `version` label of `app_build_info` to `rate(http_requests_total[5m])` by `instance`.
14. What does `absent(up{job="shop-api"})` return when the job exists? When it does not?
15. Why should you not put a `user_id` label on a metric?
16. What does federation's `honor_labels: true` do?
17. Name three remote-write targets used for long-term storage.
18. How do you reload Prometheus configuration without a restart?
19. What does the `le` label mean, and why must it be kept in `sum by (...)` before `histogram_quantile`?
20. Which query predicts whether a filesystem runs out of space within 4 hours?

<details><summary>Answers</summary>

1. `rate` averages over the whole window (smooth, robust); `irate` uses the last two samples (spiky). Use `rate` in alerts and recording rules.
2. Summing counters first hides per-series resets (a restart looks like a huge drop) and the subquery is expensive; always rate-then-sum.
3. `histogram_quantile(0.99, sum by (le, path) (rate(lab_http_request_duration_seconds_bucket[5m])))`.
4. No - pre-computed quantiles are not aggregatable; use a histogram.
5. The last scrape of that target failed (down, timeout, wrong port/path); Prometheus itself creates `up` for every target.
6. Service-level batch jobs that finish before they can be scraped; it never expires series (stale data stays), is a single point of failure, and loses `up` semantics.
7. The expression must be true continuously for 10m before firing (pending meanwhile). States: inactive, pending, firing.
8. `level:metric:operations`, e.g. `job:lab_http_requests:rate5m`.
9. Delay before the first notification of a new group; delay before notifying about new alerts added to an existing group; delay before re-sending an unchanged group.
10. `inhibit_rules: [{source_matchers: ['severity="critical"'], target_matchers: ['severity="warning"'], equal: [alertname, namespace]}]`.
11. `relabel_configs` act on targets before scraping (select/label targets); `metric_relabel_configs` act on scraped samples before storage (drop/rename series).
12. Relabelling copies `__address__` into `__param_target`, then sets `__address__` to the exporter host:9115 (`/probe?target=...&module=http_2xx`).
13. `rate(http_requests_total[5m]) * on (instance) group_left (version) app_build_info`.
14. Empty result when the series exists; a single series `{job="shop-api"}` with value 1 when it is missing.
15. Unbounded cardinality: each value creates new series, exploding memory and query cost.
16. Keeps labels (e.g. `job`, `instance`) as exposed by the federated server instead of overwriting them with the scraping server's target labels.
17. Thanos Receive, Cortex, Grafana Mimir, VictoriaMetrics (also M3, Grafana Cloud).
18. `kill -HUP <pid>` or `curl -X POST :9090/-/reload` (with `--web.enable-lifecycle`); the operator does it automatically via config-reloader.
19. `le` is the bucket upper bound ("less than or equal"); `histogram_quantile` needs it to know the bucket boundaries, so aggregate `by (le, ...)`.
20. `predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0`.
</details>

## Resources
https://prometheus.io/docs (concepts, querying, alerting), https://promlabs.com/promql-cheat-sheet/, "Prometheus: Up & Running" 2nd ed. (O'Reilly), https://github.com/prometheus/prometheus/tree/main/documentation/examples, PromLabs/KodeKloud PCA courses, https://training.linuxfoundation.org/certification/prometheus-certified-associate/ (curriculum PDF)
