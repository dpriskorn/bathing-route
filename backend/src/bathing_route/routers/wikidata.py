import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter

from bathing_route.wikidata_cache import (
    get_cached_label,
    get_cached_wikidata_details,
    set_cached_label,
    set_cached_wikidata_details,
)


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wikidata", tags=["wikidata"])

USER_AGENT = "bathing-route/0.1 (Python; https://github.com/anomalyco/bathing-route)"


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
                        label = data.get(qid, {}).get("value")
                except Exception:
                    text = response.text.strip()
                    label = text if text and text != "null" else None
                return label
        except Exception as e:
            log.warning(f"Failed to fetch label for {qid}: {e}")
    return None
    return None


async def _fetch_p18(qid: str) -> str | None:
    url = f"https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/{qid}/statements?property=P18"
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                statements = data.get("P18", data.get("statements", {}).get("P18", []))
                for statement in statements:
                    if "value" in statement and isinstance(statement.get("value"), dict) and "content" in statement["value"]:
                        return statement["value"]["content"]
                    mainsnak = statement.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value")
                    if value:
                        return value
        except Exception as e:
            log.warning(f"Failed to fetch P18 for {qid}: {e}")
    return None


async def _fetch_sitelinks(qid: str) -> list[dict[str, str]]:
    url = f"https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/{qid}/sitelinks"
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                sitelinks: list[dict[str, str]] = []
                for site_key, link_data in data.items():
                    if not isinstance(link_data, dict):
                        continue
                    if not site_key.endswith("wiki") or site_key == "commonswiki":
                        continue
                    title = link_data.get("title", "").replace(" ", "_")
                    wiki_url = link_data.get("url", "")
                    if not wiki_url:
                        lang_code = site_key.replace("wiki", "")
                        wiki_url = f"https://{lang_code}.wikipedia.org/wiki/{title}"
                    else:
                        lang_code = site_key.replace("wiki", "")
                    sitelinks.append({
                        "lang": lang_code,
                        "title": title,
                        "url": wiki_url,
                    })
                return sitelinks
        except Exception as e:
            log.warning(f"Failed to fetch sitelinks for {qid}: {e}")
    return []


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

    cached_details = await get_cached_wikidata_details(qid)
    if cached_details:
        p18_image, wikipedia_urls = cached_details
    else:
        p18_image = await _fetch_p18(qid)
        wikipedia_urls = await _fetch_sitelinks(qid)
        await set_cached_wikidata_details(qid, p18_image, wikipedia_urls)

    image_url: str | None = None
    if p18_image:
        filename = p18_image.replace(" ", "_")
        image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"

    return {
        "qid": qid,
        "label": label,
        "image_url": image_url,
        "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
        "wikipedia_urls": wikipedia_urls,
    }
