import pytest
from bathing_route.models import Coordinates
from bathing_route.services import geo_service, gpx_service


GPX_SIMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test">
  <trk>
    <name>Test Route</name>
    <trkseg>
      <trkpt lat="58.0" lon="14.0"><ele>0</ele></trkpt>
      <trkpt lat="58.1" lon="14.1"><ele>0</ele></trkpt>
      <trkpt lat="58.2" lon="14.2"><ele>0</ele></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def test_parse_gpx():
    route = gpx_service.parse_gpx(GPX_SIMPLE)
    assert len(route.coords) == 3
    assert route.coords[0] == Coordinates(lat=58.0, lon=14.0)
    assert route.total_distance_m > 0


def test_coords_to_linestring():
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.1, lon=14.1)]
    linestring = geo_service.coords_to_linestring(coords)
    assert len(linestring.coords) == 2


def test_create_buffer():
    from shapely.geometry import LineString
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.1, lon=14.1)]
    linestring = geo_service.coords_to_linestring(coords)
    buffer = geo_service.create_buffer(linestring, 1000)
    assert not buffer.is_empty


def test_filter_points_in_polygon():
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.5, lon=14.5)]
    linestring = geo_service.coords_to_linestring(coords)
    buffer = geo_service.create_buffer(linestring, 50000)
    result = geo_service.filter_points_in_polygon(coords, buffer)
    assert len(result) >= 1
