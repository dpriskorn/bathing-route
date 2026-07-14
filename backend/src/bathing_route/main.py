import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from bathing_route.cache import init_cache
from bathing_route.wikidata_cache import cleanup_expired_cache, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_cache()
    await init_db()
    await cleanup_expired_cache()
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    app = FastAPI(
        title="Find bathing sites along a GPX route",
        description="Find EU bathing spots along a GPX route",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from bathing_route.api import router as api_router
    from bathing_route.routers.wikidata import router as wikidata_router
    from bathing_route.routers.commons import router as commons_router
    app.include_router(api_router)
    app.include_router(wikidata_router)
    app.include_router(commons_router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
