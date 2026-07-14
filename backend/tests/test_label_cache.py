import pytest
from pathlib import Path
from unittest.mock import patch
import aiosqlite
import asyncio


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
