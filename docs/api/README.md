# Headless API 契约（SPEC-001 · B01 · 只读公开内容 API）

| 项目 | 内容 |
| --- | --- |
| 状态 | **Accepted — 已冻结（2026-09-15 G2：Human 同意 R3 控制器结论，含 type-const 判别架构接受）**；状态权威＝[ADR-0008](../adr/0008-headless-api-contract.md) 状态字段头 |
| 修订 | 2026-09-15 **转 Accepted**（G2 门通过：Human 明确同意 R3 GPT Controller 评审结论——含对既有 `type` 字段 const 判别架构的接受，即 F04 校验修复，无新字段、载荷零变化；批准载体与留痕见 ADR-0008 状态字段头）。同日 R3 评审修订（控制器 FIX 裁定）留痕：①F5 重写为 **E9 预览契约**（新增 [`/api/v1/preview`](openapi.json)＋同源 `/preview/` 请求流，见 §3.1）；②F3 收紧为 **Gate 5 部署验收条件**（生产 `SCHED_INTERVAL_SECONDS ≤ 30`，不满足即生产切换 blocker）。双载体同一提交更新 |
| 决策记录 | [docs/adr/0008-headless-api-contract.md](../adr/0008-headless-api-contract.md)（ADR-0008，Accepted） |
| Ticket | [luehunnie/peiligo#13](https://github.com/luehunnie/peiligo/issues/13)（SPEC-001-B01） |
| 父 Spec | [SPEC-001](https://github.com/luehunnie/peiligo-frontend-rebuild/issues/2)（ Contracts 1/3/4、Architecture Constraints 1/2/3/6） |
| 机器可读形态 | [`docs/api/openapi.json`](openapi.json)（OpenAPI 3.1；F04 类型生成/校验唯一来源，与本文件同步更新） |
| 基线 | `peiligo/main = 48fd5d6`（本文档所有"现状"描述以该基线代码为准） |
| 实现归属 | **B02**（`feature/headless-api`；本契约不含任何实现） |

---

## 0. 契约范围一句话

为 Peiligo 新增**只读、零写端点**的 JSON API（`/api/v1/`），响应与现有 Django 模板渲染**行为等价**（同一可见性谓词、同一过滤层、同一排序、同一外链门控）；E1–E8 无认证且可见面＝现有匿名浏览器可见面，E9 为票据门控的预览取数出口（§3.1）；仅经 Peiligo Docker 内网供新前端（Astro SSR）消费，浏览器零直接 API 调用；实现（B02）**零迁移**。

三层分离中本契约为 **schema 层**：view 层（页面组装）与 interaction 层（交互）归前端仓库（F04 起）；后端仅提供本文件定义的资源读取。

## 1. 端点清单（9 个：E1–E8 覆盖全部公开页面类型，E9 预览面）

| # | 端点 | 等价现状消费位 | 可见性谓词 | 分页 |
| --- | --- | --- | --- | --- |
| E1 | `GET /api/v1/chrome` | `site_chrome` 处理器＋`_active_alert`（页头/页脚/紧急提示） | 每请求实时 | 无 |
| E2 | `GET /api/v1/home` | `HomePage.get_context`（Phase 8C 定稿：轮播/五板块导航/校园快讯） | CURRENT_DEFAULT | 无 |
| E3 | `GET /api/v1/sections/{slug}` | `SectionPage.get_context`（板块默认列表＋q/dept/type/tag 筛选态） | CURRENT_DEFAULT | 20/页 |
| E4 | `GET /api/v1/sections/{slug}/archive` | `home.views.section_archive`（板块历史归档） | HISTORICAL | 无（全量，同现状） |
| E5 | `GET /api/v1/search` | `search.views.search`（全站搜索，五参数） | HISTORICAL | 20/页 |
| E6 | `GET /api/v1/pages/{section}/{dept}/{slug}` | 五类内容页具名 URL 渲染（含 expired 放行语义） | live ∪ expired | 无 |
| E7 | `GET /api/v1/link-confirm` | `home.views._confirm_context`（外链确认页四要素） | 每请求实时 | 无 |
| E8 | `GET /api/v1/sitemap` | `wagtail.contrib.sitemaps` sitemap 视图输出 | live ∧ ¬noindex | 无 |
| E9 | `GET /api/v1/preview` | Wagtail 后台预览（`wagtailadmin` 既有 `FormState` 修订暂存）的新前端等价出口（§3.1） | 预览票据（≤60s 签名 token，绑定管理会话＋页面 change 权限；位于可见性谓词体系之外——预览对象正是草稿） | 无 |

**不进入 API、保持 Django 现状不变的端点**（URL 与行为均不变，由 Caddy 继续路由 Django）：

- `GET/POST /link-confirm/go/`——「继续访问」302 端点（输出层二次校验唯一出处）；
- `/documents/<id>/<filename>/`——Wagtail 文档下载（附件 URL 直接引用该形态）；
- `/admin/`、`/django-admin/`、`/healthz/`、`/readyz/`、`/robots.txt`、`/favicon.ico`、`/static/`、`/media/`。

**公开页面类型覆盖核对**：首页（E2）、板块列表/筛选态（E3）、五类内容页详情（E6：通知/文章/学习资料/软件与工具/校园指南）、板块历史归档（E4）、全站搜索（E5）、外链确认页（E7）、页头/页脚/紧急提示（E1）、sitemap（E8）；robots.txt/favicon 为静态资产、容器 URL 恒 404、部门无主页——均无数据面，无需端点。E9 为冻结 PRD（SPEC-001）明列「生产切换前 Wagtail preview 可用」所要求的预览面（票据门控，非公开页面类型、非匿名可见面），非投机端点。除此之外无任何投机端点（不为未来 i18n 或新产品预留）。

## 2. 通用规则

### 2.1 表示

- 全部端点仅 `GET`（其余方法 405，错误封装见 §2.4）；响应 `application/json; charset=utf-8`。
- 字段命名 snake_case；时间一律 ISO 8601（含时区偏移，Django `USE_TZ` 现值）；日期字段以 `date` 后缀、时间戳以 `_at` 后缀区分。
- 未知查询参数一律忽略（不报错，Django 现状同构）。
- 站内引用（`url`/`href`/`src`）一律返回**路径形态**（`/chronicle/jwc/foo/`、`/media/...`、`/documents/...`）；绝对 URL 由前端按公开域名拼装。唯一例外：`chips[].url` 与确认链 `confirm_href`/`go_href` 为完整路径含查询串。

### 2.2 可见性谓词（唯一权威＝`notices/lifecycle.py` 现有实现，API 不另立口径）

| 谓词 | 定义 | 消费端点 |
| --- | --- | --- |
| `CURRENT_DEFAULT` | `live ∧ ¬expired`（§16.4，状态 S2） | E2、E3 |
| `HISTORICAL` | `Q(live) ∨ Q(expired)`（S2 ∪ S3；ARCHIVE-SEARCH 同谓词） | E4、E5 |
| 详情放行 | live 正常；expired 具名 URL 放行并带 `expired: true`（`LifecycleStateMixin.route` 载体①）；S0 草稿/S1 预约/S4 下线 → 404 | E6 |
| 运营位有效性 | `FeaturedItem.is_on_display` / `CarouselItem.is_on_display` 每请求复核（enabled∧窗口∧所指内容 S2；失效静默跳过） | E2 |

容器页（`DepartmentContainerPage`）永不出现在任何响应中（前台 404、不在列表/搜索/导航/sitemap，现状 IA §3.2 同构）；Snippet 词表（部门/标签/学科等）不设独立端点——仅作为条目字段值与筛选参数出现。E9 位于上述谓词体系之外（其预览对象正是 S0/S1 草稿），访问面由 §3.1 票据条款单独约束；E1–E8 响应永不含草稿内容。

### 2.3 搜索与过滤语义（逐字继承 CONTENT_MODEL §21，零新增公开参数）

- 参数集：`q`（首尾 strip）、`section`（仅五冻结 slug `chronicle|events|materials|software|guide`）、`dept`（`Department.is_active` 词表内 slug）、`type`（`notice|article|material|software|guide`）、`tag`（Tag slug∪name 或四类别词表 name 之一）、`page`。
- **非法值视同未提供**（§21.3）：200 回退全量，不 400、不 404、不 5xx；`tag` 词表外值同此。
- 板块端点（E3）**不读** `?section=`（板块维度由路径唯一决定，§9.1）；搜索端点（E5）`section` 合法值同上。
- 执行模型＝filter-first＋`order_by_relevance=False` 保序（§21.6）：全部维度过滤＋可见性谓词先施加，再进既有搜索后端 `search/backends.py`（E1 icontains，ADR-0006 Accepted）；`q` 空串不进搜索后端（纯 ORM）。
- 跨类型合并排序键＝`-first_published_at`，Python 稳定排序（同刻并列按 notice→article→material→software→guide 类型顺序）。
- 分页＝`Paginator.get_page` 宽容语义：`page` 非整数→第 1 页，越界→最后一页（不 404 不 500）；`per_page` 恒 20（`LIST_PAGE_SIZE`，前后端两侧同值）。
- E4（归档）无查询参数（非 §21 载体，§21.4 零新增参数），全量返回不分页（现状模板全量渲染同构）。
- 高亮：**API 不做高亮**。E5 原样回显 `q`；命中标注属前端表示层，且必须沿用现有安全管线语义（切片→逐片段 HTML 转义→仅包无用户内容的 `<mark>`；见 `frontend/templatetags/peiligo_extras.py` `highlight`）——API 返回的均为未转义原始存储文本，转义责任在消费方渲染层。

### 2.4 错误响应

所有非 2xx 响应使用统一封装：

```json
{ "error": { "code": "not_found", "message": "资源不存在" } }
```

| HTTP | `code` | 触发 | 前端义务（SPEC-001 契约 4） |
| --- | --- | --- | --- |
| 404 | `not_found` | E6 页面不存在或状态∉{live, expired}；E3/E4 板块 slug 非法或非 live；E9 票据缺失/无效/过期/权限复核不过（一律 `not_found`，不区分原因，防预言机） | 样式化 404 态 |
| 405 | `method_not_allowed` | 非 GET | —（前端不触发） |
| 500 | `server_error` | 未预期异常 | 样式化错误态＋重试引导 |
| 503 | `unavailable` | 数据库/上游不可用（`readyz` 同判定源） | 样式化错误态＋重试引导 |

- `message` 为 zh-Hans 面向访客文案，不泄露路径、栈、环境细节（现状 `healthz` 纪律同构）。
- **E7 不产生 4xx**：目标校验失败返回 200＋`ok:false`＋`problem`（现状确认页渲染拒绝态同构）。
- 筛选值非法不属错误（§2.3 回退语义）；两空态（全空/筛选无匹配）由 `filters.active`＋空 `entries` 表达，空态文案归前端表示层。

## 3. 新鲜度语义（SPEC-001 契约 4 的 API 侧落地）

| 条款 | 内容 |
| --- | --- |
| F1 请求时计算 | 所有端点每请求从现役数据库计算响应；**API 层禁止任何应用级缓存、共享 HTTP 缓存、ETag/Last-Modified 陈旧回放**；全部 `/api/` 响应带 `Cache-Control: no-store`。 |
| F2 立即发布 | 无 `go_live_at` 的发布＝落库即对下一请求可见（≤30s 目标以其上限满足）。 |
| F3 预约发布 | 可见时点＝**下一个调度周期**（`publish_scheduler` 容器，间隔 `SCHED_INTERVAL_SECONDS`，缺省 60s），API 零附加延迟。**≤30s 目标的 Gate 5 部署验收条件：生产 `SCHED_INTERVAL_SECONDS ≤ 30` 且 scheduler 容器运行中**；缺省 60s 仅满足 ≤5min 允许窗口、**不满足** ≤30s 目标——不满足即**生产切换 blocker**（切换 runbook 显式检查项，禁止静默带病切换）。调参零代码变更。 |
| F4 永不陈旧面 | E1（含紧急提示）/E5/E7 严格请求时计算；F04 侧对应页面同样不得缓存其数据（Astro SSR 每请求取数）。紧急告警下一次请求即见。 |
| F5 预览 | 草稿/预览内容**仅**经 E9（§3.1）出口：≤60s 单跳签名票据（Django 唯一校验权威）→ Astro 以与正式页**同一模板**渲染于同源 `/preview/?token=`。除此之外任何公开面（E1–E8、sitemap、搜索、导航）**永不含 S0/S1 草稿内容**。后台既有 Django 模板预览保持现状不动，作为迁移期回退载体；E9 未接线期间该缺口为显式跟踪的迁移限制＋生产切换 blocker（§3.1），不得作为 v1 契约终态。 |
| F6 过期内容 | expired 内容按 §2.2 详情放行/HISTORICAL 谓词呈现并显式带 `expired` 标记——这是现行归档业务状态，非陈旧缓存；F1–F4 排除一切真陈旧。 |

### 3.1 预览契约（E9，冻结 PRD「生产切换前 Wagtail preview 可用」的落地）

**请求流（五步，单跳票据）**：

1. 编辑在 Wagtail 后台点「预览」——现有表单暂存机制照旧（`wagtailadmin` 既有 `FormState` 表按用户×页面暂存编辑态，后台既有行为零变更）；
2. 后台预览出口（**应用级钩子**，B02 实现）铸造**签名票据**：Django `core.signing`（复用现有 `SECRET_KEY`，无新秘密、无新存储载体），载荷绑定（管理会话、用户、页面 pk），**有效期 ≤60s**；
3. 编辑浏览器携票据访问**同源**预览页 `GET /preview/?token=…`（公开域路径，与后台同源——`WAGTAILADMIN_BASE_URL` 与 `DOMAIN` 同源现状不变；Caddy 将 `/preview/` 路由至 Astro）；
4. Astro SSR 把票据**原样透传** Django 内网 `GET /api/v1/preview?token=…`（S1 同款边界：Caddy 不公开路由 `/api/`、无 CORS、浏览器零直接 API 调用）；
5. Django 校验并出数：签名/时效 → 绑定会话仍存在且仍认证同一用户 → 用户对该页仍具 change 权限（与后台预览同一权限要求）→ 草稿暂存仍在；全部通过后**只读**重建草稿对象、经与 E6 同一序列化层输出 `preview: true` 响应（`Cache-Control: no-store`）；任一步失败一律 404 `not_found`（不区分原因，防预言机）。**兑换路径零写入**（不改 `FormState`、不写任何会话/存储）。

**义务与边界**：

- Django/Wagtail 是认证、授权、预览数据与票据校验的**唯一权威**；Astro 无数据库连接、无权限逻辑，仅票据透传与模板渲染（SPEC-001 Constraint 1 不破）。
- Astro 预览页义务（F04，亦写入 `openapi.json` `/preview` 操作）：与正式详情页**同一模板**渲染（真等价预览）；`Cache-Control: no-store`＋`X-Robots-Tag: noindex`＋`Referrer-Policy: no-referrer`；不缓存、不重放缓存票；不把票据写访问日志（记哈希或省略 query）；票据校验失败渲染样式化 404；CSP 与全站同一纪律（不豁免、不放松）；不入 sitemap/搜索/导航。
- 范围＝五类内容页（E6 判别联合）；首页/板块页预览维持后台 Django 模板预览现状。
- `/preview/` 为预览保留路径（冻结 IA 下根级子页仅五板块 slug，无路径冲突）。
- 残余风险如实记录：票据在 ≤60s 有效期内可重复兑换（换取零写入兑换路径与零新存储）；泄露影响被短时效、会话绑定与权限复核三重约束，票据换取的仅是单篇草稿的只读视图。
- **迁移期跟踪**：B02（E9＋预览出口钩子）与 F04（`/preview/` 页）部署并在 staging 验证之前，「Astro 等价预览未接线」作为**显式跟踪的迁移限制＋生产切换 blocker**（G5/B03 切换检查项）；该缺口不得作为 v1 契约终态。

**维护注记（Wagtail 升级必查——E9 镜像 `PreviewOnEdit` 表单路径）**：E9 兑换路径**有意**镜像 wagtailadmin `PreviewOnEdit` 的既有表单路径（`FormState` 暂存 → 实例绑定 edit handler 重建 → `save(commit=False)` 零写入）——Wagtail 升级若改变该内部路径，E9 的行为等价性随之失效。故**每次 Wagtail 版本升级**必须重跑以下清单（逐项留痕于升级 PR）：

- [ ] `tests/test_api_preview.py` 全绿（铸造门禁 / 兑换端到端 / 零写入证明）；
- [ ] `tests/test_api_security.py` 中 E9 反预言机失败路径全绿（票据面安全）；
- [ ] 表单路径兼容性核对：升级后 wagtailadmin `PreviewOnEdit`/`FormState` 的实现与本端点镜像路径仍一致（含 parent_page 解析、`defer_required` 等内部 API 形态）；
- [ ] 任何不一致 → 按 §7 演进规则处置（public API 语义变更，升级 R3+），禁止静默修补。

## 4. 安全与网络边界（SPEC-001 Architecture Constraints 1/2/5）

| 条款 | 内容 |
| --- | --- |
| S1 同源/内网 | `/api/` 仅经 Peiligo Docker Compose 内网暴露给前端应用容器；**Caddy 不公开路由 `/api/`**；浏览器零直接 API 调用（消费位＝Astro SSR 服务端取数），同源体验不变。无需 CORS。 |
| S2 只读/无新增认证 | 无写端点；不新增认证/权限对象/用户组（上传与权限仍全部在 Django 侧）；E1–E8 匿名可读且可见面＝现有匿名浏览器可见面（§2.2 同一谓词），不多不少；E9 不匿名——仅经 S8 票据面放行。 |
| S3 管理面不动 | `/admin/`、`/django-admin/`、axes、PasswordChangeGate、govaudit 均不因 API 改变。 |
| S4 数据最小面 | 响应仅含现有公开页面已展示的字段（含部门名、发布时间等作者元数据，PRD §4.3 口径）；无草稿、无日志、无环境细节、无秘密。 |
| S5 隔离 | API 与 Peilige/Peilike 严格 compose/network/volume/env 隔离；零交叉访问、零共享端点。 |
| S6 外链门控不变 | 正文外链块、`external_url`、`event_registration_url`、轮播外链项的出口一律由 API 提供**预构造 `confirm_href`**（`/link-confirm/?url=<quote(url, safe='/')>&from=<page.pk>`，构造规则唯一出处与 `external_link_jump.html` 同口径）；`/link-confirm/go/` 302 前输出层二次校验保持 Django 侧不变。富文本段落内既有内联外链形态**原样继承**（现状即不包装，属现状不变量；任何改变＝超范围）。 |
| S7 响应头 | `/api/` 路径不豁免现有 CSP 中间件（`peiligo.csp` 盖章行为不变）；HSTS/nosniff 由 Caddy/Django 现有配置覆盖。 |
| S8 预览票据 | E9 面仅经签名票据放行：`core.signing`（现有 `SECRET_KEY`＋专用 salt），载荷绑定（管理会话，用户，页面），有效期 ≤60s；兑换时 Django 复核签名/时效/会话存活/用户认证/页面 change 权限，失败一律 404 不区分原因；兑换只读零写入；零新存储载体（草稿表单态沿用 `wagtailadmin` 既有 `FormState` 表——Wagtail 自管迁移，已应用）。后台 URL/权限对象/认证方式零变更，S3 各项不受影响。 |

## 5. 数据形态（要点；权威定义＝`openapi.json`）

### 5.1 公共构件

- `ImageRef` `{src, width, height, alt}`——**rendition 预渲染**，且全契约只复用现有四处 rendition 规格（零新规格）：轮播/hero `width-1600`、校园快讯 `fill-800x520`、正文插图 `width-1120`、详情封面 `width-1400`（rendition 行为现有 Wagtail 运行时缓存机制，非数据迁移）。
- `SectionRef` `{slug, title}`（slug 限五冻结值）；`DepartmentRef` `{name, slug}`。
- `EventStatus` 枚举 `upcoming|ongoing|ended|null`（现有三态计算属性 `event_status` 的机器化；中文标签映射「即将开始/进行中/已结束」归前端表示层）。
- `AttachmentRef` `{title, url, file_size}`；`ExternalLinkRef` `{url, confirm_href}`。
- `ListEntry`——列表/搜索/归档共享行数据：`{type, id, title, url, expired, section_slug, section_title, department_name, published_at, event_status, list_summary}`。`list_summary`＝现有回落链解析结果（summary → license_note → location，`_content_summary` 同序，**不截断**）；90 字列表截断属前端表示层。
- `Block`（判别联合 `type`）：`heading{text,level:h2|h3}`、`paragraph{html}`（服务端渲染的安全 HTML 片段，features 白名单 bold/italic/link/ol/ul 现状不变，前端整片插入不二次加工）、`image{ImageRef}`、`attachment{AttachmentRef}`、`table{first_row_is_table_header, data:string[][]}`、`external_link{text,url,confirm_href}`。SoftwareToolPage 正文白名单天然无 `attachment` 块。

### 5.2 端点响应速览

- **E1 chrome**：`{site_name, nav_sections[5]{slug,title,url}, feedback_email, alert{文本}|null}`。`nav_sections`＝`SECTIONS` 冻结常量顺序（现状导航零查询同构，不查库）；`feedback_email`＝SiteSettings 优先、环境兜底（`_feedback_email` 同链）。
- **E2 home**：`{title, alert, carousel[≤5], sections[≤5], campus_news[≤3]}`。`carousel` 条目 `{kind:internal|external, title, href, cover, summary(≤60), section_slug}`（外链项 `href`＝confirm 链、summary 恒空串）；`sections`＝live 板块页按冻结顺序；`campus_news`＝`_campus_news_entries` 同一组稿规则（推荐位→最新通知→近期活动补位、已结束活动跳过、pk 去重、≤3），条目 `{type, id, title, href, cover(fill-800x520), summary(≤50), section_slug, department, published_at, event_status}`。
- **E3 板块列表**：`{section{slug,title,url,archive_url}, entries[≤20], pagination, filters}`；`filters{q, section:null, dept, type, tag, active, conditions[{label,value}]}`（conditions＝已选条件回显，供"筛选无匹配"空态）。
- **E4 归档**：`{section, entries[], total}`（HISTORICAL、`-first_published_at`、全量）。
- **E5 搜索**：`{q, entries[≤20], pagination, filters, chips[6]}`；`chips`＝`section_chips` 同构（"全部"置首、保留其余参数剔除 page/section、`active` 标注）。
- **E6 详情**（判别联合，公共字段＋类型差异；判别值＝既有 `type` 字段——五个 `*Detail` schema 各自以 `const` 钉死其型值，oneOf 严格恰一分支可匹配。F04 修复：钉死前 notice/article 两分支形状同构，任一有效负载双匹配，严格校验恒败；未引入新判别字段，载荷零变化）：
  - 公共：`{type, id, title, slug, url, section, department, first_published_at, last_published_at, expire_at, noindex, expired, cover(width-1400), breadcrumb[板块可点→当前页纯文本，容器段永不出现]}`
  - `notice`：＋`summary, event, body[], attachments[], external, tags[]`；`event{status,start_at,end_at,is_online,location,registration:ExternalLinkRef}|null`（`event_start_at` 空即 null）；`expire_at` 必有（通知必填有效期）。
  - `article`：同 notice（`expire_at` 可空）。
  - `material`：＋`summary, discipline, material_type, body[], attachments[], external, tags[]`。
  - `software`：＋`platforms[], source{url,confirm_href}, license_note, body[]`（无 summary/attachments/tags）。
  - `guide`：＋`category, location, opening_hours, contact, extra_notes, responsible_party, maintenance_mode(self|curated)+label, last_confirmed_on`（九字段一字不差；无 body）。
- **E7 link-confirm**：`{ok, target_domain(仅主机名), notice_text(SiteSettings 覆盖或默认文案), source{title,url}|null(from 须指向 CURRENT_DEFAULT 页，防草稿标题枚举), go_href, problem}`。
- **E8 sitemap**：`{entries[{loc(路径), lastmod}]}`——与现状 sitemap.xml 同一模型与排除口径（容器排除、noindex 排除）；公开域绝对化由前端完成。
- **分页元数据**：`{total, page, page_count, per_page:20, has_next, has_previous}`。
- **E9 preview**：E6 判别联合（公共字段＋五型差异，§5.2 详情各条）＋顶层 `preview: true`；全部字段取自预览表单状态（草稿数据），可见性谓词与 expired 放行语义不适用（`expired`/`expire_at` 等按草稿数据如实填充）；浏览器侧预览页＝同源 `/preview/?token=`（Astro 同模板渲染，义务见 §3.1）。

字段与现状模板渲染的逐条对应关系已在 `openapi.json` 各 schema 的 `description` 中给出引源（模型/模板/文档条款）。

## 6. 零迁移与实现边界（B02 义务）

1. **零 Django 迁移**：不新增模型/字段/索引/设置载体；不发生任何 schema、内容或数据迁移。契约读取面仅为现有模型：五类内容页 Page、`SectionPage`/`HomePage`、`Department`、`DepartmentContainerPage`（仅作树定位）、`FeaturedItem`/`CarouselItem`/`SiteSettings`、词表 Snippet、`wagtailimages.Image`/`wagtaildocs.Document`；E9 预览面同样零新存储——票据为签名值（无载体），草稿表单态沿用 `wagtailadmin` 既有 `FormState` 表（Wagtail 自管迁移，已应用）。
2. **零核心改动**：不改 Wagtail/Django 核心；搜索后端固定复用 `search/backends.py`（E1，ADR-0006）与 `search/services.py` 既有过滤层（或对其等价只读调用），不另立第二套搜索语义。
3. **零行为变更**：现有模板渲染、URL、管理面、发布/预览、安全基线全部不动（唯一新增交互面＝§3.1 预览出口：应用级钩子铸造票据并指向同源 `/preview/`，不改既有后台 URL/权限/认证对象，后台既有 Django 模板预览照旧）；旧前端（ADR-0002 服务端模板）在切换前保持应急回退与预览回退载体，本契约不推翻 ADR-0002/0007（其退役处置归 B05，Human-only）。
4. **实现建议**（非冻结）：普通 Django 视图＋`JsonResponse`/`TemplateResponse` 之外的纯 JSON 出口即可满足本契约；不建议为 9 个只读端点引入 DRF router/wagtail.api.v2 等通用面（见 ADR-0008 替代方案 1）。实现分支＝`feature/headless-api`（SPEC-001 Git 政策）；每 PR 必含既有完整测试套件＋零计划外 migration 检查＋契约校验（SPEC-001 Test Matrix）。
5. **红线**：任何 DB/schema/数据迁移需求 → **立即 STOP**＋Human 决策包（R4）；涉及写端点或权限变更 → 超范围 STOP。

## 7. 版本与演进

- 基础路径带版本前缀 `/api/v1/`；**加字段/加端点**＝非破坏性，允许在 v1 内演进，但须同步更新本文件与 `openapi.json` 并在 PR 中声明。E9 即按本条于 2026-09-15 R3 评审修订中纳入 v1 草案（留痕：彼时 ADR-0008 尚为 Proposed、契约未冻结，故修订不属 breaking；**ADR-0008 已于 2026-09-15 转 Accepted——此后对 E9 或任何端点的语义变更即 breaking，按本条处置**；双载体同一提交更新）。
- **破坏性变更**（删字段、改语义、改可见性、改错误码）＝public API 变更 → 按 SPEC-001 风险表升级 R3+，走新 ADR 或本 ADR 修订，禁止静默变更。
- 双载体纪律：本文件（人的契约）与 `openapi.json`（机器契约）**必须同一提交更新**；`openapi.json` 是 F04 类型生成/校验唯一来源，两载体冲突以评审裁决为准并即时修正。

## 8. 与 F04 的对齐接口

- F04 从 `openapi.json` 生成 TS 类型（schema 层），view/interaction 层在前端仓库组织（SPEC-001 Constraint 6）；本契约 §2.3/§5.1 明确划给前端的表示层义务：90 字摘要截断、`EventStatus`/维护方式中文标签、板块短名/tone 映射（`SECTION_SHORT`/`SECTION_TONE` 冻结表）、高亮安全管线、空态文案、日期展示格式（列表 `Y-m-d`、快讯卡 `m-d`）、rendition 之外的图片处理。
- 前端不得自建：可见性判定、过滤/排序/分页语义、外链 confirm 链构造、`link-confirm/go` 跳转（§4 S6）、票据校验或任何预览权限逻辑（E9 仅透传，§3.1）、任何业务规则复刻（SPEC-001 Constraint 1）。
- F04 预览页义务清单（§3.1）：同模板渲染、`no-store`＋`X-Robots-Tag: noindex`＋`Referrer-Policy: no-referrer`、票据不落日志、失败样式化 404、CSP 同纪律、不入 sitemap/搜索/导航；机器契约侧对应 `openapi.json` `/preview` 操作的 description。
- **F04 类型生成来源（精确出处，判别联合修复版）**：含 `type`-const 判别的 `openapi.json` 修复版唯一出处＝分支 `luehunnie/spec-001-b02-headless-api`（PR luehunnie/peiligo#19）commit `2f7fa021afd6777c611c86e3b78622b776a3b732`（2026-09-15，"docs(api): carry ADR-0008 headless API contract carriers (B01 copy + F04 union repair)"）；B01 分支 `luehunnie/spec-001-b01-api-contract`（PR #18，b320910 及之前）**不含**该修复。两 PR 合并先后不影响结论：类型生成/校验一律以含本修复的载体为准——schema 判别结构自该提交起未再变更（本治理提交仅追加 `/preview` description 维护注记句与状态文字）；Human 已于 2026-09-15 接受该 type-const 判别架构（ADR-0008 状态字段头留痕）。
