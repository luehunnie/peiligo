# 培黎智寻 Peiligo

面向校园的统一信息与资源检索平台，基于 Django + Wagtail 构建。

## 项目简介

校园信息长期面临分散、难检索、容易过期、来源不统一的问题。Peiligo
将全校的通知、活动、资料、软件工具与办事指南统一收纳到一个平台，
提供统一的关键词搜索与结构化筛选，并按发布生命周期自动管理内容的
上线与过期。

- **学生端（V1）**：无需登录，直接浏览与检索全部已发布内容。
- **学校部门**：通过网站后台管理各自内容，权限按部门隔离，
  部门之间互不可见、互不可改。

## 内容板块

| 板块 | 路径 | 说明 |
| --- | --- | --- |
| 校园纪事 | `/chronicle/` | 校园新闻与纪事文章 |
| 校园活动 | `/events/` | 活动通知（含活动时间与进行状态） |
| 学习资料 | `/materials/` | 学习资料（文件附件或外部链接） |
| 软件与工具 | `/software/` | 常用软件与在线工具入口 |
| 校园指南 | `/guide/` | 办事流程与校园生活指南 |

各板块均提供历史归档视图（`/<板块>/archive/`），过期与归档内容
不再出现在默认列表、导航与站点地图中。

## 核心能力

- **五类内容模型**：通知 / 文章 / 学习资料 / 软件与工具 / 校园指南，
  与五大板块一一对应；网站后台全面中文化。
- **部门级权限**：部门账号只能管理本部门的内容子树；部门之间互不可见；
  删除等高危操作仅限总管理员。
- **内容生命周期**：草稿 / 预览 / 修订历史；立即发布 / 定时发布 /
  到期 / 手动下线全状态管理，含常驻定时发布调度器（`publish_scheduler`）。
- **中文搜索**：关键词搜索 + 结构化筛选（板块、部门、分类、标签），
  采用 icontains 语义（ADR-0006 E1 选型，显式后端选择）。
- **首页运营内容**：紧急提示（站点级起止窗口，可空）、首页轮播（最多 5 条，
  站内内容或经确认跳转页的外部链接）、五大板块入口、校园快讯（最多 3 条，
  由推荐位 → 最新通知 → 即将开始的活动合并去重生成，已结束内容不进入）。
- **上传安全**：文档附件限白名单格式（doc/docx/pdf/ppt/pptx/xls/xlsx）、
  单文件 20 MiB 上限、声明类型与文件内容一致性校验、文件名清洗；
  图片限 jpg/jpeg/png/webp。
- **外链安全**：站外链接统一经确认跳转页，URL scheme 收窄为
  http/https。
- **SEO 基础**：`sitemap.xml`、`robots.txt`、canonical / noindex
  策略（搜索、归档、查询态页面不收录）、meta description。
- **登录治理**：密码最低 12 位、连续输错锁定（10 次锁 15 分钟）、
  24 小时会话、管理员重置密码后首次登录强制改密。
- **治理审计**：用户/组管理全部 DB 级变更留痕，后台
  `/admin/gov-audit/` 可查。
- **结构化日志**：全部服务日志单行 JSON 输出，带统一事件码，
  敏感信息脱敏。
- **健康检查**：`/healthz/`（存活）与 `/readyz/`（DB 就绪）端点。
- **备份与恢复**：`backup_run` / `backup_prune` / `backup_restore`
  三命令（12 小时一备、30 天保留、独立副本、隔离恢复，永不默认
  覆盖现库），附校验和与 manifest。
- **监控信号**：`ops_report` 输出数据库、磁盘、备份新鲜度、调度
  心跳、登录异常等信号，任一 CRIT 非零退出，可直接接告警。
- **CI**：GitHub Actions 单工作流质量门（system check + migration
  一致性 + ruff + pytest）。

## 技术栈

| 组件 | 版本 |
| --- | --- |
| Python | 3.13 |
| Django | 5.2 LTS（锁定 5.2.17） |
| Wagtail | 7.4 LTS（锁定 7.4.3，2026-09 安全升级） |
| 数据库 | PostgreSQL 18 |
| 前端 | Django Templates 服务端渲染（SSR），零客户端 JS 框架 |
| 应用服务器 | Gunicorn |
| 部署 | Docker Compose + Caddy（自动 HTTPS） |
| 测试 / Lint | pytest + Ruff |
| CI | GitHub Actions |

> 架构历史：项目早期曾采用 Vue + FastAPI 方案，后经架构裁决
> （ADR-0001～0003）改为 Django + Wagtail 服务端渲染整体重建，
> 不迁移旧数据。早期仓库仅作历史档案保留。

## 当前项目状态

- **主要开发（V1 纯开发阶段）：完成**（FINAL-1 / FINAL-2 已合并）。
- **本地 Production-like Docker 运行时验证：PASS**（2026-09-02）。
  四容器（db / web / scheduler / caddy）构建、启动、健康检查、页面
  发布、定时发布、备份与隔离恢复全部实跑通过；过程中发现的 5 个
  运行时问题已修复并合并回 main（PR#14）。证据见
  [docs/reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md](docs/reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md)。
- **发布安全审查（Phase 9 Release Security Gate）：PASS**（2026-09-12）。
  生产配置安全加固合并入 main：公开页面 CSP、HSTS、Secure Cookie、
  登录防爆破（django-axes）、Wagtail 7.4.2 → 7.4.3 安全升级。
- **服务器 Production 部署：尚未执行**。正式域名 / DNS / TLS、生产
  密钥、备份独立存储、性能与无障碍验证、生产告警接线等属于部署
  阶段工作，见下方「部署」。

## 快速开始（本地开发）

前置：本机运行 PostgreSQL（本地/测试统一 PostgreSQL，SQLite 不是
基线；测试库由 pytest-django 自建自清）。

```bash
git clone https://github.com/luehunnie/peiligo.git
cd peiligo

python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .

cp .env.example .env    # 按本机实际填写开发值（.env 不入库）
set -a; source .env; set +a   # Django 不自动加载 .env，需导出到 shell

python manage.py migrate
python manage.py bootstrap_sections   # 初始化五板块结构页（幂等）
python manage.py init_permissions     # 初始化部门权限组
python manage.py createsuperuser
python manage.py runserver
```

访问 <http://127.0.0.1:8000/> 为前台，<http://127.0.0.1:8000/admin/>
为管理后台。`.env.example` 中的 `DATABASE_URL` / `SECRET_KEY` /
`TEST_DATABASE_URL` 等均为哑值样例，请替换为本机真实开发值。

更多本地运行方式（含 Docker Compose 本地实跑）见
[docs/guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md](docs/guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md)。

## 部署

生产架构已完成工程化打包（Docker Compose + PostgreSQL + Gunicorn +
Caddy 自动 HTTPS + 调度器 + 备份 + 监控信号），且已在本地以
Production-like 方式完整实跑验证；**正式服务器部署尚未执行**。

- 部署步骤、环境变量、备份策略、监控接线与恢复演练流程见
  [docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md)。
- 部署前后的运维注意项与阶段清单见
  [docs/guides/SERVER_DEPLOYMENT_GUIDE.md](docs/guides/SERVER_DEPLOYMENT_GUIDE.md)。

部署阶段仍待完成的事项（均不属于仓库内代码缺口）：正式域名 /
DNS / TLS 配置、生产密钥与 `.env` 准备、`SECONDARY_BACKUP_DIR`
绑定独立存储、性能验证（含 100 并发）、无障碍（WCAG / axe）验证、
生产告警接线、恢复演练（季度，RTO ≤ 4h）。

## 文档

面向非技术读者：

- [docs/guides/CONTENT_PUBLISHING_GUIDE.md](docs/guides/CONTENT_PUBLISHING_GUIDE.md) —
  内容发布指南（业务流程：发什么、发到哪、怎么发）
- [docs/guides/DEPARTMENT_EDITOR_GUIDE.md](docs/guides/DEPARTMENT_EDITOR_GUIDE.md) —
  部门编辑操作手册（零基础：登录、建内容、发布、修改、下线）

面向技术读者（索引见 [docs/guides/README.md](docs/guides/README.md)）：

- [docs/guides/PROJECT_OVERVIEW.md](docs/guides/PROJECT_OVERVIEW.md) — 项目全景
- [docs/guides/TECHNICAL_ARCHITECTURE_GUIDE.md](docs/guides/TECHNICAL_ARCHITECTURE_GUIDE.md) — 技术架构
- [docs/guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md](docs/guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md) — 本地运行与验证
- [docs/guides/SERVER_DEPLOYMENT_GUIDE.md](docs/guides/SERVER_DEPLOYMENT_GUIDE.md) — 服务器部署指南
- [docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md) —
  生产运行手册（首次部署、备份、监控、恢复演练）
- [docs/adr/](docs/adr/README.md) — 架构决策记录（ADR-0001～0007）

历史审查与签收记录（冻结，不再更新）：`docs/G2_FREEZE_EVIDENCE.md`、
`docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md`、`docs/reviews/`。

## 测试

```bash
python manage.py check
python manage.py makemigrations --check --dry-run   # 迁移无漂移
pytest -q
ruff check .
ruff format --check .
```

当前基线实测：pytest **604 passed + 269 subtests**（2026-09-02 于
main @ 0069953 实测；至 2992b1a 测试与业务代码无变更，仅合并
Docker 修复与文档），ruff 通过。其后的首页升级与 Phase 9 发布安全
批次（2026-09-10～12）继续扩充了测试（现为 54 个测试文件）并完成
Wagtail 7.4.3 安全升级——当前全量结果以 CI 最新运行为准。CI 侧
同一套检查由 GitHub Actions 在每次 push / PR 时执行。

## 项目状态声明

| 项 | 状态 |
| --- | --- |
| 核心 V1 实现 | 完成（PURE_DEVELOPMENT_COMPLETE） |
| 架构与治理 | G2 Human Signoff PASS（2026-09-01） |
| 本地 Production-like Docker 验证 | PASS（2026-09-02） |
| 运行时修复 | 已合并 main（PR#14 @ 2992b1a） |
| 服务器 Production 部署 | **尚未执行** |
| READY_FOR_HANDOFF | **YES** |
| READY_FOR_STAGING | YES |
| READY_FOR_PRODUCTION | **NO**（待正式部署与部署阶段验证） |

## 关联项目

Peiligo、Peilige、Peilike 是三个相互独立的同级项目，各自维护独立仓库，
互不隶属：

- Peilige: https://github.com/luehunnie/peilige.git
- Peilike: https://github.com/luehunnie/peilike.git
