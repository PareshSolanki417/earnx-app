import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.utils.seed import seed_database
from app.routes import (
    auth_router,
    user_router,
    wallet_router,
    ads_router,
    tasks_router,
    referral_router,
    withdrawals_router,
    notifications_router,
    admin_router,
    bot_webhook_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("earnx.main")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds essential security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Telegram WebApp runs in an iframe within Telegram desktop/web,
        # so frame-ancestors must allow Telegram domains
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://web.telegram.org https://oauth.telegram.org;"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing %s in %s mode...", settings.APP_NAME, settings.APP_ENV)
    init_db()
    with SessionLocal() as db:
        seed_database(db)
    logger.info("%s ready to serve traffic.", settings.APP_NAME)
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="High-performance real reward earning platform for Telegram Mini App, Android APK, and Web.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_DEBUG else None,
    redoc_url="/api/redoc" if settings.APP_DEBUG else None,
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)


# Global Exception Handler to avoid exposing stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again later."},
    )


# Health check
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(user_router, prefix=settings.API_V1_STR)
app.include_router(wallet_router, prefix=settings.API_V1_STR)
app.include_router(ads_router, prefix=settings.API_V1_STR)
app.include_router(tasks_router, prefix=settings.API_V1_STR)
app.include_router(referral_router, prefix=settings.API_V1_STR)
app.include_router(withdrawals_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(bot_webhook_router, prefix=settings.API_V1_STR)

# Static file serving for Frontend and Admin Portal
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(base_dir, "frontend")
admin_dir = os.path.join(base_dir, "admin")

if os.path.exists(admin_dir):
    app.mount("/admin-portal", StaticFiles(directory=admin_dir, html=True), name="admin")

if os.path.exists(frontend_dir):
    # Mount frontend static assets
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/admin")
    async def serve_admin_index():
        return FileResponse(os.path.join(admin_dir, "index.html"))
