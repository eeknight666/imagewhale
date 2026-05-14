import aiosqlite
from pathlib import Path
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def get_project_or_404(project_uuid: str, db: aiosqlite.Connection):
    async with db.execute("SELECT * FROM project WHERE uuid = ?", (project_uuid,)) as cursor:
        project = await cursor.fetchone()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


async def check_project_access(project_id: int, current_user: dict):
    if current_user["type"] == "user" and current_user["project_id"] != project_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权访问此项目")


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                plain_password VARCHAR(128),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid VARCHAR(36) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                storage_used BIGINT DEFAULT 0,
                storage_limit BIGINT DEFAULT 1073741824,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                plain_password VARCHAR(128),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
                UNIQUE(project_id, username)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS image (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER,
                uploader_type VARCHAR(10) NOT NULL DEFAULT 'user',
                uploader_name VARCHAR(50) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                file_size BIGINT NOT NULL,
                mime_type VARCHAR(50) NOT NULL,
                width INTEGER,
                height INTEGER,
                thumbnail_path VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_image_project ON image(project_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_image_user ON image(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_project ON user(project_id)")

        await db.commit()
