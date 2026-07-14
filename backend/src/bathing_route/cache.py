import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bathing_route.models import BathingSpot


log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "sites.db"
CACHE_TTL_HOURS = 24


async def init_cache() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bathing_spot_cache (
                backend TEXT NOT NULL,
                qid TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                image_url TEXT,
                has_eu_bath INTEGER NOT NULL DEFAULT 0,
                commons_category TEXT,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (backend, qid)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bathing_cache_fetched_at ON bathing_spot_cache(fetched_at)
        """)
        try:
            await db.execute("""
                ALTER TABLE bathing_spot_cache ADD COLUMN has_eu_bath INTEGER NOT NULL DEFAULT 0
            """)
        except Exception:
            pass
        try:
            await db.execute("""
                ALTER TABLE bathing_spot_cache ADD COLUMN commons_category TEXT
            """)
        except Exception:
            pass
        await db.commit()
    log.info(f"Sites database initialized at {DB_PATH}")


async def get_cached_spots(backend: str) -> tuple[list[BathingSpot], str] | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT qid, lat, lon, image_url, has_eu_bath, commons_category, fetched_at FROM bathing_spot_cache WHERE backend = ? AND fetched_at > ?",
            (backend, cutoff_str),
        ) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return None
            first = tuple(rows[0])
            fetched_at = first[6]
            spots = [
                BathingSpot(
                    qid=row[0],
                    lat=row[1],
                    lon=row[2],
                    image_url=row[3],
                    has_eu_bath=bool(row[4]),
                    commons_category=row[5],
                )
                for row in rows
            ]
            return spots, fetched_at


async def set_cached_spots(backend: str, spots: list[BathingSpot]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for spot in spots:
            await db.execute(
                "INSERT OR REPLACE INTO bathing_spot_cache (backend, qid, lat, lon, image_url, has_eu_bath, commons_category, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (backend, spot.qid, spot.lat, spot.lon, spot.image_url, spot.has_eu_bath, spot.commons_category, now),
            )
        await db.commit()
    log.info(f"Cached {len(spots)} spots for backend '{backend}'")


async def clear_cache(backend: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if backend:
            cursor = await db.execute("DELETE FROM bathing_spot_cache WHERE backend = ?", (backend,))
        else:
            cursor = await db.execute("DELETE FROM bathing_spot_cache")
        await db.commit()
        deleted = cursor.rowcount
    log.info(f"Cleared {deleted} cache entries for backend={backend}")
    return deleted


async def get_cache_info(backend: str) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), MAX(fetched_at) FROM bathing_spot_cache WHERE backend = ?",
            (backend,),
        ) as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0
            fetched_at = row[1] if row and row[1] else None

        fresh = False
        if fetched_at:
            fetched_dt = datetime.fromisoformat(fetched_at)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
            fresh = fetched_dt > cutoff

    return {
        "backend": backend,
        "count": count,
        "fetched_at": fetched_at,
        "fresh": fresh,
        "ttl_hours": CACHE_TTL_HOURS,
    }
