from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.database import check_database
from app.core.exceptions import AppException
from app.schemas.common import ErrorBody, ErrorEnvelope
from app.services.scan_service import recover_interrupted_scans


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """启动时尽早验证数据库连接，避免服务带病运行。"""
    check_database()
    recover_interrupted_scans()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="面向 FastAPI 项目的接口调用拓扑静态分析平台。",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        payload = ErrorEnvelope(
            error=ErrorBody(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        payload = ErrorEnvelope(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="请求参数校验失败",
                details={"errors": exc.errors()},
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(status_code=422, content=payload.model_dump(by_alias=True))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        payload = ErrorEnvelope(
            error=ErrorBody(
                code="HTTP_ERROR",
                message=str(exc.detail),
                details=None,
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
