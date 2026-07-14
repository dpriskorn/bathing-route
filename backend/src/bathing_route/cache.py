import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bathing_route.models import BathingSpot


log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "cache.db"
CACHE_TTL_HOURS = 24


async def init_cache() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bathing_spot_cache (
                backend TEXT NOT NULL,
                qid TEXT NOT NULL,
                label TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (backend, qid)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bathing_cache_fetched_at ON bathing_spot_cache(fetched_at)
        """)
        await db.commit()
    log.info(f"Cache database initialized at {DB_PATH}")


async def get_cached_spots(backend: str) -> tuple[list[BathingSpot], str] | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT qid, label, lat, lon, fetched_at FROM bathing_spot_cache WHERE backend = ? AND fetched_at > ?",
            (backend, cutoff_str),
        ) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return None
            first = tuple(rows[0])  # type: ignore[index]
            fetched_at = first[4]
            spots = [
                BathingSpot(qid=row[0], label=row[1], lat=row[2], lon=row[3])
                for row in rows
            ]
            return spots, fetched_at


async def set_cached_spots(backend: str, spots: list[BathingSpot]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for spot in spots:
            await db.execute(
                "INSERT OR REPLACE INTO bathing_spot_cache (backend, qid, label, lat, lon, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
                (backend, spot.qid, spot.label, spot.lat, spot.lon, now),
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
