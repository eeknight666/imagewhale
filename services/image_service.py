import os
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
from config import UPLOAD_DIR, THUMBNAIL_DIR, THUMBNAIL_SIZE

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(THUMBNAIL_DIR).mkdir(parents=True, exist_ok=True)


def _safe_path(base_dir: str, filename: str) -> str:
    base = Path(base_dir).resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("非法文件路径")
    return str(target)


def save_image(content: bytes, filename: str, mime_type: str) -> dict:
    ext = os.path.splitext(filename)[1].lower()
    new_filename = f"{uuid.uuid4().hex}{ext}"

    file_path = os.path.join(UPLOAD_DIR, new_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    width, height = None, None
    thumbnail_name = None

    try:
        img = Image.open(BytesIO(content))
        width, height = img.size

        thumbnail_name = f"thumb_{new_filename}"
        thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_name)

        img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        img.save(thumbnail_path, "JPEG", quality=85)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return {
        "filename": new_filename,
        "width": width,
        "height": height,
        "thumbnail": thumbnail_name
    }


def delete_image_file(filename: str, thumbnail_name: str = None):
    file_path = _safe_path(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    if thumbnail_name:
        thumb_path = _safe_path(THUMBNAIL_DIR, thumbnail_name)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)


def get_image_path(filename: str) -> str:
    return _safe_path(UPLOAD_DIR, filename)


def get_thumbnail_path(filename: str) -> str:
    return _safe_path(THUMBNAIL_DIR, filename)
