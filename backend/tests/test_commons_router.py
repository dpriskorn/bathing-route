import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient


@pytest.fixture
def client():
    from bathing_route.main import create_app
    app = create_app()
    return TestClient(app)


def test_get_commons_image_cache_hit(client):
    with patch("bathing_route.routers.commons.get_cached_commons_image", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "url": "https://upload.wikimedia.org/wikipedia/commons/A/Ab.jpg",
            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/A/Ab.jpg/400px-Ab.jpg",
        }
        response = client.get("/api/commons-image?filename=Ab.jpg")
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://upload.wikimedia.org/wikipedia/commons/A/Ab.jpg"
        assert "thumburl" in data


def test_get_commons_image_strips_special_filepath(client):
    with patch("bathing_route.routers.commons.get_cached_commons_image", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "url": "https://upload.wikimedia.org/wikipedia/commons/A/Ab.jpg",
            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/A/Ab.jpg/400px-Ab.jpg",
        }
        response = client.get("/api/commons-image?filename=Special:FilePath/Ab.jpg")
        assert response.status_code == 200
        mock_get.assert_called_once_with("Ab.jpg")


def test_get_commons_image_missing_filename(client):
    response = client.get("/api/commons-image")
    assert response.status_code == 422
