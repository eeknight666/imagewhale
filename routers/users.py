from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import secrets
import aiosqlite
from database import get_db, get_project_or_404, check_project_access
from auth import require_admin, get_password_hash

router = APIRouter(prefix="/api/projects/{project_uuid}/users", tags=["用户管理"])


class UserCreate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    plain_password: Optional[str] = None
    created_at: str


class PasswordChange(BaseModel):
    new_password: str


@router.get("", response_model=List[UserResponse])
async def list_users(
    project_uuid: str,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)

    async with db.execute(
        "SELECT id, username, plain_password, created_at FROM user WHERE project_id = ? ORDER BY created_at DESC",
        (project["id"],)
    ) as cursor:
        users = await cursor.fetchall()

    return [dict(u) for u in users]


@router.post("", response_model=UserResponse)
async def create_user(
    project_uuid: str,
    request: UserCreate,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)

    username = request.username or f"user_{secrets.token_hex(4)}"
    password = request.password or secrets.token_hex(8)

    password_hash = get_password_hash(password)

    try:
        await db.execute(
            "INSERT INTO user (project_id, username, password_hash, plain_password) VALUES (?, ?, ?, ?)",
            (project["id"], username, password_hash, password)
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="用户名已存在")

    async with db.execute(
        "SELECT id, username, plain_password, created_at FROM user WHERE project_id = ? AND username = ?",
        (project["id"], username)
    ) as cursor:
        user = await cursor.fetchone()

    return dict(user)


@router.put("/{user_id}/password")
async def change_password(
    project_uuid: str,
    user_id: int,
    request: PasswordChange,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)

    async with db.execute(
        "SELECT id FROM user WHERE id = ? AND project_id = ?",
        (user_id, project["id"])
    ) as cursor:
        user = await cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    password_hash = get_password_hash(request.new_password)
    await db.execute(
        "UPDATE user SET password_hash = ?, plain_password = ? WHERE id = ?",
        (password_hash, request.new_password, user_id)
    )
    await db.commit()

    return {"message": "密码修改成功"}


@router.delete("/{user_id}")
async def delete_user(
    project_uuid: str,
    user_id: int,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)

    async with db.execute(
        "SELECT id FROM user WHERE id = ? AND project_id = ?",
        (user_id, project["id"])
    ) as cursor:
        user = await cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.execute("DELETE FROM user WHERE id = ?", (user_id,))
    await db.commit()

    return {"message": "删除成功"}
