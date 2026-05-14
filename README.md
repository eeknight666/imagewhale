# 🐳 图灵鲸

> 一个支持多项目、多用户的图片共享图床系统，带人脸识别检索功能。

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-3-brightgreen?logo=vuedotjs&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-lightgrey?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 功能特性

### 👤 用户角色

| 角色 | 说明 |
|------|------|
| 🛡️ **管理员** | 创建项目、管理用户、上传/删除任意图片、人脸注册与检索 |
| 👥 **普通用户** | 在绑定项目内上传、浏览、删除自己的图片，项目内所有图片共享可见 |

### 🖼️ 图片管理

- 📤 **批量上传** — 支持拖拽上传，单张最大 200MB
- 📥 **批量下载** — 选中多张打包 ZIP 下载原图
- 🔍 **缩略图** — 上传时自动生成 300×300 缩略图
- 🗑️ **删除管理** — 管理员可删除所有图片，普通用户仅删除自己的
- 📊 **分页浏览** — 支持 10/20/50 每页显示切换
- 🔃 **时间排序** — 正序/倒序切换
- 👤 **上传者筛选** — 按上传者过滤图片

### 🧠 人脸识别

- 📝 **人脸注册** — 支持多张照片注册，取特征向量平均值提高精度
- 🔎 **项目内检索** — 点击已注册人脸头像，在项目图片中自动匹配
- 🏷️ **结果显示** — 匹配图片高亮显示识别出的人名

### 📱 响应式设计

- 🖥️ **桌面端** (≥1024px) — 侧边栏常驻
- 📒 **平板端** (768px-1023px) — 侧边栏可折叠
- 📱 **手机端** (<768px) — 汉堡菜单

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI + aiosqlite |
| 前端 | Vue 3 (CDN，无需构建工具) |
| 数据库 | SQLite |
| 图片处理 | Pillow |
| 人脸识别 | face_recognition (dlib) |
| 认证 | JWT (python-jose + bcrypt) |

---

## 📁 项目结构

```
imagehub/
├── main.py                  # 🚀 应用入口
├── config.py                # ⚙️ 配置文件
├── database.py              # 🗄️ 数据库初始化
├── auth.py                  # 🔐 认证逻辑
├── routers/
│   ├── auth.py              # 🔑 认证路由
│   ├── projects.py          # 📁 项目路由
│   ├── users.py             # 👥 用户路由
│   ├── images.py            # 🖼️ 图片路由
│   └── face.py              # 🧠 人脸识别路由
├── services/
│   ├── image_service.py     # 🖼️ 图片处理服务
│   └── face_service.py      # 🧠 人脸识别服务
├── static/
│   ├── css/style.css        # 🎨 全局样式
│   ├── js/app.js            # 💻 Vue 应用
│   └── index.html           # 📄 主页面
├── uploads/                 # 📤 图片上传目录（自动创建）
├── thumbnails/              # 🖼️ 缩略图目录（自动创建）
├── faces_db/                # 🧠 人脸特征数据库（自动创建）
├── data/
│   └── imagehub.db          # 🗄️ SQLite 数据库（自动创建）
├── .env                     # 🔧 环境变量配置（从 .env.example 复制）
├── .gitignore
└── requirements.txt         # 📦 Python 依赖
```

---

## 🚀 快速开始

### 📋 环境要求

- Python 3.9+
- pip

### 💻 Windows 安装

```bash
# 克隆项目
git clone https://github.com/eeknight666/imagewhale.git
cd imagewhale

# 安装依赖
pip install -r requirements.txt

# 首次运行（控制台会显示管理员密码）
python main.py
```

### 🐧 Linux 安装

```bash
# 克隆项目
git clone https://github.com/eeknight666/imagewhale.git
cd imagewhale

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装系统依赖（face_recognition 需要 dlib）
sudo apt-get install -y build-essential cmake libopenblas-dev liblapack-dev
sudo apt-get install -y libx11-dev libgtk-3-dev

# 安装 Python 依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p uploads thumbnails data faces_db

# 首次运行
python main.py
```

### 🔧 环境变量配置 (.env)

```env
# 管理员账号
ADMIN_USERNAME=admin

# 服务器配置
HOST=0.0.0.0
PORT=5189

# 上传限制
MAX_FILE_SIZE=209715200       # 200MB
PROJECT_STORAGE_LIMIT=1073741824  # 1GB

# JWT密钥（首次运行自动生成，无需手动配置）
JWT_SECRET=
JWT_EXPIRE_HOURS=24

# 缩略图尺寸
THUMBNAIL_SIZE=300
```

### 🌐 访问地址

```
电脑端: http://localhost:5189
手机端: http://你的IP:5189
```

---

## 📡 API 接口

### 🔑 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/admin/login` | 管理员登录 |
| `POST` | `/api/auth/user/login` | 普通用户登录 |
| `GET` | `/api/auth/me` | 获取当前用户信息 |

### 📁 项目管理 (管理员)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects` | 获取所有项目 |
| `POST` | `/api/projects` | 创建项目 |
| `GET` | `/api/projects/{uuid}` | 获取项目详情 |
| `DELETE` | `/api/projects/{uuid}` | 删除项目 |

### 👥 用户管理 (管理员)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects/{uuid}/users` | 获取项目用户列表 |
| `POST` | `/api/projects/{uuid}/users` | 添加用户 |
| `PUT` | `/api/projects/{uuid}/users/{id}/password` | 修改密码 |
| `DELETE` | `/api/projects/{uuid}/users/{id}` | 删除用户 |

### 🖼️ 图片管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `GET` | `/api/projects/{uuid}/images` | 所有用户 | 获取图片列表(分页) |
| `POST` | `/api/projects/{uuid}/images` | 所有用户 | 上传图片(批量) |
| `DELETE` | `/api/projects/{uuid}/images/{id}` | 管理员/上传者 | 删除图片 |
| `GET` | `/api/projects/{uuid}/images/{id}/download` | 所有用户 | 下载单张 |
| `POST` | `/api/projects/{uuid}/images/batch-download` | 所有用户 | 批量下载(ZIP) |

### 🧠 人脸识别

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `POST` | `/api/face/register?name=xxx` | 管理员 | 人脸注册(支持多图) |
| `GET` | `/api/face/list` | 管理员 | 已注册人脸列表 |
| `DELETE` | `/api/face/delete/{name}` | 管理员 | 删除注册人脸 |
| `GET` | `/api/face/search-in-project/{uuid}?name=xxx` | 所有用户 | 项目内人脸检索 |

---

## 🔒 安全措施

- 🔐 **密码加密** — bcrypt 哈希存储
- 🎫 **JWT 认证** — Token 过期时间 24 小时
- 🛡️ **文件校验** — MIME 类型 + magic bytes 双重验证
- 📁 **路径安全** — Path.resolve() 防止路径遍历攻击
- 🌐 **CORS** — 跨域请求配置
- ⏱️ **登录限制** — 5 次失败锁定 15 分钟
- 💾 **存储限制** — 防止磁盘被填满

---

## 🐧 Linux 部署

### Systemd 服务

```ini
# /etc/systemd/system/imagehub.service
[Unit]
Description=图灵鲸
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/imagehub
Environment=PATH=/path/to/imagehub/venv/bin
ExecStart=/path/to/imagehub/venv/bin/python main.py
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/path/to/imagehub/uploads /path/to/imagehub/thumbnails /path/to/imagehub/data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable imagehub
sudo systemctl start imagehub
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:5189;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
```

### 目录权限

```bash
mkdir -p uploads thumbnails data faces_db
chmod 755 uploads thumbnails data faces_db
# 如果使用 www-data 用户运行
sudo chown -R www-data:www-data uploads thumbnails data faces_db
```

---

## 🎨 界面预览

色彩方案采用莫兰迪/马卡龙色系：

| 用途 | 颜色 |
|------|------|
| 主色调 | `#A8B5A2` 鼠尾草绿 |
| 辅助色 | `#B5C4B1` 薄荷绿 |
| 强调色 | `#F5E6CA` 奶油黄 |
| 背景色 | `#F8F6F2` 暖白色 |

---

## 📦 依赖

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pillow==10.2.0
python-dotenv==1.0.0
aiofiles==23.2.1
aiosqlite==0.19.0
bcrypt==4.1.2
face_recognition==1.3.0
numpy>=1.23.0
```

---

## ✅ 平台兼容性

- ✅ Windows 10/11
- ✅ Linux (Ubuntu / Debian / CentOS / RHEL)
- ✅ macOS

---

## 📄 License

MIT License
