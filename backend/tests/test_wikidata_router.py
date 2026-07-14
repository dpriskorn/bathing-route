import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    from starlette.testclient import TestClient
    from bathing_route.main import create_app
    app = create_app()
    return TestClient(app)


class TestWikidataDetails:
    def test_get_wikidata_details_basic(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {
                        "P18": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": "Test_Beach.jpg"
                                    }
                                }
                            }
                        ]
                    },
                    "sitelinks": {
                        "enwiki": {"title": "Test_Beach"},
                        "svwiki": {"title": "Test_Beach_SV"},
                    }
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock, return_value="Test Beach"), \
             patch("bathing_route.routers.wikidata._fetch_entity_data", new_callable=AsyncMock, return_value=mock_entity_data):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["qid"] == "Q1"
        assert data["label"] == "Test Beach"
        assert data["image_url"] == "https://commons.wikimedia.org/wiki/Special:FilePath/Test_Beach.jpg"
        assert data["wikidata_url"] == "https://www.wikidata.org/wiki/Q1"
        assert len(data["wikipedia_urls"]) == 2
        wikipedia_langs = {w["lang"] for w in data["wikipedia_urls"]}
        assert wikipedia_langs == {"en", "sv"}
        mock_set.assert_called_once_with("Q1", "en", "Test Beach")

    def test_get_wikidata_details_uses_cached_label(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {},
                    "sitelinks": {}
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value="Cached Label"), \
             patch("bathing_route.routers.wikidata._fetch_entity_data", new_callable=AsyncMock, return_value=mock_entity_data):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Cached Label"

    def test_get_wikidata_details_fallback_to_english(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {},
                    "sitelinks": {}
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.side_effect = [None, "English Label"]

                response = client.get("/api/wikidata/Q1/details?lang=sv")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "English Label"
        assert mock_fetch.call_count == 2

    def test_get_wikidata_details_qid_fallback(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {},
                    "sitelinks": {}
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock, return_value=None):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Q1"

    def test_get_wikidata_details_no_image(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {},
                    "sitelinks": {}
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value="Test"), \
             patch("bathing_route.routers.wikidata._fetch_entity_data", new_callable=AsyncMock, return_value=mock_entity_data):

            response = client.get("/api/wikidata/Q1/details")

        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] is None

    def test_get_wikidata_details_fetch_label_returns_text(self, client):
        mock_entity_data = {
            "entities": {
                "Q1": {
                    "claims": {},
                    "sitelinks": {}
                }
            }
        }

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock), \
             patch("bathing_route.routers.wikidata._fetch_entity_data", new_callable=AsyncMock, return_value=mock_entity_data), \
             patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "Plain Text Label"
            mock_response.json = lambda: "Plain Text Label"
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Plain Text Label"
