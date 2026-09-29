# Phase 23 - OTCA: OpenTelemetry Certified Associate

**Golden track step:** G3 · 7-16 May 2027 (see schedule) · **Hours:** 40 · **Exam:** OTCA, 90 min online proctored, multiple choice (~60 questions), USD 250, one free retake · **Lab:** `./lab.sh addon monitoring`, `lab/golden/observability/up.sh otel`

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Observability fundamentals, signals, API vs SDK, context propagation, semantic conventions, OTLP, instrumenting the Flask demo | `otel/app` traced end-to-end in Jaeger; notes on API/SDK components |
| 2 | Collector pipelines (receivers/processors/exporters/connectors), sampling, OTel Operator auto-instrumentation, backends (Jaeger, Prometheus), debugging pipelines, mocks, sit exam | `otel/collector-config.yaml` extended with a filter + tail sampling; `otel/otel-exercises.md` done; OTCA |

## Domains (sheet weights; verify the current curriculum on training.linuxfoundation.org)
| Domain | Weight | Your lab |
|---|---|---|
| The OpenTelemetry API and SDK | 46% | `otel/app/app.py` (manual spans + metrics on top of auto-instrumentation) |
| The OpenTelemetry Collector | 26% | `otel/collector-config.yaml` (OTLP in; debug, Prometheus, Jaeger out) |
| Fundamentals of Observability | 18% | this page, "Signals" and "Concepts" |
| Maintaining and Debugging Observability Pipelines | 10% | debug exporter, `zpages`, Collector self-metrics on `:8888` |

The API/SDK domain is almost half the exam: know the component names (TracerProvider, Tracer, Span, SpanProcessor, SpanExporter, MeterProvider, Meter, instruments, MetricReader, View, LoggerProvider, Resource, Propagators) and how they relate, independent of language.

## Exam technique
- Questions are conceptual and vendor-neutral; when two answers look right, pick the one that matches the **specification** wording (e.g. "SpanProcessor", "MetricReader", "Resource", "Baggage").
- Separate **API** (what instrumentation calls, no-op by default) from **SDK** (the implementation that samples, processes, exports). Libraries depend on the API only; applications install the SDK.
- For Collector questions, draw the pipeline: receivers -> processors (in order) -> exporters, per signal type. A component is only active if it is referenced in `service.pipelines`.
- Know status levels: traces/metrics/logs signals are stable in the spec; profiles is the fourth signal in development. Semantic conventions have stable and experimental parts (HTTP and DB are stable).
- Flag and move on; ~1.5 min per question; no negative marking.

## Concepts - observability fundamentals
- Observability = being able to ask new questions of a system from its outputs without shipping new code. Monitoring = watching known failure modes.
- **Telemetry signals:** traces, metrics, logs (plus baggage as a context mechanism, and profiles in development). Correlation between them (trace IDs in logs, exemplars in metrics) is the main value of OpenTelemetry.
- OpenTelemetry is a CNCF incubating project (formed from the OpenTracing + OpenCensus merger in 2019; second most active CNCF project after Kubernetes): a **specification**, **APIs and SDKs** per language, the **Collector**, **OTLP**, **semantic conventions**, and instrumentation libraries. It is not a backend: storage and visualisation are Jaeger, Prometheus, Tempo, Loki, Elastic, vendors, etc.
- SLI/SLO, RED/USE, golden signals, cardinality and sampling trade-offs appear in the fundamentals domain too (see `22-pca-prometheus.md`).

## Signals
**Traces**
- A trace is a tree (DAG) of **spans** sharing a 16-byte `trace_id`. Each span has an 8-byte `span_id`, `parent_span_id`, name, start/end timestamps, **SpanKind** (`SERVER`, `CLIENT`, `PRODUCER`, `CONSUMER`, `INTERNAL`), attributes, events (timestamped annotations, e.g. exceptions), links (to spans in other traces - batch/fan-in), and **status** (`Unset`, `Ok`, `Error`).
- Span name must be low-cardinality (`GET /users/{id}`, not `/users/42`).
- Record errors: `span.record_exception(e)` + `span.set_status(Status(StatusCode.ERROR))`. Instrumentation leaves status `Unset` on success; only the application sets `Ok`.

**Metrics**
- Instruments (API): **Counter** (monotonic, sync), **UpDownCounter** (sync), **Histogram** (sync), **Gauge** (sync, newer), and asynchronous/observable **ObservableCounter**, **ObservableUpDownCounter**, **ObservableGauge** that report through callbacks.
- Data points carry attributes. **Aggregation temporality**: *cumulative* (since start - Prometheus style) vs *delta* (since last export - StatsD/some vendors). Exporter/reader preferences decide.
- **Views** (SDK) rename instruments, drop or keep attributes, change the aggregation (explicit bucket vs exponential histogram), or drop an instrument entirely.
- **Exemplars** link a metric point to a sampled trace (trace_id/span_id).

**Logs**
- OTel does not define a new logging API for application developers: the **Logs Bridge API** connects existing libraries (Python `logging`, Log4j, SLF4J, zap) to a LoggerProvider. The LogRecord data model includes timestamp, observed timestamp, severity number/text, body, attributes, resource, trace_id, span_id, trace flags.
- The Collector can also collect logs from files (`filelog` receiver) - the "don't touch the app" path.
- Events are LogRecords with an event name (the Events API is being folded into the Logs API).

**Baggage** - key/value pairs propagated with the context across services (e.g. `tenant=acme`). Not added to spans automatically - you (or a span processor) copy it. Never put secrets in it; it travels in HTTP headers.

## The API vs the SDK
| Layer | Contains | Who uses it |
|---|---|---|
| API | `TracerProvider`/`Tracer`/`Span`, `MeterProvider`/`Meter`/instruments, Logs Bridge API, Context, Propagators API, Baggage | library authors and app code; a no-op if no SDK is installed |
| SDK | Resource, Sampler, SpanProcessor (`SimpleSpanProcessor`, `BatchSpanProcessor`), SpanExporter, IdGenerator, SpanLimits; MetricReader (`PeriodicExportingMetricReader`, pull readers like the Prometheus reader), MetricExporter, Views, Aggregations, exemplar filter; LogRecordProcessor, LogRecordExporter | application owners (configure once at startup) |
| Instrumentation libraries | Flask, requests, Django, gRPC, JDBC, Express... auto-generate spans/metrics against the API | added via `opentelemetry-bootstrap` or the agent |
| Exporters | OTLP (gRPC/HTTP), console, Prometheus, Zipkin (Jaeger exporters are deprecated - Jaeger speaks OTLP) | configured in SDK or Collector |

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=Resource.create({"service.name": "otel-demo"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)))
trace.set_tracer_provider(provider)                           # SDK installed globally
tracer = trace.get_tracer("demo.checkout", "1.0.0")           # API: instrumentation scope name + version
with tracer.start_as_current_span("charge-card", kind=trace.SpanKind.INTERNAL) as span:
    span.set_attribute("payment.method", "card")
    span.add_event("card.authorised")
```
- **Resource** = immutable attributes of the entity producing telemetry (`service.name`, `service.version`, `deployment.environment.name`, `k8s.pod.name`, `host.name`). Detectors fill them; `OTEL_RESOURCE_ATTRIBUTES` / `OTEL_SERVICE_NAME` override. `service.name` defaults to `unknown_service:<process>`.
- **Instrumentation scope** = name/version of the library that emitted the telemetry (the argument to `get_tracer`/`get_meter`).
- Batch vs simple processor: always `BatchSpanProcessor` in production (queue, `OTEL_BSP_SCHEDULE_DELAY`, `OTEL_BSP_MAX_QUEUE_SIZE`); simple exports synchronously, for debugging.
- **Zero-code / auto-instrumentation:** Python `opentelemetry-instrument python app.py`; Java `-javaagent:opentelemetry-javaagent.jar`; .NET and Node.js (`--require @opentelemetry/auto-instrumentations-node/register`); Go via eBPF (OBI, formerly Beyla). Configured through env vars:

| Variable | Meaning |
|---|---|
| `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES` | resource |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL` (`grpc`, `http/protobuf`, `http/json`), `..._HEADERS` | where/how to send |
| `OTEL_TRACES_EXPORTER`, `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER` | `otlp`, `console`, `prometheus`, `none` |
| `OTEL_TRACES_SAMPLER`, `OTEL_TRACES_SAMPLER_ARG` | e.g. `parentbased_traceidratio`, `0.25` |
| `OTEL_PROPAGATORS` | default `tracecontext,baggage`; add `b3multi`, `jaeger`, `xray` |
| `OTEL_METRIC_EXPORT_INTERVAL` | ms between metric exports (default 60000) |
| `OTEL_SDK_DISABLED` | `true` turns the SDK into no-ops |
- Declarative configuration (a YAML file via `OTEL_CONFIG_FILE`) is the newer, stable-track alternative to env vars.

## Context propagation
- **Context** is an immutable, in-process carrier of the active span and baggage (contextvars in Python, ThreadLocal in Java). Getting it wrong across threads/async breaks parent-child links.
- **Propagators** inject/extract context into carriers (HTTP headers, message metadata) across process boundaries: `inject(carrier)` on the client, `extract(carrier)` on the server. Composite propagator = several at once.
- **W3C Trace Context** (default): `traceparent: 00-<32 hex trace-id>-<16 hex parent-id>-<2 hex flags>` (flag `01` = sampled) and `tracestate` for vendor data. **W3C Baggage**: `baggage: tenant=acme,region=eu`. Legacy: B3 (Zipkin, single or multi header), Jaeger `uber-trace-id`, AWS X-Ray.
- The sampled flag travels with context: `ParentBased` samplers follow the parent's decision so traces are complete.
- Messaging: propagate via message headers; use span **links** when one consumer span processes messages from many traces.

## Semantic conventions
- Standard attribute names so backends can understand telemetry from any source. Namespaced, dot-separated, lowercase: `http.request.method`, `http.response.status_code`, `http.route`, `url.full`, `url.path`, `server.address`, `client.address`, `network.protocol.version`, `db.system.name`, `db.query.text`, `messaging.system`, `rpc.system`, `exception.type`/`exception.message`/`exception.stacktrace`, `error.type`.
- Resource conventions: `service.name` (required), `service.namespace`, `service.instance.id`, `service.version`, `deployment.environment.name`, `k8s.*`, `container.*`, `cloud.*`, `host.*`, `process.*`, `telemetry.sdk.*`.
- Metric conventions: `http.server.request.duration` (Histogram, seconds), `http.client.request.duration`, `db.client.operation.duration`, `process.cpu.time`, JVM/runtime metrics. Units follow UCUM (`s`, `By`, `{request}`).
- Stability: HTTP semconv became stable in 2023 (renamed `http.method` -> `http.request.method`, `http.status_code` -> `http.response.status_code`); `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup` emits both during migration. Database conventions are stable too; messaging, GenAI and others are still development.
- Span names per convention: HTTP server `{method} {http.route}`; DB `{db.operation.name} {target}`.

## OTLP (OpenTelemetry Protocol)
- Protobuf schema for all signals, transported over **gRPC (port 4317)** or **HTTP (port 4318)** with paths `/v1/traces`, `/v1/metrics`, `/v1/logs` (binary protobuf or JSON). Stable for traces, metrics and logs.
- Structure: `ResourceSpans` -> `ScopeSpans` -> `Span` (same shape for metrics/logs) - resource and scope are sent once per batch.
- Supports gzip compression, headers for auth, partial success responses; retryable codes (`UNAVAILABLE`, HTTP 429/502/503/504) with backoff.
- Many backends ingest OTLP natively: Jaeger (v2 is built on the Collector), Prometheus (`--web.enable-otlp-receiver`, `/api/v1/otlp/v1/metrics`), Tempo, Loki, Mimir, Elastic, Datadog, Honeycomb, etc.

## The Collector
Vendor-neutral agent/gateway that receives, processes and exports telemetry. Distributions: **core** (`otelcol`, minimal), **contrib** (`otelcol-contrib`, everything), **k8s**, and custom builds with the **OpenTelemetry Collector Builder** (`ocb`, a `builder-config.yaml` listing components).
```yaml
receivers:                     # how data gets in (push: otlp, zipkin; pull: prometheus, hostmetrics, filelog, k8s_cluster, kubeletstats)
  otlp: { protocols: { grpc: { endpoint: 0.0.0.0:4317 }, http: { endpoint: 0.0.0.0:4318 } } }
processors:                    # run in the listed order, per pipeline
  memory_limiter: { check_interval: 1s, limit_percentage: 80, spike_limit_percentage: 25 }   # first
  k8sattributes: {}            # add k8s.pod.name, k8s.namespace.name ... from the sender IP
  resource: { attributes: [{ key: deployment.environment.name, value: lab, action: upsert }] }
  filter/health: { error_mode: ignore, traces: { span: ['attributes["url.path"] == "/healthz"'] } }
  batch: {}                    # last (before exporters)
exporters:                     # where data goes
  debug: { verbosity: detailed }
  otlp/jaeger: { endpoint: jaeger:4317, tls: { insecure: true } }
  prometheus: { endpoint: 0.0.0.0:8889 }         # pull: Prometheus scrapes the Collector
connectors:                    # exporter of one pipeline + receiver of another
  spanmetrics: {}              # RED metrics generated from spans
extensions: { health_check: {}, zpages: {}, pprof: {} }
service:
  extensions: [health_check, zpages]
  pipelines:
    traces:  { receivers: [otlp], processors: [memory_limiter, k8sattributes, filter/health, batch], exporters: [otlp/jaeger, spanmetrics, debug] }
    metrics: { receivers: [otlp, spanmetrics], processors: [memory_limiter, batch], exporters: [prometheus] }
    logs:    { receivers: [otlp], processors: [memory_limiter, batch], exporters: [debug] }
  telemetry: { metrics: { level: detailed } }     # Collector's own metrics on :8888
```
- `type/name` IDs (`otlp/jaeger`) allow several instances of one component type. Declared but unused components are ignored; a pipeline must have at least one receiver and one exporter.
- Other processors: `attributes` (insert/update/delete/hash on span/log/metric attributes), `transform` (OTTL statements), `redaction`, `tail_sampling`, `probabilistic_sampler`, `groupbyattrs`, `cumulativetodelta`, `resourcedetection`.
- **Deployment patterns:** *agent* (DaemonSet or sidecar next to the app: host metrics, k8s metadata, low latency) and *gateway* (central Deployment: tail sampling, auth, fan-out to backends). Commonly agent -> gateway. Tail sampling needs all spans of a trace on one Collector: use the `loadbalancing` exporter keyed by trace ID in front of the gateway tier.
- Resilience: `sending_queue` + `retry_on_failure` on exporters, persistent queue with the `file_storage` extension; `memory_limiter` refuses data before OOM.
- CLI: `otelcol-contrib --config=config.yaml`, `otelcol-contrib validate --config=config.yaml`, `components` subcommand lists what is compiled in; config can merge several files and use `${env:VAR}`.

## Sampling
- **Head sampling** (in the SDK, at trace start): `AlwaysOn`, `AlwaysOff`, `TraceIdRatioBased(0.1)`, `ParentBased(root=...)` (default is `ParentBased(AlwaysOn)`). Cheap, but decided before you know whether the trace is interesting.
- **Tail sampling** (in the Collector, after the trace completes, `decision_wait`): policies `status_code` (keep errors), `latency` (keep slow), `probabilistic`, `string_attribute`, `rate_limiting`, `and`/`composite`. Costs memory and needs trace-aware load balancing.
- Sampling decision is recorded in the `sampled` flag (traceparent) and is respected downstream by ParentBased samplers. Unsampled spans are still created (non-recording) so context keeps propagating.
- Metrics are not sampled - that is why you derive RED metrics from spans *before* sampling (spanmetrics connector) or use SDK metrics.

## OTel Operator on Kubernetes (auto-instrumentation)
- Install (needs cert-manager for its webhooks): `helm install otel-op open-telemetry/opentelemetry-operator -n opentelemetry-operator-system --create-namespace --set "manager.collectorImage.repository=otel/opentelemetry-collector-contrib"`.
- CRDs: **OpenTelemetryCollector** (`spec.mode: deployment | daemonset | statefulset | sidecar`, `spec.config` = Collector YAML), **Instrumentation** (per-language images and SDK env), **TargetAllocator** (shards Prometheus scrape targets across Collector replicas, can read ServiceMonitors), OpAMPBridge.
- Inject by annotation on the pod template: `instrumentation.opentelemetry.io/inject-python: "true"` (also `-java`, `-nodejs`, `-dotnet`, `-go`, `-apache-httpd`, `-nginx`, `-sdk`); `sidecar.opentelemetry.io/inject: "true"` adds a Collector sidecar. The webhook adds an init container that copies the agent, then sets `PYTHONPATH`/`JAVA_TOOL_OPTIONS` and `OTEL_*` env vars.
```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata: { name: default, namespace: otel-lab }
spec:
  exporter: { endpoint: http://otel-collector.otel-lab:4318 }   # Python auto-instrumentation defaults to OTLP/HTTP
  propagators: [tracecontext, baggage]
  sampler: { type: parentbased_traceidratio, argument: "1" }
```
- Pods must be restarted after creating the Instrumentation (injection happens at admission).

## Backends
- **Jaeger** (tracing, CNCF graduated): v2 is built on the Collector framework and ingests OTLP directly on 4317/4318; UI on 16686; storage: memory/Badger (all-in-one), Elasticsearch/OpenSearch, Cassandra, ClickHouse. Search by service/operation/tags, compare traces, dependency graph (DAG).
- **Prometheus**: two ways in - (1) Collector `prometheus` exporter (pull, `:8889/metrics`, Prometheus scrapes it); (2) `prometheusremotewrite` exporter or Prometheus's native OTLP receiver (push). OTel names are translated: dots to underscores, unit and `_total` suffixes added (`http.server.request.duration` -> `http_server_request_duration_seconds_bucket`); resource attributes become `target_info` (or labels with `resource_to_telemetry_conversion`). Prometheus 3.x can keep UTF-8 names.
- Others: Zipkin, Grafana Tempo/Loki/Mimir, Elastic, OpenSearch, SigNoz, vendors via OTLP. Grafana correlates Tempo traces with Prometheus exemplars and Loki logs by trace ID.

## Debugging pipelines
- `debug` exporter with `verbosity: detailed` prints every span/metric/log to the Collector's stdout; `zpages` (`:55679/debug/tracez`, `/debug/pipelinez`) shows live pipelines; `health_check` on `:13133`.
- Collector self-metrics (`:8888/metrics`): `otelcol_receiver_accepted_spans`, `otelcol_receiver_refused_spans`, `otelcol_processor_dropped_*`, `otelcol_exporter_sent_spans`, `otelcol_exporter_send_failed_spans`, `otelcol_exporter_queue_size`. Alert on refused/failed > 0 and queue near capacity.
- Classic faults: wrong port/protocol (gRPC client to 4318), `localhost` endpoint inside a container, TLS mismatch (`insecure: true`), component declared but not in a pipeline, `service.name` missing (`unknown_service`), batch processor before memory_limiter, broken context (orphan spans / many one-span traces), SDK console exporter proving the app side works.

## Labs (kind cluster `lab`)
```bash
./lab.sh kind up && ./lab.sh addon monitoring          # Prometheus + Grafana (kps) scrape the Collector
lab/golden/observability/up.sh otel                     # ns otel-lab: Jaeger, Collector, demo app (built + pushed to localhost:5001), load generator
kubectl -n otel-lab port-forward svc/jaeger 16686 &                     # Jaeger UI
kubectl -n otel-lab port-forward svc/otel-collector 8889 8888 55679 &   # app metrics, Collector self-metrics, zpages
kubectl -n otel-lab logs deploy/otel-collector -f | grep -A20 'ResourceSpans #0'   # debug exporter output
```
1. **Traces end-to-end (day 1):** in Jaeger pick service `otel-demo`, open a `GET /checkout` trace: a SERVER span from Flask auto-instrumentation, a CLIENT span from `requests`, a child SERVER span for `/inventory` (same trace thanks to `traceparent`), and manual INTERNAL spans `reserve-stock` / `charge-card`. Inspect attributes against the semantic conventions (`http.request.method`, `http.route`, `http.response.status_code`).
2. **Propagation by hand:** `kubectl -n otel-lab exec deploy/otel-demo -- python -c "import urllib.request as u; r=u.Request('http://localhost:5000/rolldice', headers={'traceparent':'00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01'}); print(u.urlopen(r).read())"`, then search Jaeger for trace ID `0af7651916cd43dd8448eb211c80319c`. Repeat with flags `00` - what happens?
3. **API vs SDK:** read `otel/app/app.py`: it only imports `opentelemetry.trace`/`metrics` (API); the SDK is installed by `opentelemetry-instrument`. Run locally with `OTEL_TRACES_EXPORTER=console OTEL_METRICS_EXPORTER=console opentelemetry-instrument flask --app app run` to see raw spans.
4. **Metrics to Prometheus:** `curl -s localhost:8889/metrics | grep -E 'demo_checkouts|http_server'`; in Prometheus query `sum by (payment_method) (rate(demo_checkouts_total[5m]))` and `histogram_quantile(0.95, sum by (le, http_route) (rate(http_server_duration_milliseconds_bucket[5m])))` (the metric name depends on the instrumentation's semconv version - check `/metrics`).
5. **Collector pipeline changes:** edit `otel/collector-config.yaml`: uncomment `filter/health` (drops `/healthz` spans) and add it to the traces pipeline, add an `attributes` processor that deletes `user_agent.original`, and add the `spanmetrics` connector. `kubectl apply -k lab/golden/observability/otel` (the ConfigMap name hash changes, so the Collector rolls); verify in the debug output. Validate first: `docker run --rm -v $PWD/lab/golden/observability/otel:/c otel/opentelemetry-collector-contrib:0.135.0 validate --config=/c/collector-config.yaml`.
6. **Sampling:** set `OTEL_TRACES_SAMPLER=parentbased_traceidratio` and `OTEL_TRACES_SAMPLER_ARG=0.2` on the app (`kubectl set env`) - count traces per minute in Jaeger. Then revert and add a `tail_sampling` processor keeping `status_code: ERROR` plus 10% probabilistic; call `/checkout?fail=1` and confirm errors are always kept.
7. **Break and debug (10% domain):** change the app's `OTEL_EXPORTER_OTLP_ENDPOINT` to port 4318 while keeping gRPC protocol; find the error in the app logs and `otelcol_receiver_refused_spans`/`otelcol_receiver_accepted_spans` on `:8888`. Remove `otlp/jaeger` from the traces pipeline - what does zpages `/debug/pipelinez` show?
8. **Operator (reading + optional):** install cert-manager and the OTel Operator, create the `Instrumentation` shown above, deploy a plain (uninstrumented) Flask image with `instrumentation.opentelemetry.io/inject-python: "true"`, and `kubectl describe pod` to see the injected init container and env vars.

## Week plan (20 h each)
- **Week 1:** day 1 fundamentals + signals; days 2-3 API/SDK components and env vars (lab 3); day 4 propagation + semconv (labs 1-2); day 5 OTLP + metrics to Prometheus (lab 4); weekend: re-read the API/SDK section, answer the self-check.
- **Week 2:** days 1-2 Collector config and processors (lab 5); day 3 sampling (lab 6); day 4 Operator + backends (lab 8); day 5 debugging (lab 7) + `otel/otel-exercises.md`; day 6 mock exams; day 7 sit OTCA.

## Self-check
1. What is the difference between the OpenTelemetry API and the SDK, and which one should a library depend on?
2. Name the five SpanKind values and give an example of each.
3. What are the parts of a W3C `traceparent` header?
4. What is a Resource, and which resource attribute is effectively required?
5. BatchSpanProcessor vs SimpleSpanProcessor - when to use each?
6. List the synchronous and asynchronous metric instruments.
7. Cumulative vs delta temporality - which does Prometheus expect?
8. What does a View do? Give two uses.
9. How does OpenTelemetry handle logs from an existing logging library?
10. What is Baggage and what should never go in it?
11. Default ports and paths for OTLP gRPC and OTLP HTTP?
12. In what order should `memory_limiter` and `batch` appear in a pipeline, and why?
13. What is a connector? Give an example.
14. Head vs tail sampling: where does each run, and one drawback of each?
15. Why does tail sampling in a scaled-out gateway need the `loadbalancing` exporter?
16. Which annotation injects Python auto-instrumentation with the OTel Operator, and which CR must exist?
17. Agent vs gateway Collector deployment - what does each typically do?
18. How does the Collector get metrics into Prometheus? Name two ways.
19. The Collector logs no errors, but Jaeger shows nothing. List three things to check.
20. What are semantic conventions? Give the stable HTTP attribute names for method and status code.

<details><summary>Answers</summary>

1. The API defines interfaces (Tracer, Meter, Logs Bridge, Context, Propagators) and is a no-op on its own; the SDK implements them (sampling, processing, exporting). Libraries depend only on the API so apps choose the SDK/config.
2. SERVER (handles an incoming HTTP request), CLIENT (outgoing HTTP/DB call), PRODUCER (publishes a message), CONSUMER (processes a message), INTERNAL (in-process work like `charge-card`).
3. `version-traceid-parentid-flags`, e.g. `00-<32 hex>-<16 hex>-01`; flags `01` = sampled.
4. Immutable attributes describing the entity producing telemetry (service, host, pod, cloud); `service.name` (defaults to `unknown_service:...`).
5. Batch for production (async, queued, efficient); Simple for tests/debugging (exports each span synchronously on end).
6. Sync: Counter, UpDownCounter, Histogram, Gauge. Async: ObservableCounter, ObservableUpDownCounter, ObservableGauge.
7. Cumulative (running total since start); delta reports only the change since the last export.
8. SDK configuration that changes an instrument's output: rename it, drop/keep attributes (cardinality control), change histogram buckets or use exponential histograms, drop an instrument.
9. Via the Logs Bridge API: an appender/handler forwards records to a LoggerProvider, which adds trace/span IDs and resource and exports (e.g. OTLP); or the Collector's `filelog` receiver reads files.
10. Key/value context propagated to all downstream services (W3C `baggage` header). Never secrets or PII - it is visible to every hop and third parties.
11. gRPC 4317; HTTP 4318 with `/v1/traces`, `/v1/metrics`, `/v1/logs`.
12. `memory_limiter` first (refuse data before the process runs out of memory), `batch` last before exporters (batches what survived filtering/sampling).
13. A component that is an exporter in one pipeline and a receiver in another: `spanmetrics` (traces -> RED metrics), `count`, `routing`, `forward`, `servicegraph`.
14. Head: in the SDK at trace start - cheap but blind to errors/latency. Tail: in the Collector after the trace completes - smart but memory hungry and needs all spans in one place.
15. Spans of one trace arrive at different replicas; `loadbalancing` routes by trace ID so one Collector sees the complete trace.
16. `instrumentation.opentelemetry.io/inject-python: "true"` on the pod template; an `Instrumentation` CR in the namespace (or referenced as `ns/name`).
17. Agent: DaemonSet/sidecar near the app - receive locally, add host/k8s metadata, offload quickly. Gateway: central Deployment - tail sampling, auth/secrets for backends, routing, fan-out.
18. `prometheus` exporter exposing `/metrics` for Prometheus to scrape; `prometheusremotewrite` exporter or pushing OTLP to Prometheus's OTLP receiver.
19. Is the exporter actually in the traces pipeline; endpoint/port/TLS (`insecure`) correct; `otelcol_exporter_send_failed_spans` and debug exporter output; is the app sending at all (`otelcol_receiver_accepted_spans`) and with the right `service.name`; sampling set to 0.
20. Standardised names and meanings for attributes, span names, metrics and resources across languages; `http.request.method` and `http.response.status_code`.
</details>

## Resources
https://opentelemetry.io/docs (concepts, specs, Collector), https://github.com/open-telemetry/opentelemetry-specification, https://opentelemetry.io/docs/specs/semconv/, https://github.com/open-telemetry/opentelemetry-demo (the Astronomy Shop - run it once), "Learning OpenTelemetry" (O'Reilly, 2024), https://training.linuxfoundation.org/certification/opentelemetry-certified-associate-otca/ (curriculum PDF), LFS148 "Getting Started with OpenTelemetry" (free)
