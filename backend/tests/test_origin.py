import pytest
from fastapi.testclient import TestClient

from app import origin
from app.main import app

client = TestClient(app)


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(origin, "expected_secret", lambda: "s3cret")


def test_via_cloudfront(secret):
    response = client.get("/api/hello", headers={origin.HEADER: "s3cret"})
    assert response.status_code == 200


def test_skipping_cloudfront_is_refused(secret):
    response = client.get("/api/hello")
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


def test_wrong_secret_is_refused(secret):
    response = client.get("/api/hello", headers={origin.HEADER: "guess"})
    assert response.status_code == 403


def test_no_secret_set_allows_all():
    """Running locally: no ORIGIN_SECRET_ARN, so nothing to check."""
    assert client.get("/api/hello").status_code == 200
