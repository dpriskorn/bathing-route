import pytest
from unittest.mock import patch, AsyncMock

from bathing_route.models import Coordinates
from bathing_route.services import geo_service


def test_linestring_to_geojson():
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.1, lon=14.1)]
    linestring = geo_service.coords_to_linestring(coords)
    feature = geo_service.linestring_to_geojson(linestring)
    assert feature.type == "Feature"
    assert feature.geometry.type == "LineString"
    assert feature.geometry.coordinates == [[14.0, 58.0], [14.1, 58.1]]


def test_polygon_to_geojson():
    from shapely.geometry import LineString
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.1, lon=14.1), Coordinates(lat=58.0, lon=14.2)]
    linestring = geo_service.coords_to_linestring(coords)
    buffer = geo_service.create_buffer(linestring, 1000)
    feature = geo_service.polygon_to_geojson(buffer)
    assert feature.type == "Feature"
    assert feature.geometry.type == "Polygon"
    assert len(feature.geometry.coordinates) > 0


def test_polygon_to_geojson_empty():
    from shapely import wkt
    from bathing_route.models import Coordinates
    coords = [Coordinates(lat=58.0, lon=14.0), Coordinates(lat=58.1, lon=14.1)]
    linestring = geo_service.coords_to_linestring(coords)
    buffer = geo_service.create_buffer(linestring, 0)
    feature = geo_service.polygon_to_geojson(buffer)
    assert feature.geometry.coordinates == []


def test_coordinate_to_geojson():
    coord = Coordinates(lat=58.0, lon=14.0)
    feature = geo_service.coordinate_to_geojson(coord)
    assert feature.type == "Feature"
    assert feature.geometry.type == "Point"
    assert feature.geometry.coordinates == [14.0, 58.0]


def test_filter_points_none_inside():
    from bathing_route.models import Coordinates as C
    route_coords = [C(lat=10.0, lon=10.0), C(lat=10.1, lon=10.1)]
    test_points = [Coordinates(lat=50.0, lon=50.0), Coordinates(lat=60.0, lon=60.0)]
    linestring = geo_service.coords_to_linestring(route_coords)
    buffer = geo_service.create_buffer(linestring, 1000)
    result = geo_service.filter_points_in_polygon(test_points, buffer)
    assert len(result) == 0
