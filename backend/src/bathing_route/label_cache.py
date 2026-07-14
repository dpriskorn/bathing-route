import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path


log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "labels.db"
CACHE_TTL_DAYS = 7


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS label_cache (
                qid TEXT NOT NULL,
                lang TEXT NOT NULL,
                label TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                PRIMARY KEY (qid, lang)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_label_cache_fetched_at ON label_cache(fetched_at)
        """)
        await db.commit()
    log.info(f"Label database initialized at {DB_PATH}")


async def get_cached_label(qid: str, lang: str) -> str | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT label FROM label_cache WHERE qid = ? AND lang = ? AND fetched_at > ?",
            (qid, lang, cutoff_str),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]  # type: ignore[no-any-return]
    return None


async def set_cached_label(qid: str, lang: str, label: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO label_cache (qid, lang, label, fetched_at) VALUES (?, ?, ?, ?)",
            (qid, lang, label, now),
        )
        await db.commit()


async def cleanup_expired_cache() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM label_cache WHERE fetched_at <= ?",
            (cutoff_str,),
        )
        await db.commit()
        deleted = cursor.rowcount
    log.info(f"Cleaned up {deleted} expired label cache entries")
    return deleted
