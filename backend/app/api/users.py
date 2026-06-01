from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.user import MeResponse
from app.services.quota import quota_snapshot


router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snapshot = quota_snapshot(db, current_user.id)
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
        **snapshot,
    )
