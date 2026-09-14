from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wine_journal.core.config import Settings
from wine_journal.core.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    application = FastAPI(title="Wine Journal API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    application.include_router(health_router, prefix="/api/v1")
    return application


app = create_app()
