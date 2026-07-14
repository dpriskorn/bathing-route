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
        mock_wikipedia_urls = [
            {"lang": "en", "title": "Test_Beach", "url": "https://en.wikipedia.org/wiki/Test_Beach"},
            {"lang": "sv", "title": "Test_Beach_SV", "url": "https://sv.wikipedia.org/wiki/Test_Beach_SV"},
        ]

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set_label, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock, return_value="Test Beach"), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value="Test_Beach.jpg"), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=mock_wikipedia_urls), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock) as mock_set_details:

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
        mock_set_label.assert_called_once_with("Q1", "en", "Test Beach")
        mock_set_details.assert_called_once_with("Q1", "Test_Beach.jpg", mock_wikipedia_urls)

    def test_get_wikidata_details_uses_cached_label(self, client):
        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value="Cached Label"), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(None, [])), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=[]), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Cached Label"

    def test_get_wikidata_details_fallback_to_english(self, client):
        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock) as mock_fetch, \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(None, [])), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=[]), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock):
                mock_fetch.side_effect = [None, "English Label"]

                response = client.get("/api/wikidata/Q1/details?lang=sv")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "English Label"
        assert mock_fetch.call_count == 2

    def test_get_wikidata_details_qid_fallback(self, client):
        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock) as mock_set, \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(None, [])), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=[]), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Q1"

    def test_get_wikidata_details_no_image(self, client):
        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value="Test"), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(None, [])), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=[]), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock):

            response = client.get("/api/wikidata/Q1/details")

        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] is None

    def test_get_wikidata_details_fetch_label_returns_text(self, client):
        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata.set_cached_label", new_callable=AsyncMock), \
             patch("bathing_route.routers.wikidata._fetch_label", new_callable=AsyncMock, return_value="Plain Text Label"), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(None, [])), \
             patch("bathing_route.routers.wikidata._fetch_p18", new_callable=AsyncMock, return_value=None), \
             patch("bathing_route.routers.wikidata._fetch_sitelinks", new_callable=AsyncMock, return_value=[]), \
             patch("bathing_route.routers.wikidata.set_cached_wikidata_details", new_callable=AsyncMock):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Plain Text Label"

    def test_get_wikidata_details_uses_cache(self, client):
        cached_p18 = "Cached_Image.jpg"
        cached_sitelinks = [
            {"lang": "en", "title": "Cached_Page", "url": "https://en.wikipedia.org/wiki/Cached_Page"},
        ]

        with patch("bathing_route.routers.wikidata.get_cached_label", new_callable=AsyncMock, return_value="Cached Label"), \
             patch("bathing_route.routers.wikidata.get_cached_wikidata_details", new_callable=AsyncMock, return_value=(cached_p18, cached_sitelinks)):

            response = client.get("/api/wikidata/Q1/details?lang=en")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Cached Label"
        assert data["image_url"] == "https://commons.wikimedia.org/wiki/Special:FilePath/Cached_Image.jpg"
        assert len(data["wikipedia_urls"]) == 1


class TestFetchP18:
    @pytest.mark.asyncio
    async def test_fetch_p18_returns_image(self):
        from bathing_route.routers.wikidata import _fetch_p18
        mock_response = {
            "statements": {
                "P18": [
                    {
                        "mainsnak": {
                            "datavalue": {"type": "string", "value": "Beach_test.jpg"}
                        }
                    }
                ]
            }
        }
        with patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_aclient = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json = lambda: mock_response
            mock_aclient.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value = mock_aclient

            result = await _fetch_p18("Q123")

        assert result == "Beach_test.jpg"

    @pytest.mark.asyncio
    async def test_fetch_p18_returns_none_when_no_image(self):
        from bathing_route.routers.wikidata import _fetch_p18
        mock_response = {"statements": {}}
        with patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_aclient = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json = lambda: mock_response
            mock_aclient.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value = mock_aclient

            result = await _fetch_p18("Q123")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_p18_returns_none_on_error(self):
        from bathing_route.routers.wikidata import _fetch_p18
        with patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_aclient = AsyncMock()
            mock_aclient.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.return_value = mock_aclient

            result = await _fetch_p18("Q123")

        assert result is None


class TestFetchSitelinks:
    @pytest.mark.asyncio
    async def test_fetch_sitelinks_returns_list(self):
        from bathing_route.routers.wikidata import _fetch_sitelinks
        mock_response = {
            "sitelinks": [
                {"site": "enwiki", "title": "Beach"},
                {"site": "svwiki", "title": "Strand"},
                {"site": "commonswiki", "title": "File:Beach.jpg"},
            ]
        }
        with patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_aclient = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json = lambda: mock_response
            mock_aclient.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
            mock_client.return_value = mock_aclient

            result = await _fetch_sitelinks("Q123")

        assert len(result) == 2
        langs = {r["lang"] for r in result}
        assert langs == {"en", "sv"}
        assert result[0]["url"] == "https://en.wikipedia.org/wiki/Beach"

    @pytest.mark.asyncio
    async def test_fetch_sitelinks_returns_empty_on_error(self):
        from bathing_route.routers.wikidata import _fetch_sitelinks
        with patch("bathing_route.routers.wikidata.httpx.AsyncClient") as mock_client:
            mock_aclient = AsyncMock()
            mock_aclient.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.return_value = mock_aclient

            result = await _fetch_sitelinks("Q123")

        assert result == []
