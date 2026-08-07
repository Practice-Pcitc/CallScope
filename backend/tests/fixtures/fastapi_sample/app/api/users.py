from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    name: str


class CreateUserRequest(BaseModel):
    name: str


def get_user_service() -> UserService:
    return UserService()


def audit_request() -> None:
    return None


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户详情",
)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),  # noqa: B008
    keyword: str | None = None,
) -> UserResponse:
    """从服务层获取一个用户。"""
    user = service.get_user(user_id)
    return UserResponse(id=user.id, name=keyword or user.name)


@router.post(
    "/",
    tags=["write"],
    dependencies=[Depends(audit_request)],
)
async def create_user(
    payload: CreateUserRequest,
    verbose: bool = Query(False),
) -> UserResponse:
    user = UserService().create_user(payload.name)
    return UserResponse(id=user.id, name=user.name)
