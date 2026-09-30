from fastapi.testclient import TestClient


def test_health_reports_ok_without_touching_the_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_ready_reports_degraded_when_the_database_is_unreachable(
    client: TestClient, monkeypatch
) -> None:
    from app.api import health
    from sqlalchemy.exc import OperationalError

    def boom(_engine) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(health, "check_database", boom)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unreachable"


def test_ready_reports_ok_when_the_database_answers(client: TestClient, monkeypatch) -> None:
    from app.api import health

    monkeypatch.setattr(health, "check_database", lambda _engine: None)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
