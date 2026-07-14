from typing import Any, Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float
    lon: float


class BathingSpot(BaseModel):
    qid: str
    label: str
    lat: float
    lon: float


class GPXRoute(BaseModel):
    coords: list[Coordinates]
    total_distance_m: float


class GeoJSONPoint(BaseModel):
    type: Literal["Point"]
    coordinates: list[float]


class GeoJSONLineString(BaseModel):
    type: Literal["LineString"]
    coordinates: list[list[float]]


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONPoint | GeoJSONLineString | GeoJSONPolygon
    properties: dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    bathing_spots: GeoJSONFeatureCollection
    route: GeoJSONFeature
    buffer: GeoJSONFeature
