# Post-G2 全项目只读 Implementation Gap Audit（POST_G2_IMPLEMENTATION_GAP_AUDIT）

- **性质**：READ_ONLY_GAP_AUDIT_FIRST 模式下的只读调查（G2_FREEZE_EVIDENCE §9/§10 Human 2026-09-01 签收授权）；非开发任务
- **BASELINE**：`main` @ `3dd0caa`（= `origin/main`，working tree clean；branch=main 已验证）
- **日期**：2026-09-01
- **方法**：以冻结文档（G2_FREEZE_EVIDENCE §5 二十五项 Gap、SB §12/§14、NFR §13、G2_HUMAN_DECISIONS Q1–Q23、00_MASTER_PLAN §16 MB1–MB18）为 Coverage Checklist，逐项对照**当前真实代码**重新取证（rg 定位 → 小范围精读），禁止复制 G2 结论
- **生产代码改动**：零（本文件与 `docs/reviews/POST_G2_GAP_AUDIT.review.md` 为本轮仅有的两个新增文档）
- **判定标准**：DONE＝正式实现存在＋与冻结要求一致＋主路径无缺失＋有测试/Evidence；PARTIAL＝核心实现存在但覆盖不全；NOT_DONE＝冻结要求明确但当前代码/配置无对应实现；OBSOLETE＝已被后续正式架构/裁决取代

---

## 1. AUDIT_SCOPE（六必查 + 十八领域全覆盖）

A 核心架构 / B 内容类型 / C 权限 / D 发布与归档 / E 搜索 / F 上传 / G 外链 / H 生产 Web 配置 / I 登录治理 / J 推荐位 / K SEO / L 无障碍 / M 性能 / N 备份恢复 / O 监控 / P 日志 / Q CI / R 容器与生产打包。取证全部来自 `main@3dd0caa` 工作树实读，关键结论附 `file:line`。

---

## 2. 域级判定总表（A–R）

| 域 | 判定 | 关键证据 | 残留 |
| --- | --- | --- | --- |
| A 核心架构 | **DONE** | ADR-0001 锁版实测（`requirements.txt`：wagtail==7.4.2、Django==5.2.17、modelsearch==1.3.2；`pyproject.toml` python >=3.13,<3.14）；settings 三层（`src/peiligo/settings/{base,dev,production}.py`，`tests/test_settings.py` 锁定导入与 env 外置）；页面树 Home→Section→Container→五类叶（`home/models.py:42-74`、`departments/models.py:153-216` 的 parent/subpage 白名单）；容器前台 404＋不进 sitemap＋不入索引（`departments/models.py:209-216`）；StreamField 六块白名单＋RichText features 收窄（`notices/blocks.py`）；受控词表五 Snippet（departments/notices/resources/guides） | 无 |
| B 内容类型 | **DONE** | 五类 Page 模型冻结字段集＋clean 链＋面板行序＋ALLOWED_SECTIONS＋admin 中文化（`notices/models.py`、`resources/models.py`、`guides/models.py`）；EventFieldsMixin 仅挂 Notice/Article＋板块语义 clean＋event_status 三态（`notices/models.py:130-202`）；Preview＝Wagtail 内建（容器 preview_modes=[]）；列表/详情模板在库；发布窗口逐模型政策（`notices/lifecycle.py:91-123`）。测试覆盖：test_notice_article_models 13＋test_material_software_models 13＋test_taxonomy_snippets 13＋test_event_fields 18＋test_guide_models 10＋test_content_tree 32 条 | 无（首页数据区属域 J/MB9 残留，不属内容类型本身） |
| C 权限 | **DONE**（主范围） | T01–T16 16/16（M4.3，五份权限测试文件＋init_permissions 命令）；删除仅总管理员双钩子单条+批量（`departments/wagtail_hooks.py:242-280`）；非空结构页拒删双动线（`:197-231`）；移动/复制内容模型守卫（`:79-173`）；词表/集合边界（`departments/permissions.py`） | **R-05（用户/组管理 DB 级审计）＝ NOT_DONE**——全仓无任何用户/组操作审计钩子；G2 签收第 7 项交本审计分类：登记为待实现项，**前置＝项目负责人裁决是否实现**（见 F-08） |
| D 发布/归档 | **PARTIAL** | 应用层 DONE：五状态推导＋E1–E11 全边转换测试（`tests/test_lifecycle_transitions.py`，21 条）；`expired` 置位经内建 `publish_scheduled` 命令（测试 `call_command` 实证；`wagtailcore.Page.expired` 经内省证实为 Wagtail 7.4 内建字段，项目零自定义迁移）；expired 页原 URL 放行渲染＋横幅（`notices/lifecycle.py:75-88`、`templates/base.html:72-76`）；五板块历史归档视图 `/&lt;板块&gt;/archive/`（`home/views.py`、`src/peiligo/urls.py:22-26`）；HISTORICAL/CURRENT_DEFAULT 双谓词（`notices/lifecycle.py:126-147`）。**生产调度未接线**：`publish_scheduled` 依赖外部定时执行，仓库内零 cron/compose/scripts 载体 | 生产调度载体归 F-09（FINAL-2） |
| E 搜索 | **PARTIAL** | 契约/过滤层 DONE＋测试族（`search/services.py` 全 274 行：五参数白名单解析、filter-first 保序、逐类型查询、双可见性绑定；`tests/test_search_contract.py` 等 23 条）。**E1 生产接线＝NOT_DONE**：`base.py:236` 仍为通用 `wagtail.search.backends.database`，PG vendor 下走 FTS＝E2 语义；`SELECTED_SEARCH_BACKEND`/icontains 全仓零命中；ADR-0006 明示「E1 在生产成立须显式后端选择（PRODUCTION_IMPLEMENTATION_REQUIRED=YES）」。**金标集＝NOT_DONE**：仓库仅有字段结构占位（`search/services.py:273-274`），30 条金标本体不在库 | E1 接线＝F-01；接线后复验门（NF-17/POC §7）＝VALIDATION_ONLY；金标集回归＝F-01 附带 |
| F 上传 | **PARTIAL** | 扩展名白名单存在但为官方默认集（`base.py:248-259`：含 csv/txt/zip/key/odt 超界、缺 doc/xls/ppt——SB §12 判 PARTIAL 口径）；**20 MiB＝NOT_DONE**（`base.py:262` 仍 10MB）；**MIME 校验＝NOT_DONE**；**文件签名/魔数＝NOT_DONE**（项目代码零命中；依赖树内 `filetype==1.2.0` 在库可复用，SB §12 注明）；文件名规则＝仅存储层基础清洗（PARTIAL） | F-02 |
| G 外链 | **PARTIAL** | 字段在库（`resources/models.py:113,178`、`notices/models.py:255,320`、ExternalLinkBlock）；过渡安全形态＝「链接文字＋完整 URL 明文」无裸跳转（`templates/blocks/external_link.html`，自带注释声明确认页 DEFERRED）；站点设置文案位就绪（`home/models.py:177-181` redirect_notice_text）。**统一确认页＝NOT_DONE**（无路由/视图/模板）；**scheme 收窄＝NOT_DONE**（URLField/URLBlock 官方默认 scheme 集，未限 http/https） | F-03 |
| H 生产 Web 配置 | **PARTIAL** | 已接线：DEBUG=False、SECRET_KEY/ALLOWED_HOSTS env 外置快速失败、ManifestStaticFilesStorage（`production.py`）；X-Frame-Options DENY（Django 默认）；HttpOnly（Django 默认）。**未接线**：SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE、SESSION_COOKIE_SAMESITE=Lax 显式值、SESSION_COOKIE_AGE=24h（现 Django 默认 2 周）、SECURE_SSL_REDIRECT、SECURE_HSTS_*（Q5 目标 1 年先短后长）、SECURE_PROXY_SSL_HEADER。注：SECURE_CONTENT_TYPE_NOSNIFF/SECURE_REFERRER_POLICY 已由 Django 5.2 默认值生效（3.0/3.1 起默认开启），F-10 属显式钉值加固而非补缺 | F-10 |
| I 登录治理 | **PARTIAL** | Django/Wagtail 原生账号机制在位（Q2 口径）；改密后会话失效＝Django 内建。**全部冻结专属控制＝NOT_DONE**：最低 12 位未配置（`base.py:142-155` MinimumLengthValidator 用默认 8）；登录限速未实现（axes 未装，requirements 无）；临时限制无；重置/首登强制改密无 | F-05 |
| J 推荐位 | **PARTIAL** | 模型层 DONE：FeaturedItem Snippet（`home/models.py:95-156`：start/end/enabled＋clean＋`is_on_display` 四条件谓词含 CURRENT_DEFAULT 成员判定；`tests/test_publish_scheduled_boundaries.py:491-553` B16–18）。**前台消费＝NOT_DONE**：首页仅渲染搜索工作台＋五板块网格（`home/templates/home/home_page.html`，模板注释自证四数据区「待模型到位后插入」——模型现已全部到位）；≤3 条/0 条隐藏/1–2 条自然展示规则未实现；**30 天默认有效期＝NOT_DONE**（start_at/end_at 必填无预填）；首页推荐位正向渲染测试为零 | F-04 |
| K SEO | **PARTIAL**（代码已领先 G2 记录） | 已实现：query 态 noindex＋canonical（`templates/base.html:18-29`）；搜索页恒 noindex＋canonical（`search/templates/search/search.html:12-18`）；归档页 noindex＋canonical（`home/templates/home/section_archive.html:12-20`）；sitemap.xml 装配＋容器排除（`urls.py:29`、`departments/models.py:213-216`）；seo_title/search_description/meta description 输出（`base.html:6-17`）；404/500 页在库。**未实现**：robots.txt（全仓零命中）；单篇 noindex 字段（五 models 无 noindex/promote 覆写）；确认页 noindex（随确认页缺失） | F-06（robots.txt＋单篇 noindex）；确认页 noindex 随 F-03 |
| L 无障碍 | **PARTIAL**（实现面基本在库） | skip-link 首聚焦＋CSS（`base.html:49`、`peiligo.css:205-218`）；focus-visible 全局（`peiligo.css:155-161`）；搜索表单显式 label＋role=search（`search.html:30-31`、`home_page.html:26-28`）；标题层级每页恰一 h1 无跳级（五模板逐一在库）；图片 alt（`blocks/image.html:4`）；nav/aria-label/aria-current/role=status（`base.html:56-62,73`、`breadcrumb.html:9-13`）；lang=zh-hans（`base.html:3`）；JS 零交互（`static/js/peiligo.js` 为空文件）。**未做**：axe 工具化接入（随 CI，F-11）；WCAG 走查/扫描未执行（VALIDATION_ONLY）。小疵：`500.html:2` lang="en" | 工具化随 F-11；人工验收＝VALIDATION_ONLY |
| M 性能 | **NOT_DONE**（全部属验证，非开发缺口） | NF-01/02/07/08/09 零实测；测量环境未建；100 并发未执行。JS 预算 Q13≤200KiB 现状天然满足（JS 为空文件）但无正式测量。**无生产 E1 前性能数据不能算 DONE**（与 G2 判定一致） | 接线后按 §1.6/NF-17 验证（VALIDATION_ONLY＋DEPLOYMENT_ONLY 前置） |
| N 备份/恢复 | **NOT_DONE** | 备份脚本/任务零命中；12h 配套（Q11）、30 天保留（Q21）、独立副本（Q9）、恢复程序与演练工具均无实现。口径/模板已在 NFR §5 冻结（documented 层） | 脚本与编排＝F-12（FINAL-2）；演练＝OPERATIONS_ONLY |
| O 监控 | **NOT_DONE** | 健康端点路由零命中；5 分钟拨测（Q19）、磁盘 20%/10%（Q20）、备份监控、登录观测、调度监控全部无实现 | 端点随 F-09；拨测/告警脚本＝F-13（FINAL-2） |
| P 日志 | **PARTIAL** | 内容面审计 DONE（Wagtail PageLogEntry 修订/操作日志，SB §12 SATISFIED）；脱敏规则成文且现状零违规（SB §6.2/M4 审计）。**结构化 LOGGING 配置＝NOT_DONE**（settings 无 LOGGING dict）；错误可见性依赖 Django 默认 | F-07 |
| Q CI | **NOT_DONE** | `.github/` 目录不存在（MB15 零文件）；本地工具链已就绪（pytest/ruff 配置于 `pyproject.toml`，pip-audit 在 dev 依赖）但无流水线/门禁 | F-11 |
| R 容器/生产打包 | **NOT_DONE** | Dockerfile/compose/Caddyfile/scripts/ 目录全不存在（MB16–MB18 零文件）；gunicorn 已在依赖（`requirements.txt`） | F-09 |

---

## 3. LEGACY_MB_MAPPING（00_MASTER_PLAN §16 十八步，按当前代码重判）

| MB | 标题 | CURRENT_STATUS | CURRENT_EVIDENCE | REASON |
| --- | --- | --- | --- | --- |
| MB1 | 环境与依赖基线 | **DONE** | 骨架/锁版/settings 三层/TEST_DATABASE_URL 护栏（`base.py:126-136`、`test_settings.py`）；A1.x 审查在案 | 全部验收面在库 |
| MB2 | 部门模型与账号组 | **DONE** | `departments/models.py:21-52`＋`init_permissions` 命令＋组矩阵测试 15 条 | 全部验收面在库，T 系列回归在案 |
| MB3 | 权限容器树与后台安全基线 | **DONE** | 容器硬约束（404/sitemap/索引三重排除）＋T01–T16 16/16 | 冻结约束全落地 |
| MB4 | 通知与文章 Page 模型 | **DONE** | `notices/models.py` 两模型＋clean 链＋13 条模型测试 | 冻结字段一字不差 |
| MB5 | 校园活动模型 | **DONE** | EventFieldsMixin＋18 条测试（含「零 EventPage」负向断言） | 终判形态（Mixin 不建独立 Page）落地 |
| MB6 | 学习资料与软件工具模型 | **DONE** | `resources/models.py` 两模型＋删除仅总管理员守卫（自定义 permission 义务的等效关闭措施） | MB6 验收点（permission_policy）经 M4.4 双钩子方案实现并有测试 |
| MB7 | 校园指南模型 | **DONE** | `guides/models.py` 九字段＋10 条测试 | 冻结九字段一个不删 |
| MB8 | 发布、到期归档与置顶/推荐位 | **PARTIAL** | 生命周期/归档视图/expired 放行/FeaturedItem 模型全在库 | 残留：首页推荐位消费、30 天默认、生产调度载体（F-04/F-09） |
| MB9 | 前台基础模板、首页与列表页 | **PARTIAL** | base/首页/板块/五详情/归档/搜索/面包屑模板在库＋IA 前台测试 30 条 | 残留：首页四数据区渲染＋首页搜索参数 bug（F-04） |
| MB10 | 站内搜索与筛选 | **PARTIAL** | 搜索视图＋四维筛选＋保序排序＋契约测试族 | 残留：E1 生产语义接线＋金标本体不在库（F-01） |
| MB11 | 附件上传与校验 | **PARTIAL** | 扩展白名单＋大小上限（10MB）在库 | 残留：20MiB/PRD 白名单对齐/MIME/魔数（F-02） |
| MB12 | 外链确认跳转页 | **NOT_DONE** | 过渡形态（明文 URL）在库；确认页本体零文件 | 整页待实现（F-03）；字段/设置位已预留 |
| MB13 | SEO 基建与 noindex | **PARTIAL** | sitemap/canonical/查询态与归档搜索 noindex 已在库（G2 记录「未实现」已过时——M2.2/M5.2 先于 G2-B 入库） | 残留：robots.txt＋单篇 noindex 字段（F-06） |
| MB14 | 无障碍与响应式达标 | **PARTIAL** | 必查项实现面大体在库（skip-link/focus-visible/label/层级/alt/aria） | 残留：axe 工具化（F-11）＋走查实测（VALIDATION_ONLY）＋500.html lang 小疵 |
| MB15 | CI 流水线 | **NOT_DONE** | `.github/` 不存在 | 全步待实现（F-11）；本地 pytest/ruff 门已在 |
| MB16 | 容器化与本地编排 | **NOT_DONE** | 容器/编排文件不存在 | 全步待实现（F-09） |
| MB17 | 备份与恢复 | **NOT_DONE** | 备份/恢复脚本不存在 | 全步待实现（F-12） |
| MB18 | 监控与日志 | **NOT_DONE** | LOGGING/健康端点/监控脚本不存在 | 全步待实现（F-07/F-09/F-13） |

**OBSOLETE 登记一**：治理线步骤 **M0.3–M0.7**（AI_WORKFLOW/TASK_TEMPLATE/SECRETS_POLICY/CHANGE_MANAGEMENT/PHASE_GATES）＝**OBSOLETE**——SUPERSEDED_BY：Human G2 签收第 6 项（2026-09-01，G2_FREEZE_EVIDENCE §10）裁定其已被 Rolling Implementation、M1–M7 正式成果与 G2 Governance Evidence 实质取代，不再机械执行。**MB1–MB18 无一步 OBSOLETE**——全部对应真实代码现状（完成或真实残留）。

---

## 4. G2_GAP_REVALIDATION（G2_FREEZE_EVIDENCE §5 二十五项逐项重验）

> G2 期望值照录底册；现状以 `main@3dd0caa` 代码为准重新取证。

| # | GAP_ID | G2_EXPECTATION | CURRENT_EVIDENCE | STATUS | NOTES |
| --- | --- | --- | --- | --- | --- |
| 1 | E1_PRODUCTION_WIRING | 显式后端选择使 icontains 语义生产成立 | `base.py:236` 通用 database 后端；`SELECTED_SEARCH_BACKEND`/icontains 零命中 | **NOT_DONE** | F-01；接线后须过 §11.4/NF-17 复验门 |
| 2 | UPLOAD_SIZE_ENFORCEMENT | 20 MiB（Q1） | `base.py:262` 仍 10MB | **NOT_DONE** | F-02 |
| 3 | MIME_VALIDATION | 三级校验层② | 项目代码零实现 | **NOT_DONE** | F-02 |
| 4 | FILE_SIGNATURE_VALIDATION | 魔数校验（SEC-18） | 零实现；`filetype==1.2.0` 在依赖树可复用 | **NOT_DONE** | F-02 |
| 5 | EXTERNAL_REDIRECT_CONFIRMATION | 统一确认页（SB-06/SEC-21） | 无路由/视图/模板；过渡明文形态；文案位已预留 | **NOT_DONE** | F-03 |
| 6 | PRODUCTION_COOKIE_CONFIGURATION | SECURE_*/cookie 一族（Q16/Q6） | `production.py` 仅 DEBUG/KEY/HOSTS/静态后端；24h 会话未配置 | **NOT_DONE** | F-10 |
| 7 | LOGIN_RATE_LIMIT / FORCE_PASSWORD_CHANGE | axes（Q3）＋强制改密（SB-04） | axes 未装；12 位未配置（默认 8）；强制改密无 | **NOT_DONE** | F-05 |
| 8 | HSTS_FINAL_CONFIGURATION | 先短后长至 1 年（Q5） | SECURE_HSTS_* 零接线 | **NOT_DONE** | F-10 |
| 9 | FEATURED_COUNT / EXPIRY_ALIGNMENT | ≤3 条（Q14）/30 天默认（Q15）随 MB8 落地 | 模型+展示谓词+测试在库；首页消费与 30 天默认未实现 | **PARTIAL** | F-04 |
| 10 | PERFORMANCE_VALIDATION | NF-01/02/07/09 实测 | 零实测、无测量环境 | **NOT_DONE**（验证类） | VALIDATION_ONLY |
| 11 | 100_CONCURRENT_USER_VALIDATION | NF-08 执行 | 未执行 | **NOT_DONE**（验证类） | VALIDATION_ONLY |
| 12 | ACCESSIBILITY_VALIDATION | axe＋键盘走查 | 未执行；实现面大体在库 | **NOT_DONE**（验证类） | VALIDATION_ONLY；工具化随 F-11 |
| 13 | SEO_FINAL_ALIGNMENT | noindex 字段/sitemap 终态/跳转页（MB12/MB13） | 查询态/归档/搜索 noindex＋canonical＋sitemap 基础已实现（**G2 记录已落后于代码**）；robots.txt、单篇 noindex 字段、确认页仍未实现 | **PARTIAL** | F-03/F-06 |
| 14 | BACKUP_AUTOMATION | 12h DB+media 配套（Q11） | 零实现 | **NOT_DONE** | F-12 |
| 15 | BACKUP_SCHEDULE | 同上调度化 | 零实现 | **NOT_DONE** | F-12 |
| 16 | BACKUP_RETENTION | ≥30 天（Q21） | 零实现 | **NOT_DONE** | F-12 |
| 17 | INDEPENDENT_BACKUP_COPY | 本地+独立副本（Q9） | 零实现 | **NOT_DONE** | F-12 |
| 18 | RESTORE_DRILL | 季度演练 RTO≤4h（Q12/Q23） | 未执行 | **NOT_DONE**（运维类） | OPERATIONS_ONLY |
| 19 | HEALTH_CHECK | 5 分钟拨测（Q19） | 健康端点与拨测均无 | **NOT_DONE** | 端点随 F-09、拨测随 F-13 |
| 20 | MONITORING | 六项口径（NFR §6） | 全部无实现 | **NOT_DONE** | F-13 |
| 21 | DISK_ALERT | 20%/10% 阈值（Q20） | 无 | **NOT_DONE** | F-13 |
| 22 | SCHEDULER_MONITORING | publish_scheduled 告警（NF-16） | 无 | **NOT_DONE** | F-13 |
| 23 | STRUCTURED_LOGGING | LOGGING 配置＋保留期 | settings 无 LOGGING；内容审计（PageLogEntry）已在 | **NOT_DONE** | F-07 |
| 24 | CI | secret 扫描+依赖检查（MB15） | `.github/` 不存在；本地 pytest/ruff/pip-audit 工具链就绪 | **NOT_DONE** | F-11 |
| 25 | CONTAINER / CADDY FINALIZATION | Q10 基线落地（PP-19） | 容器/Caddy 文件零 | **NOT_DONE** | F-09 |

### 4.1 G2 记录与当前代码的偏差更正（本审计新证）

1. **ARCHIVE/PUBLISH 域**：G2-B 矩阵记「板块历史归档视图未实现」，但归档视图于 `4d67473`（2026-08-28，M5.2）入库，**早于** G2-B 基线 `0caece5`（2026-09-01，已验证祖先关系）——该两行现状应为「已实现」，本表已按代码更正。
2. **SEO 域**：G2 记「noindex 字段/sitemap 终态未实现」——查询态/归档/搜索 noindex＋canonical（M2.2）与 sitemap 装配实际在库，现状为 PARTIAL 而非整块未实现。
3. **G2 未登记的本审计新发现**：首页搜索表单参数名不匹配（`home/templates/home/home_page.html:28` `name="query"` vs `search/services.py:158,171` 读取 `q`）——**用户可见功能性缺陷**：首页搜索框提交的关键词被静默丢弃、恒落入表单态。归入 F-04 修复。另两处小疵：`500.html:2` lang="en"；`static/js/peiligo.js` 为空文件仍被全站加载（零功能零风险，可留 F-04 顺手清理）。

---

## 5. 分类总账

| 分类 | 域级（A–R） | MB 级 | G2 Gap 25 项 |
| --- | --- | --- | --- |
| DONE | 3（A/B/C 主范围） | 7（MB1–MB7） | 0 |
| PARTIAL | 10（D/E/F/G/H/I/J/K/L/P） | 6（MB8/9/10/11/13/14） | 2（#9、#13） |
| NOT_DONE | 5（M/N/O/Q/R） | 5（MB12/15/16/17/18） | 23（其中 3 项属纯验证：#10/11/12；1 项属纯运维：#18） |
| OBSOLETE | 0 | 0（M0.3–M0.7 治理线另计 1） | 0 |

---

## 6. 缺口性质分流（§13 要求：不把测试/部署/运维算进纯开发）

### 6.1 IMPLEMENTATION_GAP（真正要写代码/工程文件）
即 §7 FINAL_IMPLEMENTATION_BACKLOG 全部 13 项（F-01…F-13；其中 F-08 以项目负责人裁决为前置）。

### 6.2 VALIDATION_ONLY（不算纯开发）
- E1 接线后复验门（ADR-0006 §11.4/NF-17：hit@10、逐条 p50、规模/并发复测）——前置 F-01
- 性能实测 NF-01/02/07/08/09（含 100 并发 NF-08、2s 核心内容 NF-01）——前置 F-09 测量环境
- WCAG axe 扫描＋键盘走查（NF-03/04/10）；浏览器/响应式（NF-15）
- `manage.py check --deploy` 生产复核；SB-05/SB-06 等断言随 F-02/F-03 附带测试
- 金标集回归测试集构建与执行（30 条，POC §7 承接）——可并入 F-01 验证段

### 6.3 DEPLOYMENT_ONLY（不算纯开发）
- PVE/Docker 生产环境搭建、域名/TLS 证书（PP-19）、DNS、生产 `.env` 注入
- `bootstrap_sections`/`init_permissions` 生产初始化执行；测量环境（预发布同级）搭建（NF-01 前置）

### 6.4 OPERATIONS_ONLY（不算纯开发）
- 季度恢复演练（Q12/NF-05）与发布前备份确认；备份任务日常运行与监控值守
- 上线前媒体总量盘点（PP-18）；曾暴露令牌轮换确认（治理动作，项目负责人）
- R-05 裁决本身（Human 决策；若裁决「实现」则转入 F-08 开发项）

---

## 7. FINAL_IMPLEMENTATION_BACKLOG（唯一正式纯开发清单）

> 依赖说明：F-01–F-08 相互独立可并行评审，但缺省串行（主控纪律）；F-09–F-13 内部弱耦合（健康端点→healthcheck、axes→监控）。CI（F-11）宜在 FINAL-1 合并后跑绿全量测试。

| ID | TITLE | CURRENT_STATUS | FILES / MODULES | DEPENDENCIES | RISK | BATCH |
| --- | --- | --- | --- | --- | --- | --- |
| F-01 | E1 搜索语义生产接线（icontains 显式后端选择；沿 POC E1 同路径，不改 Wagtail 核心）＋金标集回归入库 | NOT_DONE | `src/peiligo/settings/base.py`；可能新增 `search/backends.py`；`tests/` | 无 | **HIGH**（接线错误将静默改变全站搜索语义；须经 NF-17 复验门） | FINAL-1 |
| F-02 | 附件上传硬化：20 MiB、PRD 白名单收窄、MIME+魔数三级校验（复用 `filetype`）、文件名显式规则 | PARTIAL（白名单/大小在库但不对齐） | `src/peiligo/settings/base.py`；新增上传校验 hook 模块；`tests/` | 无 | MEDIUM | FINAL-1 |
| F-03 | 外链统一确认页：路由/视图/模板（PRD §7.5 四要素＋noindex）＋URL scheme 收窄 http/https＋外链块与 SoftwareTool source_url 出口改造 | NOT_DONE | `src/peiligo/urls.py`；新确认页视图/模板；`notices/blocks.py`、`templates/blocks/external_link.html`、`templates/resources/software_tool_page.html`；`home/models.py`（文案位已备） | 无 | MEDIUM | FINAL-1 |
| F-04 | 首页四数据区渲染（紧急提示/推荐位 ≤3·0 隐藏·1–2 自然/最新通知/近期活动）＋FeaturedItem 30 天默认＋修复首页搜索 `name="query"`→`q` bug；顺带模板小疵：`500.html` lang 改 zh-hans、移除空 `peiligo.js` 加载（§4.1） | PARTIAL（模型全备，消费层未做） | `home/models.py`、`home/templates/home/home_page.html`、`tests/test_home.py` | 无 | LOW | FINAL-1 |
| F-05 | 登录治理：密码最低 12 位（Q2）、django-axes 限速 10 次/15 分钟→锁 15 分钟（Q3）、重置/首登强制改密、SESSION_COOKIE_AGE=24h | NOT_DONE | `src/peiligo/settings/base.py`、`requirements.txt`、认证 hook/表单；`tests/` | 无 | **HIGH**（后台公网可达（Q4）且无限速＝最大安全暴露面） | FINAL-1 |
| F-06 | SEO 收尾：单篇 noindex 字段（IA-09，promote 面板）＋robots.txt＋sitemap 终态联动 | PARTIAL | 五内容模型或公共基类、`templates/base.html`、`src/peiligo/urls.py` | 无 | LOW | FINAL-1 |
| F-07 | 结构化 LOGGING 配置（SB §6.2 脱敏规则落地、错误可见性、保留期工程默认） | NOT_DONE | `src/peiligo/settings/base.py`＋`production.py` | 无 | LOW | FINAL-1 |
| F-08 | R-05 用户/组管理 DB 级审计（**前置：项目负责人裁决是否实现**） | NOT_DONE（待裁决） | `departments/`（log_actions/hooks 扩展）＋`tests/` | Human 裁决 | LOW | FINAL-1（条件项） |
| F-09 | 容器化与生产编排：Dockerfile＋Compose（app+PostgreSQL+Caddy）＋持久卷＋env 注入＋gunicorn＋healthcheck（含健康端点视图）＋publish_scheduled 正式定时任务（Q10 调度） | NOT_DONE | 新增 `Dockerfile`、`docker-compose.yml`、`Caddyfile`、`scripts/`；健康端点视图＋`urls.py` | F-07（日志）弱依赖 | MEDIUM | FINAL-2 |
| F-10 | production.py 安全族接线：cookie 四项（Q16）、SESSION_COOKIE_AGE=24h、SECURE_SSL_REDIRECT、HSTS 先短后长（Q5）、SECURE_PROXY_SSL_HEADER（Caddy）；NOSNIFF/REFERRER 由 Django 默认已生效，此处仅显式钉值 | NOT_DONE | `src/peiligo/settings/production.py` | F-09（与反代形态对齐） | LOW | FINAL-2 |
| F-11 | CI 流水线：`.github/workflows/`（pytest＋ruff＋secret 扫描＋migration check＋axe）＋分支保护就绪（PRD §23 五强制项入口） | NOT_DONE | `.github/**`、`docs/ci/**` | FINAL-1 全量测试绿 | LOW | FINAL-2 |
| F-12 | 备份与恢复工程：12h DB+media 配套备份、30 天保留、独立副本接口、恢复程序脚本/手册（NFR §5 模板落地） | NOT_DONE | `scripts/**`、`docs/ops/**` | F-09 | MEDIUM | FINAL-2 |
| F-13 | 监控接线：磁盘 20%/10% 检查（Q20）、备份新鲜度、调度监控（NF-16）、登录观测（axes 数据源）、拨测对接 | NOT_DONE | `scripts/**`、`docs/ops/**` | F-05（axes）、F-09、F-12 | MEDIUM | FINAL-2 |

**批次聚合依据**：FINAL-1＝仓库内应用代码（互相无文件冲突、不依赖部署环境）；FINAL-2＝生产工程文件（共享 `scripts/`/编排载体、互为接线对端，且 CI 宜收口全量测试）。两批即可覆盖全部 IMPLEMENTATION_GAP，无需更细拆分。

---

## 8. HIGH_RISK_GAPS（须独立审查重点抽查）

1. **F-01 E1 接线**——ADR-0006 Accepted 的语义承诺；接线错误＝全站搜索行为静默漂移（E1→E2），且「选型 Accepted」易被误读为「已生效」（NFR §11 状态边界）。
2. **F-05 登录治理**——Q4 已定后台公网可达，无限速＋密码策略未提级＝暴力破解暴露面；Q3 参数为 Human 确认值，实现不得走样。

（其余 MEDIUM：F-02/F-03/F-09/F-12/F-13；LOW：F-04/F-06/F-07/F-08/F-10/F-11。）

---

## 9. PURE_DEVELOPMENT 估计（§16）

- **completed_items**：MB1–MB7 全部＋MB8/9/10/11/13/14 主体（18 步中 7 步全完成、6 步大半完成）；G2 二十五项 Gap 中 0 项完整闭环
- **remaining_items**：13 项（F-01…F-13；其中 F-08 条件项）
- **estimated_batches**：**2**（FINAL-1 应用层 → FINAL-2 生产工程）

**§16 问句直答**：如果只算开发，不算测试、人工验收、部署、试运行、备份演练——**还剩 2 个开发批次**。

---

## 10. 最终检查可行性（§21 问 15）

是。FINAL-1＋FINAL-2 合并且 CI 绿后，剩余工作全部落入 §6.2–§6.4 三类非开发清单（验证/部署/运维），即可进入「最终全项目检查」（含 G3 式全量门禁）；检查中须按底册执行 E1 复验门、性能与无障碍验证，不得因实现完成而豁免。

---

## 11. 边界声明

- 本审计未修改任何生产代码/配置/依赖；未执行 commit/merge/push（`git status` 核验见 Handoff）
- 判定全部基于 `main@3dd0caa` 实读证据；G2 结论凡与代码不符处以本文件 §4.1 更正为准
- 「DONE」不豁免任何 VALIDATION_ONLY 义务（NFR §0.1 状态口径不变）
