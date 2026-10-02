# OpenTelemetry exercises (OTCA)

Setup: `../up.sh otel`, then
`kubectl -n otel-lab port-forward svc/jaeger 16686 &` and `kubectl -n otel-lab port-forward svc/otel-collector 8889 8888 55679 &`.
Files: `app/app.py` (API usage), `app/deployment.yaml` (SDK env vars), `collector-config.yaml` (pipelines).
After editing `collector-config.yaml` run `kubectl apply -k .` from this directory (the ConfigMap hash rolls the Collector).

| # | Area | Task |
|---|---|---|
| 1 | signals | Find one trace, one metric and one log record produced by `otel-demo` (Jaeger, `:8889/metrics`, Collector logs). How are the log record and the trace correlated? |
| 2 | traces | Open a `GET /checkout` trace. List its spans with their SpanKind and parent. Which spans are auto-instrumented and which are manual? |
| 3 | traces | Call `/checkout?fail=1`. Where do you see the exception, and what is the span status of `charge-card` and of the SERVER span? |
| 4 | API/SDK | `app.py` never imports `opentelemetry.sdk`. Who creates the TracerProvider, and what would happen if you ran `python app.py` without `opentelemetry-instrument`? |
| 5 | resource | Which resource attributes does the trace carry, and where does each come from (env var, SDK detector, Collector processor)? |
| 6 | scope | What is the instrumentation scope of the `charge-card` span and of the Flask SERVER span? |
| 7 | propagation | Send a request with your own `traceparent` and find the trace in Jaeger by its ID. Then send the same header with flags `00`. |
| 8 | baggage | The load generator sends `baggage: tenant=acme`. Which span has `app.tenant`, and why is it not on every span automatically? |
| 9 | metrics | Which instrument types does `app.py` use? Find each one's Prometheus name on `:8889/metrics`. |
| 10 | metrics | Write a PromQL query for checkout error ratio from `demo_checkouts_total`. |
| 11 | semconv | Pick the Flask SERVER span: which attribute names does it use for method, route and status code? Are they the stable HTTP semconv names? |
| 12 | env vars | Switch the app to OTLP/HTTP. Which two env vars change, and to what values? |
| 13 | env vars | Make the app print spans to stdout as well as sending them over OTLP. |
| 14 | sampling | Configure the SDK to keep 20% of new traces but always follow the caller's decision. |
| 15 | collector | Add `filter/health` to the traces pipeline and prove `/healthz` spans are gone. |
| 16 | collector | Add a processor that deletes the `user_agent.original` attribute from all spans. |
| 17 | collector | Add the `spanmetrics` connector so RED metrics derived from spans appear on `:8889`. |
| 18 | sampling | Replace head sampling with tail sampling in the Collector: keep every error trace, plus 10% of the rest. |
| 19 | debugging | Point the app at `otel-collector:4318` while keeping `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`. What fails, where do you see it, and which Collector metric stays flat? |
| 20 | debugging | Rename `otlp/jaeger` to `otlp/jaeger2` in `exporters:` only. What does the Collector do on start, and how would `validate` have caught it? |

<details><summary>Answers</summary>

1. Jaeger service `otel-demo`; `demo_checkouts_total` on `:8889`; `kubectl -n otel-lab logs deploy/otel-collector | grep -B2 -A12 LogRecord`. The log record carries the `trace_id`/`span_id` of the span active when `log.info` ran (logging instrumentation).
2. `GET /checkout` SERVER (Flask, auto) -> `reserve-stock` INTERNAL (manual) -> `GET` CLIENT (requests, auto) -> `GET /inventory` SERVER (Flask, auto, in the same process but joined via the `traceparent` header); `charge-card` INTERNAL (manual) under the root.
3. On `charge-card`: an `exception` span event (`exception.type`, `exception.message`, `exception.stacktrace`) and status `Error`. The SERVER span has status `Error` because Flask instrumentation sets it for 5xx responses (502 here).
4. `opentelemetry-instrument` (the distro's configurator) builds the SDK providers from env vars before the app starts. Without it the API returns no-op implementations: the app works, no telemetry is produced.
5. `service.name` (`OTEL_SERVICE_NAME`), `service.version`/`service.namespace`/`k8s.*` (`OTEL_RESOURCE_ATTRIBUTES`), `telemetry.sdk.*` (SDK), `deployment.environment.name` and `k8s.cluster.name` (Collector `resource` processor).
6. `otel-demo.shop` 0.1.0 (the name passed to `get_tracer`) vs `opentelemetry.instrumentation.flask` with the instrumentation's version.
7. `curl -H 'traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01' localhost:5000/rolldice` (port-forward svc/otel-demo 5000). With flags `00` the parent says "not sampled"; `parentbased_*` samplers respect it, so the trace never reaches Jaeger.
8. The `GET /inventory` SERVER span, because `app.py` reads the baggage and sets it explicitly. Baggage is context, not span data; copying it requires code or a baggage span processor.
9. Counter `demo.checkouts` -> `demo_checkouts_total`; Histogram `demo.dice.value` -> `demo_dice_value_bucket/_sum/_count`; ObservableGauge `demo.stock.level` -> `demo_stock_level`. (Unit suffixes are only added for UCUM units; `{curly}` annotations are dropped.)
10. `sum(rate(demo_checkouts_total{outcome="error"}[5m])) / sum(rate(demo_checkouts_total[5m]))`.
11. Depends on the instrumentation version: stable names are `http.request.method`, `http.route`, `http.response.status_code`; older ones are `http.method`, `http.status_code`. `OTEL_SEMCONV_STABILITY_OPT_IN=http` (or `http/dup`) switches/duplicates.
12. `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.otel-lab.svc:4318` (the SDK appends `/v1/traces` etc.).
13. `kubectl -n otel-lab set env deploy/otel-demo OTEL_TRACES_EXPORTER=otlp,console`.
14. `OTEL_TRACES_SAMPLER=parentbased_traceidratio` and `OTEL_TRACES_SAMPLER_ARG=0.2`.
15. Uncomment `filter/health`, set traces `processors: [memory_limiter, filter/health, resource, batch]`; Jaeger search for operation `GET /healthz` returns nothing new; `otelcol_processor_filter_spans_filtered` grows on `:8888`.
16. `attributes/strip-ua: { actions: [{ key: user_agent.original, action: delete }] }` (and `http.user_agent` for older semconv), added to the traces pipeline before `batch`.
17. `connectors: { spanmetrics: {} }`; traces `exporters: [otlp/jaeger, spanmetrics, debug]`; metrics `receivers: [otlp, spanmetrics]`. New series such as `traces_span_metrics_calls_total` and `traces_span_metrics_duration_milliseconds_bucket` (names vary by version) appear on `:8889`.
18. Set the app sampler to `parentbased_always_on`, then `tail_sampling: { decision_wait: 10s, policies: [{ name: errors, type: status_code, status_code: { status_codes: [ERROR] } }, { name: rest, type: probabilistic, probabilistic: { sampling_percentage: 10 } }] }` in the traces pipeline after `memory_limiter`, before `batch`. With one Collector replica no load balancing is needed.
19. Export fails with a gRPC error (`UNAVAILABLE`/protocol error) in the app's logs (`kubectl logs deploy/otel-demo`); `otelcol_receiver_accepted_spans{transport="grpc"}` stops growing. Fix the port or switch the protocol.
20. The Collector refuses to start: the traces pipeline references an exporter `otlp/jaeger` that is not configured. `otelcol-contrib validate --config=collector-config.yaml` reports the same error without starting anything.
</details>
