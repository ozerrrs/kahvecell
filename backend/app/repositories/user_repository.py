from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_phone(self, phone_number: str) -> User | None:
        return self.db.scalar(select(User).where(User.phone_number == phone_number))

    def create(
        self,
        phone_number: str,
        full_name: str | None = None,
        email: str | None = None,
        role: UserRole = UserRole.CUSTOMER,
    ) -> User:
        user = User(phone_number=phone_number, full_name=full_name, email=email, role=role)
        self.db.add(user)
        self.db.flush()
        return user

    def list(self, offset: int, limit: int, role: UserRole | None = None) -> tuple[list[User], int]:
        query = select(User)
        if role:
            query = query.where(User.role == role)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
        return list(items), total
