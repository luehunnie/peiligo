# Wagtail 上游框架只读审计报告（版本核验 · 扩展点映射 · 结构建议）

| 项 | 内容 |
| --- | --- |
| 审计对象 | `/Users/chenjunxian/vscode_projects/Wagtail/wagtail`（本地 clone，origin=`https://github.com/wagtail/wagtail.git`，注意外层目录还包了一层 `Wagtail/wagtail`） |
| 需求基线 | `/Users/chenjunxian/vscode_projects/peiligo_restart/docs/PRODUCT_REQUIREMENTS.md`（457 行，已完整阅读） |
| 审计日期 | 2026-08-15 |
| 审计方式 | 只读：git 命令、源码/文档阅读、PyPI 与官方发布页在线核验。未修改任何被审计文件，未编写业务实现，未接触 PVE/服务器 |
| 范围纪律 | 仅覆盖 PRD §26 审计项 2（Wagtail 上游版本、扩展点与推荐项目结构）；不扩大 V1，不替代决策门 |

---

## 1. 本地仓库状态（事实，命令输出为证）

- **远端**：`git remote -v` → `https://github.com/wagtail/wagtail.git`（官方上游，fetch/push 同址）。
- **分支**：本地仅 `main`，与 `origin/main` 同步；远端含 `stable/*.x` 长期分支（`git branch -a`）。
- **HEAD**：`8885364d5c`（"Add link and credits to API v3 release note"，2026-08-14 09:22 +0100）——clone 时间戳 2026-08-15 12:15，即**今日官方 main 快照**。
- **版本常量**：`wagtail/__init__.py:9` → `VERSION = (8, 0, 0, "alpha", 0)`，即 main 为 8.0 发布后的开发线。
- **标签**（`git for-each-ref --sort=-creatordate refs/tags`）：

| 标签 | 日期 |
| --- | --- |
| `v8.0rc1` | 2026-08-13（**预发布，非稳定版**） |
| `v7.4.2` | 2026-06-15（当前最新稳定补丁） |
| `v7.3.3` / `v7.0.8` | 2026-06-15（同日安全补丁） |
| `v7.4` | 2026-05-05（**7.4 LTS 特性版本**） |

- `git merge-base --is-ancestor v8.0rc1 HEAD` → 非 ancestor（main 已进入 8.0 final 后续开发）。
- 仓库内存在他人先前留下的 `.venv-run/`（Python 3.11，装好依赖）与 `.claude/`——均未跟踪、未改动；本次审计只读取了其中安装的 `modelsearch` 包源码作为搜索后端证据。

## 2. 版本核验（截至 2026-08-15，官方证据）

### 2.1 最新稳定版 = Wagtail 7.4.2；8.0 尚未正式发布

- PyPI 官方页 https://pypi.org/project/wagtail/ ：最新稳定版 **7.4.2（2026-06-15）**；`8.0rc1`（2026-08-13）标注为 pre-release。
- 官方发布日程 https://github.com/wagtail/wagtail/wiki/Release-schedule ：**8.0 计划 2026-08-25 发布**（距今 10 天），8.1 计划 2026-11-02。
- 与本地 tag 证据一致：clone 自今日上游，仍只有 `v8.0rc1`，无 `v8.0`。

### 2.2 7.4 是 LTS，支持窗口最长

- `docs/releases/7.4.md:1-9`（本地仓库）："Wagtail 7.4 is designated a Long Term Support (LTS) release…up until the next LTS release"。
- LTS 政策 `docs/releases/release_process.md:49-63`：LTS 约每 4 个特性版本一次、支持 6 个特性版本周期（约 18 个月，含 6 个月重叠），且保证至少兼容一个 Django LTS。
- 官方日程页：**7.4 LTS 安全/数据修复支持至 2027-11-02**；对比：8.0（特性版本）安全支持仅至 **2027-02-02**，活跃支持至 2026-11-03；7.0 LTS 支持止于 2026-11-02（即将到期，不可选）。

### 2.3 官方兼容矩阵（`docs/releases/upgrading.md:88-91`）

| Wagtail | Django | Python |
| --- | --- | --- |
| 8.0（RC） | 5.2, 6.0 | 3.10–3.14 |
| **7.4 LTS** | **5.2, 6.0** | **3.10–3.14** |

- 与 `pyproject.toml:15,23-30,35`（requires-python `>=3.10`；classifiers 仅 Django 5.2/6.0；依赖 `Django>=5.2`）及 `README.md` 兼容段一致；v7.4.2 tag 内容相同（`git show v7.4.2:pyproject.toml` 已核对）。
- **Django 6.1 已被官方撤回支持**：main 上提交 `024a2f07f5`（2026-08-13，"Retract formal Django 6.1 support"，原因 django-ninja 1.6.2 上界 `Django<6.1`），改回 5.2/6.0——选 Django 6.1 无 Wagtail 支持。
- Django 官方支持表 https://www.djangoproject.com/download/ （2026-08 现状）：**5.2 LTS 扩展（安全）支持至 2028-04**；6.0 主流支持已止于 2026-08-04、扩展支持至 2027-04；6.1 已发布（最新官方版）。
- Python EOL（https://devguide.python.org/versions/ ）：3.10 → 2026-10（**即将到期，不选**）；3.11 → 2027-10；3.12 → 2028-10；3.13 → 2029-10。

### 2.4 版本决策候选（供 PRD 决策门 2 裁决）

| 候选 | 组合 | 支持 runway | 评估 |
| --- | --- | --- | --- |
| **A（推荐）** | **Wagtail 7.4.2 LTS + Django 5.2 LTS + Python 3.13** | Wagtail→2027-11、Django→2028-04、Python→2029-10，三层重叠最长 | 唯一"双 LTS"组合；符合 PRD §17 季度升级、月度安全检查的低维护节奏；Python 3.13 为当前稳定版且离 EOL 最远（3.14 亦可用，但生态包兼容面略保守） |
| B | Wagtail 8.0.x（8-25 后）+ Django 6.0 + Python 3.13/3.14 | 8.0 安全支持仅至 2027-02，2026-11 就需升 8.1 | 收益＝API v3（Django Ninja）、自定义基类 Page 模型、全局权限策略注册表；但 8.0 未发布、V1 无前后端分离诉求，升级压力与 PRD 维护节奏不匹配。可作为 V2 演进点 |
| C | 7.4.2 LTS + Django 6.0 | Django 6.0 扩展支持 2027-04 止 | 短于 5.2 LTS，且 V1 不需要 6.0 特性；无优势 |

## 3. PRD 需求 → 官方扩展点映射（逐项，均无需改核心）

### 3.1 内容模型（PRD §7）

- **通知/文章双类型**（§7.1/7.2）：两种独立 Page 模型，`parent_page_types` 限制只能挂在"校园纪事/校园活动"板块下——标准官方模式，无核心改动。
- **受控富文本与组件**（§7.7）：`StreamField` + 内建 Block 全家桶（`wagtail/blocks/field_block.py:160-976`：CharBlock/TextBlock/RichTextBlock/URLBlock/Date/Choice/Chooser 等）；`RichTextBlock(features=[...])` 按字段收窄可用功能（`field_block.py:747-762`），普通部门账号不给 RawHTMLBlock 即满足"不得输入任意 HTML/CSS"；表格用 `wagtail.contrib.table_block`。PRD 已点名 StreamField，与官方推荐一致。
- **受控标签**：核心依赖 `django-taggit>=5.0,<7`（`pyproject.toml:38`），配 `ClusterTaggableManager` + 受控词表即可。
- **活动结构化字段**（§7.3）/ **学习资料受控维度**（§7.4）/ **软件与工具字段**（§7.5）/ **校园指南统一字段**（§7.6）：四类形态两种官方载体可选——
  - **Page**：需要独立 URL、独立模板、加入树形导航时；
  - **Snippet + SnippetViewSet**：结构化记录 + 聚合列表页（指南目录、软件列表）更适合；Snippet 可按需混入 `DraftStateMixin`/`RevisionMixin`/`PreviewableMixin`/`LockableMixin` 获得草稿、修订、预览、锁定、**发布计划与过期**（`docs/topics/snippets/features.md:210-250`，明确含 PublishingPanel 排程与 `publish` 权限自动创建）。
  - 具体每类选 Page 还是 Snippet 属技术设计决策（见 §7 决策门 G4），两者都是官方一等公民。
- **外链确认跳转页**（§7.5）：自定义 Django 视图 + 模板，收集 `?next=` 参数渲染域名/来源/时间/声明——纯项目代码，无核心改动。

### 3.2 部门权限（PRD §4.3、§5）

- **不自建用户中心**：直接用 Wagtail/Django 认证（PRD 已定），部门账号 = Django Group + Wagtail 权限。
- **页面树权限**（`docs/topics/permissions.md:13-40`）：Add/Edit/Publish/Lock/Unlock 挂在树节点并向子树传播；**Add 权限 = 只能编辑/删除自己拥有的页面**——"部门只能维护本部门内容"天然成立。
- 结构选项（内容模型冻结前必须定，见决策门）：
  - **(a) 板块下按部门建隐藏容器节点**：权限挂在各部门节点上，树形传播自动隔离；这些节点是权限容器/路由分组，前台不渲染成"部门主页"，产品语义仍满足 §6"不建部门主页"；
  - **(b) 扁平结构 + 所有权**：全部内容挂板块节点，部门账号仅靠 ownership 编辑自己内容；但板块节点上的 **Publish 权限允许部门发布/下线该节点下任何部门的页面**（Publish 与 Edit 独立），存在横向越权面，需 `construct_explorer_page_queryset`（`docs/reference/hooks.md:1087`）过滤可见性并接受残余风险——(a) 更干净。
- **Snippet 侧部门隔离**：Snippet 默认权限是模型级（add/change/delete 全有全无，`wagtail/snippets/permissions.py`）；按部门隔离需自定义 `permission_policy`（`wagtail/admin/viewsets/model.py:124` 属性，7.4.2 同样存在；8.0 另有全局 `wagtail.permissions.register_permission_policy()` 注册表）+ `SnippetViewSet.get_queryset` 过滤（`docs/topics/snippets/customizing.md:69-100`，含 `list_filter`）——官方扩展点，自写少量代码。
- **图片/附件集合**：Collections 三层权限（`permissions.md:43-67`），可为共享素材做粗粒度隔离。
- **后台限校园网/VPN**（§5）：反向代理 ACL 或自写 Django 中间件按 `REMOTE_ADDR`/网段拦截 `/admin/`——配置级，无核心改动。
- **强密码/限速/强制改密**：Django `AUTH_PASSWORD_VALIDATORS`、登录限速（django-axes 等）、`WAGTAILADMIN` 外围配置；密码重置走 Django auth + 管理员操作。
- **修订历史**（§5）：内建 Revisions 记录操作者与时间（`wagtail/models/revisions.py`），另有 log_actions 审计日志可查。

### 3.3 发布、归档与到期（PRD §8）

- **预约发布/到期自动下线**：`DraftStateMixin.go_live_at` / `expire_at`（`wagtail/models/draft_state.py:35-38`，Page 与 Snippet 通用）；到期由 `publish_scheduled` 管理命令处理，官方建议每小时运行（`docs/reference/management_commands.md:19-24`）——容器环境用 cron/独立任务容器，无核心改动。
- **expired 语义**：到期执行的是带 `set_expired=True` 的 unpublish（`wagtail/actions/unpublish.py:56-57`），内容保留、前台与默认搜索不再出现。
- **注意张力**：PRD §7.1 要求到期通知"保留在历史归档及站内搜索中"，而 Wagtail 默认前台/搜索只出 live 内容——归档列表页与归档搜索需自定义 queryset 包含 `expired=True` 并标注"已过期"。这是视图/模板级自定义（项目代码），不是核心改动，但要写进验收测试（PRD §21/§23）。
- **下线/归档默认、永久删除仅总管理员**：unpublish（部门可对自己内容）+ delete 权限只授予管理员组——纯权限配置。
- **首页置顶/推荐位仅总管理员**：置顶字段用 `FieldPanel(permission=...)` 面板级权限（`docs/topics/permissions.md:93-102`）或独立 Snippet + 权限隔离；首页推荐位数量固定、带起止时间，用独立模型（含 `go_live_at`/`expire_at`）即可。

### 3.4 搜索（PRD §10，决策门 4）

- **首选 PostgreSQL 后端**：`wagtail.search.backends.database`（需 `INSTALLED_APPS` 加 `django.contrib.postgres`，`docs/topics/search/backends.md:58-61`）；7.4 起搜索实现拆分为 `modelsearch` 包（`pyproject.toml:54` `modelsearch>=1.3.2,<1.4`，`wagtail/search/backends/database/postgres/postgres.py:1` 为纯转发），配置文档指向 https://django-modelsearch.readthedocs.io/ 。
- **可配 `SEARCH_CONFIG`**（modelsearch `backends/database/postgres/postgres.py:960`）——控制 PG FTS 的分词配置。
- **中文风险（本审计最高风险项）**：PG 内建 text search 配置（english/simple）无中文分词能力，中文整句会成单 token；真正中文分词需 PG 扩展（zhparser/scws 或 pg_jieba），属于**数据库服务器运维依赖**。退路：DATABASE 后端的 fallback 匹配用 `icontains` 子串查询（modelsearch `backends/database/fallback.py:59,85`），对中文子串天然友好但无相关度排序；另有 trigram 模糊匹配（`postgres.py:63-65`，需 pg_trgm 扩展）。**与 PRD §10 一致：必须用真实中文数据 PoC 后再定**，建议三个实验：① DB 后端 icontains；② PG 后端 + `SEARCH_CONFIG='simple'`；③ PG 后端 + zhparser。只有 ①/② 不达标才评估独立搜索服务（Elasticsearch/OpenSearch 后端官方支持：`wagtail/search/backends/` 目录 elasticsearch7/8/9、opensearch2/3）。
- **筛选维度**（板块/部门/类型/类别/标签/指南结构化字段）：搜索视图里 QuerySet filter + facet 组合——项目模板自带 `search/views.py` 起点，项目代码实现。

### 3.5 前台模板与 SEO（PRD §12）

- **服务端 Django 模板是官方一等公民**：`docs/topics/writing_templates.md`；项目模板自带 `base.html`、`404/500`、search app。对 PRD 决策门 1：站内无登录、无交互前端、无 App，服务端模板在部署、预览、缓存、无障碍（WCAG 2.2 AA）上路径最短。
- **前后端分离选项**：7.4 只带只读 REST API v2（DRF）；8.0 新增 API v3（Django Ninja + Pydantic，`docs/releases/8.0.md` "What's new"首条）。若门 1 选分离，8.0 的 API v3 才是完整载体——又一个"V1 用 7.4 服务端模板、未来再评估"的论据。
- **单篇 noindex**：核心无内建字段；标准做法 = 页面模型加布尔字段 + 模板输出 `<meta name="robots">`——项目代码，无核心改动。
- **SEO 基建**：`wagtail.contrib.sitemaps`（站点地图）、`wagtail.contrib.redirects`（重定向管理）、`wagtail.contrib.settings`（站点级设置）均为官方 contrib，直接启用。

### 3.6 后台定制（PRD §4、§13）

- **Hooks 体系**：`docs/reference/hooks.md`（1669 行官方参考）——`register_admin_urls`（:304）、`construct_main_menu`、`construct_explorer_page_queryset`（:1087）、`register_rich_text_features`（:519）等，覆盖后台菜单、页面列表、编辑器扩展。
- **ViewSets**：7.x 的模型管理界面定制层（`docs/reference/viewsets.md`），Snippet/模型的列表列、过滤器、模板、权限策略皆可覆写。
- **后台简体中文开箱即用**：`wagtail/locale/zh_Hans/LC_MESSAGES/django.po/.mo` 完整翻译存在——满足 PRD §13"V1 仅简体中文"的后台体验。
- **附件限制**（§11）：`WAGTAILDOCS_CONTENT_TYPES` 等设置（`docs/reference/settings.md:537` 起）做白名单；图片经 Willow 处理。"伪造 MIME 检查"的严格程度需技术设计验证（扩展名 + content-type 白名单为主，魔数级校验可能需少量自定义）——列入未知项。

### 3.7 部署与容器（PRD §16）

- 官方项目模板自带**多阶段 Dockerfile**（`wagtail/project_template/Dockerfile`：builder/runtime 两段、`python:3.14-slim-bookworm`、gunicorn、非 root 用户、EXPOSE 8000）——容器化是官方支持路径；注意模板 `CMD` 把 migrate 与启动合并，官方自己标注为非最佳实践，生产应拆分迁移步骤。
- `publish_scheduled` 每小时任务需在容器编排里显式安排（cron 容器或宿主 cron）。
- 数据库仅 PostgreSQL（PRD 已定）；模板 settings 拆分 `base/dev/production` 与生产 `ManifestStaticFilesStorage`（`project_template/project_name/settings/production.py:9`）符合"配置外置"要求。

## 4. 官方推荐项目结构（`wagtail/project_template/`，`wagtail start` 生成）

```
project_name/
  settings/{base,dev,production}.py   # 环境拆分，密钥走环境变量
  urls.py  wsgi.py  templates/{base,404,500}.html  static/
home/      # Page 类型示例 app（models + 自己的 migrations/templates）
search/    # 搜索 app（views + 模板）——PRD 搜索的官方起点
Dockerfile # 多阶段官方容器化
```

**对 peiligo 的落地建议**（供骨架设计，不替代决策门 3）：
- 以 `wagtail start` 生成骨架后按域拆 app，例如：`notices`（通知/文章/活动 Page 类型）、`resources`（学习资料/软件工具，Snippet 或 Page）、`guides`（校园指南 Snippet）、`departments`（部门模型/岗位账号治理）、`frontend`（公共模板、静态资源、搜索视图、跳转确认页）。
- 每个内容模型独立 `models.py` + 迁移；部门字段统一 FK 到 `departments.Department`（前台只展示部门名称，PRD §4.3）。
- 并行审计（`audit-report-old-peiligo.md`）已确认旧站为 **FastAPI + Vue 3 + Element Plus**，与 Wagtail/Django 无共享栈；"原结构重构"路径等于放弃 PRD 技术基座，故**结构建议倾向"同仓库新骨架"**——正式结论归决策门 3，且旧前端资产仅静态/模板层可评估复用。

## 5. 需求满足方式汇总

| PRD 需求 | 满足方式 | 需要自写代码量 |
| --- | --- | --- |
| 内容模型（§7 全部） | Page + StreamField / Snippet + Mixin | 仅模型/模板定义 |
| 部门只能管本部门（§4.3） | 页面树权限 + ownership（方案 a 容器节点）/ Snippet 自定义 permission_policy | 小–中（权限策略类） |
| 预约发布/到期归档（§7.1、§8） | DraftStateMixin + publish_scheduled | 配置 + 归档视图 |
| 到期内容保留在归档与搜索（§7.1） | 自定义 expired 查询视图 | 小（有验收测试） |
| 搜索+筛选（§10） | wagtail.search（DB/PG 后端）+ 自定义视图 | 中（含 PoC） |
| 前台（§9、§12、§13） | Django 模板 + contrib(sitemaps/redirects/settings) | 模板工作量为主 |
| 后台定制/中文化（§13） | hooks + ViewSets + zh_Hans 内建翻译 | 小 |
| 后台限校园网（§5） | 反代/中间件 | 小 |
| 容器化（§16） | 官方 Dockerfile 模式 | 小 |
| 外链确认页（§7.5） | 自定义视图 | 小 |
| 附件白名单（§11） | WAGTAILDOCS 设置 + 校验补充 | 小 |

**结论：PRD V1 全部功能均可在不修改 Wagtail 核心的前提下，用官方扩展点（模型定义、权限配置、Mixin、hooks、ViewSets、contrib、后台设置）实现。** 未发现任何必须改核心或打补丁的需求。

## 6. 风险清单

- **R1 中文搜索质量（高，对应决策门 4）**：PG FTS 无中文分词；zhparser/jieba 属数据库扩展运维依赖（Ubuntu 需装 scws/zhparser 包并改 PG 配置）；icontains 退路无相关度排序。必须真实数据 PoC，本审计不能替代。
- **R2 Publish 权限横向越权面（中）**：扁平结构下板块节点 Publish 权限可发布/下线他部门页面；用方案 (a) 部门容器节点规避，并写进 §23 权限测试。
- **R3 Snippet 无 per-instance 权限（中）**：部门隔离依赖自写 permission_policy——官方扩展点但属自定义代码，需完整测试覆盖（"部门账号不能修改其他部门内容"是 §23 必测项）。
- **R4 expired 内容与默认 live-only 搜索/前台的张力（中低）**：归档列表/归档搜索需自定义；漏做会直接违反 §7.1 验收。
- **R5 不要用 8.0rc1/首发 8.0.0 做 V1 基线（低概率高影响）**：8.0 计划 8-25 发布，距 V1 冻结太近、无补丁沉淀；且 8.0 支持窗口短（安全支持 2027-02 止）。
- **R6 modelsearch 为新拆分包（低）**：7.4 搜索实现刚迁移到独立包（1.3.x），文档主体已迁移到其 readthedocs；受 Wagtail LTS 支持承诺覆盖，但升级时需关注两者版本联动。
- **R7 附件"伪造 MIME"校验深度（低）**：官方以扩展名/content-type 白名单为主，魔数级校验可能需少量自定义——技术设计阶段定。
- **R8 Python 3.10 即将 EOL（2026-10）（低）**：不选 3.10，避免上线即临近 EOL。

## 7. 未知项（本审计无法从证据直接确定）

- U1 PostgreSQL 生产库能否安装 zhparser/scws（校园运维约束）——直接决定搜索 PoC 方案 ③ 可行性。
- U2 部门数量与内容量级（影响搜索 PoC 数据集规模与 §14 性能目标测量口径）。
- U3 8.0.0 正式发布（计划 2026-08-25）后的实际补丁节奏——仅影响候选 B 评估，不影响推荐 A。
- U4 旧前端静态资产可复用比例（归并行审计与决策门 3，本报告仅引用其结论性事实"旧栈为 FastAPI+Vue"）。
- U5 生产服务器反向代理/证书/资源条件（PRD 决策门 5，待校方）。
- U6 校方对第三方软件资源的合规范围（PRD 决策门 7）。

## 8. 决策门（提交项目负责人，不得由开发代理代决）

- **G1（=PRD 门 2）Wagtail 版本**：推荐冻结 **Wagtail 7.4.2 LTS + Django 5.2 LTS + Python 3.13**；若项目负责人倾向 8.0 新特性（API v3/自定义基类 Page），需接受 2026-11 升 8.1 的节奏并等 8.0 首个补丁——默认不推荐。
- **G2（=PRD 门 1）前端架构**：本审计证据（无登录前台、无交互需求、WCAG/性能目标、7.4 API 只读 v2）支持**服务端模板**；需正式裁决。
- **G3（=PRD 门 3）项目骨架**：旧栈与 Wagtail 无共享代码路径，证据倾向**同仓库干净 Wagtail 骨架**（`wagtail start`）；需正式裁决。
- **G4（本审计新增，属内容模型设计前置）权限树结构**：方案 (a) 部门容器节点 vs 方案 (b) 扁平+所有权过滤——影响 URL 结构与权限模型，须在内容模型冻结前定。
- **G5（=PRD 门 4）中文搜索**：按 §3.4 三方案 PoC 后定；PoC 前不得采购/搭建独立搜索服务。

## 9. 结论

截至 2026-08-15，Wagtail 最新稳定版为 **7.4.2（LTS 线，2026-06-15）**，8.0 处于 RC（计划 8-25 发布）；官方兼容矩阵给出 7.4 LTS = Django 5.2/6.0 + Python 3.10–3.14，结合 Django 5.2 LTS（支持至 2028-04）与 Python 3.13（EOL 2029-10），推荐版本组合 **7.4.2 LTS + Django 5.2 LTS + Python 3.13**。PRD V1 的内容模型、部门权限、发布/归档、搜索、前台模板与后台定制**全部可经官方扩展点实现，无需修改 Wagtail 核心**；唯一高不确定项是中文搜索质量（已有三方案 PoC 路径），另有两项需产品/技术共同确认的结构决策（部门权限树形态、每类内容 Page vs Snippet）。

---

### 附：关键证据索引

| 证据 | 位置 |
| --- | --- |
| 8.0 开发版常量 | `wagtail/__init__.py:9` |
| 兼容矩阵表 | `docs/releases/upgrading.md:88-91` |
| 7.4 LTS 声明 | `docs/releases/7.4.md:1-9` |
| LTS 政策 | `docs/releases/release_process.md:49-63` |
| Django 6.1 撤回 | 提交 `024a2f07f5`（2026-08-13） |
| go_live_at/expire_at | `wagtail/models/draft_state.py:35-38` |
| expired unpublish | `wagtail/actions/unpublish.py:56-57` |
| publish_scheduled 每小时 | `docs/reference/management_commands.md:19-24` |
| 页面权限模型 | `docs/topics/permissions.md:13-40` |
| explorer 过滤 hook | `docs/reference/hooks.md:1087` |
| Snippet Mixin 能力 | `docs/topics/snippets/features.md:210-250` |
| ViewSet permission_policy | `wagtail/admin/viewsets/model.py:124`（7.4.2 同位） |
| Snippet list_filter/get_queryset | `docs/topics/snippets/customizing.md:69-100` |
| RichTextBlock features | `wagtail/blocks/field_block.py:747-762` |
| PG 后端与 SEARCH_CONFIG | `docs/topics/search/backends.md:58-61`；modelsearch `postgres.py:960` |
| icontains fallback | modelsearch `fallback.py:59,85` |
| 后台中文翻译 | `wagtail/locale/zh_Hans/LC_MESSAGES/django.po` |
| 官方 Dockerfile | `wagtail/project_template/Dockerfile` |
| PyPI 最新稳定 7.4.2 | https://pypi.org/project/wagtail/ |
| 发布日程（8.0=2026-08-25；7.4 LTS 支持→2027-11-02） | https://github.com/wagtail/wagtail/wiki/Release-schedule |
| Django 支持时间表 | https://www.djangoproject.com/download/ |
| Python EOL | https://devguide.python.org/versions/ |
