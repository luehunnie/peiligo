# 旧 peiligo 仓库只读审计报告（V1 需求基线核对 · 前端复用分类 · 骨架路径比较）

| 项 | 内容 |
| --- | --- |
| 审计对象 | `/Users/chenjunxian/vscode_projects/peiligo`（本地 clone，origin=`https://github.com/luehunyo/peiligo.git`） |
| 需求基线 | `/Users/chenjunxian/vscode_projects/peiligo_restart/docs/PRODUCT_REQUIREMENTS.md`（457 行，已完整阅读） |
| 审计日期 | 2026-08-15 |
| 审计方式 | 只读：git 命令、文件阅读、依赖清单核对。未修改任何被审计文件，未执行任何业务实现，未接触 PVE/服务器 |
| 范围纪律 | 仅覆盖 PRD §26 审计项 1（旧仓库与前端复用）；不扩大 V1，不替代决策门 |

---

## 1. 仓库状态（事实，命令输出为证）

- **远端**：`git remote -v` → `https://github.com/luehunyo/peiligo.git`（fetch/push 同一地址）。可见性本地无法判定（未知项 U5，对应 PRD 决策门 6）。
- **分支**：本地 3 个分支——`main`、`feat/m4-admin-auth`（当前分支）、`luehunyo/peiligo-rebuild-audit`；远端仅 `origin/main`。
- **提交历史**：14 个提交，全部集中在 2026-08-12 一天内（`ac0a6f6` M0 脚手架 → `bd85115` M3 合并 PR #4）。线性、干净、无真实业务内容期。
- **标签**：`git tag` 输出为空——**PRD §18 要求的"旧实现只读标签/归档分支"尚未建立**（决策门 G5）。
- **工作区不干净**（审计时 `git status --porcelain`）：
  - 已修改未提交：`.env.example`、`backend/app/config.py`、`backend/requirements.txt`（+27/-1，新增 APP_ENV / SESSION_SECRET / SESSION_MAX_AGE_SECONDS / argon2-cffi）
  - 未跟踪：`backend/app/auth/`、`backend/scripts/create_admin.py`、`backend/tests/test_auth_security.py`、`backend/tests/test_config_session.py`、`backend/tests/test_create_admin.py`
  - 即 **M4（管理员认证）做到一半、零提交**：目前只有 Argon2id hash/verify 无状态函数（`backend/app/auth/security.py:14-28`）与本地建号脚本，无登录端点、无 Session 中间件、无 CSRF（风险 R1，决策门 G4）。
- **仓库体积**：318MB（含 `node_modules`、`.venv`，均被 `.gitignore` 排除，不入库）。
- **`docs/ai/` 不入库**：`.gitignore` 明确忽略 `docs/ai/`，阶段汇报仅存本地（交接文档 `docs/ai/handoffs/M2_...` 与三份阶段汇报均在本地）。

## 2. 技术栈与依赖（事实）

**后端**（`backend/requirements.txt`、`requirements-dev.txt`）：
- FastAPI（>=0.115,<1.0）+ uvicorn[standard] + python-dotenv + SQLAlchemy 2.x（同步 Engine/Session）+ psycopg3（PostgreSQL 专用驱动）+ Alembic + argon2-cffi（M4 未提交新增）
- 开发依赖：pytest、httpx、ruff（`pyproject.toml`：target py311，line-length 100，规则 E/F/I/UP/B）
- **与 PRD 技术基座（Wagtail/Django，PRD 第 10 行）完全不同框架**——这是骨架路径决策的核心事实。

**前端**（`frontend/package.json`）：
- Vue 3.5 + TypeScript 5.9 + Vite 8（rolldown）+ vue-router 5 + **Element Plus 2.14.3**
- devDependencies 仅构建链：**无任何测试框架（无 vitest/jest/playwright）、无 ESLint/Prettier、无无障碍检测工具**
- Element Plus 全量注册（`src/main.ts:2-9`，含 `element-plus/dist/index.css` 全量 CSS），但实际只在 1 处使用（`src/pages/NotFoundPage.vue:3` 的 `ElButton`）；M3 汇报记录其生产 chunk 约 1017kB（>500kB 告警，非阻断遗留）。属**重依赖近零使用**（未知项 U1：无文档解释为何引入；风险 R3）。

**CI/部署（事实：全部缺失）**：
- 无 `.github/workflows`、无任何 yml；无 Dockerfile / docker-compose / Caddy / Nginx 配置（`find` 无命中）。README 自述"本阶段不包含数据库、登录、后台、搜索、Docker、Caddy、Element Plus 页面或正式部署"（其中数据库/搜索等已在 M2/M3 部分落地，部署仍是零）。
- 前后端唯一耦合点：Vite 开发代理 `'/api' → http://127.0.0.1:8000`（`frontend/vite.config.ts:7-9`）。FastAPI 未配置 CORS、未托管前端静态文件——**生产部署形态从未定义**。
- 环境变量仅 5 个（`.env.example`）：DATABASE_URL、TEST_DATABASE_URL、APP_ENV、SESSION_SECRET、SESSION_MAX_AGE_SECONDS。

## 3. 前后端结构与耦合（事实）

```
Vue3 SPA ──fetch /api/contents──▶ FastAPI(3端点) ──SQLAlchemy同步──▶ PostgreSQL(peiligo_dev)
```

- **后端仅 3 个端点**：`GET /api/health`、`GET /api/contents`（全量已发布列表，无分页/无搜索/无排序参数，`backend/app/api/contents.py:50-59`）、`GET /api/contents/{id}`（draft/offline/不存在统一 404，`contents.py:62-79`）。无任何写端点。
- **数据模型仅两张表**（Alembic head `fd086137d596`，2026-08-10）：
  - `contents`（`backend/app/models/content.py:21-62`）：id、content_type（CHECK 白名单五板块）、title、summary、body(TEXT 整段)、source_name、source_url、extra_data(JSONB)、status（CHECK：draft/published/offline）、三个 timestamptz。**没有：有效期/到期字段、部门字段、标签字段、预约发布、置顶、图片、附件、修订历史**。
  - `admin_users`（`backend/app/models/admin_user.py:11-25`）：username 唯一、password_hash、is_active、created_at、last_login_at。**没有：角色、部门归属、强制改密标记**——即 PRD 的"部门岗位账号 + 本部门内容隔离"概念在整个代码库中不存在。
- **契约冻结在三处重复**（风险 R7）：DB CHECK（`content.py:49-58`）、TS 类型 `ContentStatus = 'draft' | 'published'`（`frontend/src/types/content.ts:15`，**与后端 'offline' 已经漂移**，风险 R6）、板块配置 `CONTENT_TYPE_OPTIONS`（`content-types.ts:11-37`）与 `CONTENT_EXTRA_FIELDS`（`content-extra-fields.ts:18-44`）。M3 汇报§9 自认 seed 的 extraData 键与配置口径不一致。
- **搜索/筛选现状**：纯前端内存过滤——拉全量列表后在浏览器过滤（`ContentListPage.vue:92-114` 关键词 `toLowerCase().includes()` 匹配标题+摘要+正文；板块 chip 过滤），首页 `HomeRecentContents` 另行再拉一次全量。**后端无搜索端点、无中文分词、无分页**；无部门/类别/标签/指南结构化筛选（PRD §10 的核心要求全部缺失，属决策门 G9/PRD 决策门 4 的验证对象）。
- **硬编码环境耦合**（风险 R5，阻碍 CI 与容器化）：`backend/tests/conftest.py:20-24` 硬断言测试库必须 `127.0.0.1:5432/peiligo_test/peiligo_test_user`；`create_admin.py:22-45` 与 `seed_dev_contents.py` 的安全护栏硬编码仅允许本地 `peiligo_dev/peiligo_dev_user`。护栏工程质量好，但取值需参数化才能进 PRD §23 要求的 CI。
- **测试现状**：后端 49 个 `def test_`（37 个已提交 = M2 的 21 + M3 的 16；12 个属 M4 未提交），事务回滚隔离、不打印凭据，质量好。**前端 0 测试、0 CI**（PRD §23 的前端测试/构建/无障碍 CI 门禁不存在）。

## 4. PRD V1 逐项核对（重点章节）

> 图例：✅ 已满足｜🟡 部分满足/需改造｜❌ 缺失｜⛔ 与 PRD 冲突

| PRD 条目 | 旧项目现状 | 判定 | 证据 |
| --- | --- | --- | --- |
| §6 五板块：校园纪事/校园活动/学习资料/软件与工具/校园指南 | 五板块值存在，但 3 个中文名不一致：院内逸事≠校园纪事、软件资源≠软件与工具、学院指南≠校园指南 | 🟡 | `content-types.ts:14-36` vs PRD:97-101 |
| §6 部门=作者元数据、可筛选、无部门主页 | contents 无部门字段，仅可选 `source_name` 文本；无部门筛选 | ❌ | `content.py:29` |
| §7.1 通知：有效期、到期自动退出、预约发布 | 无 expire_at、无归档逻辑、无定时发布 | ❌ | `content.py:21-62` 全字段 |
| §7.2 通知与文章两种独立类型 | 单一 Content 模型混装五板块（PRD 明令"不通过单一模型强行混用"） | ⛔ | `content.py:21`；PRD:125 |
| §7.3 活动结构化字段（起止时间/地点/线上标记/报名链接/三态状态） | extraData 仅 eventTime(自由文本)/eventLocation/organizer；无结构化时间、无状态计算 | ❌ | `content-extra-fields.ts:24-28` |
| §7.4 学习资料受控维度（学科/类型/标签） | courseName/resourceType/applicableStage 均自由文本，非受控分类法 | ❌ | `content-extra-fields.ts:29-33` |
| §7.5 软件与工具字段 + **统一确认跳转页** | platforms/softwareVersion/licenseType 近似；跳转页不存在——详情页外链直接 `target=_blank` 跳转 | ❌（跳转页）/🟡（字段） | `ContentDetailPage.vue:167-175` |
| §7.6 校园指南 9 个统一字段（含责任单位/维护方式/最后确认日期） | extraData 仅 targetAudience/guideTopic/applicableSemester，字段集完全不同 | ❌ | `content-extra-fields.ts:39-43` |
| §7.7 StreamField 受控富文本组件、禁任意 HTML | body 为 TEXT 按空行切段纯文本渲染；无图片/附件/表格 | 🟡（纯文本天然安全，能力缺失） | `contents.py:24-30`、`ContentDetailPage.vue:145-153` |
| §4-5 权限：总管理员+部门岗位账号、本部门隔离、Wagtail 自带认证 | 仅单表 admin_users，无角色/部门/隔离/登录流程（M4 半成品未提交） | ❌ | `admin_user.py:11-25`；`git status` |
| §8 发布治理：免审批、置顶仅总管理员、默认归档不删除、邮件纠错带标题和地址 | status 仅 draft/published/offline；无置顶、无归档态、无预约；纠错邮箱未定（`contactEmail = '待项目方确认'`） | ❌ | `SubmissionPage.vue:12` |
| §9 首页：紧急提示位/最新有效通知/近期活动/推荐位管理 | 首页有 hero+搜索+五板块入口+近 5 条预览；无紧急提示位、无置顶/推荐位（近期 5 条与"仅有效通知"语义也不同） | 🟡 | `HomePage.vue`、`HomeRecentContents.vue:14`（RECENT_LIMIT=5） |
| §10 站内搜索（标题正文/板块/类型/部门/类别标签/指南结构化 + 无结果提示） | 前端 includes() 过滤标题/摘要/正文 + 板块 chip；有优雅无结果提示；其余全缺；后端零搜索 | 🟡（交互形态在，引擎缺失） | `ContentListPage.vue:92-114,219` |
| §11 附件上传与校验 | 无任何上传能力/字段/接口 | ❌ | 全库无 file/upload 字段 |
| §12 SEO（默认可收录、单篇 noindex）、匿名最小化统计 | CSR SPA 无 SSR/预渲染/meta 管理/noindex；无统计 | ❌ | `main.ts`（纯 SPA 挂载） |
| §13 桌面优先+手机可用、WCAG 2.2 AA、学校视觉规范 | 有 skip-link（`App.vue:8`）、:focus-visible（`global.css:27-33,157-170`）、aria-current/aria-pressed/role=group 等；但仅 2 处 `@media (max-width:600px)`（`SiteHeader.vue:106`、`ContentListPage.vue:328`）；未做 AA 检查；品牌色 `#2f7a6e`（`tokens.css:13`）非学校 VI，PRD:255 明确旧前端不自动成为设计基线 | 🟡 | 见左列行号 |
| §14 性能（2s 可见/1s 搜索） | 未测；Element Plus ~1017kB chunk 是明确反例 | ❌（未测） | M3 汇报§9 |
| §15 PostgreSQL、媒体本地存储、每日备份 | PostgreSQL 18.4 ✅（本机 Homebrew）；媒体存储/备份为零 | 🟡 | M3 汇报§2 |
| §16 三环境、PVE 测试、Docker、配置外置 | 仅本地开发环境；无容器/反代/HTTPS | ❌ | §2 CI/部署事实 |
| §17 监控 | 无 | ❌ | — |
| §18 旧站策略（真实内容为零、测试数据不迁移、先归档标签） | 确认无真实业务内容：seed 仅 7 条虚构数据且带本地护栏；归档标签未建 | 🟡 | `seed_dev_contents.py:6-13`；`git tag` 空 |
| §23 自动化测试与 CI 门禁 | 后端 49 pytest 质量好；前端 0 测试；CI 0 | 🟡 | §3 测试现状 |
| §20 V1 不做清单 | 旧代码未实现任何越界功能（无评论/点赞/推送/AI/App）；汇报中提过"AI 搜索"属旧路线图设想，**不在 V1，不得顺带实现** | ✅（无越界） | 教师汇报§1"还没做"清单 |

**核对总结**：旧项目完成度 = "公开只读浏览链路"（M1-M3 已合并）+ "认证半成品"（M4 未提交）。对照 V1 必备能力，**所有编辑侧/治理侧/搜索侧/部署侧需求基本为零起点**；公开浏览侧有可观的 UX 与工程资产。

## 5. 前端资产复用分类（直接复用 / 改造复用 / 重新实现）

> 前提：PRD 决策门 1（前端架构：Vue 前后端分离 vs Wagtail 服务端模板）未决。下表"直接/改造"判定尽量给出两种路径下的差异说明。共 2549 行前端源码。

### 5.1 直接复用（机制/内容可近乎原样搬走，与框架无关）

| 资产 | 路径:行 | 说明 |
| --- | --- | --- |
| 设计令牌机制（间距/字号/行高/圆角/阴影/中文字体栈） | `frontend/src/styles/tokens.css:1-60` | 纯 CSS 变量，任何栈直接复制。注意：品牌色 `--brand-color:#2f7a6e`（:13）非学校 VI，按 PRD:255 需以学校视觉规范为准替换色值（机制复用、色值待换） |
| 无障碍外壳模式：skip-link + main 地标 | `frontend/src/App.vue:8-13`；`global.css:157-170`（.skip-link） | 跳转主内容链接 + `#main-content` 地标，直接翻译进 Wagtail base 模板 |
| 焦点可见性样式 | `global.css:27-33`（:focus-visible outline）+ `ContentListPage.vue:166`（aria-pressed）、`SiteHeader.vue`（aria-current） | WCAG 2.2 AA 必需项，可直接沿用写法 |
| 列表页四态交互规格（loading/error+重试/全空/筛选无匹配） | `ContentListPage.vue:174-220`、`ContentDetailPage.vue:104-131` | 作为验收级交互规格文档复用（PRD §10 要求"清晰的无结果提示"） |
| URL 驱动的搜索/筛选状态（?q=&type=，非法值回退全部） | `ContentListPage.vue:66-89,116-139`；`ContentCard.vue:13-21`（携带 q/type 进详情） | 交互规格直接复用：可分享、可刷新、面包屑可复原 |
| 五板块中文描述文案 | `content-types.ts:14-36` | 文案基础可沿用，但 3 个板块名须改 PRD §6 命名（见 §4 表） |
| 后端测试工程范式（事务回滚隔离 + 测试库 URL 硬护栏 + 不打印凭据） | `conftest.py:1-40`、`create_admin.py` 文档串 | 范式可直接移植到 Django/Wagtail 测试（取值参数化，见 R5） |

### 5.2 改造复用（结构/语义可参考，需按 PRD 或目标栈改写）

| 资产 | 路径:行 | 改造点 |
| --- | --- | --- |
| 全局基础样式（盒模型/排版/表单控件/容器） | `global.css:1-229` | 整体可移植为站点基础 CSS；类名与 Element Plus 无关（好消息：业务组件几乎没用 EP） |
| 内容详情页信息结构（面包屑→标题→meta→摘要→正文分段→补充信息 dl→来源） | `ContentDetailPage.vue:88-180` | 结构照搬为 Wagtail 详情模板；"来源"区须按 §7.5 改为**确认跳转页**入口 |
| 内容卡片 / 元信息 / 空状态 / 首页近期列表组件 | `ContentCard.vue`(94行)、`ContentMeta.vue`(51)、`ContentEmptyState.vue`(42)、`HomeRecentContents.vue`(188) | SPA 路径下可改 API 契约后继续用；模板路径下按现有结构重写为模板（组件小、重写成本低） |
| 前端冻结契约 `ContentItem` | `types/content.ts:7-35` | 字段集与 PRD 内容模型差距大（无有效期/部门/标签/预约/附件/图片）；仅作字段映射起点；且 `ContentStatus`(:15) 缺 'offline' 已与后端漂移 |
| API client 错误语义（status 0=网络 / 404 / 5xx 三分 + 不吞异常不回退假数据） | `api/contents.ts:21-58` | 仅 SPA 路径有意义；模板路径下此层消失 |
| 板块专属字段配置驱动机制 | `content-extra-fields.ts:18-44` | 机制（配置驱动、键值类型）可借鉴；字段集按 §7.3/7.4/7.5/7.6 大改（尤其指南 3→9 字段） |
| 投稿说明/关于页文案 | `SubmissionPage.vue:1-60`、`AboutPage.vue`(89行) | 措辞从"向项目方投稿"改为 PRD §4.1/§8 的"纠错/失效链接/版权反馈至统一工作邮箱"，并补 mailto 自动带标题+地址（PRD:202）；邮箱占位 `SubmissionPage.vue:12` 待定（U4） |
| 页脚免责/演示声明结构 | `SiteFooter.vue:9-17` | 结构可沿用；文案仍是"M1 静态原型阶段…非正式网站"（:11-13,17），必须重写（陈旧副本，风险 R11） |
| 头部导航（品牌+导航+aria-current 高亮） | `SiteHeader.vue:7-49` | 结构照搬；副标题写死"M1 静态原型"（:14）须删 |

### 5.3 重新实现（不迁移，在目标栈上重建）

| 资产 | 路径 | 理由 |
| --- | --- | --- |
| 整个 FastAPI 后端（app/、models、schemas、alembic、API 测试） | `backend/` 约 20 源文件 | PRD 技术基座是 Wagtail/Django；内容模型不满足 PRD（§4 表全部 ❌/⛔ 项）；无真实数据可迁移（PRD:312 测试数据不迁移，seed 仅 7 条虚构记录）。功能上仅"只读列表+详情"两个端点 |
| 管理后台全部 UI | `AdminLoginPrototypePage.vue`(69行)、`AdminContentEditorPrototypePage.vue`(141行) | 纯静态原型、零真实功能（页面自述"不会保存密码/数据"）；Wagtail admin + StreamField + 部门权限须全部重来 |
| M4 认证半成品 | `backend/app/auth/security.py`、`create_admin.py`、config session 段 | 框架级替换为 Django/Wagtail 认证（PRD §5 明确"使用 Wagtail/Django 自带认证"）；Argon2id 选型与参数实践可作参考 |
| vue-router 路由层 | `router/index.ts`(59行) | Wagtail 页面树/路由取代；五板块成为页面类型而非前端路由 |
| Element Plus 集成 | `main.ts:2-9`、`NotFoundPage.vue:3` | 全量引入换 1 个按钮，~1017kB 包重（R3）；无论哪条路径都应移除（决策门 G6 记录即可） |
| 搜索实现（前端 includes 过滤） | `ContentListPage.vue:92-114` | PRD §10 要服务端搜索+中文验证；现实现连分页都没有，无迁移价值，仅交互规格（已列入 5.1） |
| Vite 构建链（若选模板路径） | `vite.config.ts`、tsconfig*、package.json | 模板路径下前端构建链大幅缩水或移除；SPA 路径下可保留（属决策门 1 输出） |

**复用比例估算（供决策参考，非承诺）**：2549 行前端源码中，"直接复用"约 300 行当量（tokens/global/a11y 模式/文案规格），"改造复用"约 1200 行当量的结构与规格价值，其余约 1000 行（管理原型、路由、EP、搜索实现）重写。后端复用率在 Wagtail 基座下 ≈ 0（测试范式与安全护栏思路除外）。

## 6. 路径比较：原结构重构 vs 同仓库干净 Wagtail 骨架

> 本节为证据归纳，**最终选择属 PRD 决策门 3，不由本审计代决**。

### 路径 A：在旧结构（Vue3+FastAPI）内重构演进到 V1

- 需自建（Wagtail 上游现成提供）：部门岗位账号+对象级权限隔离、通知/文章双类型、有效期+到期自动归档、预约发布、StreamField 级受控富文本、附件上传与校验、修订历史、管理后台、中文服务端搜索、SEO/SSR 或预渲染。逐条对应 PRD §5/7/8/10/12/23 的测试要求也都要从零写。
- 与 PRD 第 10 行"技术基座 Wagtail/Django"和 §3"优先使用官方扩展机制"直接冲突；选 A 等于项目负责人重开 PRD 技术基线。
- 现有可保留资产主要只剩前端展示层与后端测试范式；编辑侧/治理侧无论如何都是绿地。
- 隐性优势：团队（旧汇报显示为学生团队）对 Vue/FastAPI 已有一轮实操经验（PRD:321 明确"团队熟悉度是重要因素"）；已打通一条真实读链路可继续演进，无需框架切换学习成本。

### 路径 B：同一 `peiligo` 仓库内建干净 Wagtail 骨架（重建分支）

- 与 PRD 第 9 行"现有 peiligo 仓库的重建分支"、§18 逐句吻合（旧实现打只读标签→独立重建分支→验收后替换主分支）。
- 仓库现状支持：历史仅 14 提交/1 天、无真实数据、无标签，归档成本极低；M4 未提交工作区先处置（G4）即可 `git tag` 归档。
- 从旧仓库收割：§5.1 全部 + §5.2 大部（作为模板/规格/文案来源），后端以"测试护栏范式"为经验输入。
- 成本：前端若走模板路径，展示层需按模板重写一轮（组件小、成本低，见 §5.2）；若走 SPA 路径（决策门 1），Vue 组件可多保留一些，但 PRD:321 提醒必须计入 API、预览、缓存、无障碍、部署成本，且 SPA 与 §12 SEO 要求存在结构性张力（R2）。
- 两条路径都要做的事（即真正的工作量所在，与 A/B 无关）：PRD §4 表中全部 ❌/⛔ 项——内容模型、部门权限、归档与预约、跳转页、服务端搜索、附件、部署、监控、备份、CI。

### 证据倾向（供决策门 3 输入）

- 旧后端对 V1 的功能覆盖率极低（两个只读端点），且框架与 PRD 基座不同——留在旧结构内并不能"少写"，编辑侧仍是绿地。
- 旧前端资产中真正有价值的是与框架无关的令牌/样式/无障碍模式/交互规格/文案，这些在路径 B 下同样可以完整收割。
- 因此**证据倾向路径 B**；路径 A 的实质是放弃 PRD 的 Wagtail 基座，需项目负责人显式重开基线，而非默认选项。

## 7. 风险清单

| # | 风险 | 证据 |
| --- | --- | --- |
| R1 | M4 半成品零提交躺在工作区，重建分支建立或归档标签前若不处置，可能丢失或混入重建 | `git status`（§1） |
| R2 | SPA 无 SSR/预渲染/meta 管理，与 PRD §12"默认允许搜索引擎收录"结构性冲突（若决策门 1 选 SPA） | `main.ts` 纯客户端挂载 |
| R3 | Element Plus 全量引入 ~1017kB chunk，与 PRD §14"主要页面 2 秒内可见"相悖 | `main.ts:2-9`、M3 汇报§9 |
| R4 | 全量列表拉取+前端过滤：无分页无中文分词，数据量增长即失效；首页还重复拉一次全量 | `contents.py:50-59`、`HomeRecentContents.vue:33` |
| R5 | conftest/建号/seed 硬编码本地库标识（host/db/user），照搬即阻断 PRD §23 的 CI 与 §16 容器化 | `conftest.py:20-24`、`create_admin.py:22-45` |
| R6 | status 枚举前后端漂移（后端含 offline，前端类型不含）——契约单一事实源缺失的实证 | `content.py:56` vs `types/content.ts:15` |
| R7 | 板块分类法三处重复（DB CHECK/TS 配置/专属字段配置）+ seed 键不一致（M3 汇报§9 自认） | §3 |
| R8 | FastAPI 无 CORS、无静态托管、无 HTTPS/会话中间件——生产形态从未定义 | `main.py:1-12` 全文 |
| R9 | 旧演示数据（7 条虚构 seed）不得进入新系统（PRD:312），重建须全新建库 | `seed_dev_contents.py` |
| R10 | 移动端仅 2 处 600px 断点，PRD:255 要求手机可正常阅读/搜索/筛选，未经验证 | `SiteHeader.vue:106`、`ContentListPage.vue:328` |
| R11 | 陈旧"M1 原型"文案残留在生产可见位置（页脚、头部副标题、首页 hero note），复用时必须清理 | `SiteFooter.vue:11-17`、`SiteHeader.vue:14` |
| R12 | 3/5 板块命名与 PRD 不一致，若沿用旧 slug/文案将造成需求基线漂移 | `content-types.ts:14-36` vs PRD:97-101 |

## 8. 未知项（本审计无法从本地证据确定）

- U1 Element Plus 引入动机（无文档，仅 1 处使用）。
- U2 学校视觉识别规范是否已有可用形态（PRD §13 假设其存在；旧品牌色为自造）。
- U3 正式生产服务器约束（PRD 决策门 5：反代/证书/备份位/规格）。
- U4 统一工作邮箱地址（`SubmissionPage.vue:12` 占位"待项目方确认"；阻塞 §4.1/§8/§7.6 的反馈与投稿通道）。
- U5 origin 仓库当前公开/私有状态（本地不可见；PRD 决策门 6 要求按私有管理）。
- U6 M4 原计划的剩余范围（登录端点/会话中间件/CSRF）——仓库内无计划文档。
- U7 旧 slug（campus-story 等）与 PRD 板块命名（校园纪事等）的映射取舍。
- U8 Vite 8 / Vue Router 5 / TS 5.9 / @types/node 26 均为当前新版本组合，但本机 Node 运行时版本未验证（对路径 B 无影响）。

## 9. 决策门（提交项目负责人，不得由开发代理代决）

1. **G-front（PRD 决策门 1）前端架构**：Vue SPA（挂 Wagtail API）vs Wagtail 服务端模板。本审计输入：SPA 路径可多保留 §5.2 组件（约千行当量），但引入 R2/R3/R8 成本；模板路径复用以规格与样式为主。
2. **G-wagtail（PRD 决策门 2）Wagtail/Django/Python 版本**：属 PRD §26 审计项 2（Wagtail 上游审计），本报告不覆盖。
3. **G-skeleton（PRD 决策门 3）骨架路径**：A 原结构重构 vs B 同仓库干净骨架。本审计证据倾向 B（§6），但 A 的"团队熟悉度"权重（PRD:321）只有项目负责人能评。
4. **G-m4 M4 工作区处置**（新发现，阻塞归档）：`feat/m4-admin-auth` 上的未提交修改/未跟踪文件——提交留档还是废弃？须先决，才能建 §18 归档标签。
5. **G-archive 归档时机**：`git tag` 目前为空，PRD:310 要求重建开始前完成归档。
6. **G-ep Element Plus 移除确认**：无论路径均建议移除，作为变更记录留痕即可。
7. **G-mail 统一邮箱地址**：U4，阻塞反馈/投稿链路与相关页面文案。
8. **G-search 中文搜索验证方案**（PRD 决策门 4）：旧系统无任何服务端搜索可继承，验证须在新骨架上以真实中文数据执行。
9. **G-vis 仓库可见性**（PRD 决策门 6）与 G-prod 生产服务器（决策门 5）：维持待确认状态。

## 10. 结论

1. 旧 `peiligo` 是一个 2026-08-12 一天内完成 M0-M3、M4 半途的**Vue3+FastAPI+PostgreSQL 前后端分离原型**：公开只读链路完整（列表/详情/前端筛选），49 个后端测试质量良好；但对照 V1，内容模型（通知/文章/活动/指南结构化字段）、部门权限、归档与预约、确认跳转页、服务端搜索、附件、SEO、部署、监控、备份、CI **全部缺失**，且技术基座与 PRD 指定的 Wagtail/Django 不同。
2. 前端复用价值集中在**与框架无关层**：设计令牌、全局样式与无障碍模式、列表四态与 URL 筛选交互规格、板块文案、测试护栏范式；管理原型、路由、Element Plus、前端搜索实现应重写或废弃。
3. 两条骨架路径的证据比较倾向"同仓库干净 Wagtail 骨架"（路径 B），因为旧后端对 V1 覆盖率趋近于零、无数据迁移负担、PRD §18 本就为此设计；但**最终裁决连同前端架构决策一并属于项目负责人**（决策门 3 + 1），处置 M4 未提交工作是启动前置条件（决策门 4）。
4. 本审计未发现任何需要扩大 V1 范围的旧功能；旧路线图中的"AI 搜索"设想不属于 V1，不得顺带实现。
