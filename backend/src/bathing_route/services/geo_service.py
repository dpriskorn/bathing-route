import logging
from collections.abc import Sequence

from pyproj import Transformer
from shapely.geometry import LineString, MultiPoint, Point  # type: ignore[import-untyped]
from shapely.ops import transform  # type: ignore[import-untyped]

from bathing_route.models import (
    BathingSpot,
    Coordinates,
    GeoJSONFeature,
    GeoJSONLineString,
    GeoJSONPoint,
    GeoJSONPolygon,
)


log = logging.getLogger(__name__)

WGS84 = 4326
SWEREF99_TM = 3006

_to3006 = Transformer.from_crs(WGS84, SWEREF99_TM, always_xy=True).transform
_to4326 = Transformer.from_crs(SWEREF99_TM, WGS84, always_xy=True).transform


def coords_to_linestring(coords: list[Coordinates]) -> LineString:
    points = [(c.lon, c.lat) for c in coords]
    return LineString(points)


def create_buffer(route: LineString, buffer_m: float) -> LineString:
    route3006 = transform(_to3006, route)
    buffer3006 = route3006.buffer(buffer_m)
    buffer4326 = transform(_to4326, buffer3006)
    return buffer4326


def filter_points_in_polygon(
    points: Sequence[Coordinates | BathingSpot],
    polygon: LineString,
) -> list[Coordinates | BathingSpot]:
    if polygon.is_empty:
        return []
    multipoint = MultiPoint([Point(p.lon, p.lat) for p in points])
    if hasattr(multipoint, "geoms"):
        return [points[i] for i, contained_pt in enumerate(multipoint.geoms) if polygon.contains(contained_pt)]
    return [p for p in points if polygon.contains(Point(p.lon, p.lat))]


def linestring_to_geojson(route: LineString) -> GeoJSONFeature:
    coords_geojson: list[list[float]] = [[lon, lat] for lon, lat in route.coords]
    return GeoJSONFeature(
        geometry=GeoJSONLineString(type="LineString", coordinates=coords_geojson),
        properties={},
    )


def polygon_to_geojson(polygon: LineString) -> GeoJSONFeature:
    if polygon.is_empty:
        return GeoJSONFeature(
            geometry=GeoJSONPolygon(type="Polygon", coordinates=[]),
            properties={},
        )
    coords_geojson: list[list[list[float]]] = [[[p[0], p[1]] for p in polygon.exterior.coords]]
    return GeoJSONFeature(
        geometry=GeoJSONPolygon(type="Polygon", coordinates=coords_geojson),
        properties={},
    )


def coordinate_to_geojson(coord: Coordinates) -> GeoJSONFeature:
    return GeoJSONFeature(
        geometry=GeoJSONPoint(type="Point", coordinates=[coord.lon, coord.lat]),
        properties={},
    )
