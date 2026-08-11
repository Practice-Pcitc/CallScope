from fastapi import APIRouter

from app.api.routes import (
    ai_analyses,
    endpoints,
    graphs,
    health,
    projects,
    scans,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(scans.router, tags=["scans"])
api_router.include_router(endpoints.router, tags=["endpoints"])
api_router.include_router(graphs.router, tags=["graphs"])
api_router.include_router(ai_analyses.router, tags=["ai-analysis"])
