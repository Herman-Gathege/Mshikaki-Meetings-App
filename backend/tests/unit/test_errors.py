from fastapi.testclient import TestClient


def test_unknown_api_route_returns_json_not_the_spa(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http.404"
