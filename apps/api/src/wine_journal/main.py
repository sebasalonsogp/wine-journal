from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from wine_journal.accounts.routes import router as accounts_router
from wine_journal.core.auth import TokenVerifier
from wine_journal.core.config import Settings
from wine_journal.core.database import database_engine
from wine_journal.core.errors import RequestContextMiddleware, install_error_handlers
from wine_journal.core.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    engine = database_engine(settings.database_url) if settings.database_url else None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    application = FastAPI(title="Wine Journal API", version="0.1.0", lifespan=lifespan)
    application.state.session_factory = (
        sessionmaker(engine, expire_on_commit=False) if engine is not None else None
    )
    application.state.token_verifier = (
        TokenVerifier(settings.auth_issuer) if settings.auth_issuer else None
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(accounts_router, prefix="/api/v1")
    install_error_handlers(application)
    return application


app = create_app()
