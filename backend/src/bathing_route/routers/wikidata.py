import logging
from typing import Any

import httpx
from fastapi import APIRouter

from bathing_route.label_cache import get_cached_label, set_cached_label


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wikidata", tags=["wikidata"])

USER_AGENT = "bathing-route/0.1 (Python; https://github.com/anomalyco/bathing-route)"
COMMONS_FILE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"


async def _fetch_label(qid: str, lang: str) -> str | None:
    url = f"https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/{qid}/labels/{lang}"
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, str):
                        label: str | None = data
                    else:
                        label = data.get(qid, {}).get("value")  # pragma: no cover
                except Exception:  # pragma: no cover
                    text = response.text.strip()
                    label = text if text and text != "null" else None
                return label
        except Exception as e:  # pragma: no cover
            log.warning(f"Failed to fetch label for {qid}: {e}")
    return None  # pragma: no cover
    return None


async def _fetch_entity_data(qid: str) -> dict[str, Any]:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


@router.get("/{qid}/details")
async def get_wikidata_details(qid: str, lang: str = "en") -> dict[str, Any]:
    cached_label = await get_cached_label(qid, lang)
    label: str
    if cached_label:
        label = cached_label
    else:
        fetched_label = await _fetch_label(qid, lang)
        if fetched_label is None and lang != "en":
            fetched_label = await _fetch_label(qid, "en")
        if fetched_label is None:
            label = qid
        else:
            label = fetched_label
        await set_cached_label(qid, lang, label)

    entity_data = await _fetch_entity_data(qid)
    entities = entity_data.get("entities", {})
    entity = entities.get(qid, {})

    claims = entity.get("claims", {})

    image_url: str | None = None
    p18_list = claims.get("P18", [])
    for p18 in p18_list:
        mainsnak = p18.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value")
        if value:
            filename = value.replace(" ", "_")
            image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
            break

    sitelinks = entity.get("sitelinks", {})
    wikipedia_urls: list[dict[str, str]] = []
    for key, data in sitelinks.items():
        if key.endswith("wiki"):
            lang_code = key.replace("wiki", "")
            title = data.get("title", "").replace(" ", "_")
            url = f"https://{lang_code}.wikipedia.org/wiki/{title}"
            wikipedia_urls.append({
                "lang": lang_code,
                "title": title,
                "url": url,
            })

    return {
        "qid": qid,
        "label": label,
        "image_url": image_url,
        "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
        "wikipedia_urls": wikipedia_urls,
    }
