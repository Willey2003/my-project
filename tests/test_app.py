"""Tests for the GitHub Code Analyzer API (no network required)."""
import pytest
from fastapi.testclient import TestClient

from app import app, extract_repo_info

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_ready():
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_extract_repo_info_valid():
    owner, repo = extract_repo_info("https://github.com/octocat/Hello-World")
    assert (owner, repo) == ("octocat", "Hello-World")


def test_extract_repo_info_trailing_slash():
    owner, repo = extract_repo_info("https://github.com/octocat/Hello-World/")
    assert (owner, repo) == ("octocat", "Hello-World")


def test_extract_repo_info_invalid():
    with pytest.raises(ValueError):
        extract_repo_info("not-a-url")


def test_analyze_rejects_invalid_url():
    # Reaches the 400 branch before any network call.
    r = client.post("/analyze", json={"repo_url": "bad"})
    assert r.status_code == 400
