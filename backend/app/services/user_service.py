"""Kullanıcı profili ve rol yönetimi iş kuralları."""

import logging

from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate

logger = logging.getLogger("kahvecell.users")


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def update_profile(self, user: User, data: UserUpdate) -> User:
        changes = data.model_dump(exclude_unset=True)
        if "full_name" in changes and changes["full_name"] is None:
            raise AppException(status.HTTP_400_BAD_REQUEST, "INVALID_NAME", "Ad soyad boş bırakılamaz.")
        for field, value in changes.items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self, offset: int, limit: int, role: UserRole | None) -> tuple[list[User], int]:
        return self.users.list(offset, limit, role)

    def change_role(self, actor: User, user_id: str, role: UserRole) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise AppException(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Kullanıcı bulunamadı.")
        if user.id == actor.id and role != UserRole.ADMIN:
            raise AppException(
                status.HTTP_400_BAD_REQUEST, "CANNOT_DEMOTE_SELF", "Kendi admin yetkinizi kaldıramazsınız."
            )
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        logger.info("role_changed user_id=%s role=%s by=%s", user.id, role.value, actor.id)
        return user
