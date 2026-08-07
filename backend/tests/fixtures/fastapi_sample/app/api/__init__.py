from fastapi import APIRouter

from .users import router as users_router

api_router = APIRouter(prefix="/v1", tags=["root"])
api_router.include_router(
    users_router,
    prefix="/accounts",
    tags=["mounted"],
)

