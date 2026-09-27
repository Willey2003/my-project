"""Tiny API used by the Docker, CI/CD, Kubernetes and GitOps labs."""
import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)
VERSION = os.environ.get("APP_VERSION", "dev")


def db_ok() -> bool:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        import psycopg
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("select 1")
        return True
    except Exception:
        return False


@app.get("/")
def index():
    return jsonify(service="lab-api", version=VERSION, host=socket.gethostname())


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/readyz")
def readyz():
    ok = db_ok() or os.environ.get("REQUIRE_DB", "true") == "false"
    return jsonify(ready=ok), (200 if ok else 503)


def add(a: int, b: int) -> int:
    return a + b
