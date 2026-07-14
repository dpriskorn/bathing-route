import pytest
from io import BytesIO
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


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_invalid_backend(client):
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="58.0" lon="14.0"></trkpt>
<trkpt lat="58.1" lon="14.1"></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("route.gpx", BytesIO(gpx_content), "application/gpx+xml")}
    response = client.post("/api/analyze", params={"backend": "invalid"}, files=files)
    assert response.status_code == 400


def test_analyze_invalid_buffer(client):
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="58.0" lon="14.0"></trkpt>
<trkpt lat="58.1" lon="14.1"></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("route.gpx", BytesIO(gpx_content), "application/gpx+xml")}
    with patch("bathing_route.api.wikidata_service.WikidataService") as MockWDS:
        mock_instance = MockWDS.return_value
        mock_instance.is_loaded.return_value = True
        mock_instance.get_loaded_backend.return_value = "wdqs"
        mock_instance.load_bathing_spots.return_value = None
        mock_instance.get_bathing_spots.return_value = []
        response = client.post("/api/analyze", params={"buffer_km": 100}, files=files)
    assert response.status_code == 400


def test_analyze_invalid_gpx(client):
    files = {"file": ("notgpx.txt", BytesIO(b"not gpx content"), "text/plain")}
    response = client.post("/api/analyze", data={"buffer_km": 10}, files=files)
    assert response.status_code == 400


def test_analyze_too_few_points(client):
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="58.0" lon="14.0"></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("route.gpx", BytesIO(gpx_content), "application/gpx+xml")}
    response = client.post("/api/analyze", data={"buffer_km": 10}, files=files)
    assert response.status_code == 400


def test_analyze_valid_gpx(client):
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test">
<trk><name>Test</name><trkseg>
<trkpt lat="58.0" lon="14.0"><ele>0</ele></trkpt>
<trkpt lat="58.1" lon="14.1"><ele>0</ele></trkpt>
<trkpt lat="58.2" lon="14.2"><ele>0</ele></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("route.gpx", BytesIO(gpx_content), "application/gpx+xml")}

    mock_spots = [
        type("BathingSpot", (), {"qid": "Q1", "lat": 58.05, "lon": 14.05, "image_url": None})(),
    ]

    with patch("bathing_route.api.wikidata_service.WikidataService") as MockWDS:
        mock_instance = MockWDS.return_value
        mock_instance.is_loaded.return_value = True
        mock_instance.get_loaded_backend.return_value = "wdqs"
        mock_instance.load_bathing_spots.return_value = None
        mock_instance.get_bathing_spots.return_value = mock_spots

        response = client.post("/api/analyze", data={"buffer_km": 10}, files=files)
        assert response.status_code == 200

        data = response.json()
        assert "bathing_spots" in data
        assert "route" in data
        assert "buffer" in data
        assert data["route"]["geometry"]["type"] == "LineString"
        assert data["buffer"]["geometry"]["type"] == "Polygon"


def test_bathing_spots_count_loaded(client):
    with patch("bathing_route.api.wikidata_service.WikidataService") as MockWDS:
        mock_instance = MockWDS.return_value
        mock_instance.is_loaded.return_value = True
        mock_instance.get_bathing_spots.return_value = [
            type("BathingSpot", (), {"qid": "Q1", "lat": 1.0, "lon": 2.0, "image_url": None})(),
        ]

        response = client.get("/api/bathing-spots/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1


def test_bathing_spots_count_not_loaded(client):
    with patch("bathing_route.api.wikidata_service.WikidataService") as MockWDS:
        mock_instance = MockWDS.return_value
        mock_instance.is_loaded.return_value = False

        response = client.get("/api/bathing-spots/count")
        assert response.status_code == 503
