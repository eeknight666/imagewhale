import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import HOST, PORT, ADMIN_USERNAME, JWT_SECRET
from database import init_db
from auth import get_password_hash
from routers import auth, projects, users, images, face


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_admin()
    print_admin_info()
    yield


app = FastAPI(
    title="图灵鲸",
    description="图床共享系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(users.router)
app.include_router(images.router)
app.include_router(face.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


async def init_admin():
    import aiosqlite
    from database import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admin WHERE username = ?", (ADMIN_USERNAME,)) as cursor:
            admin = await cursor.fetchone()

        if admin is None:
            import secrets
            password = secrets.token_hex(16)
            password_hash = get_password_hash(password)

            await db.execute(
                "INSERT INTO admin (username, password_hash, plain_password) VALUES (?, ?, ?)",
                (ADMIN_USERNAME, password_hash, password)
            )
            await db.commit()

            print("\n" + "=" * 50)
            print("首次运行，已创建管理员账号:")
            print(f"账号: {ADMIN_USERNAME}")
            print(f"密码: {password}")
            print("密码已保存到数据库")
            print("=" * 50 + "\n")


def print_admin_info():
    print("\n" + "=" * 50)
    print("图灵鲸 已启动")
    print(f"访问地址: http://localhost:{PORT}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True
    )
