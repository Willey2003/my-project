# PromQL exercises (PCA)

Run against the kube-prometheus-stack Prometheus after `../up.sh pca`:
`kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090` -> http://localhost:9090/query (Table and Graph tabs).
Metrics come from `app.py` (`lab_*`, 2 replicas, job `shop-api`, ns `prom-lab`), node-exporter (`node_*`) and kube-state-metrics (`kube_*`).
Try each task before opening the answer. Write down the result type (instant vector, range vector, scalar) too.

| # | Topic | Task |
|---|---|---|
| 1 | selectors | All `lab_http_requests_total` series for `/checkout` that returned 5xx. |
| 2 | range vector | The raw samples of `lab_queue_jobs` for one pod over the last 2 minutes (Table tab). |
| 3 | rate | Per-second request rate for each shop-api pod over 5 minutes. |
| 4 | increase | Total number of requests the whole service handled in the last hour. |
| 5 | irate | A spiky, "instant" request rate per pod suitable for a live graph (not for alerting). |
| 6 | aggregation | Request rate per status `code`, across all pods and paths. |
| 7 | without | Request rate with the `pod`, `instance` and `endpoint` labels removed, keeping everything else. |
| 8 | ratio | Service-wide 5xx error ratio (0-1) over 5 minutes. |
| 9 | topk | The 2 busiest paths by request rate. |
| 10 | histogram | Service-wide p95 latency. |
| 11 | histogram | p99 latency per path. |
| 12 | histogram | Average (mean) latency per path from `_sum`/`_count`. |
| 13 | histogram | Fraction of requests served in 100 ms or less (latency SLI). |
| 14 | comparison | Only pods whose request rate is above 2 req/s. |
| 15 | bool | Return 1/0 per pod: is its 5xx ratio above 5%? |
| 16 | join | Request rate per pod with the `version` label from `lab_build_info` attached. |
| 17 | ignoring | 5xx rate per path divided by total rate per path, using the `code`-labelled series on the left (match while ignoring `code`). |
| 18 | offset | How much has the service request rate changed compared to the same time one hour ago (ratio)? |
| 19 | subquery | The maximum 1-minute request rate observed in the last 30 minutes, sampled every 30 seconds. |
| 20 | _over_time | Average queue depth per pod over the last 10 minutes, and the peak. |
| 21 | absent | An expression that returns a series only when no shop-api target is being scraped. |
| 22 | predict_linear | Filesystems (non-tmpfs) predicted to run out of space in the next 24 hours. |
| 23 | label_replace | Add a label `ip` holding only the IP part of `instance` for `up{job="shop-api"}`. |
| 24 | count | How many targets per job are down right now? And how many distinct versions of shop-api are running? |
| 25 | recording rules | Query the recorded p95 for `/checkout` and compare it to the raw expression. Why might they differ slightly? |

<details><summary>Answers</summary>

1. `lab_http_requests_total{path="/checkout", code=~"5.."}` - instant vector; `=~` is fully anchored.
2. `lab_queue_jobs{pod="<pod-name>"}[2m]` - range vector (about 8 samples at a 15 s interval); cannot be graphed.
3. `sum by (pod) (rate(lab_http_requests_total[5m]))`.
4. `sum(increase(lab_http_requests_total[1h]))` - may be a non-integer because of extrapolation.
5. `sum by (pod) (irate(lab_http_requests_total[1m]))`.
6. `sum by (code) (rate(lab_http_requests_total[5m]))`.
7. `sum without (pod, instance, endpoint) (rate(lab_http_requests_total[5m]))`.
8. `sum(rate(lab_http_requests_total{code=~"5.."}[5m])) / sum(rate(lab_http_requests_total[5m]))`.
9. `topk(2, sum by (path) (rate(lab_http_requests_total[5m])))`.
10. `histogram_quantile(0.95, sum by (le) (rate(lab_http_request_duration_seconds_bucket[5m])))`.
11. `histogram_quantile(0.99, sum by (le, path) (rate(lab_http_request_duration_seconds_bucket[5m])))` - dropping `le` gives an empty result.
12. `sum by (path) (rate(lab_http_request_duration_seconds_sum[5m])) / sum by (path) (rate(lab_http_request_duration_seconds_count[5m]))`.
13. `sum(rate(lab_http_request_duration_seconds_bucket{le="0.1"}[5m])) / sum(rate(lab_http_request_duration_seconds_count[5m]))` - the `le` value must be an existing bucket boundary.
14. `sum by (pod) (rate(lab_http_requests_total[5m])) > 2` - comparison without `bool` filters.
15. `sum by (pod) (rate(lab_http_requests_total{code=~"5.."}[5m])) / sum by (pod) (rate(lab_http_requests_total[5m])) > bool 0.05`.
16. `sum by (pod) (rate(lab_http_requests_total[5m])) * on (pod) group_left (version) lab_build_info` - `lab_build_info` is 1, so the value is unchanged.
17. `sum by (path, code) (rate(lab_http_requests_total{code=~"5.."}[5m])) / ignoring (code) group_left sum by (path) (rate(lab_http_requests_total[5m]))` - many-to-one because the left side may have several 5xx codes per path.
18. `sum(rate(lab_http_requests_total[5m])) / sum(rate(lab_http_requests_total[5m] offset 1h))` - empty until the lab has an hour of data.
19. `max_over_time(sum(rate(lab_http_requests_total[1m]))[30m:30s])`.
20. `avg_over_time(lab_queue_jobs[10m])` and `max_over_time(lab_queue_jobs[10m])` - one result per pod each.
21. `absent(up{job="shop-api"} == 1)` - scale to 0 to test: `kubectl -n prom-lab scale deploy/shop-api --replicas=0`.
22. `predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}[6h], 24 * 3600) < 0`.
23. `label_replace(up{job="shop-api"}, "ip", "$1", "instance", "(.*):.*")`.
24. `count by (job) (up == 0)` (empty if none are down) and `count(count by (version) (lab_build_info))` - or `count_values("v", ...)` style variants.
25. `namespace_job_path:lab_http_request_duration_seconds:p95_rate5m{path="/checkout"}` vs `histogram_quantile(0.95, sum by (namespace, job, path, le) (rate(lab_http_request_duration_seconds_bucket{path="/checkout"}[5m])))`. The recorded series is evaluated every 30 s at rule-evaluation timestamps, while the ad-hoc query is evaluated at the query time or step, so values are close but not identical.
</details>
