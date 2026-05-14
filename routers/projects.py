from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
import aiosqlite
from database import get_db, get_project_or_404
from auth import require_admin

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


class ProjectCreate(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: int
    uuid: str
    name: str
    storage_used: int
    storage_limit: int
    user_count: int = 0
    image_count: int = 0
    created_at: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    storage_limit: Optional[int] = None


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM user WHERE project_id = p.id) as user_count,
               (SELECT COUNT(*) FROM image WHERE project_id = p.id) as image_count
        FROM project p
        ORDER BY p.created_at DESC
    """) as cursor:
        projects = await cursor.fetchall()

    return [dict(p) for p in projects]


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project_uuid = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO project (uuid, name) VALUES (?, ?)",
        (project_uuid, request.name)
    )
    await db.commit()

    async with db.execute(
        "SELECT *, 0 as user_count, 0 as image_count FROM project WHERE uuid = ?",
        (project_uuid,)
    ) as cursor:
        project = await cursor.fetchone()

    return dict(project)


@router.get("/{project_uuid}")
async def get_project(
    project_uuid: str,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)

    async with db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM user WHERE project_id = p.id) as user_count,
               (SELECT COUNT(*) FROM image WHERE project_id = p.id) as image_count
        FROM project p WHERE p.uuid = ?
    """, (project_uuid,)) as cursor:
        result = await cursor.fetchone()

    return dict(result)


@router.put("/{project_uuid}")
async def update_project(
    project_uuid: str,
    request: ProjectUpdate,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    await get_project_or_404(project_uuid, db)

    updates = []
    params = []
    if request.name is not None:
        updates.append("name = ?")
        params.append(request.name)
    if request.storage_limit is not None:
        updates.append("storage_limit = ?")
        params.append(request.storage_limit)

    if updates:
        params.append(project_uuid)
        await db.execute(
            f"UPDATE project SET {', '.join(updates)} WHERE uuid = ?",
            params
        )
        await db.commit()

    return {"message": "更新成功"}


@router.delete("/{project_uuid}")
async def delete_project(
    project_uuid: str,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    await get_project_or_404(project_uuid, db)

    await db.execute("DELETE FROM project WHERE uuid = ?", (project_uuid,))
    await db.commit()

    return {"message": "删除成功"}
