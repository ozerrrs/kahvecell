from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.user import UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Kullanıcı Profili"])


@router.get("/me", response_model=ApiResponse[UserOut])
def get_me(user: User = Depends(get_current_user)):
    """Giriş yapmış kullanıcının profili."""
    return ok(UserOut.model_validate(user))


@router.patch("/me", response_model=ApiResponse[UserOut])
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Profil tamamlama / güncelleme: ad soyad, e-posta, kahve tercihleri, alerjenler."""
    return ok(UserOut.model_validate(UserService(db).update_profile(user, body)))
