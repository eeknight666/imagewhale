import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5189"))

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "209715200"))
PROJECT_STORAGE_LIMIT = int(os.getenv("PROJECT_STORAGE_LIMIT", "1073741824"))

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if "JWT_SECRET=" in content and not content.split("JWT_SECRET=")[1].split("\n")[0].strip():
            content = content.replace("JWT_SECRET=", f"JWT_SECRET={JWT_SECRET}")
            env_path.write_text(content, encoding="utf-8")

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "imagehub.db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
THUMBNAIL_DIR = os.getenv("THUMBNAIL_DIR", str(BASE_DIR / "thumbnails"))
THUMBNAIL_SIZE = int(os.getenv("THUMBNAIL_SIZE", "300"))

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif",
    "image/webp", "image/bmp"
}
