# PEILIGO_V1_FINAL_FULL_PROJECT_REVIEW

性质：READ-ONLY FINAL AUDIT（主审报告，Phase 1）
审查基线：`/Users/chenjunxian/vscode_projects/peiligo` @ `main` = `origin/main` = `f3bbbed74dbe68fa13f2552383d7f29f7e1862a2`
审查日期：2026-09-01
本文件 untracked/uncommitted，等 Human 阅读后决定是否落档。

---

## STATUS

| 项 | 值 |
| --- | --- |
| repo | /Users/chenjunxian/vscode_projects/peiligo（canonical SSOT） |
| main | f3bbbed74dbe68fa13f2552383d7f29f7e1862a2 |
| origin_main | f3bbbed74dbe68fa13f2552383d7f29f7e1862a2（fetch 后复核一致） |
| clean | YES（Safety Gate 通过，无 divergence） |

## FINAL_VERDICT

**PASS_WITH_FIXES**

开发主体完成且质量高于常见交付水准；无 BLOCKER；**HIGH 1 项**（H-1：部门组 change GPP 挂容器节点自身 → R2 可编辑容器 department/slug，违反冻结矩阵 M-C3——独立 Reviewer A 发现，主审已亲证升级）。修复＝一条 `before_edit_page` 只拒绝守卫，架构本身健全。另存 MEDIUM 2 + LOW 11 + INFO 10 的有限 Final Fix 批次，修完即可进入部署验证阶段。注：L-6/L-7/L-8 来自 Reviewer B；H-1/L-9/L-10/L-11/V-9/V-10 来自 Reviewer A，均已主审复核并入。

---

## EXECUTIVE_SUMMARY

V1 主要开发真实完成：五大板块内容模型、部门权限树、认证治理（axes/12 位密码/强制改密）、R-05 治理审计、上传三级校验、外链确认页、E1 中文搜索、生命周期五状态推导、归档视图、SEO 收口、Docker/Compose/Caddy 生产打包、备份/恢复/监控三件套均已实现且相互一致。本地 Final Gate 实测：`check`（15 项警告均为上游/已文档化设计项，exit 0）、`makemigrations --check` 无漂移、`pytest` **574 passed + 266 subtests**、`ruff check`/`format` 全绿、`check --deploy`（production settings + 哑值）仅余 1 项冻结决策内的 HSTS preload 警告。

架构零漂移：单一技术栈（Django 5.2 + Wagtail 7.4 + PostgreSQL 18 + SSR 模板）、单一认证、单一发布状态、单一 RBAC、单一搜索后端，无 Vue/FastAPI/第二套体系残留。

本轮（含两名独立 Reviewer 对抗复核）发现三项必须修的核心问题：**H-1 权限边界缺口**——部门组 `change` GPP 挂在部门容器节点自身（GPP 子树语义含节点本身），R2 可经正常后台编辑容器 `department` 外键与 `slug`，违反冻结矩阵 M-C3（"容器是权限边界载体"）；**M-1 功能断线**——站点设置"统一反馈邮箱"零前台消费点；**M-2 潜在降级开关**——production.py 尾部 `from .local import *`。三者修复均为小改动（守卫钩子/一行接线/删三行），不动摇架构。

---

## ARCHITECTURE

- **status**: 健康。Django+Wagtail+PostgreSQL+SSR 单栈；生产工程 Gunicorn + Docker Compose + Caddy 齐备。
- **drift**: **NO**。全局扫描无 Vue/FastAPI/DRF 直用/celery/双认证/双发布状态/双 RBAC/双搜索残留（requirements 中的 djangorestframework/django-filter 为 Wagtail 传递依赖）。frontend app 为 M1 空壳（仅 `__init__.py`）。`frontend/` 无代码即无漂移载体。
- 生产代码规模：apps 约 2,700 行 + `src/peiligo` 核心约 2,500 行，体量与冻结功能面匹配。

## CONTENT_MODEL

五类内容页（NoticePage/ArticlePage/MaterialPage/SoftwareToolPage/GuidePage）+ EventFieldsMixin（纯抽象、仅 Notice/Article 继承）+ Department/Tag/四类别词表 Snippet + FeaturedItem/SiteSettings。字段无重复失控：共享骨架经 `content_search_fields()`/`clean_content_page()`/`clean_publish_window()` 单源复用；Page/Snippet 边界与 ADR-0005 一致（运营词表=Snippet、内容=Page）。`makemigrations --check` 实测无漂移。SoftwareToolPage.platforms 的"创建表单校验期跳过"有亲证注释（construct_instance 不处理 m2m），非疏漏。

## INFORMATION_ARCHITECTURE

Root→HomePage→SectionPage×5（SECTIONS 冻结清单）→DepartmentContainerPage→五类叶子，parent/subpage 白名单逐层钉死。容器 `serve()` 恒 404、`get_sitemap_urls()=[]`、`search_fields=[]`、导航上下文处理器零树查询永不渲染容器——容器"路由分组非页面"语义四处收口一致。归档视图 `/<板块>/archive/` 正则封闭五 slug 且不遮蔽内容页路径（边缘：容器 slug 恰为 "archive" 时其容器 URL 会被归档视图截胡——容器本身 404 语义变为其板块归档页，子页不受影响，见 L-5）。面包屑/两空态/历史归档入口齐备。

## PERMISSIONS

- **status**: 健壮。骨架=`init_permissions` 幂等命令（总管理员组根级 GPP add/change/publish + 全模型权限 + 根集合 GCP；部门组 `dept-<slug>` 恰一枚 access_admin + 本部门容器 GPP×3 + 本部门集合 GCP×2；技术维护组零权限占位）。口令仅 stdin/env，零明文。
- 部门 A 不能管理 B 的**内容面**：结构性成立（GPP 挂各自容器节点；图片 chooser/列表按 collection 过滤、can_move_to 受目的地权限闸——Reviewer A 源码级证实）+ `tests/test_permissions_cross_dept.py`、`test_permissions_own_subtree.py`、`test_permissions_admin_boundary.py`、`test_permissions_governance.py` 等在库且本轮实跑通过（M4 T01–T16 的当前等价物存在）。
- **但容器自身编辑面存在 H-1 缺口**（见 HIGH_FINDINGS）：change GPP 含容器节点本身，R2 可编辑容器 department/slug，违反冻结矩阵 M-C3——独立复核发现，主审已亲证。
- "永久删除仅总管理员"：`before_delete_page` + `before_bulk_action` 双钩子只拒绝守卫（批量动线直调 delete 绕过单页钩子的坑已封），fail-closed。
- move/copy 递归路径绕过 clean 的缺口经 `before_move_page`/`before_copy_page` 子树复检封堵——**仅单页动线成立**：批量移动（`MoveBulkAction.action_type="move"`，execute_action 直调 `page.move()`）不经 `before_move_page`，而项目 `before_bulk_action` 两钩子只拦 `delete`（见 L-9）。

## AUTHENTICATION

12 位密码下限（MinimumLengthValidator OPTIONS）✓；django-axes 8.3.1：10 次/锁 15 分钟/成功清零/锁定键 `[username, ip_address]`（显式钉值防 NAT 误锁）/DB handler ✓；AxesStandaloneBackend 置首、ModelBackend 唯一凭据校验者（无第二套认证/token/学生账号残留）✓；会话 24h + SameSite=Lax + HttpOnly + 生产 Secure ✓；改密后会话失效 + PasswordChangeGateMiddleware 强制改密闸（放行清单仅改密页/登出）✓。无自研哈希。

## R05_GOVERNANCE_AUDIT

复用 Wagtail `log_actions`（零自建模型）。用户/组 CRUD 主行 + 组员 m2m 变动（正反向）+ 组权限逐项 + GPP 行级 + 批量启停（`after_bulk_action` 补 queryset.update 绕信号缺口）+ 删除兜底（同 uuid 去重）。**actor 不伪造**：无请求上下文记 `actor_type='non_request'` 而非编造 system。`/admin/gov-audit/` 权限门 = superuser ∨ `auth.change_user` ∨ `auth.change_group`，部门账号（仅 access_admin）不可读。审计行随 wagtail ModelLogEntry 表持久保留。

## UPLOAD

20 MiB（`WAGTAILDOCS_MAX_UPLOAD_SIZE`，G2 冻结值）✓；扩展白名单（docs 7 类 + images 收窄 jpg/jpeg/png/webp，显式排除 avif/gif）✓；**不信任浏览器 MIME**：声明 MIME 仅作矛盾拒绝、generic 声明忽略、filetype 内容签名正向识别（doc/xls/ppt 走 CFB 魔数）、识别失败一律拒绝 ✓；文件名路径形式拒绝/控制字符剥离/255 字节保扩展名截断 ✓；收口点=官方 `WAGTAILDOCS_DOCUMENT_FORM_BASE`，单文件/多文件/编辑替换三路径同经 `get_document_form` ✓。

## EXTERNAL_LINKS

http/https 白名单、缺协议拒绝不静默补全、userinfo 拒绝、URLValidator 兜底；统一确认页（四要素）+ 独立 go 端点，无自动跳转（无 meta refresh/JS/302）；go 端点输出层二次校验防库内脏数据；`from` 参数只回引 live∧¬expired 页（R 审查 M3 已修枚举泄漏）；确认页/端点不入页面树不进 sitemap，robots.txt Disallow + 模板 noindex。

## PUBLISH_LIFECYCLE

无平行状态：五状态纯推导（零新增字段），S1 挂官方 `approved_go_live_at`，live 优先、非法组合返回 None。`clean_publish_window` 全路径闸口（Notice 必填未来/Article 可选须未来/Material·Software·Guide 强制空 + go_live<expire 严于官方）。调度器常驻容器：单周期失败吞入结构化日志续跑 + 心跳双落（成功/失败皆记，`ops_report` 可区分"没跑"与"跑了失败"）+ compose restart 兜底，无静默死亡。expired：默认浏览（板块列表/首页）=CURRENT_DEFAULT 排除；/search/ 与归档视图=HISTORICAL（含 expired 带「已过期」徽标）+ `route()` 覆写放行 expired 具名 URL——与 M5.2 冻结设计一致（搜索入口语义=归档搜索，非缺陷）。

## SEARCH

E1 落地为真：`WAGTAILSEARCH_BACKENDS.default` 显式钉 `search.backends.E1IcontainsSearchBackend`（DatabaseSearchBackend fallback 子类），任何 vendor 下 icontains 语义，杜绝 PG 下静默走 FTS。q/section/dept/type/tag 组合过滤、非法值 200 回退、filter-first 保序（`order_by_relevance=False`）、跨类型 Python 稳定合并 `-first_published_at`、CJK 靠 icontains 天然可用。每类型一个 queryset（≤5 查询）+ 实例已是 specific，无 N+1、无重复 queryset、无 Python 全表过滤。FINAL-1 修复未引入性能回退。已知边界（RelatedFields 缺席/boost 忽略）为 ADR-0006 已接受选型代价且有回归测试（test_search_e1_backend/test_search_golden_set）。

## HOMEPAGE

顺序=冻结四层：紧急提示（窗口语义）→推荐位（≤3、0 整区不渲染、30 天默认可延长、enabled 即时撤下、is_on_display 唯一权威口径）→最新通知（CURRENT_DEFAULT，8 条）→近期活动（events 子树 event_end≥now，4 条）→五板块网格（冻结顺序、容器天然排除）。首页搜索 `name="q"`，无旧 query 兼容残留。

## SEO

query 态一律 noindex + canonical 指参数剥离 URL；逐内容页 noindex 开关（promote 面板）且 `get_sitemap_urls` 覆写**确实尊重 noindex**（sitemap 不入）；容器整类排除 sitemap；/search/ 归档态 noindex；确认页整页 noindex；robots.txt 管理面/确认页 Disallow、/search/ 刻意不 Disallow（noindex 语义正确性）；404/500 基本元数据齐（500 lang=zh-hans 有测试断言）。

## ACCESSIBILITY

- skip link（首焦点元素）、`:focus-visible` 样式、语义 landmark（header/nav[aria-label]/main/footer）、aria-current 导航、svg aria-hidden、表单 label、h1–h3 层级正确。
- 分类：**IMPLEMENTED**（代码层）；**VALIDATION_REQUIRED**：WCAG 2.2 AA 正式验证（axe/读屏）未执行——README 已如实声明，本轮不声称 PASS。

## PUBLIC_FRONTEND

base.html 继承树完整（404/内容页/归档/搜索/确认页均继承）；响应式 viewport + 移动端样式在 css 内；空状态两分界（筛选无匹配 vs 板块全空）有 filter_active 机制；全站零客户端 JS（纯 SSR）；中文 lang（zh-hans）。未重做视觉评审（按指令）。

## WAGTAIL_ADMIN

品牌 "Peiligo"、中文 verbose_name 全覆盖、zh-hans + LOCALE_PATHS 补译（Wagtail 缺失 msgid）、登录页三处最小 override（有升级 diff 注记）、治理审计页/强制改密闸可用。无阻塞后台使用的问题。

## CODE_QUALITY

- 循环 import 仅一处受控迟导入（search.services↔home.models，有注释论证）；signals 副作用全部 dispatch_uid + 文档化；无 fat settings（base 350 行且逐项有依据注释）；命令职责单一；备份/恢复子进程封装统一走 `_lib`；事务边界依赖 Wagtail 官方钩子事务语义并已注释论证。
- 死代码极少：`static/js/peiligo.js` 为 0 字节空文件（有测试断言其不被加载，保留属刻意但可删，L-4）。
- 检查警告 15 项：10× treebeard.E001（**上游** Wagtail manager vs treebeard 6 未来版本，非项目代码）；5× wagtailsearch.W001（五内容页 search_fields 刻意最小化遮蔽基类——代码注释与测试已文档化该设计，索引字段经 FilterField 覆盖 section/排序/可见性谓词全部消费点）。均 exit 0。

## PRODUCTION_PY_LOCAL_IMPORT

- **verdict**: **B · TECH_DEBT_NON_BLOCKING**
- **reason**（基于实测证据，非历史惯性）：
  1. `src/peiligo/settings/local.py` **当前不存在**（git 与构建上下文均无）；
  2. 生产模块导入链被 Dockerfile/entrypoint/compose/CI 四处显式钉死 `peiligo.settings.production`，环境变量缺失即快速失败（`env_required`），哑值无法上线；
  3. 风险路径仅剩"未来有人在构建上下文里创建 local.py"（.dockerignore 未排除该文件名），届时其会在尾部静默覆盖 SECRET_KEY/ALLOWED_HOSTS/cookie 全套安全值——**潜在降级开关，而非现存漏洞**。
  4. 建议：并入 Final Fix 批次删除 production.py 尾部 3 行（`try: from .local import *` 块，dev.py 保留），同时把 `local.py` 加入 .gitignore。不构成部署阻断。

## MIGRATIONS

各 app migration 链完整线性、无 merge migration 需求、无环境依赖迁移；数据迁移仅 2 处 RunPython 且均为 Wagtail 官方骨架模式（`home/migrations/0002_create_homepage.py` 建首页、`0004_homepage_title_zh.py` 改标题，均带 reverse，Reviewer B 复核确认无风险）；全库无 RunSQL/RemoveField/DeleteModel；`makemigrations --check --dry-run` 实测 "No changes detected"；新 app 中 govaudit/backupkit/applog 零模型零迁移（符合设计），passwordgate/opsignal 各 0001_initial；axes 迁移随第三方 app。无不可逆破坏性迁移（删除守卫在应用层）。

## DEPENDENCIES

全部 `==` 钉版；未发现直接弃养依赖。djangorestframework/django-filter/django-tasks/modelsearch/laces/beautifulsoup4 等为 Wagtail 7.4.2 传递依赖（非自选栈污染）。psycopg 3.3.4 + psycopg-binary（官方支持的生产形态）；filetype 1.2.0 偏老但其行为（含 doc/xls/ppt CFB 盲区）被上传模块显式适配并有测试锁定，升级需连带回归。dev/runtime 边界清晰（requirements-dev.txt 叠加式）。django-axes 8.3.1 与 Django 5.2 兼容（CI 实跑佐证）。未做网络 CVE 扫描（按指令）。

## DOCKER

Python 3.13-slim、非 root（`useradd peiligo` + chown /app /data）、依赖层缓存有序、PG18 客户端按 Debian 代号动态装、构建期 collectstatic 仅哑值（明确注释非真实秘密）、`exec gunicorn` 前置 entrypoint（信号正确传递）、多源 COPY 受 .dockerignore 裁剪（.env/.git/tests/docs 不进镜像）。

## COMPOSE

db（postgres:18 + healthcheck + pgdata 卷）/ web（env 注入秘密、media/static/backups 卷、depends_on db healthy、健康探针）/ scheduler（等 web healthy 后启动、间隔经 SCHED_INTERVAL_SECONDS）/ caddy（80/443、caddy_data 卷、static/media 只读挂载）。秘密全部 `${VAR}` 插值自 deploy/.env，仓库内无真实秘密（.env.example 全哑值）。restart: unless-stopped 全覆盖。

## CADDY

DOMAIN env 零硬编码、自动 HTTPS、gzip、HSTS 头、`-Server`、admin 仅回环、静态/媒体直出、/healthz* 反代、stdout 日志。未要求真实证书（首启自动申请）。

## HEALTH_READINESS

/healthz/（不触库、200 JSON）/readyz/（SELECT 1，失败 503）。响应恒最小 JSON，无 stack/path/credential/db 信息泄漏。SSL redirect 豁免两探针（`SECURE_REDIRECT_EXEMPT`），Caddy 侧 /healthz* 亦可直达。

## SCHEDULER

见 PUBLISH_LIFECYCLE：60s 缺省间隔、异常不断循环、`--once` 补跑载体、心跳落 DB、compose restart 兜底。静默死亡路径已封（失败心跳让 ops_report 可见"跑了但失败"）。

## BACKUP

backup_run：时间戳目录 + db.dump（custom 格式）+ media.tar.gz + manifest.json + sha256sums.txt；失败记结构化日志 + 心跳 + 清残集 + 非零退出；口令仅 PGPASSWORD 子进程环境（不落 argv/输出）；SECONDARY_BACKUP_DIR 未配置显式报告不静默。

## RESTORE

backup_restore：`--dry-run` 为显式 opt-in（`store_true`）；不带 `--dry-run` 且未给隔离目标参数时 CommandError 拒绝执行，带齐参数即实恢复——**"缺省 dry-run"的字面承诺不成立**（模块 docstring 同病，见 L-7），但破坏性防护铁律不依赖该语义：实际恢复必须显式给隔离 `--target-database`（须已 createdb）与 `--media-target-dir`，与当前库同名/与 MEDIA_ROOT 同径一律拒绝；校验和逐项核对（清单条目路径逃逸整体拒绝）；恢复前 pg_restore --list + tar 可读性双验证；tar 解包 `filter="data"` 防路径穿越。pg_restore 版本假设 = 容器内 PG18 客户端（与 postgres:18 服务端同大版本，Dockerfile 保证）。

## RETENTION

backup_prune：30 天硬下限（`days < 30` raise）；缺省 dry-run、`--apply` 才删；只删 `is_backup_set` 双特征（严格时间戳目录名 ∧ 含 manifest.json）项，绝不通配；副本侧同规则。race 面：备份进行中的新集 mtime 新，不会被当期 prune 命中（余下极端竞态为运维窗口问题，非代码缺陷）。

## MONITORING

ops_report 为真实现非文档摆设：database（SELECT 1，失败 CRIT）/ disk（项目路径 20% WARN / 10% CRIT）/ backup_freshness（12h WARN / 24h CRIT / 无备份 CRIT / 副本未配置 WARN）/ publish 心跳（15min WARN / 2h CRIT / 失败 CRIT）/ login_anomalies（axes AccessFailureLog 近 24h，仅提示）/ app_errors（可选 OPS_LOG_FILE）。任一 CRIT 非零退出，可直连告警。

## LOGGING

单行 JSON 入 stdout（JsonFormatter），peiligo/django/django.request/root 分层接线，≥INFO，脱敏原则落在 SB §6.2；容器/宿主负责保留期（与备份保留对齐）。零文件 handler、零外部日志框架，与冻结架构一致。

## CI

ci.yml 为诚实质量门：Python 3.13 + postgres:18 服务容器（哑值凭据）、PG18 客户端安装（backupkit 真调 pg_dump/pg_restore）、`pip install -e .`（src 布局修复）、check → makemigrations --check → ruff check → ruff format --check → pytest。**未发现** skip/xfail/删测试/降 lint 换绿色：门控类跳过共三类且 CI 中全部满足（TEST_DATABASE_URL skipif、`tests/test_backupkit.py` 3 处 `skipUnless(PG_TOOLS)`、`tests/test_search_e1_backend.py` PG vendor 门控——CI 装 PG18 客户端 + PG18 服务容器，实际零跳过）；历史 CI 修复提交（41af7b1/a98c1b9/a44149a/75c1ad1）均为补真实缺口而非绕过。

## TESTS

44 个测试文件覆盖全部关键业务边界：permissions×4（cross-dept/own-subtree/admin-boundary/governance）+ init 命令、search×5（contract/E1/fields/golden-set/ordering）、upload、external-link-confirm、gov-audit、password-gate、login-governance、backupkit、opsignal、health+scheduler、publish 边界、lifecycle 状态/转换、SEO、IA 结构/前端、home 数据区、删除/批量删除政策、revisions、tag 受控、streamfield、settings、smoke。本轮实跑 574+266 全绿。brittle/sleep 型测试未见（publish 边界测试明确"禁 sleep"）。无 coverage 工具配置——按指令不因此扣分。

## README

与实况一致：架构/版本/启动/测试命令/“engineered-not-deployed”状态/剩余验证清单/文档链接/架构历史声明（Vue+FastAPI 为史前史）。无旧状态残留。措辞小疵见 L-2。

## PRODUCTION_RUNBOOK

env/启动/scheduler/backup/restore/monitoring/HSTS 观察期/回滚/初始化齐备，宿主 cron 示例明确，"另一位开发者可接管"门槛达到。不足：邮件姿势（SMTP 未配置下的密码自助重置不可用）未见显式处置条目（V-2）。

## ADR_CONSISTENCY_MATRIX

| ADR | 主题 | 判定 |
| --- | --- | --- |
| 0001 | Wagtail/Django/Python 版本 | **ALIGNED**（pyproject/Dockerfile/requirements 三处一致） |
| 0002 | 服务端模板、零客户端框架 | **ALIGNED**（base.html 零 JS 位；测试断言） |
| 0003 | clean Wagtail skeleton | **ALIGNED**（settings 官方模板默认 + M1 注记改动） |
| 0004 | 部门权限容器树 | **ALIGNED**（容器语义四处收口 + 权限骨架 + 守卫） |
| 0005 | Page vs Snippet 载体分配 | **ALIGNED**（内容=Page、词表/推荐位/部门=Snippet、设置=BaseSiteSetting） |
| 0006 | 中文搜索 E1 icontains | **ALIGNED**（显式后端钉值 + 语义锁定回归测试） |

## REPO_HYGIENE

干净：无 tracked .env/dump/备份产物/pycache/venv/IDE 敏感配置/大文件（>1MB 零个）；"backup" 命中仅为 backupkit 源码与测试。`.DS_Store` 已 gitignore（工作树内一处 untracked 本地文件，不入库）。

## GIT_HEALTH

main = origin/main = f3bbbed，历史线性干净（PR merge 链）。历史分支（backup/、feat/m4-admin-admin、arch/*、luehunyo/* 批次分支）与 10 个 worktree 均不污染 main，符合"非 release blocker"判定。

---

# FINDINGS

## BLOCKERS

无。

## HIGH_FINDINGS

| ID | DOMAIN | EVIDENCE | RISK | ACTION_TYPE | RECOMMENDATION |
| --- | --- | --- | --- | --- | --- |
| H-1 | PERMISSIONS | ①`departments/management/commands/init_permissions.py:171-176` 把 add/change/publish GPP 挂在 `DepartmentContainerPage` 节点自身；②Wagtail GPP 子树语义含节点本身（`wagtail/models/pages.py:2195` `self.page.path.startswith(perm.page.path)`）；③容器 `content_panels` 含 `FieldPanel("department")`＋title/slug 可编辑（`departments/models.py:185-187`）；④冻结矩阵 `docs/ROLE_PERMISSION_MATRIX.md:92` M-C3：R2 编辑容器＝❌（"容器是权限边界载体，改容器即改权限边界"） | R2 部门账号经正常后台即可：改 `slug`（整部门前台 URL 断链/SEO 损失）、改 `department` 外键（破坏 §4 部门绑定，子树 clean 连锁拒绝＝自伤）；**升级链**：容器 FK 改指 B 部门后再跑幂等 `init_permissions`（`:171` 按 `department=B` 查容器），B 部门组 GPP 会挂上 A 部门容器子树 → B 获得 A 子树编辑发布权。违反冻结治理规格，主审已亲证全链 | CODE_FIX | 仿删除守卫加 `before_edit_page` 只拒绝钩子：非特权用户编辑 `DepartmentContainerPage`（及 SectionPage/HomePage）一律拒绝，fail-closed；补"R2 编辑容器被拒"回归测试（当前零覆盖）。可覆盖 N-2 的批量移动面一并收口 |

## MEDIUM_FINDINGS

## MEDIUM_FINDINGS

| ID | DOMAIN | EVIDENCE | RISK | ACTION_TYPE | RECOMMENDATION |
| --- | --- | --- | --- | --- | --- |
| M-1 | 站点设置/前台 | `src/peiligo/context_processors.py:25`（`settings.FEEDBACK_EMAIL`）；`templates/base.html:97`、`home/templates/home/home_page.html:103`（消费 context processor 值）；`home/models.py:286`（SiteSettings.feedback_email 声明，help_text 称"每页反馈链接…同源单值"）；全仓 grep 证实 **SiteSettings.feedback_email 零消费点**；`src/peiligo/settings/base.py:347-350` 注释仍称"此前以 settings 过渡承载"（模型已于 migration 0005 落地，切换未发生） | 管理员在后台修改"统一反馈邮箱"完全不生效，前台 mailto 永远指向 env 旧值/哑值 feedback@example.com；字段存在即暗示可用，属静默失效 | CODE_FIX | Final Fix：context processor 改读 `SiteSettings.for_request(request).feedback_email`（保留 env 为 fallback），或删字段收敛为 env 单源；二选一，同时修正 base.py 过渡注释。补一条回归测试断言"后台改设置→页脚 mailto 变化" |
| M-2 | 生产配置 | `src/peiligo/settings/production.py:54-57` 尾部 `try: from .local import * except ImportError: pass`；`local.py` 现不存在（实测）；`.dockerignore` 未排除该文件名 | 潜在安全降级开关：未来任何 local.py 进入构建上下文即静默覆盖 SECRET_KEY/ALLOWED_HOSTS/cookie/HSTS 全套冻结值；当下无暴露路径 | CODE_FIX（Final Fix 批次内） | 删除 production.py 尾部覆盖点（dev.py 保留）；`.gitignore` 增加 `src/peiligo/settings/local.py`。裁决记录：**B · TECH_DEBT_NON_BLOCKING**（详见 PRODUCTION_PY_LOCAL_IMPORT 节） |

## LOW_FINDINGS

| ID | DOMAIN | EVIDENCE | RISK | ACTION_TYPE | RECOMMENDATION |
| --- | --- | --- | --- | --- | --- |
| L-1 | 生产配置 | `production.py` 无 `WAGTAILADMIN_BASE_URL` 覆盖；`base.py:321` 恒为 `http://example.com`，生产不读 env | 后台邮件类链接（如密码重置信）拼出错误绝对 URL；V1 主流程不经邮件（强制改密在登录侧），影响延迟暴露 | CODE_FIX | 并入 Final Fix：`WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", ...)`，并纳入 .env.example/compose |
| L-2 | 文档 | `README.md:98-99` 称"生产编排（docker-compose.yml）另含…cron 定时触发 backup_run/ops_report"；cron 实际为**宿主侧**（Runbook §40/76 示例），compose 内无 cron 服务 | 接管者按 README 找编排内定时器会落空 | DOC_FIX | README 措辞改为"生产运行（宿主 cron，见 Runbook）" |
| L-3 | 运维 | `deploy/docker-entrypoint.sh:26` `cp -a /app/staticfiles/. /data/static/` 只增不删 | 跨版本升级后旧哈希静态资产在卷内累积（ManifestStaticFilesStorage 下无功能影响，仅磁盘增长） | OPERATIONS_REQUIRED | 升级流程加一次性清理（停机换卷或 rsync --delete 语义） |
| L-4 | 代码卫生 | `static/js/peiligo.js` 0 字节；`templates/base.html:105` 注明脚本位已移除；`tests/test_home_data_areas.py:405` 断言不加载 | 无功能风险；纯遗留空文件 | CODE_FIX（可随 Final Fix 顺手删） | 删除文件 |
| L-5 | IA 边缘 | `src/peiligo/urls.py:16,39-43`：归档视图正则先于 Wagtail 兜底；容器 slug 可编辑为 "archive" 时，`/chronicle/archive/` 命中归档视图而非容器 404 | 极端配置下容器 URL 渲染归档页（IA §3.2"容器 URL 恒 404"字面破例）；其子内容页不受影响 | VALIDATION_REQUIRED | 运营侧禁用 "archive" 容器 slug，或接受并登记为已知边缘 |
| L-6 | 监控 | `src/peiligo/opsignal/management/commands/ops_report.py:60-70`：database 检查有 try/except，但后续 `_backup_heartbeat_check`/`_publish_check`/`_login_check` 直查 DB 无捕获 | DB 不可达时命令在输出 JSON 前崩溃（违背其自身注释"快照仍如实输出"），已算得的 disk/backup 信号一并丢失；exit code 告警锚点仍有效，影响有界 | CODE_FIX（可随 Final Fix 批次） | 三处 DB 直查补 try/except 降级为 signal error 行，保住 JSON 快照语义 |
| L-7 | 备份文档 | `backup_restore.py:5`（docstring）与 `:25,64,73-74`（实现）：docstring 称"缺省 dry-run"，实际 `--dry-run` 是 opt-in；缺省行为＝无参数拒绝/带参数实恢复 | 接管者按文档预期"默认只打印计划"，实际语义差一档；防护铁律（拒当前库/当前媒体）不受影响 | CODE_FIX（随 Final Fix 改一行 docstring） | 修正 docstring 与 `--help` 文案为实际语义（"不显式给隔离目标即拒绝；--dry-run 显式校验"） |
| L-8 | 恢复隔离 | `backup_restore.py:79-82`：媒体隔离仅拒绝 `media_dir.resolve() == current_media.resolve()` 精确相等 | `--media-target-dir` 指向 MEDIA_ROOT **子目录**（如 /data/media/restore-x）时放行，解包文件混入在线媒体树（/media/ 可达）；非破坏性但违背"隔离"意图字面 | CODE_FIX（可随 Final Fix） | 加路径前缀检查：目标在当前 MEDIA_ROOT 内即拒绝 |
| L-9 | 权限/内容模型 | `departments/wagtail_hooks.py:223,269`（before_bulk_action 只拦 delete）＋ Wagtail `bulk_actions/move.py:32`（`action_type="move"` 的 execute_action 直调 `page.move()`，不经 before_move_page） | 批量移动绕过 §1.4 板块白名单与 §4 部门一致性复检：R2 可把 MaterialPage 批量移入自己另一板块容器；R1 可批量制造部门不一致。**非安全越权**（R2 跨部门被 can_move_to 目的地权限闸拦截），属冻结内容模型一致性缺口 | CODE_FIX（建议随 H-1 同钩子批次） | `before_bulk_action` 增拦 `move` 类型，复用 `_subtree_violation`/`clean_content_page` 同口径复检 |
| L-10 | 治理审计 | `src/peiligo/govaudit/receivers.py`：覆盖 User.groups/Group.permissions/GroupPagePermission 行级，但 `GroupCollectionPermission`（部门图片集合授权面）无逐项明细接收器 | 图片集合隔离所依赖的 GCP 变动只有组级 wagtail.edit 主行，与 GPP 留痕粒度不对称 | CODE_FIX（可随 Final Fix） | 补 post_save/post_delete sender=GroupCollectionPermission 接收器 |
| L-11 | 生产配置 | `deploy/docker-compose.yml:31-45` web/scheduler env 清单无 `FEEDBACK_EMAIL` 透传 | 运维在 .env 配置反馈邮箱不进容器，恒为 base.py:350 哑值；M-1 修复若保留 env fallback 则生产同样静默哑值 | CODE_FIX（随 M-1 同批） | compose env 增 `FEEDBACK_EMAIL: ${FEEDBACK_EMAIL:-}` 并入 .env.example |

## INFO_VALIDATION_ITEMS

| ID | 域 | 事项 | ACTION_TYPE |
| --- | --- | --- | --- |
| V-1 | 检查警告 | `check` 15 项警告：10× treebeard.E001（上游 Wagtail↔treebeard 6 预警，跟踪升级）；5× wagtailsearch.W001（§20.1 表 A 冻结最小索引集的已文档化代价）。exit 0，不阻断 | NO_ACTION（登记跟踪） |
| V-2 | 邮件姿势 | 生产未配置 EMAIL_BACKEND/SMTP（settings 无生产邮件配置，Runbook 无处置条目）：后台密码自助重置（邮件链路）不可用。V1 账号恢复路径=总管理员后台改密/CLI。部署时须显式决策（配 SMTP 或把 CLI 恢复写入 Runbook） | OPERATIONS_REQUIRED |
| V-3 | 性能 | 板块列表/搜索/归档全量单页渲染无分页（代码注明"V1 全量单页渲染"冻结）；E1 icontains 为全表 LIKE 语义。当前校内体量可承受，数据量增长后需复核 | VALIDATION_REQUIRED |
| V-4 | 部署验证 | Docker 镜像构建与容器启动未实跑（README 已如实声明）；TLS/DNS、100 并发、恢复演练（RTO≤4h）、WCAG/axe 正式验证均待执行 | DEPLOYMENT_REQUIRED / VALIDATION_REQUIRED |
| V-5 | CI 记录 | CI 首跑 PASS 记录在 GitHub Actions 页（PR #10 时代）；本轮 fetch 无新提交，末次 main CI 状态以 Actions 页为准 | VALIDATION_REQUIRED（Humans 复核一眼即可） |
| V-6 | axes 代理面 | 锁定键=(username, ip_address)；经 Caddy 反代后 gunicorn 所见 REMOTE_ADDR 为代理 IP，实际退化≈按 username 锁定——**行为可接受且反而消除了 NAT 误锁面**，但部署验证时应确认 X-Forwarded-For 链路符合预期并记入 Runbook | VALIDATION_REQUIRED |
| V-7 | HSTS | 冻结"无 preload"（`check --deploy` 唯一安全警告 W021 即此，属决策内）；首期可用 HSTS_SECONDS 观察期 | NO_ACTION |
| V-8 | 无障碍 | WCAG 2.2 AA 正式验证未执行（代码层已 IMPLEMENTED 部分） | VALIDATION_REQUIRED |
| V-9 | 附件公开面 | `src/peiligo/urls.py:21` 挂载 wagtaildocs serve 视图（Wagtail 缺省无权限检查）：未认证者可按自增 ID 枚举下载文档库文件 | 文档＝公开附件模型属设计语义；但"按 ID 枚举"面应被知情。如需收口可用 collection view restrictions | NO_ACTION（登记为已知设计面） |
| V-10 | 运维摩擦 | `init_permissions.py:24-29` 根集合 GCP 仅 add/change（collection+image），无 delete_image/delete_collection | 非超管 R1 无法删除误传图片/集合（Wagtail 删除走 GCP 记录）；矩阵未列 delete 项疑为有意 | OPERATIONS_REQUIRED（Runbook 登记超管通道或补 GCP） |

---

# FINAL_DEVELOPMENT_TRUTH

**PURE_DEVELOPMENT_COMPLETE: NO**

REMAINING_CODE_FIXES: **3**（H-1、M-1、M-2）

1. **H-1** 容器编辑守卫（`before_edit_page` 只拒绝钩子 + 回归测试；建议连带 L-9 批量移动收口）——冻结权限矩阵 M-C3 违反，部署前必须修；
2. **M-1** feedback_email 消费接线（真功能性缺口，必须修）；
3. **M-2** production.py 删除 `from .local import *` 覆盖点 + .gitignore 补条（小、防御性，强烈建议随批）。

另建议同批顺手：L-1（WAGTAILADMIN_BASE_URL env 化）、L-2（README 一句话）、L-4（删空 js）、L-6/L-7/L-8（Reviewer B 三项小修：ops_report 快照保活、backup_restore docstring 语义、媒体目标子目录拒绝）、L-10（GCP 审计接收器）、L-11（compose FEEDBACK_EMAIL 透传）。合计一天内的 Final Fix 批次。

**其余全部剩余事项属于 Validation / Deployment / Operations**：容器实跑、TLS/DNS、性能与并发、无障碍正式验证、恢复演练、邮件姿势决策、备份副本绑定独立存储、CI 记录复核——均无仓库内代码缺口（M-1/M-2 除外）。

# DEPLOYMENT_READINESS

- **READY_FOR_VALIDATION: YES**（Final Fix 可与验证准备并行；M-1 修后须进回归）
- **READY_FOR_STAGING_DEPLOYMENT: NO**（Final Fix 合入并 CI 绿后即 YES）
- **READY_FOR_PRODUCTION: NO**（严格解释：须先完成 staging/验证阶段——容器实跑、备份/恢复演练、监控接线、性能与无障碍验证；当前"engineered-not-deployed"状态被 README 准确陈述）

# TEACHER_MAINTAINER_VIEW（工程视角，不讨好）

1. **最可能首先质疑**：① H-1——"容器是权限边界载体"的冻结语义为什么没有被一条编辑守卫钉死（GPP 挂节点自身是 Wagtail 惯用形态，但与治理矩阵对读就是缺口）；② M-1 这类"模型有字段、前台无消费"的收尾断线；③ E1 icontains 全表 LIKE 语义在数据上量后的查询成本；④ 单机 compose 形态的运维成熟度（cron 在宿主、无集中 secret、主机单点）——对校内 V1 是正确取舍，但接管者需知道边界在哪。
2. **三个最合理的设计**：① 所属板块由树位置推导（SectionContextMixin），零冗余字段、单一事实源；② search.services 单一过滤层被板块列表/搜索/归档三个入口共用，可见性谓词由入口显式绑定（CURRENT_DEFAULT/HISTORICAL），语义不漂移；③ 权限体系完全建立在 Wagtail 原生 GPP/GCP 之上加"只拒绝"守卫，fail-closed，没有自造第二套 RBAC。
3. **三个最明显的技术债**：① production.py 尾部 local 覆盖点（M-2）；② 无分页的全量单页渲染（冻结的 V1 简化）；③ treebeard 6 兼容预警 + filetype 1.2.0 偏老，两个上游升级项被有意按住不动（各自有测试护栏，可接受但要在升级时付出回归成本）。
4. **AI 堆代码迹象**：无。反证充分：注释密度高且几乎每处非平凡决策带规格出处与"亲证"记录（如 construct_instance 的 m2m 时序注释、entrypoint 的 check --database 陷阱注释）；无复制粘贴膨胀（apps 共 2700 行）；无过度抽象。唯一风格代价：代码注释与 docs/ 规格强引用耦合，规格文档若失修会增加新人的考古成本——治理仓风格使然，可接受。
5. **可维护性**：高。5,200 行生产代码、全钉版依赖、44 个测试文件覆盖关键边界且跑得快（134s）、ruff 全绿、迁移无漂移、README/Runbook 足以冷启动接管。
6. **上线前重点复核**：H-1 守卫修复 + 权限回归（重点补"R2 编辑容器被拒"断言）；M-1 修复后回归；V-2 邮件姿势显式决策；恢复演练真做一遍（backup_restore 的隔离铁律设计很好，但没演过就不算数）；axes 在 Caddy 后的锁定行为按 V-6 确认；HSTS 观察期走一遍。

# NEXT_STEP_DECISION

**B · FINAL_FIX_REQUIRED**

最小 Final Fix Backlog（一天内可完成）：
1. **H-1**：容器编辑守卫（before_edit_page 只拒绝 + "R2 编辑容器被拒"测试；连带 L-9 批量移动收口）；
2. M-1：feedback_email 接线（SiteSettings 优先、env 兜底）+ 回归测试 + L-11 compose 透传；
3. M-2：production.py 删 local 覆盖点 + .gitignore 补 `local.py`；
4. （顺手）L-1：WAGTAILADMIN_BASE_URL env 化；L-2：README cron 措辞；L-4：删空 peiligo.js；L-6：ops_report 三处 DB 直查加保护；L-7：backup_restore docstring 语义修正；L-8：恢复目标媒体子目录拒绝；L-10：GCP 审计接收器。

不开始执行（本轮只读纪律）。

# GIT_DISCIPLINE

本轮零 commit/zero push/零 merge/零生产代码改动。实测执行面仅：只读 git 命令、只读文件读取、本地 Final Gate（check/makemigrations/pytest/ruff/check --deploy，均为既有命令无副作用）。本文件与 `docs/reviews/FINAL_FULL_PROJECT_REVIEW.review.md` 保持 untracked，等 Human 决定是否落档。

---

*主审：Claude（主 Session）· 2026-09-01 · 基线 f3bbbed*
