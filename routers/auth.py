from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import aiosqlite
from database import get_db
from auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class UserLoginRequest(BaseModel):
    project_uuid: str
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_type: str
    username: str
    project_uuid: str = None


@router.post("/admin/login", response_model=LoginResponse)
async def admin_login(request: AdminLoginRequest, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM admin WHERE username = ?", (request.username,)) as cursor:
        admin = await cursor.fetchone()

    if not admin or not verify_password(request.password, admin["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    token = create_access_token({"sub": str(admin["id"]), "type": "admin"})
    return LoginResponse(token=token, user_type="admin", username=admin["username"])


@router.post("/user/login", response_model=LoginResponse)
async def user_login(request: UserLoginRequest, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM project WHERE uuid = ?", (request.project_uuid,)) as cursor:
        project = await cursor.fetchone()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    async with db.execute(
        "SELECT * FROM user WHERE project_id = ? AND username = ?",
        (project["id"], request.username)
    ) as cursor:
        user = await cursor.fetchone()

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    token = create_access_token({"sub": str(user["id"]), "type": "user"})
    return LoginResponse(token=token, user_type="user", username=user["username"], project_uuid=request.project_uuid)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
