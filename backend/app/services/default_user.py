from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.entities import User


def ensure_default_admin(db: Session) -> User:
    settings = get_settings()
    username = settings.default_admin_username
    user = db.query(User).filter(User.username == username).one_or_none()
    password_hash = hash_password(settings.default_admin_password)

    if user is None:
        user = User(
            username=username,
            email=None,
            password_hash=password_hash,
            status="active",
            is_admin=True,
        )
        db.add(user)
    else:
        user.password_hash = password_hash
        user.status = "active"
        user.is_admin = True
    db.commit()
    db.refresh(user)
    return user
