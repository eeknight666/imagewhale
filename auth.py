from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiosqlite
from database import get_db
from config import JWT_SECRET, JWT_EXPIRE_HOURS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: aiosqlite.Connection = Depends(get_db)
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        user_type: str = payload.get("type")
        if not user_id or not user_type:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    if user_type == "admin":
        async with db.execute("SELECT id, username FROM admin WHERE id = ?", (user_id,)) as cursor:
            admin = await cursor.fetchone()
            if admin is None:
                raise credentials_exception
            return {"type": "admin", "id": admin["id"], "username": admin["username"]}
    elif user_type == "user":
        async with db.execute(
            "SELECT u.id, u.username, u.project_id, p.uuid as project_uuid FROM user u JOIN project p ON u.project_id = p.id WHERE u.id = ?",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            if user is None:
                raise credentials_exception
            return {
                "type": "user",
                "id": user["id"],
                "username": user["username"],
                "project_id": user["project_id"],
                "project_uuid": user["project_uuid"]
            }
    else:
        raise credentials_exception


async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["type"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


async def require_user(current_user: dict = Depends(get_current_user)):
    return current_user
