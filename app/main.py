import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.exceptions import InvalidRequest, InvalidTransition, NotFound, NotPermitted
from app.routers import api_router, router, static_files, templates

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.seed import seed

    # First boot on Render often races the free Postgres instance.
    seed(reset=False)
    yield


app = FastAPI(
    middleware=[
        Middleware(SessionMiddleware, secret_key=get_settings().secret_key)
    ],
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(api_router)
app.mount("/static", static_files, name="static")


@app.middleware("http")
async def recover_uninitialized_db(request: Request, call_next):
    """If a request hits a missing schema, create tables once and retry."""
    from app.database import recover_if_uninitialized

    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 — catch then re-raise if not DB init
        if not recover_if_uninitialized(exc):
            raise
        logger.info("Retrying %s after database init", request.url.path)
        try:
            return await call_next(request)
        except Exception:
            # Schema exists now but the prior response may still need a refresh.
            if request.method.upper() == "GET":
                return RedirectResponse(url=str(request.url), status_code=303)
            raise


@app.get("/health")
async def health():
    return {
        "ok": True,
        "status": "ok",
        "scenario": "student-accommodation",
        "version": "0.2.0",
    }


ERROR_STATUS = {
    InvalidRequest: status.HTTP_400_BAD_REQUEST,
    NotPermitted: status.HTTP_403_FORBIDDEN,
    NotFound: status.HTTP_404_NOT_FOUND,
    InvalidTransition: status.HTTP_409_CONFLICT,
}


async def service_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=ERROR_STATUS[type(exc)], content={"detail": str(exc)}
    )


for error_class in ERROR_STATUS:
    app.add_exception_handler(error_class, service_error_handler)


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_redirect_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return templates.TemplateResponse(
        request=request,
        name="401.html",
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=get_settings().app_host,
        port=get_settings().app_port,
        reload=get_settings().env.lower() != "production",
    )
