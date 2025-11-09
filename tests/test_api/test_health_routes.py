import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_all_ok(client):
    ok_result = {"status": "ok", "message": "ok"}

    with patch("src.api.routes.health.check_database", return_value=ok_result), \
            patch("src.api.routes.health.check_redis", return_value=ok_result), \
            patch("src.api.routes.health.check_celery_workers", return_value=ok_result), \
            patch("src.api.routes.health.check_disk_space", return_value=ok_result):
        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["checks"]["database"] == ok_result
    assert data["checks"]["redis"] == ok_result
    assert data["checks"]["celery_workers"] == ok_result
    assert data["checks"]["disk"] == ok_result


def test_healthz_warning(client):
    ok_result = {"status": "ok", "message": "ok"}
    warning_result = {"status": "warning", "message": "disk high"}

    with patch("src.api.routes.health.check_database", return_value=ok_result), \
            patch("src.api.routes.health.check_redis", return_value=ok_result), \
            patch("src.api.routes.health.check_celery_workers", return_value=ok_result), \
            patch("src.api.routes.health.check_disk_space", return_value=warning_result):
        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "warning"
    assert data["checks"]["disk"] == warning_result


def test_healthz_error(client):
    ok_result = {"status": "ok", "message": "ok"}
    error_result = {"status": "error", "message": "redis down"}

    with patch("src.api.routes.health.check_database", return_value=ok_result), \
            patch("src.api.routes.health.check_redis", return_value=error_result), \
            patch("src.api.routes.health.check_celery_workers", return_value=ok_result), \
            patch("src.api.routes.health.check_disk_space", return_value=ok_result):
        response = client.get("/healthz")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["redis"] == error_result


def test_simple_healthz(client):
    response = client.get("/healthz/simple")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_database_healthz_success(client):
    ok_result = {"status": "ok", "message": "ok"}

    with patch("src.api.routes.health.check_database", return_value=ok_result):
        response = client.get("/healthz/database")

    assert response.status_code == 200
    assert response.json() == ok_result


def test_database_healthz_failure(client):
    error_result = {"status": "error", "message": "db error"}

    with patch("src.api.routes.health.check_database", return_value=error_result):
        response = client.get("/healthz/database")

    assert response.status_code == 503
    assert response.json() == error_result


def test_redis_healthz_success(client):
    ok_result = {"status": "ok", "message": "ok"}

    with patch("src.api.routes.health.check_redis", return_value=ok_result):
        response = client.get("/healthz/redis")

    assert response.status_code == 200
    assert response.json() == ok_result


def test_redis_healthz_failure(client):
    error_result = {"status": "error", "message": "redis error"}

    with patch("src.api.routes.health.check_redis", return_value=error_result):
        response = client.get("/healthz/redis")

    assert response.status_code == 503
    assert response.json() == error_result
