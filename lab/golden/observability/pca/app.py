"""shop-api: tiny HTTP service instrumented with prometheus_client for the PCA lab.

Serves /, /cart, /checkout, /healthz on :8000 and /metrics on the same port.
A background thread generates its own traffic so PromQL always has data.
Env: ERROR_RATE (0-1, default 0.02), TRAFFIC_RPS (default 5), APP_VERSION.
"""
import os
import random
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               Info, generate_latest)

ERROR_RATE = float(os.environ.get("ERROR_RATE", "0.02"))
TRAFFIC_RPS = float(os.environ.get("TRAFFIC_RPS", "5"))
VERSION = os.environ.get("APP_VERSION", "1.0.0")
PORT = int(os.environ.get("PORT", "8000"))

REQUESTS = Counter("lab_http_requests", "HTTP requests handled",
                   ["method", "path", "code"])
LATENCY = Histogram("lab_http_request_duration_seconds", "HTTP request latency",
                    ["path"], buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
INFLIGHT = Gauge("lab_inflight_requests", "Requests currently being served")
QUEUE = Gauge("lab_queue_jobs", "Jobs waiting in the checkout queue")
ORDERS = Counter("lab_orders", "Orders placed", ["payment"])
BUILD = Info("lab_build", "Build information")  # exposed as lab_build_info{version=...} 1
BUILD.info({"version": VERSION})

# Pre-initialise known label combinations so series exist at 0.
for p in ("/", "/cart", "/checkout"):
    for c in ("200", "500"):
        REQUESTS.labels("GET", p, c)
for m in ("card", "paypal"):
    ORDERS.labels(m)

BASE_DELAY = {"/": 0.01, "/cart": 0.05, "/checkout": 0.2}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep pod logs quiet
        pass

    def _send(self, code, body, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/metrics":
            return self._send(200, generate_latest(), CONTENT_TYPE_LATEST)
        if path == "/healthz":
            return self._send(200, b"ok\n")
        if path not in BASE_DELAY:
            REQUESTS.labels("GET", "other", "404").inc()
            return self._send(404, b"not found\n")
        with INFLIGHT.track_inprogress(), LATENCY.labels(path).time():
            time.sleep(random.expovariate(1 / BASE_DELAY[path]))
            code = 500 if random.random() < ERROR_RATE else 200
            if path == "/checkout" and code == 200:
                ORDERS.labels(random.choice(["card", "card", "paypal"])).inc()
        REQUESTS.labels("GET", path, str(code)).inc()
        self._send(code, f"{path} -> {code}\n".encode())


def traffic():
    paths = ["/"] * 5 + ["/cart"] * 3 + ["/checkout"] * 2 + ["/missing"]
    while True:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}{random.choice(paths)}", timeout=5)
        except Exception:  # 404/500 raise HTTPError - expected
            pass
        QUEUE.set(max(0, 20 + 15 * random.uniform(-1, 1)))
        time.sleep(1 / TRAFFIC_RPS)


if __name__ == "__main__":
    if TRAFFIC_RPS > 0:
        threading.Thread(target=traffic, daemon=True).start()
    print(f"shop-api {VERSION} listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
