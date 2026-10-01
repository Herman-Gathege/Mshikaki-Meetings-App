from fastapi.testclient import TestClient


def test_unknown_api_route_returns_json_not_the_spa(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http.404"


def test_every_response_carries_a_request_reference(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    reference = response.headers.get("x-request-id")
    assert reference and len(reference) >= 8


def test_an_unexpected_failure_gives_the_user_a_reference(settings) -> None:
    """A crash shows a human sentence and a reference, never a stack trace."""
    from app.main import create_app

    app = create_app(settings)

    @app.get("/api/_boom")
    def boom() -> None:
        raise RuntimeError("something genuinely broken")

    with TestClient(app, raise_server_exceptions=False) as failing:
        response = failing.get("/api/_boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert "try again" in error["message"].lower()
    assert error["details"]["request_id"] == response.headers["x-request-id"]
