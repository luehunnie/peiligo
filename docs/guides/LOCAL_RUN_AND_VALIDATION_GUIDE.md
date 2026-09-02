# Peiligo 本地运行与验证指南

目标:**几周后忘了怎么跑,照这篇就能启动。** 全部命令核对自当前 `main` 仓库真实文件。

本地有两套**用途不同、不要混用**的运行方式:

| 方式 | 用途 | 组成 |
|---|---|---|
| **A. Native Development Run** | 日常开发、跑测试 | Python venv + 本机 PostgreSQL + Django development server |
| **B. Local Production-like Docker Validation** | 部署前的生产同构验证 | `deploy/` 下的 Docker Compose(PostgreSQL 容器 + Gunicorn + Caddy + scheduler) |

> **状态(2026-09-02 基线)**:两条路径均已在本地实跑通过。方式 A 是被 CI 与 600+ 项测试持续验证的日常路径;方式 B 已于 2026-09-02 完整执行一轮并通过(证据见 [../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md](../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md),过程中发现的 5 个运行时问题已修复合并回 `main`)。尚未在真实服务器上执行过——那是 [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) 的范围。

---

## 方式 A:Native Development Run

### A0. 前置条件(macOS 示例)

- **Git**(取得代码);
- **Python 3.13**(`python3.13 --version`;macOS 可用 Homebrew 安装:`brew install python@3.13`——brew 只是示例,按你机器实际方式装);
- **PostgreSQL 18**(本机服务;`psql --version` 能看到版本即可。本机实际端口/套接字目录以安装为准);
- 不需要 Docker、不需要 Node。

取得代码:

```bash
git clone <仓库地址> peiligo
cd peiligo
git checkout main
```

### A1. 创建虚拟环境并安装依赖

项目包在 `src/peiligo`(src 布局),必须 editable 安装后 `manage.py` 才能导入 `peiligo.settings`(与 CI、Docker 镜像同构):

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # 已含 requirements.txt
pip install -e .                      # editable 安装 src/peiligo 配置包
```

> ⚠️ 不要复用其他仓库/其他 worktree 的现成 venv:editable 安装的 `.pth` 指向创建时的 `src` 路径,跨目录复用会导入到别的代码。每个工作副本建自己的 `.venv`。

### A2. 环境变量(`.env.example` → `.env`)

仓库根有哑值样例 `.env.example`;复制为 `.env` 并按本机实际修改。**两者区别**:`.env.example` 入库(哑值模板),`.env` 被 `.gitignore` 排除(本机真实值,禁止提交)。

**Django 不会自动加载 `.env`**——每次开新终端先导出:

```bash
set -a; source .env; set +a
```

开发必填变量(完整语义见 `.env.example` 注释):

| 变量 | 是否必填(dev) | 说明与哑值示例 |
|---|---|---|
| `DATABASE_URL` | **必填**,缺失即拒绝启动 | `postgres://peiligo_dev:change-me@localhost:5432/peiligo_dev` |
| `SECRET_KEY` | **必填**,缺失即拒绝启动 | 任意长随机串即可:`django-insecure-...` 样例风格(dev 用);生产必须是 `python -c "import secrets;print(secrets.token_urlsafe(64))"` 生成的真随机值 |
| `TEST_DATABASE_URL` | 跑 pytest 必填 | 独立测试库,如 `postgres://peiligo_dev:change-me@localhost:5432/peiligo_test` |
| `WAGTAILADMIN_BASE_URL` | dev **不需要** | 仅 production / Docker 必填(后台通知邮件的基准 URL) |
| `MEDIA_ROOT` | 可选 | 媒体根目录,不设默认仓库内 `media/` |
| `FEEDBACK_EMAIL` | 可选 | 反馈邮箱兜底值,正式载体是后台「站点设置」 |

`.env` 不提交 Git。

### A3. 创建本机数据库

用 psql 建开发库与测试库(用户名/密码/库名按你本机习惯,与 `DATABASE_URL` 一致即可):

```bash
psql -U postgres
```

```sql
CREATE USER peiligo_dev WITH PASSWORD 'change-me';
CREATE DATABASE peiligo_dev OWNER peiligo_dev;
CREATE DATABASE peiligo_test OWNER peiligo_dev;
\q
```

### A4. 初始化与启动(最短链)

```bash
cd <仓库根>
source .venv/bin/activate
set -a; source .env; set +a

python manage.py check          # 系统检查
python manage.py migrate        # 建表(M1 基线迁移)
python manage.py runserver
```

启动后(开发服务器 `http://127.0.0.1:8000`):

| 地址 | 内容 |
|---|---|
| `/` | 首页(迁移后还没有业务数据,先做 A5) |
| `/admin/` | Wagtail 后台 |
| `/search/` | 全站搜索(无参数 = 表单态) |
| `/healthz/` | 存活探针(不触库) |
| `/readyz/` | 就绪探针(DB `SELECT 1`) |
| `/django-admin/` | Django 原生 admin |
| `/sitemap.xml`、`/robots.txt` | SEO |

开发模式(DEBUG=True)下 static 与 media 由开发服务器直接供带,无需 collectstatic。

### A5. 业务初始化(建演示数据)

```bash
python manage.py bootstrap_sections     # 首页下幂等创建五个板块页(直接发布)
python manage.py init_permissions       # 建 R1/R2/R3 三组权限骨架(见下)
python manage.py createsuperuser        # 技术维护/应急 superuser(R3 载体)
```

- `bootstrap_sections`:幂等,重复执行零副作用;默认站点根不是 `HomePage` 时报错退出;
- `init_permissions`:建「总管理员组 / 部门组 `dept-<slug>` / 技术维护组」,并清理迁移自动生成的空 Editors/Moderators 组。账号选项:
  - `--admin-user <用户名>`:R1 总管理员账号(非 superuser,靠组行权);
  - `--dept-user <用户名> --department <slug>`:R2 部门账号(每部门至多一个);
  - **口令只经 stdin 或环境变量传入**,两者皆缺则拒绝创建:
    ```bash
    python manage.py init_permissions --admin-user admin --password-stdin < 密码文件
    # 或:PEILIGO_INIT_PASSWORD=... python manage.py init_permissions --dept-user jwc --department jwc
    ```
- 部门与容器随后在后台操作:`/admin/` 建部门 Snippet,在板块页下建「部门容器」并绑定部门,再在容器下发内容。

### A6. 常用检查与测试命令

| 命令 | 作用 |
|---|---|
| `python manage.py check` | Django 系统检查(配置/模型明显问题) |
| `python manage.py makemigrations --check --dry-run` | 校验模型改动都已生成迁移(防漂移,CI 同款) |
| `pytest -q` | 全量测试套件(48 个测试文件;库取 `TEST_DATABASE_URL`) |
| `ruff check .` | Lint(规则集 E/F/W/I/B/UP,line-length 100) |
| `ruff format --check .` | 格式检查(不改动,只报告) |
| `pip-audit` | 依赖漏洞审计(可选,dev 依赖已含) |

跑测试前记得环境变量已导出(`TEST_DATABASE_URL` 缺失时 pytest-django 回落 Django 默认的 `test_` 前缀库,不是基线口径)。

---

## 方式 B:Local Production-like Docker Validation

用生产同构的四容器编排(db / web / scheduler / caddy)在本机完整走一遍「构建 → 启动 → 初始化 → 验收」。

### 已验证基线(2026-09-02)

方式 B 已完整实跑一轮,**全部阶段 PASS**,含:

- 四容器构建与启动;db / web healthcheck 通过;
- `/healthz/`、`/readyz/`、首页、`/admin/` 登录、static 资源;
- 人工验收:后台建部门与部门容器、建内容页、上传图片、前台可见;
- 重启后数据与 media 卷持久化;
- scheduler 端到端定时发布(内容到点自动上线);
- `ops_report` 快照、`backup_run` 备份集生成;
- 备份集在隔离环境 `backup_restore` 演练通过。

证据与逐项结论见 [../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md](../reviews/LOCAL_DOCKER_RUNTIME_VALIDATION.md)。该轮验证发现的 5 个运行时问题(Dockerfile / compose 层)已修复并合并回 `main`,当前代码即验证后的形态。下文 B0–B5 保留为**复现步骤**——重新执行一轮验证时照做即可。

### B0. 前提

- Docker daemon 正常运行(Docker Desktop 已启动;`docker info` 无报错);
- 本机 80/443 端口未被占用(Caddy 要绑;若被占,临时停掉本机 web 服务或改 Compose 端口映射实验)。

### B1. 准备部署环境变量

`deploy/.env.example` 是 compose 形态的哑值样例(与根目录 `.env.example` **不是一套**,变量见 [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md))。本地验证填法:

```bash
cd deploy
cp .env.example .env
vi .env
```

本地 dummy 取值示例(勿用真实秘密):

```ini
POSTGRES_DB=peiligo
POSTGRES_USER=peiligo
POSTGRES_PASSWORD=local-validation-only
SECRET_KEY=local-validation-random-not-a-real-secret
ALLOWED_HOSTS=localhost
CSRF_TRUSTED_ORIGINS=https://localhost
WAGTAILADMIN_BASE_URL=https://localhost
DOMAIN=localhost
# 可选:GUNICORN_WORKERS=2 / SCHED_INTERVAL_SECONDS=60
```

`localhost` 域名下 Caddy 用**本地自签证书**(不申请公网证书),浏览器会提示不受信任——本地验证接受告警或信任 Caddy 本地 CA 即可;`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`WAGTAILADMIN_BASE_URL` 三处都按 `https://localhost` 同源填写。

### B2. 构建与启动

```bash
# 校验编排文件与 .env 插值(不启动)
docker compose config

# 构建 + 启动(RUNBOOK 正式形态,仓库根执行)
cd ..
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build

# 或等价简写(deploy 目录执行,compose 自动读同目录 .env)
#   cd deploy && docker compose up -d --build
```

启动时序(自动完成,无需人工干预):db 健康检查通过 → **web entrypoint 自动等库 + `migrate` + 铺 static** → gunicorn 起来、healthz 探针通过(start_period 60s)→ scheduler 启动 → caddy 出证书。**迁移是自动的,不要重复手工执行。**

观察状态与日志:

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.yml ps
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f web
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f scheduler
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f caddy
```

### B3. 容器内业务初始化

```bash
alias dcr='docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec web'

dcr python manage.py bootstrap_sections
# stdin 重定向须加 -T(禁用 TTY 分配),否则 docker 报 "the input device is not a TTY":
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T web \
    python manage.py init_permissions --admin-user admin --password-stdin < 密码文件
dcr python manage.py createsuperuser      # 交互式;应急 superuser
```

随后访问 `https://localhost/admin/` 登录总管理员账号,建部门、部门容器与内容。

### B4. Docker 验证清单

一次合格的本地生产同构验证,至少勾完这些(2026-09-02 那轮验证已全部勾完):

- [ ] `docker compose ps`:db / web / scheduler / caddy 四服务全部 running;db 与 web 显示 healthy(仅这两者配置了 healthcheck)
- [ ] `curl -fk https://localhost/healthz/` 返回 `{"status":"ok"}`(存活)
- [ ] `curl -fk https://localhost/readyz/` 返回 ok(就绪,DB 可达)
- [ ] 首页 `https://localhost/` 可访问,五板块入口正常
- [ ] `/admin/` 可登录(init_permissions 建的账号;强制改密动线可在后台重置某账号密码后另测)
- [ ] migrate 已由 entrypoint 自动完成(日志可见 `applying migrations`)
- [ ] `/static/...` 资源 200(Caddy 直供 static 卷)
- [ ] 后台上传一张图片/一个文档后,前台可访问对应 media 地址
- [ ] `docker compose restart web` 后:数据库数据还在、media 文件还在(验证卷持久化)
- [ ] scheduler 日志周期性输出 `publish_scheduled.run`(心跳在动)
- [ ] `dcr python manage.py ops_report` 输出 JSON 快照
- [ ] `dcr python manage.py backup_run` 生成备份集(backups 卷内出现 `<时间戳>/`)

### B5. 停止(重要:两种停止天差地别)

```bash
# 常规停止:保留全部卷(pgdata/media/static/backups/caddy_*),下次 up 原样恢复
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down

# ⚠️ 危险:额外删除全部卷 = 清空数据库、媒体、备份集、TLS 证书。
# 仅在确认要完全重来时使用,绝不作为常规关闭方式。
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down -v
```

---

## Troubleshooting

| 症状 | 原因与处置 |
|---|---|
| 启动即 `RuntimeError: DATABASE_URL 未设置` | settings 快速失败(设计如此)。`.env` 没建或没导出:`set -a; source .env; set +a` |
| `RuntimeError: SECRET_KEY 未设置` | 同上,dev 也必填 |
| `RuntimeError: WAGTAILADMIN_BASE_URL 未设置` | 只在 production settings / Docker 出现;compose 里它是 `${WAGTAILADMIN_BASE_URL:?}` 必填项,检查 `deploy/.env` |
| `connection refused ... :5432` / 认证失败 | 本机 PostgreSQL 没起,或 `DATABASE_URL` 的用户/密码/库名/端口与实际不符;`psql "<DATABASE_URL 的连接串>" -c 'select 1'` 先通它 |
| `django.db.utils.ProgrammingError: relation 不存在` | 没跑 `migrate`,或连到了另一个空库 |
| 端口 8000 被占 | `lsof -i :8000` 找到占用进程停掉,或 `python manage.py runserver 127.0.0.1:8001` 换端口 |
| `docker compose config` 报 `WAGTAILADMIN_BASE_URL is required` | `deploy/.env` 缺必填变量(compose `:?` 快速失败,属预期防护) |
| `Cannot connect to the Docker daemon` | Docker Desktop 未启动 |
| web 容器一直 `starting`/unhealthy | 看日志:entrypoint 在「waiting for database」= db 未健康(查 db 日志);迁移失败也会卡在这(start_period 60s 内多给点时间再判断) |
| Caddy 证书报错 / 浏览器告警 | `DOMAIN=localhost` 时是本地自签(接受即可);填了真实域名但 DNS 未指向本机,Let's Encrypt 会申请失败——本地验证就用 `localhost` |
| `/admin/` 提示 CSRF 或 403 | `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` 与实际访问域名不一致(必须含 `https://localhost` 这类带 scheme 的来源) |
| static 404 | 确认走的容器链路(entrypoint 已铺 static 卷);本机 dev 模式则确认 DEBUG=True 且 URL 是 `/static/` |
| media 上传后 404 | dev 模式确认 `MEDIA_ROOT` 指向的目录存在;容器里 media 卷属主是非 root 的 `peiligo` 用户,不要用 root 手改卷内文件属主 |
| scheduler 没起来 | 它 depends_on **web healthy**——web 没健康它不会启动;先修 web,再看 `logs scheduler`;间隔由 `SCHED_INTERVAL_SECONDS` 控制 |

---

## 下一步

本地两条路都走通后,进入正式部署:[SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md)。运维细节(备份 cron、监控接线、恢复演练)以 [../PRODUCTION_RUNBOOK.md](../PRODUCTION_RUNBOOK.md) 为准。
