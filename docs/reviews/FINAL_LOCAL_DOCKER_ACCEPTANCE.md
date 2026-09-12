# Final Local Docker Release Acceptance — 证据记录

- 日期:2026-09-12(UTC 时间戳以容器日志为准)
- 性质:发布前最终门禁——Final Docker Release 打包 + 本机生产级(production-like)验收 + 仅限 Peiligo 的 QA 资产清理
- 结论:**FINAL_LOCAL_DOCKER_ACCEPTANCE = PASS**(零代码改动;仅新增本证据文件)
- 边界:全程仅本机(localhost / Caddy 本地自签)。**未做任何公网部署**:无 DNS、无云资源、无真实 TLS/域名、无公网暴露、无镜像推送、无生产秘密
- 本文件为验证证据,不含任何密码/秘密/令牌/私人环境信息

## 环境

| 项 | 值 |
|---|---|
| 基线 | `main` @ `b962ff2`(本地 == origin/main,工作区 clean) |
| 验证分支 | `feat/final-local-docker-acceptance`(独立 worktree `anthias`,自 origin/main 最新提交创建;**BASE_HEAD == FINAL_HEAD == `b962ff2`,本阶段零提交**) |
| 宿主 | macOS arm64,Docker Desktop(Docker 29.6.1 / Compose v5.3.0) |
| 编排 | `deploy/docker-compose.yml`(db/web/scheduler/caddy);本阶段以 `-p deploy-phase10` 独立项目名运行,**不触碰**此前 `deploy` 项目卷 |
| 本地 .env | 未入库(gitignored);仅本地哑值:DOMAIN=localhost、HSTS_SECONDS=3600(观察值口径,与冻结策略一致:首次公网部署 3600 / 终态 31536000 / 无 preload);变量名与 .env.example 一致 |
| PYTHONPATH 证明 | 宿主 venv 解释器 `import peiligo` → `/Users/chenjunxian/orca/workspaces/peiligo/anthias/src/peiligo/__init__.py`(Phase 10 worktree 内解析) |

## 验证结果

| 阶段 | 项 | 结果 | 关键证据 |
|---|---|---|---|
| A | 构建最终发布镜像 | PASS | `deploy-phase10-web:latest`(9cbd068eab70)、`deploy-phase10-scheduler:latest`(a9a3f3aa3354);python:3.13-slim + gunicorn 26.1.0 CMD(无 runserver);非 root `peiligo` 用户;构建期 collectstatic(哑 env)成功 |
| B | 栈首启 | PASS | 四容器 running,db/web healthy;web healthcheck 经 ALLOWED_HOSTS 首项 Host 探测;entrypoint:等库 → `migrate --noinput` → static 落卷 → exec gunicorn |
| C | 迁移 | PASS | `makemigrations --check --dry-run` = No changes detected(宿主与容器一致);全新卷冷启动一次性应用 221 个迁移;entrypoint 重复启动幂等 |
| D | 静态/媒体 | PASS | ManifestStaticFilesStorage 清单资源全部 200(无 404);Caddy file_server 直服 /static/ /media/;QA 上传图片(封面/正文插图/轮播外链封面)落 media 卷且前台可达 |
| E | 安全响应 | PASS | CSP 头精确匹配冻结策略,`/admin/`、`/django-admin/` 按豁免前缀不带 CSP;X-Content-Type-Options: nosniff;X-Frame-Options: DENY;Referrer-Policy: strict-origin-when-cross-origin;会话 Cookie HttpOnly+Secure+SameSite=Lax,CSRF Cookie Secure+SameSite=Lax(非 HttpOnly 为 Django 设计);HSTS 由 Caddy 钉 `max-age=31536000`(反代覆盖,Django 层 3600 已实证加载,不属代码缺陷);SECURE_SSL_REDIRECT 仅豁免 healthz/readyz;404/500 走安全模板无调试信息泄漏 |
| F | 功能验收 | PASS | 首页五板块 + Site Alert 时窗内显示;Hero 轮播 3 项(internal XOR external),`is-active`/`hidden`/`aria-current` 状态契约经 JS 确定性点击验证;搜索 icontains 命中 + `<mark>` 高亮(标题含词用例 40 处 mark;正文命中而展示字段不含词时无 mark 属正确行为)+ 分页(22 条通知 → 每页 20 共 2 页);五类详情页(Article/Notice/Material/SoftwareTool/Guide)全通过;封面/无封面/超长中文标题渲染正常;外链确认页流程通过,`javascript:` 非法目标被拒(go 端点不存在);设计内 404 正常;`/admin/` 登录(HTTP + UI)成功,未执行任何破坏性后台流程 |
| G | 运维链 | PASS | ops_report JSON 八类信号整体 ok/warn(仅 SECONDARY_BACKUP_DIR 未配的 warn,设计内);backup_run 备份集(db.dump/media.tar.gz/manifest/sha256sums)落卷且校验通过;scheduler `publish_scheduled.run` 心跳与 OpsHeartbeat 记录同时刻 |
| H | Playwright(唯一技能) | PASS | 四视口 1440×1000 / 430×932@3x / 393×852@3x / 360×800,各 15 条路由:无横向溢出(scrollWidth≤clientWidth)、无坏图(complete && naturalWidth===0 为 0)、无意外 console error、无资产 404(唯一 ≥400 为刻意请求的设计内 404 页);首页与长标题页桌面/移动截图目检通过(截图仅临时存放 /tmp,验收后删除,未入库) |
| I | 重启/持久化 | PASS | `docker compose restart web` 与全量 `down` → `up --build` 两轮:QA 文章/媒体/备份集俱在,自动迁移幂等;**未删除任何持久化卷** |
| J | 全新卷冷启动 | PASS | `down -v` 后重建:空库初始化 221 迁移 → healthz/readyz 200 → 空首页 200 → `/admin/login/` 200 → QA 文章 404(隔离性反证);演练卷随即销毁 |
| K | 文档可执行性 | PASS | LOCAL_RUN_AND_VALIDATION_GUIDE 按文执行全通;唯一操作者偏差:以 `-p deploy-phase10` 运行(本阶段任务强制的隔离要求),非文档缺陷亦非代码缺陷 → 无 DOC_BUG / 无 CODE_CONFIG_BUG;SERVER_DEPLOYMENT_GUIDE 仅作未来公网部署参考通读,**未执行任何公网部署章节** |
| L | 测试 | PASS | `git diff --check` clean;`manage.py check` 15 项均为既有 wagtailsearch.W001 警告(零新增);`ruff check` 通过(1 处既有 noqa 格式警告);`ruff format --check` 224 文件全过;**零代码/配置改动 → 全量 pytest 未重跑**(Phase 9 全量绿色基线有效) |

## 遗留偏差(如实披露,不阻塞本机验收)

| # | 事项 | 说明 |
|---|---|---|
| 1 | `brave_lewin`(Peilige 所有容器)曾被误删并即刻复原 | 清理批次中一条命令误以 `docker rm` 执行了本应只读的核查;该容器自创建起从未启动(Created 状态,无任何数据),随即以同一镜像 `peilige:phase8-rc` 重建同名容器,恢复至 Created 状态;`peilige:*` 镜像全程未动 |
| 2 | 操作者隔离偏差 | 上文 K 行 `-p deploy-phase10`,任务书要求所致,已在证据中登记 |
| 3 | HSTS 观察口径差异(未来公网部署前置项,非 Phase 10 阻塞) | 本机验收期间 Django 已实证加载 `HSTS_SECONDS=3600`,而实际 Caddy 响应头为 `max-age=31536000`(反代覆盖);本机验收 PASS、不受影响;但任何**未来公网部署**前,若首公网发行值仍为 3600,必须先对齐 Caddy 与 Django 的 HSTS 行为,方可依赖 3600(首发)→ 31536000(终态)的分阶段 rollout |

## 清理记录(仅限 Peiligo)

- **/tmp QA 产物归零(0)**:`boom_urls.py`、`peiligo_phase9_qa_media/`、`peiligo_phase95.diff`、`peiligo_qa/`、`peiligo_qa_seed_phase9.py`、`peiligo_restart_media/`、`peiligo-8c-fix-qa/`、`peiligo-8c-pr-body.md`、`peiligo-8c-qa/`、`peiligo-qa-8d/`、`wt742/`、本阶段 `peiligo-phase10-qa/`(含种子脚本/截图)及 worktree `.playwright-cli/` 全部删除;终态 `/tmp` 无任何 Peiligo QA 残留
- **QA 数据库**:`peiligo_phase9_qa`(有显式 QA 证据:种子脚本自述运行于该隔离库)已 DROP;**保留** peiligo_dev、peiligo_test、peiligo_restart_dev、peiligo_grunion_dev、peiligo_mullet_dev、peiligo_m4_poc、peiligo_m4_t16
- **Docker**:旧 `deploy` 项目卷 7 个(pgdata/media/static/backups/caddy_data/caddy_config 及同期匿名卷)与 deploy-web/deploy-scheduler 旧镜像移除;deploy-phase10 验收栈 `down -v`(QA 卷/网络销毁),最终发布镜像保留;未运行任何 prune 类命令
- **保留(非 Peiligo / 归属不明)**:Peilige 镜像与 brave_lewin 容器(见偏差 #1)、Peilike 无任何资源、ruoyi 全栈(容器/镜像/网络/卷)、3 个归属不明匿名卷(UNKNOWN_OWNERSHIP,按任务书原则原样保留)
- **保留(任务书指定)**:`orca/workspaces/peiligo/sevengill/ai/final-reference` 原样保留;旧 Orca worktrees 未做任何处置

## 变更清单

- 新增:`docs/reviews/FINAL_LOCAL_DOCKER_ACCEPTANCE.md`(本文件,未入库)
- 其余:**零改动**——无模型/迁移/前端/安全代码变更;`deploy/.env` 仅为本地 gitignored 验收配置
- 状态:工作区仅含本文件(untracked);未 commit、未 push、未建 PR,等待评审
