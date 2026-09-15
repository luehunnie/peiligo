# Headless API 契约（SPEC-001 · B01 · 只读公开内容 API）

| 项目 | 内容 |
| --- | --- |
| 状态 | **Proposed — 待 R3 评审**（评审通过前不视为已冻结；状态权威＝[ADR-0008](../adr/0008-headless-api-contract.md)） |
| 决策记录 | [docs/adr/0008-headless-api-contract.md](../adr/0008-headless-api-contract.md)（ADR-0008，Proposed） |
| Ticket | [luehunnie/peiligo#13](https://github.com/luehunnie/peiligo/issues/13)（SPEC-001-B01） |
| 父 Spec | [SPEC-001](https://github.com/luehunnie/peiligo-frontend-rebuild/issues/2)（ Contracts 1/3/4、Architecture Constraints 1/2/3/6） |
| 机器可读形态 | [`docs/api/openapi.json`](openapi.json)（OpenAPI 3.1；F04 类型生成/校验唯一来源，与本文件同步更新） |
| 基线 | `peiligo/main = 48fd5d6`（本文档所有"现状"描述以该基线代码为准） |
| 实现归属 | **B02**（`feature/headless-api`；本契约不含任何实现） |

---

## 0. 契约范围一句话

为 Peiligo 公开内容新增**只读、无写端点、无认证**的 JSON API（`/api/v1/`），响应与现有 Django 模板渲染**行为等价**（同一可见性谓词、同一过滤层、同一排序、同一外链门控）；仅经 Peiligo Docker 内网供新前端（Astro SSR）消费，浏览器零直接调用；实现（B02）**零迁移**。

三层分离中本契约为 **schema 层**：view 层（页面组装）与 interaction 层（交互）归前端仓库（F04 起）；后端仅提供本文件定义的资源读取。

## 1. 端点清单（8 个，覆盖全部公开页面类型）

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

**不进入 API、保持 Django 现状不变的端点**（URL 与行为均不变，由 Caddy 继续路由 Django）：

- `GET/POST /link-confirm/go/`——「继续访问」302 端点（输出层二次校验唯一出处）；
- `/documents/<id>/<filename>/`——Wagtail 文档下载（附件 URL 直接引用该形态）；
- `/admin/`、`/django-admin/`、`/healthz/`、`/readyz/`、`/robots.txt`、`/favicon.ico`、`/static/`、`/media/`。

**公开页面类型覆盖核对**：首页（E2）、板块列表/筛选态（E3）、五类内容页详情（E6：通知/文章/学习资料/软件与工具/校园指南）、板块历史归档（E4）、全站搜索（E5）、外链确认页（E7）、页头/页脚/紧急提示（E1）、sitemap（E8）；robots.txt/favicon 为静态资产、容器 URL 恒 404、部门无主页——均无数据面，无需端点。无任何投机端点（不为未来 i18n 或新产品预留）。

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

容器页（`DepartmentContainerPage`）永不出现在任何响应中（前台 404、不在列表/搜索/导航/sitemap，现状 IA §3.2 同构）；Snippet 词表（部门/标签/学科等）不设独立端点——仅作为条目字段值与筛选参数出现。

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
| 404 | `not_found` | E6 页面不存在或状态∉{live, expired}；E3/E4 板块 slug 非法或非 live | 样式化 404 态 |
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
| F3 预约发布 | 可见时点由现有 `publish_scheduler`（`SCHED_INTERVAL_SECONDS`，缺省 60s）决定，API 零附加延迟；≤5min 允许窗口在缺省配置下成立；如需 30s 内则调低该运维参数（零代码变更）。 |
| F4 永不陈旧面 | E1（含紧急提示）/E5/E7 严格请求时计算；F04 侧对应页面同样不得缓存其数据（Astro SSR 每请求取数）。紧急告警下一次请求即见。 |
| F5 预览 | v1 API **不暴露任何草稿/预览内容**（无 preview 端点、响应永不含 S0/S1 内容）。Wagtail 后台预览（渲染内存修订版）保持现状，为切换前的 preview 权威载体；若未来需要面向新前端的预览面＝契约变更→按 §7 演进规则升级（R3）。 |
| F6 过期内容 | expired 内容按 §2.2 详情放行/HISTORICAL 谓词呈现并显式带 `expired` 标记——这是现行归档业务状态，非陈旧缓存；F1–F4 排除一切真陈旧。 |

## 4. 安全与网络边界（SPEC-001 Architecture Constraints 1/2/5）

| 条款 | 内容 |
| --- | --- |
| S1 同源/内网 | `/api/` 仅经 Peiligo Docker Compose 内网暴露给前端应用容器；**Caddy 不公开路由 `/api/`**；浏览器零直接 API 调用（消费位＝Astro SSR 服务端取数），同源体验不变。无需 CORS。 |
| S2 只读/无新增认证 | 无写端点；不新增认证/权限对象/用户组（上传与权限仍全部在 Django 侧）；API 匿名可读，且其可见面＝现有匿名浏览器可见面（§2.2 同一谓词），不多不少。 |
| S3 管理面不动 | `/admin/`、`/django-admin/`、axes、PasswordChangeGate、govaudit 均不因 API 改变。 |
| S4 数据最小面 | 响应仅含现有公开页面已展示的字段（含部门名、发布时间等作者元数据，PRD §4.3 口径）；无草稿、无日志、无环境细节、无秘密。 |
| S5 隔离 | API 与 Peilige/Peilike 严格 compose/network/volume/env 隔离；零交叉访问、零共享端点。 |
| S6 外链门控不变 | 正文外链块、`external_url`、`event_registration_url`、轮播外链项的出口一律由 API 提供**预构造 `confirm_href`**（`/link-confirm/?url=<quote(url, safe='/')>&from=<page.pk>`，构造规则唯一出处与 `external_link_jump.html` 同口径）；`/link-confirm/go/` 302 前输出层二次校验保持 Django 侧不变。富文本段落内既有内联外链形态**原样继承**（现状即不包装，属现状不变量；任何改变＝超范围）。 |
| S7 响应头 | `/api/` 路径不豁免现有 CSP 中间件（`peiligo.csp` 盖章行为不变）；HSTS/nosniff 由 Caddy/Django 现有配置覆盖。 |

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
- **E6 详情**（判别联合，公共字段＋类型差异）：
  - 公共：`{type, id, title, slug, url, section, department, first_published_at, last_published_at, expire_at, noindex, expired, cover(width-1400), breadcrumb[板块可点→当前页纯文本，容器段永不出现]}`
  - `notice`：＋`summary, event, body[], attachments[], external, tags[]`；`event{status,start_at,end_at,is_online,location,registration:ExternalLinkRef}|null`（`event_start_at` 空即 null）；`expire_at` 必有（通知必填有效期）。
  - `article`：同 notice（`expire_at` 可空）。
  - `material`：＋`summary, discipline, material_type, body[], attachments[], external, tags[]`。
  - `software`：＋`platforms[], source{url,confirm_href}, license_note, body[]`（无 summary/attachments/tags）。
  - `guide`：＋`category, location, opening_hours, contact, extra_notes, responsible_party, maintenance_mode(self|curated)+label, last_confirmed_on`（九字段一字不差；无 body）。
- **E7 link-confirm**：`{ok, target_domain(仅主机名), notice_text(SiteSettings 覆盖或默认文案), source{title,url}|null(from 须指向 CURRENT_DEFAULT 页，防草稿标题枚举), go_href, problem}`。
- **E8 sitemap**：`{entries[{loc(路径), lastmod}]}`——与现状 sitemap.xml 同一模型与排除口径（容器排除、noindex 排除）；公开域绝对化由前端完成。
- **分页元数据**：`{total, page, page_count, per_page:20, has_next, has_previous}`。

字段与现状模板渲染的逐条对应关系已在 `openapi.json` 各 schema 的 `description` 中给出引源（模型/模板/文档条款）。

## 6. 零迁移与实现边界（B02 义务）

1. **零 Django 迁移**：不新增模型/字段/索引/设置载体；不发生任何 schema、内容或数据迁移。契约读取面仅为现有模型：五类内容页 Page、`SectionPage`/`HomePage`、`Department`、`DepartmentContainerPage`（仅作树定位）、`FeaturedItem`/`CarouselItem`/`SiteSettings`、词表 Snippet、`wagtailimages.Image`/`wagtaildocs.Document`。
2. **零核心改动**：不改 Wagtail/Django 核心；搜索后端固定复用 `search/backends.py`（E1，ADR-0006）与 `search/services.py` 既有过滤层（或对其等价只读调用），不另立第二套搜索语义。
3. **零行为变更**：现有模板渲染、URL、管理面、发布/预览、安全基线全部不动；旧前端（ADR-0002 服务端模板）在切换前保持应急回退与 preview 载体，本契约不推翻 ADR-0002/0007（其退役处置归 B05，Human-only）。
4. **实现建议**（非冻结）：普通 Django 视图＋`JsonResponse`/`TemplateResponse` 之外的纯 JSON 出口即可满足本契约；不建议为 8 个只读端点引入 DRF router/wagtail.api.v2 等通用面（见 ADR-0008 替代方案 1）。实现分支＝`feature/headless-api`（SPEC-001 Git 政策）；每 PR 必含既有完整测试套件＋零计划外 migration 检查＋契约校验（SPEC-001 Test Matrix）。
5. **红线**：任何 DB/schema/数据迁移需求 → **立即 STOP**＋Human 决策包（R4）；涉及写端点或权限变更 → 超范围 STOP。

## 7. 版本与演进

- 基础路径带版本前缀 `/api/v1/`；**加字段/加端点**＝非破坏性，允许在 v1 内演进，但须同步更新本文件与 `openapi.json` 并在 PR 中声明。
- **破坏性变更**（删字段、改语义、改可见性、改错误码）＝public API 变更 → 按 SPEC-001 风险表升级 R3+，走新 ADR 或本 ADR 修订，禁止静默变更。
- 双载体纪律：本文件（人的契约）与 `openapi.json`（机器契约）**必须同一提交更新**；`openapi.json` 是 F04 类型生成/校验唯一来源，两载体冲突以评审裁决为准并即时修正。

## 8. 与 F04 的对齐接口

- F04 从 `openapi.json` 生成 TS 类型（schema 层），view/interaction 层在前端仓库组织（SPEC-001 Constraint 6）；本契约 §2.3/§5.1 明确划给前端的表示层义务：90 字摘要截断、`EventStatus`/维护方式中文标签、板块短名/tone 映射（`SECTION_SHORT`/`SECTION_TONE` 冻结表）、高亮安全管线、空态文案、日期展示格式（列表 `Y-m-d`、快讯卡 `m-d`）、rendition 之外的图片处理。
- 前端不得自建：可见性判定、过滤/排序/分页语义、外链 confirm 链构造、`link-confirm/go` 跳转（§4 S6）、任何业务规则复刻（SPEC-001 Constraint 1）。
