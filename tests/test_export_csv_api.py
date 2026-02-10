from fastapi.testclient import TestClient

from app.main import app


def test_export_api_usage_csv_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/export/api-usage.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "provider,calls_last_hour,hourly_budget" in response.text


def test_export_opportunities_csv_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/export/opportunities.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "opportunity_id,created_at,decision" in response.text
