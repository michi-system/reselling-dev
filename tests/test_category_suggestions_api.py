from fastapi.testclient import TestClient

from app.main import app
from app.services.categories import suggest_categories


def test_suggest_categories_prefers_matching_alias() -> None:
    items = suggest_categories(
        source_site="yahoo",
        market_source="ebay",
        query_text="sony speaker",
        selected_category="",
        search_text="",
        limit=10,
    )
    assert items
    assert items[0].internal_category == "audio"


def test_category_suggestions_api_returns_items() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/v1/categories/suggestions",
            params={
                "source_site": "rakuten",
                "market_source": "ebay",
                "query": "camera lens",
                "q": "カメラ",
                "limit": 20,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
