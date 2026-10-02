"""otel-demo: small Flask shop instrumented with OpenTelemetry for the OTCA lab.

Run under zero-code instrumentation, which installs and configures the SDK from OTEL_* env vars:
    opentelemetry-instrument python app.py
This file only uses the OpenTelemetry *API* (trace, metrics, baggage). Flask, requests and logging
spans/metrics/log records come from the auto-instrumentation libraries; reserve-stock and charge-card
are manual spans; demo.checkouts is a manual metric.

Endpoints: /  /rolldice  /checkout[?fail=1]  /inventory  /healthz
"""
import logging
import os
import random
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import baggage, metrics, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

PORT = int(os.environ.get("PORT", "5000"))
SELF_URL = os.environ.get("SELF_URL", f"http://127.0.0.1:{PORT}")

app = Flask(__name__)
log = logging.getLogger("otel-demo")
logging.basicConfig(level=logging.INFO)

tracer = trace.get_tracer("otel-demo.shop", "0.1.0")        # instrumentation scope
meter = metrics.get_meter("otel-demo.shop", "0.1.0")
checkouts = meter.create_counter("demo.checkouts", unit="{checkout}",
                                 description="Checkouts attempted")
dice = meter.create_histogram("demo.dice.value", unit="{pip}", description="Dice rolls")
stock_level = {"widget": 100, "gadget": 40}
meter.create_observable_gauge(
    "demo.stock.level", unit="{item}", description="Items in stock",
    callbacks=[lambda options: [metrics.Observation(v, {"item": k}) for k, v in stock_level.items()]])


@app.get("/")
def index():
    return jsonify(service="otel-demo", endpoints=["/rolldice", "/checkout", "/inventory"])


@app.get("/healthz")
def healthz():
    return "ok\n"


@app.get("/rolldice")
def rolldice():
    value = random.randint(1, 6)
    trace.get_current_span().set_attribute("dice.value", value)   # enrich the auto-created SERVER span
    dice.record(value)
    log.info("rolled %d", value)
    return jsonify(value=value)


@app.get("/inventory")
def inventory():
    item = request.args.get("item", "widget")
    tenant = baggage.get_baggage("tenant") or "none"               # baggage extracted from the caller
    trace.get_current_span().set_attribute("app.tenant", tenant)
    time.sleep(random.uniform(0.005, 0.03))
    return jsonify(item=item, available=stock_level.get(item, 0))


@app.get("/checkout")
def checkout():
    fail = request.args.get("fail") == "1"
    method = random.choice(["card", "card", "paypal"])
    item = random.choice(list(stock_level))
    # CLIENT span + traceparent header come from the requests instrumentation: /inventory joins this trace.
    with tracer.start_as_current_span("reserve-stock", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("app.item", item)
        resp = requests.get(f"{SELF_URL}/inventory", params={"item": item}, timeout=5)
        stock_level[item] = max(0, resp.json()["available"] - 1) or 100
    with tracer.start_as_current_span("charge-card") as span:
        span.set_attribute("payment.method", method)
        time.sleep(random.uniform(0.05, 0.25))
        try:
            if fail or random.random() < 0.05:
                raise RuntimeError("payment gateway timeout")
            span.add_event("payment.authorised", {"payment.method": method})
        except RuntimeError as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            checkouts.add(1, {"payment.method": method, "outcome": "error"})
            log.error("checkout failed: %s", exc)                  # log record carries trace_id/span_id
            return jsonify(error=str(exc)), 502
    checkouts.add(1, {"payment.method": method, "outcome": "ok"})
    log.info("checkout ok item=%s method=%s", item, method)
    return jsonify(status="ok", item=item, payment=method)


if __name__ == "__main__":
    # threaded so /checkout can call /inventory on the same process; no reloader (breaks instrumentation)
    app.run(host="0.0.0.0", port=PORT, threaded=True, debug=False)
