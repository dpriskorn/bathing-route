import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from bathing_route.cache import init_cache
from bathing_route.label_cache import cleanup_expired_cache, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_cache()
    await init_db()
    await cleanup_expired_cache()
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    app = FastAPI(
        title="Bathing Route API",
        description="Find EU bathing spots along a GPX route",
        version="0.1.0",
        lifespan=lifespan,
    )
    from bathing_route.api import router as api_router
    from bathing_route.routers.wikidata import router as wikidata_router
    app.include_router(api_router)
    app.include_router(wikidata_router)
    return app


app = create_app()
