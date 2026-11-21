from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import ApiResponse, ok
from app.schemas.user import RoleUpdate, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_roles(UserRole.ADMIN)


class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


@router.get("/users", response_model=ApiResponse[UserPage])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    """Tüm kullanıcıları listeler (sadece ADMIN)."""
    items, total = UserService(db).list_users((page - 1) * page_size, page_size, role)
    return ok(UserPage(items=[UserOut.model_validate(u) for u in items], total=total, page=page, page_size=page_size))


@router.patch("/users/{user_id}/role", response_model=ApiResponse[UserOut])
def change_role(
    user_id: str,
    body: RoleUpdate,
    actor: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    """Kullanıcının rolünü değiştirir (örn. bir müşteriyi dükkân sahibi yapmak). Sadece ADMIN."""
    return ok(UserOut.model_validate(UserService(db).change_role(actor, user_id, body.role)))
