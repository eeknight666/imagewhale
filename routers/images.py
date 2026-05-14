from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import List
import aiosqlite
import os
import zipfile
import io
from datetime import datetime
from database import get_db, get_project_or_404, check_project_access
from auth import require_user
from services.image_service import save_image, delete_image_file, get_image_path
from config import MAX_FILE_SIZE, ALLOWED_EXTENSIONS, PROJECT_STORAGE_LIMIT, ALLOWED_MIME_TYPES

router = APIRouter(prefix="/api", tags=["图片管理"])


def _validate_file(file: UploadFile, content: bytes) -> str:
    if not file.filename:
        return "文件名为空"
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "不支持的文件格式"
    if len(content) > MAX_FILE_SIZE:
        return f"文件超过{MAX_FILE_SIZE // 1048576}MB限制"
    magic_bytes = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89PNG': 'image/png',
        b'GIF8': 'image/gif',
        b'RIFF': 'image/webp',
        b'BM': 'image/bmp',
    }
    detected = False
    for magic, mime in magic_bytes.items():
        if content[:len(magic)] == magic:
            detected = True
            break
    if not detected:
        return "文件内容与图片格式不匹配"
    return None


@router.get("/projects/{project_uuid}/images")
async def list_images(
    project_uuid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    offset = (page - 1) * page_size

    async with db.execute(
        "SELECT COUNT(*) as total FROM image WHERE project_id = ?", (project["id"],)
    ) as cursor:
        total = (await cursor.fetchone())["total"]

    async with db.execute("""
        SELECT id, project_id, user_id, uploader_type, uploader_name,
               filename, original_name, file_size, mime_type,
               width, height, thumbnail_path, created_at
        FROM image
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (project["id"], page_size, offset)) as cursor:
        images = await cursor.fetchall()

    return {
        "items": [dict(img) for img in images],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/projects/{project_uuid}/images")
async def upload_images(
    project_uuid: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    is_admin = current_user["type"] == "admin"
    user_id = None if is_admin else current_user["id"]
    uploader_type = "admin" if is_admin else "user"
    uploader_name = current_user["username"]

    results = []
    errors = []

    for file in files:
        content = await file.read()

        validation_error = _validate_file(file, content)
        if validation_error:
            errors.append({"filename": file.filename, "error": validation_error})
            continue

        file_size = len(content)

        if project["storage_used"] + file_size > PROJECT_STORAGE_LIMIT:
            errors.append({"filename": file.filename, "error": "项目存储空间不足"})
            continue

        try:
            result = save_image(content=content, filename=file.filename, mime_type=file.content_type)

            await db.execute("""
                INSERT INTO image (project_id, user_id, uploader_type, uploader_name,
                    filename, original_name, file_size, mime_type, width, height, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project["id"], user_id, uploader_type, uploader_name,
                result["filename"], file.filename, file_size, file.content_type,
                result["width"], result["height"], result["thumbnail"]
            ))

            await db.execute(
                "UPDATE project SET storage_used = storage_used + ? WHERE id = ?",
                (file_size, project["id"])
            )

            results.append({
                "filename": result["filename"],
                "original_name": file.filename,
                "size": file_size
            })
        except Exception:
            errors.append({"filename": file.filename, "error": "图片处理失败"})

    await db.commit()

    return {
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.delete("/projects/{project_uuid}/images/{image_id}")
async def delete_image(
    project_uuid: str,
    image_id: int,
    current_user: dict = Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    async with db.execute(
        "SELECT * FROM image WHERE id = ? AND project_id = ?",
        (image_id, project["id"])
    ) as cursor:
        image = await cursor.fetchone()

    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    if current_user["type"] == "user":
        if image["uploader_type"] != "user" or image["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="只能删除自己上传的图片")

    await delete_image_file(image["filename"], image["thumbnail_path"])

    await db.execute(
        "UPDATE project SET storage_used = MAX(0, storage_used - ?) WHERE id = ?",
        (image["file_size"], project["id"])
    )

    await db.execute("DELETE FROM image WHERE id = ?", (image_id,))
    await db.commit()

    return {"message": "删除成功"}


@router.get("/projects/{project_uuid}/images/{image_id}/download")
async def download_image(
    project_uuid: str,
    image_id: int,
    current_user: dict = Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    async with db.execute(
        "SELECT * FROM image WHERE id = ? AND project_id = ?",
        (image_id, project["id"])
    ) as cursor:
        image = await cursor.fetchone()

    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    file_path = get_image_path(image["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=image["original_name"],
        media_type=image["mime_type"]
    )


@router.post("/projects/{project_uuid}/images/batch-download")
async def batch_download_images(
    project_uuid: str,
    image_ids: List[int],
    current_user: dict = Depends(require_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    project = await get_project_or_404(project_uuid, db)
    await check_project_access(project["id"], current_user)

    if not image_ids:
        raise HTTPException(status_code=400, detail="请选择要下载的图片")

    placeholders = ",".join(["?" for _ in image_ids])
    async with db.execute(
        f"SELECT * FROM image WHERE id IN ({placeholders}) AND project_id = ?",
        (*image_ids, project["id"])
    ) as cursor:
        images = await cursor.fetchall()

    if not images:
        raise HTTPException(status_code=404, detail="图片不存在")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        name_count = {}
        for img in images:
            file_path = get_image_path(img["filename"])
            if os.path.exists(file_path):
                original_name = img["original_name"]
                if original_name in name_count:
                    name_count[original_name] += 1
                    name, ext = os.path.splitext(original_name)
                    original_name = f"{name}_{name_count[original_name]}{ext}"
                else:
                    name_count[original_name] = 0
                zip_file.write(file_path, original_name)

    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"images_{timestamp}.zip"

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


@router.get("/images/{filename}")
async def serve_image(filename: str):
    try:
        file_path = get_image_path(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)


@router.get("/thumbnails/{filename}")
async def serve_thumbnail(filename: str):
    from config import THUMBNAIL_DIR
    try:
        from services.image_service import get_thumbnail_path
        file_path = get_thumbnail_path(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)
