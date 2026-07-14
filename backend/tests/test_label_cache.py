import pytest
from pathlib import Path
from unittest.mock import patch
import aiosqlite
import asyncio


@pytest.mark.asyncio
async def test_init_db_creates_commons_cache(tmp_path):
    test_db = tmp_path / "labels.db"

    with patch('bathing_route.label_cache.DB_PATH', test_db):
        from bathing_route.label_cache import init_db
        await init_db()

        async with aiosqlite.connect(test_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS commons_cache (
                    filename TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    thumburl TEXT,
                    fetched_at TIMESTAMP NOT NULL
                )
            """)
            await db.commit()

        async with aiosqlite.connect(test_db) as db:
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commons_cache'") as cursor:
                row = await cursor.fetchone()
                assert row is not None


@pytest.mark.asyncio
async def test_clear_all_cache(tmp_path):
    test_db = tmp_path / "labels.db"

    with patch('bathing_route.label_cache.DB_PATH', test_db):
        async with aiosqlite.connect(test_db) as db:
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
                CREATE TABLE IF NOT EXISTS commons_cache (
                    filename TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    thumburl TEXT,
                    fetched_at TIMESTAMP NOT NULL
                )
            """)
            await db.execute(
                "INSERT INTO label_cache (qid, lang, label, fetched_at) VALUES (?, ?, ?, ?)",
                ("Q1", "en", "test", "2024-01-01T00:00:00")
            )
            await db.commit()

        from bathing_route.label_cache import clear_all_cache
        deleted = await clear_all_cache()
        assert deleted == 1

        async with aiosqlite.connect(test_db) as db:
            async with db.execute("SELECT COUNT(*) FROM label_cache") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 0
            async with db.execute("SELECT COUNT(*) FROM commons_cache") as cursor:
                row = await cursor.fetchone()
                assert row[0] == 0


@pytest.mark.asyncio
async def test_get_set_cached_commons_image(tmp_path):
    test_db = tmp_path / "labels.db"

    with patch('bathing_route.label_cache.DB_PATH', test_db):
        async with aiosqlite.connect(test_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS commons_cache (
                    filename TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    thumburl TEXT,
                    fetched_at TIMESTAMP NOT NULL
                )
            """)
            await db.commit()

        from bathing_route.label_cache import get_cached_commons_image, set_cached_commons_image

        result = await get_cached_commons_image("Test.jpg")
        assert result is None

        await set_cached_commons_image("Test.jpg", "https://example.com/T.jpg", "https://example.com/T_thumb.jpg")
        result = await get_cached_commons_image("Test.jpg")
        assert result is not None
        assert result["url"] == "https://example.com/T.jpg"
        assert result["thumburl"] == "https://example.com/T_thumb.jpg"


@pytest.mark.asyncio
async def test_get_set_cached_label(tmp_path):
    test_db = tmp_path / "labels.db"

    with patch('bathing_route.label_cache.DB_PATH', test_db):
        async with aiosqlite.connect(test_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS label_cache (
                    qid TEXT NOT NULL,
                    lang TEXT NOT NULL,
                    label TEXT NOT NULL,
                    fetched_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (qid, lang)
                )
            """)
            await db.commit()

        from bathing_route.label_cache import get_cached_label, set_cached_label

        result = await get_cached_label("Q1", "en")
        assert result is None

        await set_cached_label("Q1", "en", "Test Label")
        result = await get_cached_label("Q1", "en")
        assert result == "Test Label"


@pytest.mark.asyncio
async def test_cleanup_expired_cache(tmp_path):
    test_db = tmp_path / "labels.db"

    with patch('bathing_route.label_cache.DB_PATH', test_db):
        async with aiosqlite.connect(test_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS label_cache (
                    qid TEXT NOT NULL,
                    lang TEXT NOT NULL,
                    label TEXT NOT NULL,
                    fetched_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (qid, lang)
                )
            """)
            await db.execute(
                "INSERT INTO label_cache (qid, lang, label, fetched_at) VALUES (?, ?, ?, ?)",
                ("Q1", "en", "fresh", "2099-01-01T00:00:00")
            )
            await db.execute(
                "INSERT INTO label_cache (qid, lang, label, fetched_at) VALUES (?, ?, ?, ?)",
                ("Q2", "en", "expired", "2020-01-01T00:00:00")
            )
            await db.commit()

        from bathing_route.label_cache import cleanup_expired_cache

        deleted = await cleanup_expired_cache()
        assert deleted == 1

        from bathing_route.label_cache import get_cached_label
        result = await get_cached_label("Q1", "en")
        assert result == "fresh"
        result = await get_cached_label("Q2", "en")
        assert result is None
