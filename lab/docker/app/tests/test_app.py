import os

os.environ["REQUIRE_DB"] = "false"

from app import add, app  # noqa: E402


def test_add():
    assert add(2, 3) == 5


def test_health():
    client = app.test_client()
    assert client.get("/healthz").json == {"status": "ok"}


def test_ready_without_db():
    client = app.test_client()
    assert client.get("/readyz").status_code == 200
