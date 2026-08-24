# peiligo_restart

Peiligo V1 重建的唯一执行仓库。当前基座：M1 工程基座——按 ADR-0003 以官方
`wagtail start` 生成的干净 Wagtail 骨架（ADR-0001 版本组合、ADR-0002 服务端
Django 模板），仓库布局按 `docs/plans/03_DELIVERY_OPERATIONS_PLAN.md` §2；
其上 A1.1 完成 S1 环境依赖补齐（本地/测试统一 PostgreSQL、连接与敏感配置
全环境变量外置、psycopg/gunicorn/pip-audit 钉版）。

## 版本组合（ADR-0001，冻结）

| 组件 | 锁定版本 | 约束区间 |
| --- | --- | --- |
| Python | 3.13（本仓验证于 3.13.11） | 3.13.x |
| Wagtail | 7.4.2（LTS） | `>=7.4.2,<7.5` |
| Django | 5.2.17（LTS） | `>=5.2,<5.3` |
| modelsearch | 1.3.2 | `>=1.3.2,<1.4` |

**首次锁依赖定向复核记录（2026-08-18，官方来源 PyPI JSON API
`https://pypi.org/pypi/<pkg>/json`）**：

- wagtail：最新稳定版 7.4.2；7.4.x 线 = 7.4.1、7.4.2，无晚于 7.4.2 的补丁
  → 锁 `wagtail==7.4.2`（与 ADR-0001 复核结论一致）
- django：最新稳定版 6.1（超约束线不取）；5.2.x 线最新 = 5.2.17（2026-08-04
  安全版）→ 锁 `django==5.2.17`（满足 `>=5.2.17`）
- modelsearch：最新版 1.3.2（2026-08-11 上传）→ 锁 `modelsearch==1.3.2`

**A1.1（S1 环境依赖补齐）同日定向复核补记**：psycopg 最新稳定版 3.3.4
（2026-05-01 上传）→ 锁 `psycopg==3.3.4` + `psycopg-binary==3.3.4`（binary 分发，
免本机编译）；gunicorn 最新稳定版 26.1.0（2026-08-18 上传）→ 锁
`gunicorn==26.1.0`；dev 工具链 pip-audit 最新稳定版 2.10.1（2026-06-10 上传）→
锁 `pip-audit==2.10.1`。三者均当日经 PyPI JSON API 复核。

注意：wagtail 7.4.2 对 django 未设上界，裸 `pip install wagtail==7.4.2` 会解析
到 Django 6.1（违反 ADR-0001 区间、且已被 Wagtail 上游撤回正式支持）——依赖一律
按 `requirements.txt` 钉版安装，勿单独解析。全部依赖经 `pip freeze` 钉死（36 个
运行时包，无浮动版本）。

## 本地启动（A1.1：本地与测试统一 PostgreSQL，SQLite 不再是基线）

前置：本机 PostgreSQL 运行中（验证于 Homebrew PostgreSQL 18.4，socket
`/tmp/.s.PGSQL.5432`，`psql -h /tmp -d postgres` 可连通）。首次需建开发库
（测试库由 pytest-django 自建自清，无需手工创建）：

```bash
psql -h /tmp -d postgres -c "CREATE DATABASE peiligo_restart_dev"
```

环境变量（连接/密钥全部外置，哑值样例见 `.env.example`；`.env` 不入库）：

```bash
cp .env.example .env                        # 按本机实际修改（用户/口令/socket 路径等）
set -a; source .env; set +a                 # Django 不自动加载 .env，需导出到 shell
python3.13 -m venv .venv                    # Python 3.13（本仓验证于 3.13.11）
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -e .                  # 安装 src/peiligo 项目装配包
.venv/bin/python manage.py migrate          # 迁移到 DATABASE_URL 指向的 PG 开发库
.venv/bin/python manage.py bootstrap_sections   # 五板块结构页（幂等，可重复执行）
.venv/bin/python manage.py runserver
```

连接经 socket（免密）时 `DATABASE_URL` 可用形如
`postgres://<用户>@/<库名>?host=/tmp` 的连接串。未设置 `DATABASE_URL` /
`SECRET_KEY`（及 production 的 `ALLOWED_HOSTS`）时 settings 导入即快速失败。

浏览器访问与预期可见内容（已实测）：

- <http://127.0.0.1:8000/> → 200，全站页头（品牌 + 首页/五板块/站内搜索一级导航）
  与页脚（关于 + 反馈邮箱）；首页 h1 **“首页”** + 五板块入口网格（M2.2）
- <http://127.0.0.1:8000/admin/login/> → 200，**“Sign in to Wagtail”** 登录页
  （首次使用先 `manage.py createsuperuser` 创建账号）
- <http://127.0.0.1:8000/search/> → 200，站内搜索页（无参数=表单态；含无参数态
  一律 noindex+canonical，IA §10 #7）；`/search/?query=校园` 可检索已发布页面
- <http://127.0.0.1:8000/sitemap.xml> → 200，仅首页+五板块（容器/query 态排除）
- 任意未知路径（含 `/<板块>/<部门>/` 容器 URL）→ 404 通用页（提供站内搜索与
  五板块入口；`DEBUG=True` 时开发服务器显示 Django 技术 404 页，`DEBUG=False`
  与测试环境渲染本项目 `404.html`）

A2.1（M2.1 结构实现）新增五板块结构页（`bootstrap_sections` 幂等创建，
复用既有首页，零业务内容）：

- `/chronicle/`（校园纪事）、`/events/`（校园活动）、`/materials/`（学习资料）、
  `/software/`（软件与工具）、`/guide/`（校园指南）→ 各 200；M2.2 起板块页含
  面包屑（首页 > 板块名）与“本板块暂无内容”全空态引导（内容页类型 M3 落地）
- 部门容器节点（`/<板块>/<部门>/`）前台一律 404，不入导航/默认列表/sitemap/
  默认搜索（ADR-0004 决策 2；覆盖见 `tests/test_ia_structure.py` 与
  `tests/test_ia_frontend.py`）

数据库与敏感配置全环境变量外置（A1.1，03 计划 S1）：`DATABASE_URL`（开发库）、
`TEST_DATABASE_URL`（独立测试库，pytest-django 沿用该库名建/删，不加 `test_`
前缀）、`SECRET_KEY`（dev 与 production 均必填）、`ALLOWED_HOSTS`（production
必填，逗号分隔）、`MEDIA_ROOT`（可选，默认仓库内 `media/`）、
`FEEDBACK_EMAIL`（M2.2 页脚反馈邮箱，哑值默认；正式载体为站点级配置 M3+）。
`.env.example` 为哑值样例（无真实秘密）；本地 `.env` 已被 gitignore 排除。

## 验收命令（全绿基线；先 `set -a; source .env; set +a` 导出环境变量）

```bash
python --version                                             # 3.13.x
.venv/bin/pip install -r requirements.txt && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run   # 无漂移
.venv/bin/python -m pytest                                    # 65 passed（PG 实跑）
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

附加（A1.1 自测，非合并门）：三套 settings 可导入性由 pytest 覆盖；生产配置
检查 `DJANGO_SETTINGS_MODULE=peiligo.settings.production .venv/bin/python
manage.py check --deploy`（需完整环境变量；样例哑值下仍会提示 W009 密钥过短等
部署环境项）；`pip-audit` 漏洞扫描按 03 计划 S1 属记录项——发现漏洞仅记
Evidence 与上报，不擅自改动 ADR-0001 钉版。

已知无害输出：`manage.py check` 会有 5 条 `treebeard.E001` WARNING（上游
django-treebeard 5.3 对 Wagtail 7.4 管理器的弃用提示——每个使用基类管理器的
Page 模型各报一条，退出码 0，与 Wagtail 7.4.2 官方组合一致；M1 基线为 3 条，
A2.1 新增 SectionPage/DepartmentContainerPage 两个 Page 类型后为 5 条）。

## 仓库布局（03 计划 §2）

```text
manage.py / pyproject.toml / requirements*.txt / .env.example
src/peiligo/          # 项目装配层：settings/{base,dev,production}.py、urls.py、wsgi.py、context_processors.py
home/ search/         # 首页/板块页模型与模板、站内搜索视图（M2.2 前台 IA 已挂全局模板）
departments/ notices/ resources/ guides/ frontend/   # §2 预置空壳 app（仅包标记，无模型）
templates/ static/    # 项目级模板与静态资源（base/404/500.html、面包屑 partial、结构样式）
tests/                # pytest：冒烟+settings+IA 结构（M2.1）+ 前台 IA/无障碍（M2.2）
docs/                 # 治理文档（PRD、计划、ADR，本里程碑只读）
```

M1 边界：不含任何业务页面树/内容模型/权限/发布/中文搜索实现；上表空壳 app 的
模型与功能由后续里程碑（MB2+）填充。A1.1 边界：仅补 S1 环境依赖与配置外置
（PostgreSQL 基线、psycopg/gunicorn/pip-audit 钉版、`.env.example` 哑值、
dev 密钥与生产敏感项环境变量化）；无 CI/容器/备份/监控（S15+）。
