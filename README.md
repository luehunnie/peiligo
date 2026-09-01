# 培黎智寻 Peiligo

面向校园的统一信息与资源检索平台，基于 Django + Wagtail 构建。

## 项目简介

校园信息长期面临分散、难检索、容易过期、来源不统一的问题。Peiligo
将全校的通知、活动、资料、软件工具与办事指南统一收纳到一个平台，
提供统一的关键词搜索与结构化筛选，并按发布生命周期自动管理内容的
上线与过期。

- **学生端（V1）**：无需登录，直接浏览与检索全部已发布内容。
- **学校部门**：通过 Wagtail Admin 管理各自内容，权限按部门隔离，
  部门之间互不可见、互不可改。

## 内容板块

| 板块 | 路径 | 说明 |
| --- | --- | --- |
| 校园纪事 | `/chronicle/` | 校园新闻与纪事文章 |
| 校园活动 | `/events/` | 活动通知（含活动时间与进行状态） |
| 学习资料 | `/materials/` | 可下载的学习资料文件 |
| 软件与工具 | `/software/` | 常用软件与在线工具入口 |
| 校园指南 | `/guide/` | 办事流程与校园生活指南 |

各板块均提供历史归档视图（`/<板块>/archive/`），过期与归档内容
不再出现在默认列表、导航与站点地图中。

## 核心能力

- **Wagtail CMS**：五类正式内容模型，覆盖上述五大板块；后台中文化。
- **部门级权限**：部门权限容器树（ADR-0004），部门账号只能管理
  本部门子树；删除等高危操作仅限总管理员。
- **内容生命周期**：草稿 / 预览 / 修订历史；发布 / 定时发布 /
  到期 / 归档全状态管理，含后台定时发布调度器（`publish_scheduler`）。
- **中文搜索**：关键词搜索 + 结构化筛选（板块、部门、分类等），
  生产环境采用 icontains 语义（ADR-0006 E1 选型，显式后端选择）。
- **首页运营内容**：紧急提示、推荐位（最多 3 条、30 天默认有效期）、
  最新通知、近期活动四个运营数据区。
- **上传安全**：20 MiB 大小上限、扩展名白名单、MIME + 文件魔数
  一致性校验、文件名清洗。
- **外链安全**：站外链接统一经确认跳转页，URL scheme 收窄为
  http/https。
- **SEO 基础**：`sitemap.xml`、`robots.txt`、canonical / noindex
  策略（搜索、归档、查询态页面不收录）、meta description。
- **登录治理**：密码最低 12 位、django-axes 登录限速与锁定、
  24 小时会话、后台重置/新建密码后强制改密工作流。
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
| Wagtail | 7.4 LTS（锁定 7.4.2） |
| 数据库 | PostgreSQL 18 |
| 前端 | Django Templates 服务端渲染（SSR），零客户端 JS 框架 |
| 应用服务器 | Gunicorn |
| 部署 | Docker Compose + Caddy（自动 HTTPS） |
| 测试 / Lint | pytest + Ruff |
| CI | GitHub Actions |

> 架构历史：项目早期曾采用 Vue + FastAPI 方案，后经架构裁决
> （ADR-0001～0003）改为 Django + Wagtail 服务端渲染整体重建，
> 不迁移旧数据。早期仓库仅作历史档案保留。

## 架构

```text
Browser
  │ HTTPS
  ▼
Caddy ──── 静态文件 / 媒体文件直出
  ▼
Gunicorn
  ▼
Django + Wagtail（服务端渲染）
  ▼
PostgreSQL
```

生产编排（`deploy/docker-compose.yml`）另含：

- **持久卷**：PostgreSQL 数据、media、static、备份各独立卷；
- **scheduler**：常驻定时发布调度服务；
- **备份与监控**：compose 内不含 cron——备份（`backup_run`，独立副本
  目录可配置）与巡检快照（`ops_report`，非零退出接告警）由宿主机
  cron（或等效定时器）触发，条目样例见 `docs/PRODUCTION_RUNBOOK.md`。

本地开发不需要 Docker，直接使用 Django development server。

## 本地开发

前置：本机运行 PostgreSQL（本地/测试统一 PostgreSQL，SQLite 不是
基线；测试库由 pytest-django 自建自清）。

```bash
git clone https://github.com/luehunyo/peiligo.git
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

## 测试

```bash
python manage.py check
python manage.py makemigrations --check --dry-run   # 迁移无漂移
pytest -q
ruff check .
ruff format --check .
```

本地 FINAL-2 validation 结果：pytest 574 passed + 266 subtests，
ruff 通过。CI 侧同一套检查由 GitHub Actions 在每次 push / PR 时执行。

## 生产部署

生产架构已完成工程化打包（Docker Compose + PostgreSQL + Gunicorn +
Caddy 自动 HTTPS + 调度器 + 备份 + 监控信号），**尚未执行实际部署**。

部署步骤、环境变量、备份策略、监控接线与恢复演练流程见
[docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md)。

## 项目状态

| 项 | 状态 |
| --- | --- |
| 核心 V1 实现 | 完成 |
| 架构与治理 | G2 Human Signoff PASS（2026-09-01） |
| 纯开发阶段 | 完成（FINAL-1 / FINAL-2 已合并） |
| 生产部署 | 尚未执行 |

尚待执行的验证与运维事项（均不属于仓库内代码缺口）：

- 容器运行时构建与启动验证
- GitHub Actions CI 实跑记录（见仓库 Actions 页）
- 生产环境部署（含 TLS / DNS）
- 性能验证（含 100 并发）
- 无障碍（WCAG / axe）验证
- 恢复演练（季度，RTO ≤ 4h）

## 已知限制

以下为当前真实状态（非缺陷）：

- Docker 镜像构建与容器启动尚未实跑（`docker compose config`
  静态校验已通过）；
- GitHub Actions CI 已在最终实现 PR 中完成首次真实运行并通过；
- 生产 TLS 证书与 DNS 未配置（Caddy 首次启动自动申请证书）；
- `SECONDARY_BACKUP_DIR`（备份独立副本）需在部署阶段绑定到
  独立存储，未配置时监控信号会显式 WARN；
- 性能与无障碍最终验证未执行。

## 文档

- [docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md) —
  生产运行手册（首次部署、备份、监控、恢复演练）
- [docs/G2_FREEZE_EVIDENCE.md](docs/G2_FREEZE_EVIDENCE.md) —
  架构冻结一致性与 Human 签收记录
- [docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md](docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md) —
  收尾前实现缺口审计（F-01～F-13 清单来源）
- [docs/adr/](docs/adr/README.md) — 架构决策记录（ADR-0001～0006）
