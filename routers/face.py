from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from typing import List
import aiosqlite
from auth import require_admin, get_current_user
from database import get_db, get_project_or_404, check_project_access
from services.face_service import (
    register_face, list_registered_faces,
    delete_registered_face, batch_search_faces,
    search_faces_in_project_images
)

router = APIRouter(prefix="/api/face", tags=["人脸识别"])

ALLOWED_FACE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FACE_FILE_SIZE = 50 * 1024 * 1024


@router.post("/register")
async def register_face_api(
    name: str,
    files: List[UploadFile] = File(...),
    admin: dict = Depends(require_admin)
):
    if not name.strip():
        raise HTTPException(status_code=400, detail="姓名不能为空")

    if not files:
        raise HTTPException(status_code=400, detail="请上传照片")

    image_contents = []
    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if f".{ext}" not in ALLOWED_FACE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"{file.filename} 格式不支持，仅支持 JPG/PNG")

        content = await file.read()
        if len(content) > MAX_FACE_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"{file.filename} 文件过大")

        image_contents.append(content)

    try:
        result = register_face(name.strip(), image_contents)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="人脸注册失败")


@router.get("/list")
async def list_faces_api(admin: dict = Depends(require_admin)):
    faces = list_registered_faces()
    return {"count": len(faces), "names": faces}


@router.delete("/delete/{name}")
async def delete_face_api(name: str, admin: dict = Depends(require_admin)):
    if delete_registered_face(name):
        return {"message": f"已删除 {name}"}
    raise HTTPException(status_code=404, detail="未找到该人脸")


@router.post("/search")
async def search_faces_api(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    if not files:
        raise HTTPException(status_code=400, detail="请上传图片")

    image_list = []
    for file in files:
        if not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if f".{ext}" not in ALLOWED_FACE_EXTENSIONS:
            continue

        content = await file.read()
        if len(content) > MAX_FACE_FILE_SIZE:
            continue

        image_list.append({
            "filename": file.filename,
            "content": content
        })

    if not image_list:
        raise HTTPException(status_code=400, detail="无有效图片")

    try:
        results = batch_search_faces(image_list)
        matched = [r for r in results if r.get("matched")]
        return {
            "total": len(results),
            "matched_count": len(matched),
            "results": results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="人脸检索失败")


@router.get("/search-in-project/{project_uuid}")
async def search_faces_in_project(
    project_uuid: str,
    name: str = Query(..., description="要检索的人名"),
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    if not name.strip():
        raise HTTPException(status_code=400, detail="请输入人名")

    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    async with db.execute(
        "SELECT id, filename, thumbnail_path FROM image WHERE project_id = ?",
        (project["id"],)
    ) as cursor:
        images = await cursor.fetchall()

    if not images:
        return {"total": 0, "matched_count": 0, "results": []}

    image_paths = [(img["id"], img["filename"], img["thumbnail_path"]) for img in images]

    try:
        results = search_faces_in_project_images(image_paths, name.strip())
        return {
            "total": len(images),
            "matched_count": len(results),
            "results": results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="人脸检索失败")
