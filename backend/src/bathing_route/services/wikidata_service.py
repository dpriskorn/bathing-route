import logging
import re

import requests

from bathing_route.cache import get_cached_spots, set_cached_spots
from bathing_route.models import BathingSpot


USER_AGENT = "bathing-route/0.1 (Python; https://github.com/anomalyco/bathing-route)"
log = logging.getLogger(__name__)

SPARQL_PREFIXES = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""

EU_BATH_QUERY = """
SELECT DISTINCT ?item ?coord ?image WHERE {
  ?item wdt:P9616 ?euBathId .
  ?item wdt:P625 ?coord .
  OPTIONAL { ?item wdt:P18 ?image }
}
"""

WD_ALL_QUERY = """
SELECT DISTINCT ?item ?coord ?image WHERE {
  ?item wdt:P31/wdt:P279* wd:Q567998 .
  ?item wdt:P625 ?coord .
  OPTIONAL { ?item wdt:P18 ?image }
}
"""

ENHANCED_QUERY = """
SELECT DISTINCT ?item ?coord ?image ?commonsCategory ?euBathId WHERE {
  ?item wdt:P31/wdt:P279* wd:Q567998 .
  ?item wdt:P625 ?coord .
  OPTIONAL { ?item wdt:P18 ?image }
  OPTIONAL { ?item wdt:P373 ?commonsCategory }
  OPTIONAL { ?item wdt:P9616 ?euBathId }
}
"""


class WikidataService:
    _instance: "WikidataService | None" = None
    _bathing_spots: list[BathingSpot] = []
    _loaded: bool = False
    _loaded_backend: str | None = None

    def __new__(cls) -> "WikidataService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_loaded(self) -> bool:
        return self._loaded

    def get_loaded_backend(self) -> str | None:
        return self._loaded_backend

    async def load_bathing_spots(self, backend: str = "wdqs") -> None:
        if self._loaded and self._loaded_backend == backend:
            return

        cached = await get_cached_spots(backend)
        if cached is not None:
            self._bathing_spots, fetched_at = cached
            self._loaded = True
            self._loaded_backend = backend
            log.info(f"Loaded {len(self._bathing_spots)} EU bathing spots from cache (fetched {fetched_at})")
            return

        full_query = SPARQL_PREFIXES + EU_BATH_QUERY

        if backend == "qlever":
            endpoint = "https://qlever.cs.uni-freiburg.de/api/wikidata"
            params = {"query": full_query, "action": "json_export"}
            log.info("Fetching EU bathing spots from QLever...")
        else:
            endpoint = "https://query.wikidata.org/sparql"
            params = {"query": full_query, "format": "json"}
            log.info("Fetching EU bathing spots from WDQS...")

        response = requests.get(endpoint, params=params, headers={"User-Agent": USER_AGENT}, timeout=120.0)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {}).get("bindings", [])
        log.debug(f"SPARQL returned {len(results)} raw results")

        self._bathing_spots = []
        for r in results:
            qid = self._extract_qid(r.get("item", {}).get("value", ""))
            if not qid:
                continue

            coord_str = r.get("coord", {}).get("value", "")
            coord = self._parse_coord(coord_str)
            if not coord:
                continue

            image_value = r.get("image", {}).get("value")
            image_url = self._parse_image_url(image_value) if image_value else None

            self._bathing_spots.append(BathingSpot(
                qid=qid,
                lat=coord["lat"],
                lon=coord["lon"],
                image_url=image_url,
            ))

        await set_cached_spots(backend, self._bathing_spots)

        self._loaded = True
        self._loaded_backend = backend
        log.info(f"Loaded {len(self._bathing_spots)} EU bathing spots from {backend}")

    async def load_bathing_spots_all(self, backend: str = "wdqs-all") -> None:
        if self._loaded and self._loaded_backend == backend:
            return

        cached = await get_cached_spots(backend)
        if cached is not None:
            self._bathing_spots, fetched_at = cached
            self._loaded = True
            self._loaded_backend = backend
            log.info(f"Loaded {len(self._bathing_spots)} bathing spots from cache (fetched {fetched_at})")
            return

        full_query = SPARQL_PREFIXES + ENHANCED_QUERY

        if backend == "qlever":
            endpoint = "https://qlever.cs.uni-freiburg.de/api/wikidata"
            params = {"query": full_query, "action": "json_export"}
            log.info("Fetching bathing spots from QLever...")
        else:
            endpoint = "https://query.wikidata.org/sparql"
            params = {"query": full_query, "format": "json"}
            log.info("Fetching bathing spots from WDQS...")

        response = requests.get(endpoint, params=params, headers={"User-Agent": USER_AGENT}, timeout=120.0)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {}).get("bindings", [])
        log.debug(f"SPARQL returned {len(results)} raw results")

        self._bathing_spots = []
        for r in results:
            qid = self._extract_qid(r.get("item", {}).get("value", ""))
            if not qid:
                continue

            coord_str = r.get("coord", {}).get("value", "")
            coord = self._parse_coord(coord_str)
            if not coord:
                continue

            image_value = r.get("image", {}).get("value")
            commons_category = r.get("commonsCategory", {}).get("value")
            eu_bath_id = r.get("euBathId", {}).get("value")

            self._bathing_spots.append(BathingSpot(
                qid=qid,
                lat=coord["lat"],
                lon=coord["lon"],
                image_url=image_value,
                commons_category=commons_category,
                has_eu_bath=eu_bath_id is not None,
            ))

        await set_cached_spots(backend, self._bathing_spots)

        self._loaded = True
        self._loaded_backend = backend
        log.info(f"Loaded {len(self._bathing_spots)} bathing spots from {backend}")

    def get_bathing_spots(self) -> list[BathingSpot]:
        if not self._loaded:
            raise RuntimeError("Bathing spots not loaded. Call load_bathing_spots() first.")
        return self._bathing_spots

    def _extract_qid(self, uri: str) -> str | None:
        if not uri:
            return None
        match = re.search(r"(Q\d+)", uri)
        return match.group(1) if match else None

    def _parse_coord(self, coord_str: str) -> dict[str, float] | None:
        match = re.match(r"Point\(([^ ]+) ([^ ]+)\)", coord_str)
        if match:
            return {"lon": float(match.group(1)), "lat": float(match.group(2))}
        return None

    def _parse_image_url(self, filename: str) -> str:
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
