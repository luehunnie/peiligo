# ADR-0008 · Headless API 契约（只读公开内容 API 冻结）

## 状态字段头

| 字段 | 值 |
| --- | --- |
| 编号 | 0008 |
| 日期 | 2026-09-15（首落盘） |
| 状态 | Accepted（2026-09-15 由 SPEC-001-B01 代理以 Proposed 落盘；README §4：ADR 状态变更决策人＝项目负责人或其书面授权，代理不得代决。**2026-09-15 R3 评审修订（控制器 FIX 裁定，代理按修订执行、仍不代决状态）**：①F5 重写为 E9 预览契约（新增 `/api/v1/preview`＋同源 `/preview/` 请求流，契约 §3.1）；②F3 收紧为 Gate 5 部署验收条件（生产 `SCHED_INTERVAL_SECONDS ≤ 30` 且 scheduler 运行中，不满足即生产切换 blocker）。**2026-09-15 F04 校验修订（控制器裁定，B02 代理按修订执行）**：E6/E9 判别联合的 notice/article 两分支形状同构致 oneOf 严格校验恒败——五个 `*Detail` schema 以既有 `type` 字段钉死判别常量（无新字段、载荷零变化），README §5.2 与 openapi.json 同步。**2026-09-15 转 Accepted（G2 门通过）**：项目负责人（Human）对 R3 GPT Controller 评审结论明确同意——含对既有 `type` 字段 const 判别架构（即上记 F04 校验修订，无新字段、载荷零变化）的接受；G2 条件（R3 GPT Controller 评审＋项目负责人签收）就此满足，本契约自此视为冻结。批准载体＝Human 经任务控制链传达的明确同意（传达形态即如此，无独立签批文件或外部链接——如实记录、不虚构批准元数据）；本状态行与 `docs/adr/README.md` §2 索引行/§3 看板同步留痕，代理仅按 README §4/§5 门批准结果同步状态，不代决） |
| 关联决策 | SPEC-001（Human 冻结 PRD 的忠实转译，G1 已通过 2026-09-15）——决策依据＝SPEC-001 Contracts 1（Headless API 契约冻结为 ADR）/3（安全 parity）/4（内容新鲜度）与 Architecture Constraints 1（事实源唯一）/2（API 只读·内网）/3（数据零迁移）/6（schema/view/interaction 分离）；授权载体＝SPEC-001 Spec Issue（https://github.com/luehunnie/peiligo-frontend-rebuild/issues/2 ，G1 Human 已授权发布）与执行 Ticket SPEC-001-B01（https://github.com/luehunnie/peiligo/issues/13 ，风险 R3）。契约正文双载体：[docs/api/README.md](../api/README.md)（人的契约）＋ [docs/api/openapi.json](../api/openapi.json)（机器契约，F04 类型生成唯一来源） |

## 背景

- **要解决的问题**：SPEC-001 确定以 Astro 重建 Peiligo 公共前端，Django/Wagtail 保持唯一事实源——两条产品线之间需要一份**在 G2 冻结的只读 Headless API 契约**（端点清单＋请求/响应 schema），作为前端类型化消费（F04）与后端实现（B02）的共同依据，并把"公开 API 面"这一 R3 风险的处置（契约先行、评审冻结）落到实处。无契约即开工，前后端将各自发明字段与语义，等价验收（G4）与安全 parity（G5）无从核对。
- **现状盘点（基线 48fd5d6）**：公开页面类型全集为——首页（Phase 8C 定稿层级：紧急提示→Hero 轮播≤5→五分类导航→校园快讯≤3→Footer）、五板块列表页（`SectionPage.get_context`，q/dept/type/tag 筛选态与默认列表共用同一过滤层）、五类内容页详情（NoticePage/ArticlePage/MaterialPage/SoftwareToolPage/GuidePage，树形具名 URL `/<板块>/<部门>/<slug>/`）、板块历史归档（`/<板块>/archive/`，HISTORICAL）、全站搜索（`/search/`，五参数，ARCHIVE-SEARCH 同谓词）、外链确认页＋go 端点（F-03 门控）、robots/sitemap/favicon/healthz。数据消费全部来自现有模型与 `search.services` 过滤层；无任何写面。
- **约束**：①事实源唯一——Astro 不连数据库、不复刻业务规则；②API 只读、正常仅经 Peiligo Docker 内网访问、浏览器同源；③数据零迁移——任何 DB/schema/数据变更触发 R4 立即 STOP；④新鲜度——发布 ≤30s 可见、普通内容 ≤5min 允许窗口、搜索/preview/链接确认不得陈旧；⑤schema/view/interaction 三层分离；⑥不加投机抽象与投机端点（不为未来 i18n/新产品预留）。现有不变量（URL、安全基线、搜索转义、外链门控、发布与预览）全部视为不可改。
- **触发事件**：SPEC-001 Ticket Graph 于 2026-09-15 生成，B01 为无阻塞的初始 ready 项，G2＝F01（脚手架）＋B01（本契约 ADR）。

## 决策

**冻结一份 9 端点的只读公开内容 API 契约（基础路径 `/api/v1/`；E1–E8 行为等价镜像现有 Django 渲染语义，E9 为冻结 PRD 要求的预览取数面），以双载体形式落盘（docs/api/README.md 人的契约＋docs/api/openapi.json 机器契约），作为 F04 类型生成与 B02 实现的唯一依据。**

端点清单（完整 schema、可见性、错误、新鲜度、安全条款见契约正文，此处记其骨架）：

1. `GET /api/v1/chrome`——页头/页脚/紧急提示（site_chrome＋_active_alert 等价）；
2. `GET /api/v1/home`——首页三区（轮播≤5/五板块导航/校园快讯≤3，HomePage.get_context 等价）；
3. `GET /api/v1/sections/{slug}`——板块默认列表＋筛选态（CURRENT_DEFAULT，20/页）；
4. `GET /api/v1/sections/{slug}/archive`——板块历史归档（HISTORICAL，全量）；
5. `GET /api/v1/search`——全站搜索（HISTORICAL，五参数，20/页）；
6. `GET /api/v1/pages/{section}/{dept}/{slug}`——五类内容页详情（live 正常、expired 放行带标记、S0/S1/S4→404，`LifecycleStateMixin.route` 等价）；
7. `GET /api/v1/link-confirm`——外链确认页四要素（校验失败 200＋ok:false，不产生 4xx）；
8. `GET /api/v1/sitemap`——sitemap 条目（与现状 sitemap.xml 同一排除口径）；
9. `GET /api/v1/preview`——预览取数（E9，2026-09-15 R3 评审修订纳入）：签名票据（≤60s，绑定管理会话＋页面 change 权限）门控，Django 校验后按 E6 同一序列化层出 `preview:true` 草稿数据，Astro 以同模板渲染于同源 `/preview/?token=`；后台 Django 模板预览保持现状为迁移期回退（请求流与安全条款＝契约 §3.1/S8）。

边界条款（与端点同等冻结）：`/link-confirm/go/`、`/documents/`、`/admin/`、`/django-admin/`、`/healthz/`、`/readyz/`、`/robots.txt`、`/static/`、`/media/` **不进入 API**，保持 Django 现状；可见性谓词唯一权威＝`notices/lifecycle.py` 现有实现（CURRENT_DEFAULT＝live∧¬expired；HISTORICAL＝Q(live)∨Q(expired)；运营位有效性每请求复核）；搜索语义逐字继承 CONTENT_MODEL §21（非法值视同未提供 200 回退、filter-first＋保序、`-first_published_at` 稳定合并、宽容分页、E1 后端复用）；外链出口一律预构造 `confirm_href`（构造规则唯一出处，go 端点输出层二次校验保持 Django 侧）；富文本段落返回服务端渲染的安全 HTML 片段（features 白名单现状不变）。错误统一 `{error:{code,message}}` 封装（404/405/500/503 四码）；全部响应 `Cache-Control: no-store`、请求时计算——API 零附加新鲜度延迟：≤30s 由立即发布满足（下一请求即见），紧急告警下一请求即见，预约发布＝下一调度周期、其 ≤30s 目标以 **Gate 5 部署验收条件（生产 SCHED_INTERVAL_SECONDS ≤ 30 且 scheduler 容器运行中）** 保障，缺省 60s 不满足目标、不满足即生产切换 blocker（禁止静默带病切换）；preview 经 E9 票据面提供（后台 Django 模板预览保持现状为迁移期回退；E9 未接线期间该缺口为显式跟踪的迁移限制＋生产切换 blocker，不得作为契约终态）；`/api/` 仅经 Compose 内网供 Astro SSR 取数、Caddy 不公开路由。

**一句话可检验**：`docs/api/openapi.json` 中 9 个 GET 端点的 schema 与 `docs/api/README.md` 的条款一一对应，且每条响应字段都能指回 48fd5d6 基线中的模型字段、视图/模板消费位或 CONTENT_MODEL/IA 条款（E9 的数据源为 wagtailadmin 既有 `FormState` 表单暂存与既有权限判定，仍为零新载体）——无现状之外的任何数据面、写端点、认证对象或缓存层。

## 后果

**正面收益**：

- 前后端得以并行：F04 可立即从 `openapi.json` 生成 TS 类型（schema 层），B02 的实现验收有逐字段依据；G4 等价验收与 G5 安全 parity 有了可核对的机器契约。
- R3 风险前置收口：公开 API 面在写任何实现代码之前定形，评审对象是 9 个端点＋若干冻结条款，而非散落的代码决策；breaking 变更自此有明确的"public API 变更升级 R3+"处置通道。
- 等价性由构造保证：契约不发明语义，只投影现有模型/过滤层/模板消费位——B02 复用 `search.services` 与 `lifecycle.py` 即天然对齐，偏离反而需要额外代码。
- 零迁移可静态核验：契约读取面全部是现有模型与既有 E1 搜索后端，B02 不需要任何模型/字段/索引改动。

**代价与权衡**：

- 契约粒度偏"行为镜像"：列表摘要回落链、组稿规则、chips 构造等服务端出全量结果，前端表示层只做截断/标签/高亮——换取等价可核对，代价是响应体比极简 REST 略厚（均为现有页面已公开字段，无数据面扩大）。
- 双载体（README＋openapi.json）需要纪律维持同步；演进规则（契约 §7）已将"同一提交更新"定为义务。
- 富文本段落以服务端渲染 HTML 片段交付：前端插入信任 Django 输出（与现状模板同源同权），代价是 F04 不能对该片段做组件化拆解；这是"事实源唯一"约束的直接推论。
- 新鲜度的 ≤30s 目标对预约发布由调度间隔决定：本修订将「生产 `SCHED_INTERVAL_SECONDS` ≤ 30 且 scheduler 容器运行中」定为 Gate 5 部署验收条件，缺省 60s 仅满足 ≤5min 允许窗口、不满足 ≤30s 目标，不满足即生产切换 blocker——契约不再以"如实记录缺省 60s"替代验收，杜绝静默违反。
- 预览票据面（E9）为本修订新增的评审面：签名票据 ≤60s、绑定管理会话与页面 change 权限、兑换只读零写入、Astro 零权限逻辑零库连接；票据在有效期内可重复兑换为如实记录的残余风险（短时效×会话绑定×权限复核三重约束）。以此在零迁移内闭合冻结 PRD「生产切换前 Wagtail preview 可用」，代价是 B02/F04 各增一件实现物与一项切换前置检查。

**受影响的后续步骤与产物**：B02（feature/headless-api 实现，每 PR 须含既有测试套件＋零计划外 migration 检查＋契约校验；含 E9 端点与后台预览出口钩子）；F04（openapi.json 类型生成＋服务端取数义务清单＋同源 `/preview/` 预览页，契约 §8/§3.1）；F11/B03（拓扑 ADR ②：Caddy 对 `/api/` 不公开路由、旧 Django 路径继续路由的接线即本契约 S1 条款）；G5/B03 切换前置检查新增两项——预览经新前端走通、生产 `SCHED_INTERVAL_SECONDS` ≤ 30（均为生产切换 blocker）；G2 门以本 ADR 转 Accepted 为契约冻结标志。

**复核时点**：R3 GPT Controller 评审（已于 2026-09-15 通过——Human 同意控制器结论，见状态字段头）；G4/G5 验收中发现契约与现状行为偏差时以本 ADR 修订流程处理；未来 i18n、写端点需求（以及 E9 预览面的任何语义变更）一律视为契约变更走 §7 演进规则，禁止在 v1 内静默扩展。**Wagtail 版本升级为固定复核触发器**：E9 有意镜像 wagtailadmin `PreviewOnEdit` 既有表单路径，升级改变该内部路径即破坏 E9 等价性——每次升级必须重跑预览兑换/表单路径安全与兼容性测试（清单＝[docs/api/README.md](../api/README.md) §3.1 维护注记）。

## 替代方案

1. **启用 Wagtail API v2（wagtail.contrib.wagtailapi）/基于 DRF 构建通用 REST 面** → 未选：requirements 中 djangorestframework 仅作为 Wagtail 管理面的传递依赖存在，仓库从未启用任何公开 API app；通用 `pages` 端点会把容器/结构页/草稿面一并卷入公开面治理（与最小面冲突），且 §21.3 非法值回退、入口绑定可见性（CURRENT_DEFAULT/HISTORICAL 双谓词）、校园快讯组稿、轮播运行时复核、confirm_href 门控等冻结语义均需在其上再建定制层——层上加层徒增 R3 评审面与偏离面；8 个只读端点用普通 Django 视图即可达成，符合"简单优先"。
2. **Astro 直连数据库/共享只读库账号** → 未选：直接违反 SPEC-001 Architecture Constraint 1（Django/Wagtail 是唯一事实源，Astro 不连数据库、不复刻业务规则）与 Constraint 2（API 只读、内网、同源拓扑）；且把可见性谓词复制到第二个消费方，等价性从构造保证退化为双实现比对。
3. **构建时静态导出/发布触发重建（headless 静态化）** → 未选：与新鲜度契约直接冲突——紧急告警须下一次请求即见、发布 ≤30s 可见且**不得**触发前端重建/部署；亦与"无 Redis/队列/复杂基础设施"的冻结架构相悖。
4. **GraphQL 单端点** → 未选：对固定五类页面＋少量聚合区而言是投机抽象（SPEC-001 明令禁止）；schema 演进/缓存/查询复杂度治理成本显著高于 8 个稳定 GET 端点，且更难做行为等价评审。
5. **无版本前缀裸路径（/api/…）** → 未选：契约即公共 API 冻结，前缀化 `/api/v1/` 使未来 breaking 变更存在版本化通道（契约 §7），零成本消除一类升级僵局。
6. **预览缺口保持现状（仅后台 Django 模板预览，无 Astro 等价面）** → 未选：与冻结 PRD「生产切换前 Wagtail preview 可用」直接冲突；R3 评审（2026-09-15，控制器 FIX 裁定）明确缺口只能作为显式跟踪的迁移限制与生产切换 blocker 存在，不得作为契约终态——故本修订以 E9 票据面闭合（契约 §3.1）。
7. **Astro 代理后台渲染的预览 HTML（iframe 嵌入 Django 预览页）** → 未选：预览渲染的是 Django 旧模板而非 Astro 正式模板，「预览」失去等价意义（所见非所得）；且需对管理域放宽 frame-ancestors/CSP 纪律，与严格 CSP 要求冲突。E9 改为 Django 出 E6 同构数据、Astro 同模板渲染，等价性与 CSP 均不破。

## 合规性

- **SPEC-001 Contracts 1/3/4 与 Architecture Constraints 1/2/3/5/6**：端点只读公开内容、内网/同源边界（S1）、零迁移（§6 义务条款）、新鲜度逐条落地（F1–F6）、schema 层交付给前端三层分离（§8）；与 Peilige/Peilike 零交叉（S5）。不违反。
- **SPEC-001 发布时效（发布 ≤30s 可见且不触发重建；紧急告警下一请求即见；生产切换前 Wagtail preview 可用）**：F1/F2 请求时计算使手动发布下一请求即见；F4 使紧急告警下一请求即见；预约发布以 Gate 5 部署验收条件（生产 SCHED_INTERVAL_SECONDS ≤ 30）承接 ≤30s 目标、不满足即切换 blocker；E9＋同源 /preview/ 闭合「切换前 preview 可用」，预览权威（认证/授权/数据/票据校验）全在 Django 侧，Astro 零库连接零权限复刻（Constraint 1/2 不破），零迁移（FormState 为 wagtailadmin 既有表，签名票据无载体）。不违反。
- **ADR-0002/0007（服务端模板＋最小 JS 渐进增强）**：本 ADR 不推翻、不改变现状仓库前端；旧前端在切换前保持应急回退与 preview 载体，其退役处置归 B05（Human-only）。Accepted→Superseded 的任何状态变更留待切换治理，本 ADR 不代决。不违反。
- **ADR-0005（Page/Snippet 载体）与 CONTENT_MODEL/IA**：API 全部消费现有载体与冻结语义（§21 过滤层、§16.4 可见性、§1.4 树形 URL、容器 404/不入列表/不入 sitemap 等），无新载体、无新 URL 形态。不违反。
- **ADR-0006（中文搜索后端 E1）**：契约明确搜索固定复用 `search/backends.py` 与 `search/services.py` 既有过滤层，不另立第二套搜索语义。不违反。
- **PRD §20 V1 不做清单**：无部门主页端点（部门仅作为元数据与筛选维度）、无 i18n 端点、无新产品功能面、无投机端点。不违反。
- **"不修改 Wagtail 核心"（02 §0.2-2）**：契约不含任何核心改动；实现建议限定普通 Django 视图层。不违反。
- **数据零迁移红线（R4）**：契约 §6 将零迁移列为 B02 义务并保留"任何 DB/schema/数据变更需求 → 立即 STOP＋Human 决策包"条款；本 ADR 自身零代码、零迁移、零配置变更。不违反。
- **ADR 机制（docs/adr/README.md §4/§5）**：以 Proposed 落盘、不代决状态；README 索引仅新增本 ADR 行并同步 §3 看板；收录范围扩展依据＝SPEC-001（G1 Human 批准）明列"G2 预期产出首批 ADR：① Headless API 契约"，已在索引收录范围注记中留痕。不违反。
- **秘密纪律（00 §4.5）**：契约与 ADR 全文无秘密、无凭据、无内网拓扑细节（仅部署形态约束条款）。不违反。
- **旧仓只读（OR-2）／Peilige·Peilike 隔离**：全文无旧仓读写安排，无跨项目访问安排。不违反。
- **Ticket 红线（peiligo#13 Do Not）**：未实现任何 Django 代码、未改 schema/模型/数据、未为未来功能预留投机端点（E9 由冻结 PRD 直接要求，非投机）；本批改动仅文档（docs/api/*、docs/adr/0008 本修订、部署指南 SCHED 行注记；docs/adr/README.md 索引行与看板随后续状态行一致——2026-09-15 G2 转 Accepted 时已同步）。不违反。

**结论：不违反任何一条，无豁免申请。**
