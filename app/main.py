from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(title="Reselling Opportunity Engine", version="0.1.0", lifespan=lifespan)
    app.include_router(router)

    return app


app = create_app()
