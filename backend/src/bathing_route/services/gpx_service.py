import logging
from io import StringIO

import gpxpy

from bathing_route.models import Coordinates, GPXRoute


log = logging.getLogger(__name__)


def parse_gpx(gpx_content: str) -> GPXRoute:
    gpx = gpxpy.parse(StringIO(gpx_content))

    coords: list[Coordinates] = []
    total_distance_m = 0.0

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords.append(Coordinates(lat=point.latitude, lon=point.longitude))

            for i, point in enumerate(segment.points):
                if i > 0:
                    prev = segment.points[i - 1]
                    total_distance_m += haversine(
                        prev.latitude, prev.longitude,
                        point.latitude, point.longitude,
                    )

    log.info(f"Parsed GPX: {len(coords)} points, {total_distance_m:.0f} m total distance")
    return GPXRoute(coords=coords, total_distance_m=total_distance_m)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
