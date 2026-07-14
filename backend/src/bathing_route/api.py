import logging
from typing import Any, cast

from fastapi import APIRouter, File, HTTPException, UploadFile

from bathing_route.cache import clear_cache, get_cache_info
from bathing_route.models import (
    AnalyzeResponse,
    BathingSpot,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONPoint,
)
from bathing_route.services import geo_service, gpx_service, wikidata_service


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/cache")
async def cache_info(backend: str = "wdqs") -> dict[str, Any]:
    if backend not in ("wdqs", "qlever"):
        raise HTTPException(status_code=400, detail="backend must be 'wdqs' or 'qlever'")
    return await get_cache_info(backend)


@router.delete("/cache")
async def delete_cache(backend: str | None = None) -> dict[str, Any]:
    if backend is not None and backend not in ("wdqs", "qlever"):
        raise HTTPException(status_code=400, detail="backend must be 'wdqs' or 'qlever'")
    if backend:
        wikidata_service.WikidataService._loaded = False
        wikidata_service.WikidataService._loaded_backend = None
    deleted = await clear_cache(backend)
    return {"deleted": deleted}


@router.get("/bathing-spots/count")
async def bathing_spots_count() -> dict[str, int]:
    service = wikidata_service.WikidataService()
    if not service.is_loaded():
        raise HTTPException(status_code=503, detail="Bathing spots not loaded yet")
    return {"count": len(service.get_bathing_spots())}


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    buffer_km: float = 10.0,
    backend: str = "wdqs",
) -> AnalyzeResponse:
    if backend not in ("wdqs", "qlever"):
        raise HTTPException(status_code=400, detail="backend must be 'wdqs' or 'qlever'")

    if buffer_km < 1.0 or buffer_km > 50.0:
        raise HTTPException(status_code=400, detail="buffer_km must be between 1 and 50")

    contents = await file.read()
    try:
        gpx_content = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="GPX file must be valid UTF-8 text")

    try:
        route = gpx_service.parse_gpx(gpx_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse GPX: {e}")

    if len(route.coords) < 2:
        raise HTTPException(status_code=400, detail="GPX must contain at least 2 points")

    linestring = geo_service.coords_to_linestring(route.coords)
    buffer_polygon = geo_service.create_buffer(linestring, buffer_km * 1000)

    wikidata_svc = wikidata_service.WikidataService()
    if not wikidata_svc.is_loaded() or wikidata_svc.get_loaded_backend() != backend:
        log.info(f"Bathing spots not yet loaded for backend '{backend}', fetching...")
        await wikidata_svc.load_bathing_spots(backend)

    all_spots = wikidata_svc.get_bathing_spots()

    spots_in_buffer = geo_service.filter_points_in_polygon(all_spots, buffer_polygon)

    bathing_features: list[GeoJSONFeature] = []
    for spot in spots_in_buffer:
        spot = cast(BathingSpot, spot)
        bathing_features.append(GeoJSONFeature(
            geometry=GeoJSONPoint(type="Point", coordinates=[spot.lon, spot.lat]),
            properties={
                "qid": spot.qid,
                "image_url": spot.image_url,
            },
        ))

    route_feature = geo_service.linestring_to_geojson(linestring)
    buffer_feature = geo_service.polygon_to_geojson(buffer_polygon)

    return AnalyzeResponse(
        bathing_spots=GeoJSONFeatureCollection(features=bathing_features),
        route=route_feature,
        buffer=buffer_feature,
    )
