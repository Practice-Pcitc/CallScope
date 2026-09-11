from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
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
from app.core.logging import logger, request_id_context
from app.schemas.common import ErrorBody, ErrorEnvelope
from app.services.ai_analysis_service import recover_ai_analyses
from app.services.scan_service import recover_interrupted_scans


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """启动时尽早验证数据库连接，避免服务带病运行。"""
    check_database()
    recover_interrupted_scans()
    recover_ai_analyses()
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
        allow_credentials=False,
        expose_headers=["X-Request-ID"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = f"req_{uuid4().hex}"
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.error("request_failed", extra={"error_type": type(exc).__name__})
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "服务内部错误，请凭请求编号排查",
                            "details": None,
                            "requestId": request_id,
                        }
                    },
                )
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request_completed",
                extra={
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000),
                },
            )
            return response
        finally:
            request_id_context.reset(token)

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
                details={
                    "errors": [{"type": item["type"], "loc": item["loc"]} for item in exc.errors()]
                },
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(status_code=422, content=payload.model_dump(by_alias=True))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
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
