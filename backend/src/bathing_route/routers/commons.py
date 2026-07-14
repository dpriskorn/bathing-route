import httpx
from fastapi import APIRouter, HTTPException, Query
from urllib.parse import unquote

from bathing_route.label_cache import get_cached_commons_image, set_cached_commons_image


router = APIRouter(prefix="/api", tags=["commons"])

USER_AGENT = "bathing-route/0.1 (Python; https://github.com/anomalyco/bathing-route)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


@router.get("/commons-image")
async def get_commons_image(
    filename: str = Query(..., description="Image filename (raw, without File: prefix)"),
) -> dict:
    decoded = unquote(filename)
    clean_filename = decoded
    if decoded.startswith("File:"):
        clean_filename = decoded[5:]
    elif decoded.startswith("Special:FilePath/"):
        clean_filename = decoded[len("Special:FilePath/"):]

    if not clean_filename:
        raise HTTPException(status_code=400, detail="filename required")

    cached = await get_cached_commons_image(clean_filename)
    if cached:
        return cached

    titles = f"File:{clean_filename}"
    url = f"{COMMONS_API}?action=query&titles={titles}&prop=imageinfo&iiprop=url|thumburl&iiurlwidth=400&format=json"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        data = response.json()

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "imageinfo" in page and page["imageinfo"]:
            info = page["imageinfo"][0]
            result = {
                "url": info["url"],
                "thumburl": info.get("thumburl", info["url"]),
            }
            await set_cached_commons_image(clean_filename, result["url"], result["thumburl"])
            return result

    return {"url": None, "thumburl": None}
