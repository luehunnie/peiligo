# 培黎智寻

“培黎智寻”M0 仓库初始化与最小运行骨架。

## 当前范围

- Vue 3 + TypeScript + Vite 最小前端
- FastAPI 最小后端
- `GET /api/health` 健康检查
- pytest 后端测试
- 前端类型检查与后端静态检查

本阶段不包含数据库、登录、后台、搜索、Docker、Caddy、Element Plus 页面或正式部署。

## 环境要求

- Node.js 20.19+ 或 22.12+
- npm
- Python 3.11+

## 依赖结构

依赖安装在项目本地标准位置，不使用目录联接或外部依赖目录：

- Python 虚拟环境：`backend/.venv`
- Node 依赖：`frontend/node_modules`

两者均已被 `.gitignore` 排除，不会进入提交。

## 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

健康检查地址：`http://127.0.0.1:8000/api/health`

## 启动前端

另开终端：

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`

开发服务器会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 验证

后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

前端：

```powershell
cd frontend
npm run type-check
npm run build
```

## 目录结构

```text
peiligo/
├─ backend/       FastAPI 应用与测试
├─ frontend/      Vue 3 前端
├─ docs/          阶段开发汇报
├─ .editorconfig
├─ .gitignore
└─ README.md
```
