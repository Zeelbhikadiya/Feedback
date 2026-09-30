from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.audit import write_audit
from app.core.security import authenticate_user, create_access_token, get_current_user, hash_password
from app.database import get_db
from app.models import User
from app.schemas import SSOConfigOut, TokenWithUser, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenWithUser)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    write_audit(db, actor_id=user.id, action="login", entity_type="user", entity_id=user.id)
    db.commit()
    return TokenWithUser(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.get("/sso/config", response_model=SSOConfigOut)
def sso_config():
    settings = get_settings()
    enabled = bool(settings.oidc_client_id and settings.oidc_discovery_url)
    return SSOConfigOut(
        enabled=enabled,
        discovery_url=settings.oidc_discovery_url or None,
        client_id=settings.oidc_client_id or None,
    )


@router.post("/sso/dev-login", response_model=TokenWithUser)
def sso_dev_login(email: str, db: Session = Depends(get_db)):
    """
    Development SSO stub: when OIDC is not fully configured,
    allows login-by-email for an existing active user to demonstrate SSO flow wiring.
    In production, replace with real OIDC callback exchange.
    """
    settings = get_settings()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found for SSO")
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "sso": True})
    write_audit(
        db,
        actor_id=user.id,
        action="sso_login",
        entity_type="user",
        entity_id=user.id,
        detail=f"oidc_configured={bool(settings.oidc_client_id)}",
    )
    db.commit()
    return TokenWithUser(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=UserOut)
def register_bootstrap(payload: UserCreate, db: Session = Depends(get_db)):
    """Only allowed when no users exist (first admin bootstrap)."""
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="Registration closed; ask an admin")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        department_id=payload.department_id,
        employee_code=payload.employee_code,
        is_leader=payload.is_leader,
        locale=payload.locale,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
