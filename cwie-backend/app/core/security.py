"""
Security - JWT, Password, Auth Dependencies
"""
from datetime import datetime, timedelta
from typing import Optional, List

from jose import JWTError, jwt
import bcrypt as _bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def decode_token(token: str) -> dict:
    """ถอดรหัส token — ถ้าไม่ถูกต้องจะ raise HTTPException"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Token ไม่ถูกต้องหรือหมดอายุ")
    return payload

def create_registration_token(line_user_id: str) -> str:
    return create_access_token(
        data={"line_user_id": line_user_id, "type": "registration"},
        expires_delta=timedelta(hours=1),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    if not credentials:
        raise HTTPException(401, "กรุณาเข้าสู่ระบบ")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Token ไม่ถูกต้องหรือหมดอายุ")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token ไม่ถูกต้อง")
    user = db.query(User).filter(User.id == int(user_id), User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    return user


def require_roles(allowed_roles: List[str]):
    """Dependency: จำกัดสิทธิ์ตาม role"""
    async def check_role(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db),
    ):
        from app.models.user import User
        if not credentials:
            raise HTTPException(401, "กรุณาเข้าสู่ระบบ")
        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(401, "Token ไม่ถูกต้องหรือหมดอายุ")
        user = db.query(User).filter(
            User.id == int(payload["sub"]),
            User.deleted_at.is_(None)
        ).first()
        if not user:
            raise HTTPException(404, "ไม่พบผู้ใช้งาน")
        if user.sys_role.value not in allowed_roles:
            raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึง")
        return user
    return check_role
