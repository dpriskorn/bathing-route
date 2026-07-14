import pytest
from unittest.mock import patch

from starlette.testclient import TestClient

from bathing_route.services.wikidata_service import WikidataService


@pytest.fixture(autouse=True)
def reset_wikidata_singleton():
    WikidataService._instance = None
    WikidataService._loaded = False
    WikidataService._loaded_backend = None
    yield
    WikidataService._instance = None
    WikidataService._loaded = False
    WikidataService._loaded_backend = None


@pytest.fixture
def client():
    from bathing_route.main import create_app
    app = create_app()
    return TestClient(app)


def test_delete_cache_clears_singleton(client):
    with patch("bathing_route.api.clear_cache") as mock_clear, \
         patch("bathing_route.api.clear_label_cache") as mock_clear_labels:
        mock_clear.return_value = 10
        mock_clear_labels.return_value = 5
        response = client.delete("/api/cache")
        assert response.status_code == 200
        assert response.json()["deleted_sites"] == 10
        assert response.json()["deleted_labels"] == 5
        assert WikidataService._loaded is False


def test_delete_cache_with_backend(client):
    with patch("bathing_route.api.clear_cache") as mock_clear, \
         patch("bathing_route.api.clear_label_cache") as mock_clear_labels:
        mock_clear.return_value = 5
        mock_clear_labels.return_value = 3
        response = client.delete("/api/cache?backend=wdqs")
        assert response.status_code == 200
        assert response.json()["deleted_sites"] == 5
        assert response.json()["deleted_labels"] == 3
        mock_clear.assert_called_once_with("wdqs")


def test_delete_cache_invalid_backend(client):
    response = client.delete("/api/cache?backend=invalid")
    assert response.status_code == 400


def test_cache_info_endpoint(client):
    with patch("bathing_route.api.get_cache_info") as mock_info:
        mock_info.return_value = {
            "backend": "wdqs",
            "count": 100,
            "fetched_at": "2024-01-01T00:00:00",
            "fresh": True,
            "ttl_hours": 24,
        }
        response = client.get("/api/cache?backend=wdqs")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "wdqs"
        assert data["count"] == 100
        assert data["fresh"] is True


def test_cache_info_invalid_backend(client):
    response = client.get("/api/cache?backend=invalid")
    assert response.status_code == 400
