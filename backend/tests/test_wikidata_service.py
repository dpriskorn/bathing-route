import pytest
from unittest.mock import patch

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


class TestWikidataServiceSync:
    def test_extract_qid(self):
        svc = WikidataService()
        assert svc._extract_qid("http://www.wikidata.org/entity/Q123") == "Q123"
        assert svc._extract_qid("Q456") == "Q456"
        assert svc._extract_qid("") is None
        assert svc._extract_qid("http://example.com/item/Q789") == "Q789"

    def test_parse_coord_valid(self):
        svc = WikidataService()
        result = svc._parse_coord("Point(14.5 58.2)")
        assert result == {"lon": 14.5, "lat": 58.2}

    def test_parse_coord_invalid(self):
        svc = WikidataService()
        assert svc._parse_coord("invalid") is None
        assert svc._parse_coord("") is None

    def test_is_loaded_false_by_default(self):
        svc = WikidataService()
        assert svc.is_loaded() is False

    def test_get_loaded_backend_none_by_default(self):
        svc = WikidataService()
        assert svc.get_loaded_backend() is None

    def test_get_bathing_spots_raises_if_not_loaded(self):
        svc = WikidataService()
        svc._loaded = False
        with pytest.raises(RuntimeError, match="load_bathing_spots"):
            svc.get_bathing_spots()


class TestWikidataServiceLoad:
    @pytest.mark.asyncio
    async def test_load_bathing_spots_wdqs(self):
        mock_data = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q1"},
                        "itemLabel": {"value": "Test Beach"},
                        "coord": {"value": "Point(14.0 58.0)"},
                    },
                ]
            }
        }

        with patch("bathing_route.services.wikidata_service.get_cached_spots", return_value=None), \
             patch("bathing_route.services.wikidata_service.set_cached_spots"), \
             patch("bathing_route.services.wikidata_service.requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_data

            svc = WikidataService()
            await svc.load_bathing_spots("wdqs")

        spots = svc.get_bathing_spots()
        assert len(spots) == 1
        assert spots[0].qid == "Q1"
        assert spots[0].label == "Test Beach"
        assert spots[0].lat == 58.0
        assert spots[0].lon == 14.0
        assert svc.get_loaded_backend() == "wdqs"

    @pytest.mark.asyncio
    async def test_load_bathing_spots_skips_invalid_coords(self):
        mock_data = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q1"},
                        "itemLabel": {"value": "Valid Spot"},
                        "coord": {"value": "Point(14.0 58.0)"},
                    },
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q2"},
                        "itemLabel": {"value": "Invalid Coord"},
                        "coord": {"value": "not_a_point"},
                    },
                ]
            }
        }

        with patch("bathing_route.services.wikidata_service.get_cached_spots", return_value=None), \
             patch("bathing_route.services.wikidata_service.set_cached_spots"), \
             patch("bathing_route.services.wikidata_service.requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_data

            svc = WikidataService()
            await svc.load_bathing_spots("wdqs")

        spots = svc.get_bathing_spots()
        assert len(spots) == 1
        assert spots[0].qid == "Q1"

    @pytest.mark.asyncio
    async def test_load_bathing_spots_does_not_reload_same_backend(self):
        mock_data = {
            "results": {"bindings": []}
        }

        with patch("bathing_route.services.wikidata_service.get_cached_spots", return_value=None), \
             patch("bathing_route.services.wikidata_service.set_cached_spots"), \
             patch("bathing_route.services.wikidata_service.requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_data

            svc = WikidataService()
            await svc.load_bathing_spots("wdqs")
            await svc.load_bathing_spots("wdqs")

        assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_load_bathing_spots_reloads_different_backend(self):
        mock_data = {
            "results": {"bindings": []}
        }

        with patch("bathing_route.services.wikidata_service.get_cached_spots", return_value=None), \
             patch("bathing_route.services.wikidata_service.set_cached_spots"), \
             patch("bathing_route.services.wikidata_service.requests.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_data

            svc = WikidataService()
            await svc.load_bathing_spots("wdqs")
            await svc.load_bathing_spots("qlever")

        assert mock_get.call_count == 2
