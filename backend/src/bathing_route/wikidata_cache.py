import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path


log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "wikidata.db"
CACHE_TTL_DAYS = 7
COMMONS_CACHE_TTL_DAYS = 7


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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS commons_cache (
                filename TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                thumburl TEXT,
                fetched_at TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_commons_cache_fetched_at ON commons_cache(fetched_at)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wikidata_details_cache (
                qid TEXT PRIMARY KEY,
                p18_image TEXT,
                sitelinks_json TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_wikidata_details_fetched_at ON wikidata_details_cache(fetched_at)
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


async def clear_all_cache() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor1 = await db.execute("DELETE FROM label_cache")
        cursor2 = await db.execute("DELETE FROM commons_cache")
        await db.commit()
        return cursor1.rowcount + cursor2.rowcount


async def get_cached_commons_image(filename: str) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=COMMONS_CACHE_TTL_DAYS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT url, thumburl FROM commons_cache WHERE filename = ? AND fetched_at > ?",
            (filename, cutoff_str),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"url": row[0], "thumburl": row[1]}
    return None


async def set_cached_commons_image(filename: str, url: str, thumburl: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO commons_cache (filename, url, thumburl, fetched_at) VALUES (?, ?, ?, ?)",
            (filename, url, thumburl, now),
        )
        await db.commit()


async def clear_commons_cache() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM commons_cache")
        await db.commit()
        return cursor.rowcount


async def get_cached_wikidata_details(qid: str) -> tuple[str | None, list[dict[str, str]]] | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
    cutoff_str = cutoff.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT p18_image, sitelinks_json FROM wikidata_details_cache WHERE qid = ? AND fetched_at > ?",
            (qid, cutoff_str),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                import json
                p18_image: str | None = row[0]
                sitelinks = json.loads(row[1]) if row[1] else []
                return p18_image, sitelinks
    return None


async def set_cached_wikidata_details(
    qid: str,
    p18_image: str | None,
    sitelinks: list[dict[str, str]],
) -> None:
    import json
    now = datetime.now(timezone.utc).isoformat()
    sitelinks_json = json.dumps(sitelinks)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO wikidata_details_cache (qid, p18_image, sitelinks_json, fetched_at) VALUES (?, ?, ?, ?)",
            (qid, p18_image, sitelinks_json, now),
        )
        await db.commit()
