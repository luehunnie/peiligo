# 内容模型（Content Model）

## 文档信息

| 字段 | 值 |
| --- | --- |
| 文档 | `docs/CONTENT_MODEL.md` |
| 日期 | 2026-08-21（首落盘，A3.1 批次＝M3.1＋M3.2；同日 A3.2 批次＝M3.3 增补 §14–§19；同日 A3.3 批次＝M3.4 增补 §20–§24）；2026-09-10 首页升级批次＝Phase 3.5 模型落地后同步增补 §25，并对 §1.3/§5.1/§8.1/§9.1/§10.1 作定点修订（位点登记见 §25.4） |
| 本步范围 | §1–§13：M3.1 类型清单与 Page/Snippet 载体分配（§1–§4）＋ M3.2 字段级定义、StreamField 白名单、受控标签（§5–§13）。§14–§19：M3.3 状态机、修订/预览/锁、预约与到期字段映射、删除政策（A3.2 批次增补，§1–§13 零改动）。§20–§24：M3.4 搜索索引字段映射、筛选维度契约、D7 三方案对接点、金标集挂接点与断言（A3.3 批次增补，§1–§19 零改动） |
| 引源 | 00_MASTER_PLAN §10 M3.1/M3.2；02_ARCHITECTURE_DOMAIN_PLAN §5 S3.1/S3.2（L74-75 映射）、§0.1 C4；PRD §7/§10/§11；ADR-0004、ADR-0005（Accepted，只读）；INFORMATION_ARCHITECTURE §1–§5（只读）；上游审计 §3.1（定向）；现有代码 `home/models.py`、`departments/models.py`、`src/peiligo/settings/base.py`（只读事实）。M3.4 增补引源：00 §10 M3.4（含 v1.1）＋§2.2 D7；02 §5 S3.4、§8 S6.1；PRD §10/§12；IA §8–§11（M2.2 产物，只读承接）；ADR-0001（C1：wagtail 7.4.2＋modelsearch 1.3.2）；上游审计 §3.4；wagtail 7.4.2/modelsearch 1.3.2/Django 5.2.17 源码亲证（位点见 §20.0）；`search/views.py`、`src/peiligo/urls.py`、各 app `models.py`、`requirements.txt`（只读事实） |
| 分支 | `arch/a3.1-content-model-design`（基于 `rebuild/v1` @ a34d75a）；M3.3 增补分支 `arch/a3.2-state-machine-design`（基于 `rebuild/v1` @ c89acd6）；M3.4 增补分支 `arch/a3.3-search-contract-design`（基于 `rebuild/v1` @ 8baf26f） |
| 步骤约束 | 只产出设计文档；不写代码/迁移/测试；不改视觉 |

## 阅读约定

- **DEFERRED_TO_M3_3**：状态机（draft→published→expired/offline）、DraftStateMixin 行为语义（go_live_at/expire_at 的生效与归档行为）、修订/预览、删除政策——属 M3.3（§14–§19）。本文只冻结**字段位与必填性**，行为语义一行不写，仅留本标记。
- **DEFERRED_TO_M3_4**：search_fields 搜索索引映射、筛选维度契约——属 M3.4（§20–§24），本文不定义，仅留本标记。
- **实现留 B 阶段**：统一确认跳转页为自定义视图（ADR-0005 载体表 #5），本文只冻结**字段与输出安全语义**（§11.4），不造跳转体系；编辑界面按板块显隐事件面板等表单定制亦属 B 阶段实现。
- 字段表列口径：**字段**（业务中文名）｜**属性**（Model 属性名，内建字段标注）｜**类型与约束**｜**必填**｜**引源**。CharField 长度上限为默认值，B 阶段可微调并留痕（同 IA §4.3 slug 口径）。
- 命名口径：§1.2 终判的英文 Model 名为全项目唯一正式名。IA §5 挂载表中的页面类型工作名随本文转正或映射（该表表头已预留"正式类型清单与命名由 M3.1 终判"）；02 §5 S3.1 规格行中的 `StudyMaterialPage`/`GuideEntryPage` 为规格起草期候选名，终判未采纳，理由与映射见 §1.2。后续文档与代码一律使用正式名。
- 字段来源纪律：每字段逐项引源 PRD（或经 02 计划规格明确列出），无"以后可能有用"字段；PRD 未要求的字段一律不设（各类型的显式禁项见表内"无字段声明"行）。

## 1. 类型总清单与命名终判（M3.1）

### 1.1 六类内容载体总表（与 C4/ADR-0005 零冲突）

引源：ADR-0005"载体分配原则表"（Accepted）；PRD §7；IA §2。

| # | 内容 | 中文类型名（冻结） | 正式 Model 名 | 载体 | 可挂板块 | PRD | ADR-0005 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 通知 | 通知页 | `NoticePage` | Page | 校园纪事 / 校园活动 | §7.1 | 载体表 #1 |
| 2 | 文章 | 文章页 | `ArticlePage` | Page | 校园纪事 / 校园活动 | §7.2 | 载体表 #2 |
| 3 | 活动（内容类别，非独立页型） | 活动结构化字段 | `EventFieldsMixin`（仅挂 `NoticePage`/`ArticlePage`，终判见 §2） | Page（载体不变，无独立活动 Page） | 校园活动 | §7.3 | 载体表 #3 |
| 4 | 学习资料 | 学习资料页 | `MaterialPage` | Page | 学习资料 | §7.4 | 载体表 #4 |
| 5 | 软件与工具 | 软件与工具页 | `SoftwareToolPage` | Page | 软件与工具 | §7.5 | 载体表 #5 |
| 6 | 校园指南 | 校园指南页（指南条目） | `GuidePage` | Page | 校园指南 | §7.6 | 载体表 #6 |

载体硬规则（承接 ADR-0005）：上表 Page 六类不得改为 Snippet/设置；下表 §1.3 受控数据不得改为公开 URL 内容；任何载体变更须新开 ADR，不得在实现步骤内静默改判。断言对应 CM-00（§13.5）。

### 1.2 Page 正式命名终判与取舍记录

**终判原则**（任务批令）：选最简单、清晰、长期可维护的一套；均一「内容名＋Page」模式；不为文件名好看或表面区分度引入抽象（如无信息量的后缀/前缀）；中文名随 PRD §7 冻结，后台 `verbose_name` 用中文类型名。

| 正式名 | 后台 verbose_name | 说明 |
| --- | --- | --- |
| `NoticePage` | 通知页 | 与 02 规格、IA 工作名、A2 审查哨兵名三方一致，直接转正 |
| `ArticlePage` | 文章页 | 同上，直接转正 |
| `MaterialPage` | 学习资料页 | IA 工作名转正（取舍见下表） |
| `SoftwareToolPage` | 软件与工具页 | IA 工作名＝02 规格名，直接转正 |
| `GuidePage` | 校园指南页 | IA 工作名转正（取舍见下表） |

**取舍记录**（长期可维护性裁定，不重开载体问题）：

| 候选名 | 出处 | 终判 | 理由 |
| --- | --- | --- | --- |
| `StudyMaterialPage` | 02 §5 S3.1 §1 规格行 | 未采纳 → `MaterialPage` | "Study" 前缀与板块语境、app 归属（resources）重复，加长不加清；`MaterialPage` 已是 IA §5 工作名且 `departments/models.py`、`home/models.py` 代码注释均按此预留 M3 扩展位，转正零改名成本 |
| `GuideEntryPage` | 02 §5 S3.1 §1 规格行 | 未采纳 → `GuidePage` | "Entry" 后缀无信息量（五类内容页皆为部门容器下的叶子条目页），且仅指南单加后缀破坏 `XxxPage` 均一命名；IA 工作名与代码注释同款 |
| `MaterialEntry` / `SoftwareEntry` / `GuideEntry` | A2.2/A2.3 审查报告的 M3 越界 grep 哨兵名（预期名，非契约） | 未采纳 | 审查哨兵名只是"当时预期 M3 会出现的标识符"，随本终判映射为正式名；后续审查 grep 一律改用本文正式名 |
| `EventPage` | 批令明令排除 | 不建 | 见 §2 终判 |

**app 归属**：非本文件冻结项（B 阶段实现自由）。03 计划已示例 `notices` app 承载 `NoticePage`/`ArticlePage`；`MaterialPage`/`SoftwareToolPage`/`GuidePage` 与各 Snippet 的 app 归属由 B 阶段按 03 计划落位。本文字段表中的跨模型引用一律写模型名（如 `Department`），不预设 app 前缀。

### 1.3 受控数据清单（Snippet / 设置）

引源：ADR-0005 载体表 #7–#14；PRD §4.3/§6/§7.4/§7.5/§7.6/§9；C4"部门、受控分类、标签、配置使用 Snippet 或设置模型"。字段定义见 §13。

| 数据 | 正式 Model 名 | 载体 | 用途（M3.2 当前需要，字段只到此） | PRD / ADR-0005 |
| --- | --- | --- | --- | --- |
| 部门 | `Department` | Snippet | 权限锚点、URL 部门段、内容作者元数据、部门筛选维度 | §4.3、§6、§10；#7 |
| 学科·专业方向词表 | `Discipline` | Snippet | `MaterialPage` 受控外键（受控类别） | §7.4；#8 |
| 资料类型词表 | `MaterialType` | Snippet | `MaterialPage` 受控外键（受控类别） | §7.4；#9 |
| 指南类别词表 | `GuideCategory` | Snippet | `GuidePage` 受控外键（受控类别） | §7.6；#10 |
| 适用平台词表 | `Platform` | Snippet | `SoftwareToolPage` 受控多对多 | §7.5；#11 |
| 受控标签 | `Tag`（自定义，继承 taggit `Tag`；词表经 Snippet 管理） | Snippet（词表）＋`ClusterTaggableManager` 挂 Page 侧 | 通知/文章/学习资料的受控关键词（机制终判见 §12） | §7.1/§7.2/§7.4、§10；#12 |
| 首页推荐位 | `FeaturedItem` | Snippet | 数量固定、带起止时间的运营位（载体确认见 §3） | §9、§8；#13 |
| 站点设置 | `SiteSettings` | settings（`BaseSiteSetting`） | 紧急提示、统一反馈邮箱、跳转页文案（载体确认见 §3） | §9、§8、§7.5；#14 |
| 首页轮播项 | `CarouselItem` | Snippet | 首页轮播位条目（V1 基线后首页升级新增，无 ADR-0005 载体表编号；独立 Snippet 不复用 FeaturedItem；字段与校验见 §25.2） | 首页升级 PRD §11/§15；§25.2 |

V1 部门岗位账号不持有任何 Snippet 权限，上述词表/部门/推荐位均由总管理员管理（ADR-0004 决策 3；ADR-0005）。受控标签的"部门账号不能新建自由标签"机制见 §12（CM-08）。

### 1.4 页面树挂载与板块级校验总则

引源：IA §1.3/§5（工作名表随 §1.2 转正）；ADR-0004 决策 1；PRD §6。**公开内容仅挂 `DepartmentContainerPage`；板块级归属限制由页面级校验落实**（IA §5 表头注：类型级白名单无法表达祖级约束）。

**类型级挂载表（parent_page_types / subpage_types 终态）**：

| 页面类型 | parent_page_types | subpage_types | 板块级限制（允许的板块 slug，冻结） | 依据 |
| --- | --- | --- | --- | --- |
| `HomePage`（现状已有） | `wagtailcore.Page`（站点根，唯一实例） | `home.SectionPage`（仅） | — | PRD §6；IA §5 |
| `SectionPage`（现状已有，×5） | `home.HomePage` | `departments.DepartmentContainerPage`（仅） | slug 按 IA §2 冻结五值 | PRD §6 |
| `DepartmentContainerPage`（现状已有） | `home.SectionPage` | **五类内容页（本表下五行）**；不含任何容器/板块类型 | 每板块下按部门建，仅确有内容者（IA §1.3） | ADR-0004 决策 1 |
| `NoticePage` | `departments.DepartmentContainerPage`（唯一父级） | `[]`（叶子） | `chronicle`、`events` | PRD §7.1；IA §5 |
| `ArticlePage` | 同上 | `[]` | `chronicle`、`events` | PRD §7.2 |
| `MaterialPage` | 同上 | `[]` | `materials` | PRD §7.4 |
| `SoftwareToolPage` | 同上 | `[]` | `software` | PRD §7.5 |
| `GuidePage` | 同上 | `[]` | `guide` | PRD §7.6 |

现状衔接：`departments/models.py` 的 `subpage_types = []` 为 M3 前占位（代码注释已预留），B 阶段按本表扩充为五类内容页白名单。补充约束（IA §5）：内容页均为叶子，树深固定四层；容器下不得再建容器；板块下不得跳过容器直接建内容页；Snippet/设置不入页面树。

**所属板块推导规则（无存储字段，单一事实源）**：内容页的所属板块由树位置推导——`自身 → get_parent()（部门容器）→ get_parent()（SectionPage）.slug`，对照 `home.SECTIONS` 冻结清单（`chronicle`/`events`/`materials`/`software`/`guide`）得出板块。各内容页模型提供只读 property（如 `section`/`section_slug`），全站（列表、筛选、前台展示）一律消费该推导值，**不设任何"所属板块"存储字段**（防双源漂移；PRD §7.1/§7.2 的"所属板块"即此推导值）。

**板块级校验方案（clean 方案，冻结）**：

1. **创建/编辑**：各内容页类型 `clean()` 解析所属板块 slug，不在本类型"板块级限制"集合内即抛 `ValidationError`（如 `NoticePage` 挂到 `materials` 下被拒）。创建表单的父容器在提交流程中可得，校验在保存前生效。
2. **移动**：Wagtail 移动页面不触发 `clean()`，板块外移动经官方信号/hook 在移动路径强制同一规则（机制细节 B 阶段实测留痕；**约束本身在此冻结**：任何时点树上不存在违反本表板块级限制的内容页）。移动页面产生的旧 URL 重定向按 Wagtail 原生行为（IA §4.1/§10.2 已核对位点）。
3. **兜底**：部门账号的 Add 权限仅授予本部门容器（ADR-0004），违规放置主要防总管理员误操作与跨板块移动；本条校验纳入 M4.3 越权测试矩阵（断言 CM-02）。
4. **搜索索引映射与筛选维度契约**：DEFERRED_TO_M3_4。

## 2. 活动结构化字段承载终判（EventFieldsMixin）

**终判：采纳 `EventFieldsMixin` 挂载于 `NoticePage` 与 `ArticlePage`，不建独立 `EventPage`。** 与 C4 逐字相容："活动类通过 Notice/Article Page 上的 EventFieldsMixin 结构化字段承载（M3.1 终判），载体仍为 Page，不违反本条"（ADR-0005 决策节引用）。

**类型组织终判**：

- `EventFieldsMixin` 为纯抽象 Mixin（`models.Model` 子类＋`Meta.abstract = True`），**非** Page 子类、非 Snippet、不注册任何 admin/编辑界面；
- 仅 `NoticePage`、`ArticlePage` 以 `class NoticePage(EventFieldsMixin, Page)` 顺序继承（MixIn 在前，字段/校验经 MRO 参与）；`MaterialPage`/`SoftwareToolPage`/`GuidePage`/容器/板块类型**禁止继承**（文档级断言，B 阶段以单一模块定义＋评审核对落实）；
- 定义位置：与 `NoticePage`/`ArticlePage` 同模块单源定义（03 已示例 notices app；app 归属 B 阶段定，"单一模块、双页继承"冻结）；
- 字段集与校验见 §7（§2 只终判载体与组织）。

**候选否决记录**：

| 候选 | 终判 | 理由 |
| --- | --- | --- |
| `EventFieldsMixin` 挂 Notice/Article（02 §5 S3.1 默认候选） | **采纳** | 活动板块承载"通知＋文章＋活动结构化字段"（IA §2 #2）——同一活动既可是通知式短讯也可是长文，独立活动类型无法二者兼顾；PRD §7.2"通知与文章是两种独立内容类型，不通过单一模型强行混用"——独立类型仅为通知/文章两种，活动是**内容类别**而非第三类型；字段单源定义避免双页复制漂移 |
| 独立 `EventPage` | 否决 | 发明第三内容类型，违反上述 PRD §7.2 与本批次令"不建 EventPage"；且会使"通知/文章可否带活动字段"出现第三套答案 |
| 活动字段拆 Snippet＋页面关联 | 否决 | 违反 C4（活动内容载体=Page，ADR-0005 #3）；Snippet 无公开 URL/预览/排程；活动字段是内容本体一部分，跨载体关联徒增查询与权限面 |
| Notice/Article 各自复制一份活动字段 | 否决 | 同一字段集两处定义，长期漂移；Mixin 单源即可 |

## 3. 推荐位与紧急提示载体确认

- **推荐位（首页 FeaturedItem，`Snippet`）**：数量固定、带起止时间、仅总管理员可管理（ADR-0005 #13；PRD §9"总管理员可管理数量固定、具有开始与结束时间的推荐位或置顶位"、§8"只有总管理员可以设置全站重要内容或首页置顶"）。数量固定原则由 IA §7.2 冻结（展示数量为前台消费侧规则，模型不设数量字段）；部门置顶申请走统一工作邮箱（PRD §8），不建模。字段见 §13.3。
- **紧急提示（`SiteSettings` 字段，非独立模型、非页面）**：站点级单例配置，ADR-0005 #14（否决 Snippet 承载的替代方案——单例建可多实例 Snippet 引入误配风险）。首页信息优先级层 1（PRD §9；IA §7.1），起止时间控制展示窗口。字段见 §13.4。

## 4. 部门字段规范（M3.1 §4）

引源：PRD §4.3/§6/§10；ADR-0004；ADR-0005 #7；IA §3.3/§3.4；02 §5 S3.1 §4。

- **五类内容页一律含 `department = ForeignKey(Department, on_delete=PROTECT)`，必填**。前台仅展示部门名称作为作者元数据（PRD §4.3：不显示登录用户名或具体操作人员姓名；PRD §6：部门名称作为内容作者元数据展示，可用于搜索结果筛选）；部门筛选结果不是部门主页（IA §3.3 硬约束）。
- **部门容器绑定**：`DepartmentContainerPage` 增设 `department = ForeignKey(Department, on_delete=PROTECT)`（必填；B 阶段落地——现状最小壳已预留注释）。容器 `slug` 默认取 `department.slug`（URL 部门段，IA §4.1/§4.3）；同一板块页下不得存在两个指向同一 `Department` 的容器（容器 `clean()` 兜底，slug 同父唯一性之外的词源级唯一）。
- **一致性校验（零漂移）**：内容页 `department` 编辑默认值＝父容器的 `department`；`clean()` 强制二者相等，不等即 `ValidationError`——保证部门元数据与树位置（URL 部门段、权限边界）永远一致。
- **PROTECT 语义**：部门被任何内容/容器引用时禁止删除（受控数据治理；部门退场用 `is_active=False` 停用，见 §13.1）。引用解除与删除政策：DEFERRED_TO_M3_3。
- 部门清单与部门 slug 由 `Department` Snippet 承载（IA §3.4；ADR-0005 #7），总管理员维护。

## 5. NoticePage（通知页）字段定义

引源：PRD §7.1 逐条；02 §5 S3.2 §5。必含＝标题、摘要、正文、所属板块（推导）、发布部门、发布时间、**有效期（必填）**；可含＝图片、附件、外部链接、受控标签（PRD §7.1 三句原文逐项落位）。

### 5.1 字段表

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 标题 | `title`（Page 内建，不另设） | CharField(max_length=255)（Wagtail 内建） | 必填 | PRD §7.1 |
| URL slug | `slug`（Page 内建） | 同父唯一；规范 IA §4.3（[a-z0-9-]，建议 ≤64） | 必填（自动生成，可改） | IA §4.3 |
| 摘要 | `summary` | TextField（无 DB 硬上限；列表卡片位由模板截断） | 必填 | PRD §7.1 |
| 正文 | `body` | StreamField（§11 白名单；`min_num=1` 至少一块；JSON 存储） | 必填 | PRD §7.1、§7.7 |
| 所属板块 | —（无存储字段） | 由树位置推导的只读 property（§1.4）；clean 校验 ∈ {`chronicle`,`events`} | 推导必得 | PRD §7.1；IA §5 |
| 发布部门 | `department` | ForeignKey(`Department`, on_delete=PROTECT)；默认与校验同 §4 | 必填 | PRD §7.1、§4.3 |
| 发布时间 | `first_published_at`（Page 内建，只读） | DateTimeField；首次转公开时刻落定并持久（改版重发不重置） | 必填（发布即有） | PRD §7.1 |
| 有效期 | `expire_at`（Page 内建列，本类型经 clean 强制非空） | DateTimeField；到期行为 DEFERRED_TO_M3_3，此处只冻结"必填" | **必填**（CM-01） | PRD §7.1 |
| 图片 | `image` | ForeignKey(`wagtailimages.Image`, null=True, blank=True, on_delete=SET_NULL)——专属题图/列表图 | 可选 | PRD §7.1 |
| 轮播封面图 | `cover_image` | ForeignKey(`wagtailimages.Image`, null=True, blank=True, on_delete=SET_NULL, related_name="+")——首页轮播封面（首页升级批次增补，见 §25.1；ArticlePage 经 §6"逐行相同"同获本行） | 可选 | 首页升级 PRD §12；§25.1 |
| 附件 | `attachments` | ParentalManyToManyField(`wagtaildocs.Document`, blank=True)（0..n；类型/大小/扩展名限制为全站上传策略，见 §11.4） | 可选 | PRD §7.1、§11 |
| 外部链接 | `external_url` | URLField(blank=True)；输出经统一确认跳转页（§11.4） | 可选 | PRD §7.1、§11 |
| 受控标签 | `tags` | ClusterTaggableManager(through=…，§12；blank=True)；仅词表内标签 | 可选（0..n） | PRD §7.1；§12 |
| 活动结构化字段 | （`EventFieldsMixin` 继承，§7） | 校园活动板块下必填组＋校园纪事板块下强制空（§7.2 适用规则） | 板块决定 | PRD §7.3；§2 |

无字段声明：PRD §7.1 未列的字段一律不设（无自定义"通知编号/置顶标记"等——置顶经 `FeaturedItem`，§3）。

### 5.2 校验（clean）

板块 ∈ {`chronicle`,`events`}（§1.4）；`department`＝父容器 `department`（§4）；`expire_at` 非空（CM-01）；`body` ≥1 块；活动字段按 §7.2 适用规则；标签 ⊆ 受控词表（§12，CM-08）。

### 5.3 panels 组织（冻结）

- `content_panels` 顺序：标题（内建）→ 发布部门 → 摘要 → 正文 → 图片 → 附件 → 外部链接 → 受控标签（选择器，§12）→ 事件面板组（`EventFieldsMixin` 注入，校园纪事板块下隐藏，§7.2；表单定制实现留 B 阶段）。
- `promote_panels`：保持官方默认（slug/seo_title/search_description，Page 内建，非新增字段；搜索消费 DEFERRED_TO_M3_4）。
- `settings_panels`：官方 PublishingPanel（含 go_live_at/expire_at 位点；行为语义 DEFERRED_TO_M3_3）。

### 5.4 延期

预约发布语义、到期退出首页/默认列表、历史归档与站内搜索保留（PRD §7.1 后三句）：DEFERRED_TO_M3_3（字段位与必填性本文已冻结）；搜索索引映射：DEFERRED_TO_M3_4。

## 6. ArticlePage（文章页）字段定义

引源：PRD §7.2 逐条；02 §5 S3.2 §6（"同通知去掉有效期必填"）。与 `NoticePage` 字段集完全同构，差异仅一行：

| 差异字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 有效期 | `expire_at`（Page 内建列，保持可空） | DateTimeField；编辑表单默认空（"不默认设置下线时间"）；到期行为 DEFERRED_TO_M3_3 | **可选**（与 §5.1 唯一差异；CM-01 仅约束通知） | PRD §7.2 |

其余字段（标题/slug/摘要/正文 StreamField/所属板块推导{`chronicle`,`events`}/发布部门/发布时间/图片/附件/外部链接/受控标签/EventFieldsMixin）与 §5.1 逐行相同，引源改 PRD §7.2；校验、panels、无字段声明同 §5.2/§5.3（有效期非空校验除外）。通知与文章保持两种独立 Page 类型，不混用（PRD §7.2 末句；ADR-0005 #2）。

## 7. EventFieldsMixin（活动结构化字段）定义与适用规则

引源：PRD §7.3 逐条；02 §5 S3.2 §7。载体与组织终判见 §2；字段如下。

### 7.1 字段表

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 开始时间 | `event_start_at` | DateTimeField(null=True, blank=True) | 校园活动板块下必填；校园纪事下强制空（§7.2） | PRD §7.3 |
| 结束时间 | `event_end_at` | DateTimeField(null=True, blank=True)；成对校验：与开始同时填/同时空，且结束 ≥ 开始（相等合法，零时长活动瞬时"进行中"） | 同上 | PRD §7.3 |
| 活动地点 | `event_location` | CharField(max_length=200, blank=True)——线下地点 | 校园活动且线下（§7.2）：必填；线上：可空、前台展示"线上" | PRD §7.3 |
| 线上标记 | `event_is_online` | BooleanField(default=False) | 必填（有默认值） | PRD §7.3 |
| 报名链接 | `event_registration_url` | URLField(blank=True)；报名跳转至外部系统，V1 无站内报名；输出经统一确认跳转页（§11.4） | 可选 | PRD §7.3 |
| 活动状态 | `event_status`（property，不落库） | 三态按当前时间对比起止：`now < start` → **即将开始**；`start ≤ now ≤ end` → **进行中**（闭区间）；`now > end` → **已结束** | 推导必得（活动板块下起止已必填） | PRD §7.3；CM-03 |

### 7.2 适用规则（板块决定，冻结）

- **板块＝`events`（校园活动）**：`event_start_at`/`event_end_at` 必填（clean 强制）——无起止则三态无法计算，活动板块语义即活动；`event_is_online=False` 时 `event_location` 必填，`True` 时地点可空、前台统一展示"线上"；`event_registration_url` 可选。通知与文章同等适用（IA §2 #2：活动板块承载通知＋文章＋活动结构化字段）。
- **板块＝`chronicle`（校园纪事）**：五个存储字段必须全部为空（clean 对任何已填活动字段报错），编辑面板隐藏该组（实现留 B 阶段）——纪事内容不是活动，双保险防误填。
- 其他板块：本 Mixin 类型根本不可挂（`parent_page_types` 唯一容器＋板块白名单，§1.4）。

### 7.3 延期

已结束活动的列表降权/归档与搜索展示策略：DEFERRED_TO_M3_3/M3_4（本文只冻结状态推导规则本身，CM-03）。

## 8. MaterialPage（学习资料页）字段定义

引源：PRD §7.4（受控三维度＋不做课程库）；PRD §7.7（正文组件）、§10（标题与正文为搜索覆盖面）、§11（附件与外部资源）；02 §5 S3.2 §8。**V1 明确不做课程、教师、学期课程库（PRD §7.4 末句）——不设任何课程/教师/学期字段。**

### 8.1 字段表

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 标题 | `title`（Page 内建） | CharField(max_length=255)（内建） | 必填 | PRD §7.4；§10 |
| URL slug | `slug`（Page 内建） | 同父唯一；IA §4.3 | 必填（自动生成） | IA §4.3 |
| 摘要 | `summary` | TextField | 必填 | 02 §5 S3.2 §8（规格字段；PRD §7.4 未逐字单列，沿用通知/文章摘要语义 PRD §7.1/§7.2，列表与搜索摘要位消费） |
| 正文 | `body` | StreamField（§11 白名单；`min_num=1`） | 必填 | PRD §7.7、§10 |
| 学科·专业方向 | `discipline` | ForeignKey(`Discipline`, on_delete=PROTECT)——受控词表外键，非自由文本（CM-04） | 必填 | PRD §7.4 |
| 资料类型 | `material_type` | ForeignKey(`MaterialType`, on_delete=PROTECT)——受控词表外键（CM-04） | 必填 | PRD §7.4 |
| 关键词标签 | `tags` | ClusterTaggableManager(through=…，§12；blank=True)；仅词表内标签 | 可选（0..n；学科/类型为主分类硬维度，标签为补充检索维度——PRD §7.4 无"必须包含"句式） | PRD §7.4 |
| 外部链接 | `external_url` | URLField(blank=True)；资源优先链官方或可信来源；输出经跳转页（§11.4） | 可选 | PRD §11；02 §5 S3.2 §8 |
| 附件 | `attachments` | ParentalManyToManyField(`wagtaildocs.Document`, blank=True) | 可选（0..n） | PRD §11；02 §5 S3.2 §8 |
| 所属板块 | —（无存储字段） | 推导 property（§1.4）；clean 校验 ∈ {`materials`} | 推导必得 | PRD §7.4；IA §5 |
| 发布部门 | `department` | 同 §4 | 必填 | PRD §4.3 |
| 发布时间 | `first_published_at`（Page 内建，只读） | DateTimeField | 必填（发布即有） | PRD §10（搜索覆盖发布部门与时间语境） |
| 轮播封面图 | `cover_image` | 同 §25.1（首页升级批次增补） | 可选 | 首页升级 PRD §12；§25.1 |

无字段声明：无正文插图/列表图字段（PRD §7.4 未列"图片"——通知/文章的 §7.1/§7.2 可选项不外溢；插图经正文图片块 §7.7）；**轮播封面图 `cover_image` 为本类型唯一图片字段**（首页升级批次增补，非 PRD §7.4 原始范围——首页升级 PRD §12，§25.1）；无有效期字段（PRD §7.4 无有效期要求；文章/资源手动下线属 PRD §8，行为 DEFERRED_TO_M3_3）。

### 8.2 校验与 panels

校验：板块 ∈ {`materials`}；`department` 一致性（§4）；学科/类型必为词表 FK（CM-04）；标签 ⊆ 词表（CM-08）。`content_panels` 顺序：标题 → 发布部门 → 学科·专业方向 → 资料类型 → 摘要 → 正文 → 外部链接 → 附件 → 关键词标签；promote/settings 同 §5.3 口径。

## 9. SoftwareToolPage（软件与工具页）字段定义

引源：PRD §7.5 逐条（"每条内容至少包含"六项）。**网站不直接托管软件安装包（PRD §7.5 原则）；V1 不巡检第三方链接、不开发爬虫。**

### 9.1 字段表

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 软件或工具名称 | `title`（Page 内建，界面标签定制"软件或工具名称"） | CharField(max_length=255)（内建，映射不另设） | 必填 | PRD §7.5 |
| URL slug | `slug`（Page 内建） | 同父唯一；IA §4.3 | 必填（自动生成） | IA §4.3 |
| 用途说明 | `body` | StreamField（**收窄白名单＝§11 全集减附件块**；`min_num=1`）——说明可含截图/步骤表格 | 必填 | PRD §7.5、§7.7 |
| 适用平台 | `platforms` | ParentalManyToManyField(`Platform`, blank=False)；clean 强制 ≥1——受控词表多对多，非自由文本 | 必填（≥1） | PRD §7.5 |
| 来源链接或第三方网盘链接 | `source_url` | URLField；**输出仅经统一确认跳转页**（CM-05；跳转页显示目标域名、资源来源、发布/更新时间、第三方内容可能变化声明——PRD §7.5） | 必填 | PRD §7.5 |
| 授权或费用说明 | `license_note` | TextField | 必填 | PRD §7.5 |
| 发布时间或最后更新时间 | `first_published_at` / `last_published_at`（Page 内建，只读） | DateTimeField ×2；二者居一即满足"或"（展示取较近者由模板冻结，B 阶段） | 必填（发布即有） | PRD §7.5 |
| 所属板块 | —（无存储字段） | 推导 property（§1.4）；clean 校验 ∈ {`software`} | 推导必得 | PRD §7.5；IA §5 |
| 发布部门 | `department` | 同 §4 | 必填 | PRD §4.3 |
| 轮播封面图 | `cover_image` | 同 §25.1（首页升级批次增补） | 可选 | 首页升级 PRD §12；§25.1 |

无字段声明：**无附件字段且正文白名单不含附件块**（不托管安装包，PRD §7.5——附件仅可能经全站 §11 白名单存在于通知/文章/学习资料正文）；无正文插图字段（PRD §7.5 未列；插图经正文图片块；**轮播封面图 `cover_image` 为本类型唯一图片字段**——首页升级 PRD §12，§25.1）；无摘要字段（PRD §7.5 六项无摘要）。

### 9.2 校验与 panels

校验：板块 ∈ {`software`}；`department` 一致性（§4）；`platforms` ≥1；`source_url` 输出仅经跳转页（CM-05）。`content_panels` 顺序：名称（标题）→ 发布部门 → 适用平台 → 用途说明（正文）→ 来源链接 → 授权或费用说明；promote/settings 同 §5.3 口径。版权/安全投诉的立即隐藏与内部记录（PRD §11 末段）经下线/删除政策实现：DEFERRED_TO_M3_3。

## 10. GuidePage（校园指南页）九字段定义

引源：PRD §7.6"统一字段"九项**一字不差、一个不删**（含看似与其他字段重复者，任务批令明令冻结）；02 §5 S3.2 §10。维护治理（部门自维护/邮箱投稿、每月查邮箱、每学期复核、V1 无自动提醒——PRD §7.6 后两句）为运营流程，不建提醒模型。

### 10.1 字段表（九字段逐项）

| # | 字段（PRD 原文） | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- | --- |
| 1 | 服务名称 | `title`（Page 内建，界面标签"服务名称"——映射不删字段、不双轨命名） | CharField(max_length=255)（内建） | 必填 | PRD §7.6 |
| 2 | 指南类别 | `category` | ForeignKey(`GuideCategory`, on_delete=PROTECT)——受控词表（食堂/场馆/服务地点类目由词表维护） | 必填 | PRD §7.6 |
| 3 | 地点 | `location` | CharField(max_length=200)（可含校区/楼栋/房间） | 必填 | PRD §7.6 |
| 4 | 开放时间 | `opening_hours` | TextField（多行自由文本，如"周一至周五 8:00–22:00"；不建结构化时段模型——PRD 无此要求） | 必填 | PRD §7.6 |
| 5 | 联系方式 | `contact` | TextField（电话/邮箱等多行） | 必填 | PRD §7.6 |
| 6 | 补充说明 | `extra_notes` | TextField(blank=True) | 可选 | PRD §7.6 |
| 7 | 责任来源或责任单位 | `responsible_party` | CharField(max_length=200) | 必填 | PRD §7.6 |
| 8 | 维护方式 | `maintenance_mode` | CharField(max_length=20, choices= [("self", "责任部门后台自维护"), ("curated", "统一邮箱投稿·总管理员代维护")])——两选项逐源 PRD §7.6 两句原文 | 必填 | PRD §7.6 |
| 9 | 最后确认日期或更新时间 | `last_confirmed_on` | DateField——显式业务字段（承载"每学期复核/更短人工复核周期"的人工确认语义，CMS 时间戳不承载此语义） | 必填 | PRD §7.6 |

公共内建行：`slug`（IA §4.3）；`department`（§4，责任部门）；所属板块推导 ∈ {`guide`}（§1.4）；`first_published_at`（内建，非九字段项，不另列展示）；另含轮播封面图 `cover_image`（首页升级批次增补，可选，非九字段项——§25.1）。CM-06 必填集＝#1–#5、#7–#9（仅 #6 补充说明可选）。

无字段声明：**无 StreamField 正文**（九字段无"正文"项，补充说明以纯文本承载——表单最简，适配邮箱投稿代维护动线）；无附件/外部链接/标签字段（PRD §7.6 未列）；轮播封面图 `cover_image` 为本类型唯一图片字段（首页升级批次增补——首页升级 PRD §12，§25.1；非 PRD §7.6 九字段原始范围）。

### 10.2 校验与 panels

校验：板块 ∈ {`guide`}；`department` 一致性（§4）；九字段必填集（CM-06）。`content_panels` 顺序：服务名称（标题）→ 发布部门 → 指南类别 → 地点 → 开放时间 → 联系方式 → 补充说明 → 责任来源或责任单位 → 维护方式 → 最后确认日期或更新时间；promote/settings 同 §5.3 口径。

## 11. StreamField Block 白名单与 RichText features 收窄

引源：PRD §7.7（受控内容模块：标题、正文、图片、附件、表格等组合）；PRD §11（附件与外部资源）；02 §5 S3.2 §11；上游审计 §3.1（StreamField＋内建 Block 全家桶；RichTextBlock features 按字段收窄为官方机制，引用 `wagtail/blocks/field_block.py:747-762`；表格用 `wagtail.contrib.table_block`）。

### 11.1 Block 白名单（全站 StreamField 唯一允许集）

| Block（业务名） | 官方实现 | 用途 | 引源 |
| --- | --- | --- | --- |
| 标题块 | CharBlock ＋ 级别 choices（`h2`/`h3`） | 文内小标题；h1 禁用（页面标题已是唯一 h1——无障碍与文档结构） | PRD §7.7 |
| 正文段落块（受控富文本） | RichTextBlock(features=§11.2 清单) | 段落与行内格式 | PRD §7.7 |
| 图片块 | ImageChooserBlock | 插图（经 Wagtail 图片库治理） | PRD §7.7 |
| 附件块 | DocumentChooserBlock | 文档附件（上传策略见 §11.4） | PRD §7.7、§11 |
| 表格块 | `wagtail.contrib.table_block.TableBlock` | 表格 | PRD §7.7 |
| 外链块 | StructBlock(url=URLBlock ＋ link_text=CharBlock) | 文内外部链接；输出经统一确认跳转页（§11.4） | PRD §7.7、§11 |

口径映射：六块＝"标题＋文本段落（受控 RichText）＋图片＋附件＋表格＋外链"——文本段落即受控富文本段落块，**不另设纯文本段落块**（同义双块徒增编辑歧义；纯文本场景由受控 RichText 留空格式承担）；标题块为 PRD §7.7 点名组件（"组合标题、正文、图片、附件、表格"），02 §5 S3.2 §11 同构（标题＝CharBlock 级）。白名单外**一律不得**出现（类型级排除，B 阶段以 StreamField 参数收口并测试）。**禁项（显式）**：RawHTML——原始 HTML 直写块全族（含旧版 Legacy 变体）禁入白名单，任何内容类型、任何字段不得启用（CM-07）；普通部门账号不得输入任意 HTML 或 CSS（PRD §7.7）——本模型全链路无 HTML/CSS 直写入口即结构性满足。类型级收窄：`SoftwareToolPage.body` ＝ §11.1 全集**减附件块**（§9.1，不托管安装包）；`GuidePage` 无 StreamField（§10.1）。

落位提示（B 阶段）：`wagtail.contrib.table_block` 现未在 `src/peiligo/settings/base.py` INSTALLED_APPS 中启用（现状实证），落地时加入；`django-taggit==6.1.0` 已在依赖且 `taggit` 已装（现状实证）。

### 11.2 RichText features 显式白名单

`RichTextBlock(features=[...])`：**`bold, italic, link, ol, ul`**（02 §5 S3.2 §11 示例采纳）。排除项及理由：各级标题（h1–h6——结构经标题块单轨，防双轨漂移与 h1 滥用）；image（插图经图片块，防绕过图片库治理）；文档链接 feature（附件经附件块）；embed/code/hr/strikethrough 等（PRD 未要求，不扩围）。features 机制为官方双层收窄：编辑器工具条按清单渲染，入库内容转换同样按清单过滤（上游审计 §3.1）。

### 11.3 附件上传约束语义（字段级）

允许 PDF、Office 文档与常见图片；设置文件类型与大小限制，检查危险扩展名与伪造 MIME（校验实现与限额数值＝B 阶段安全基线，本文件冻结语义与字段位）；禁止上传密码、个人敏感信息、成绩名单等不应公开数据（PRD §11 上传红线，治理约束）。

### 11.4 外部链接字段与安全语义（统一口径）

- 字段层：所有外链一律 URLField/URLBlock 存**原始 URL**（§5/§6 `external_url`、§7 报名链接、§8 `external_url`、§9 `source_url`、§11.1 外链块）。
- 输出层安全语义（冻结）：前台**不直出裸跳转**——外链输出统一经确认跳转页包装，跳转页显示目标域名、资源来源、发布时间或最后更新时间、第三方内容可能变化的声明，无需强制勾选免责协议（PRD §7.5、§11）。软件工具来源/网盘/报名链接一律适用（CM-05）。
- 实现载体：自定义 Django 视图＋模板（ADR-0005 #5），**实现留 B 阶段，本文不造跳转体系**；`SiteSettings.redirect_notice_text`（§13.4）承载可配声明文案。

## 12. 受控标签机制（终判）

引源：PRD §7.1/§7.2/§7.4（受控标签）；§10（受控类别和标签为搜索/筛选维度）；02 §5 S3.2 §12；上游审计 §3.1（taggit＋ClusterTaggableManager＋受控词表即官方路径）；ADR-0005 #12；ADR-0004 决策 3。

**问题**：taggit 默认自由输入会在保存时自动创建新 `Tag`（modelcluster 集群行为），"受控"不成立——必须拦截自动创建。

**候选与终判**：

| 候选机制 | 终判 | 理由 |
| --- | --- | --- |
| A. 自定义 `Tag`（继承 taggit `Tag`，`register_snippet` 注册词表）＋`ClusterTaggableManager(through=…)`＋页面 clean 拦截未知标签＋表单仅选择器 | **采纳** | Wagtail 官方 taxonomy 模式（词表进 Snippet 管理界面）；标签仍走 taggit 官方集成（修订/预览集群行为正确）；三道闸满足"部门账号只能从既有标签选择"（CM-08，见下） |
| B. taggit 默认自由 Tag＋事后治理 | 否决 | 保存即自动建新标签，CM-08 不成立；词表治理失效 |
| C. 弃 taggit，改 FK/M2M 至自建标签 Snippet | 否决 | 放弃官方 taggit 集成与集群修订语义，02 §5 S3.2 §12 已定向 taggit；自建等价物属重复造轮子 |

**采纳机制的三道闸（CM-08 落实点）**：

1. **权限闸**：`Tag` Snippet 的增改权限仅总管理员组；部门岗位账号不持有任何 Snippet 权限（ADR-0004 决策 3）——词表唯一入口收归总管理员。
2. **校验闸**：挂标签的三类页面（Notice/Article/Material）`clean()` 校验所提交标签**全部已存在于词表**，未知标签即 `ValidationError`——在集群自动创建发生前拦截（表单校验层，非事后）。
3. **表单闸**：编辑表单标签控件为**仅选择器**（从词表中选，无自由输入框）；控件实现细节 B 阶段，约束在此冻结。

`Tag` 字段＝taggit 内建 `name`/`slug` 两字段，**不新增字段**（词表即名称集）；词表初始内容为空，由总管理员按需建立。类别（Discipline/MaterialType/GuideCategory/Platform）与标签的区分：类别为单选/多选受控外键（结构性分类），标签为多值受控词表（补充检索维度）——二者皆 Snippet 词表、皆非自由文本（PRD §7.4/§10）。

## 13. Snippet 与站点设置字段定义

引源：02 §5 S3.2 §13（字段只到 M3.2 当前需要）；ADR-0005 #7–#14；任务批令"字段只到 M3.2 当前需要"——以下各表之外**不设任何字段**。

### 13.1 Department（部门）

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 名称 | `name` | CharField(max_length=100, unique=True)——前台作者元数据唯一展示位 | 必填 | PRD §4.3、§6；IA §3.3 |
| 代号（URL 部门段） | `slug` | SlugField(max_length=64, unique=True)，[a-z0-9-]；创建后原则上不变更（IA §4.3——部门归属变更经移动页面＋原生重定向） | 必填 | IA §4.1/§4.3 |
| 排序 | `sort_order` | IntegerField(default=0)——筛选器/选择器词表顺序 | 必填（有默认） | 02 §5 S3.2 §13 |
| 停用 | `is_active` | BooleanField(default=True)——最小语义：停用即退出新建选择与筛选词表；既有内容展示保留部门名称 | 必填（有默认） | 02 §5 S3.2 §13 |

容器绑定与一致性：§4。panels：名称/代号/排序/停用 四面板一行序。

### 13.2 受控类别词表（Discipline / MaterialType / GuideCategory / Platform）

四词表结构同构，字段仅两枚：

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 名称 | `name` | CharField(max_length=100, unique=True) | 必填 | PRD §7.4（Discipline/MaterialType）、§7.6（GuideCategory）、§7.5（Platform）；ADR-0005 #8–#11 |
| 排序 | `sort_order` | IntegerField(default=0) | 必填（有默认） | 02 §5 S3.2 §13 |

词表由总管理员维护；被引用（FK PROTECT/M2M）时删除受保护（删除政策 DEFERRED_TO_M3_3）。`Platform` 消费形态为 M2M（§9.1），其余为单 FK。

### 13.3 FeaturedItem（首页推荐位）

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 指向内容 | `content` | ForeignKey(`wagtailcore.Page`, on_delete=CASCADE)——选择器过滤仅五类内容页；推荐位随所指内容删除而失效（运营位无独立保留价值） | 必填 | PRD §9；ADR-0005 #13 |
| 开始时间 | `start_at` | DateTimeField；clean 成对校验 end ≥ start | 必填 | PRD §9、§8 |
| 结束时间 | `end_at` | DateTimeField | 必填 | PRD §9、§8 |
| 启用 | `enabled` | BooleanField(default=True)——总管理员的即时开关 | 必填（有默认） | 02 §5 S3.2 §13 |

不设字段声明：无排序字段（展示数量与顺序规则由 IA §7.2 数量固定原则在前台消费侧冻结）、无文案/图片字段（推荐位呈现所指内容自身的标题/摘要）。仅总管理员可管理（§3）。

### 13.4 SiteSettings（站点设置，`BaseSiteSetting` 单例）

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 紧急提示文案 | `alert_text` | TextField(blank=True)——空＝无提示不展示（首页层 1，IA §7.1） | 可选 | PRD §9；ADR-0005 #14 |
| 紧急提示起 | `alert_start_at` | DateTimeField(null=True, blank=True)；与止成对（同时填/同时空，止 ≥ 起） | 可选 | PRD §9 |
| 紧急提示止 | `alert_end_at` | DateTimeField(null=True, blank=True) | 可选 | PRD §9 |
| 统一反馈邮箱 | `feedback_email` | EmailField——每页反馈链接（自动带内容标题与页面地址，PRD §8）与指南投稿邮箱（PRD §7.6）同源单值 | 必填 | PRD §8、§7.6 |
| 跳转页声明文案 | `redirect_notice_text` | TextField(blank=True)——空＝仅渲染 §11.4 四要素结构化信息（域名/来源/时间/变化声明） | 可选 | PRD §7.5；ADR-0005 #14 |

编辑权限收归总管理员侧（ADR-0005 替代方案 3 遗留要求）。不设字段声明：无统计/分析配置（PRD §12 分析位点注记归 M2.2/B 阶段）、无其他站点配置。

### 13.5 断言清单（CM-00–CM-08，B 阶段测试与 M4.3 越权矩阵对应）

| 断言 | 内容 | 落点 |
| --- | --- | --- |
| CM-00 | 每种公开内容类型（六类）均为 Page，且父级只能是本部门容器（`DepartmentContainerPage`）；Snippet/设置不入页面树 | §1.1/§1.4；ADR-0004/0005 |
| CM-01 | 通知必填集含有效期（`expire_at` 非空，clean 强制；文章不约束） | §5.1/§6 |
| CM-02 | 通知/文章父级仅校园纪事/校园活动板块下的本部门容器（板块白名单＋部门一致性 clean） | §1.4/§4；M4.3 |
| CM-03 | 活动状态三态按当前时间与起止正确计算（即将开始/进行中/已结束，闭区间） | §7.1 |
| CM-04 | 学习资料学科·专业方向与资料类型必为受控词表 FK（非自由文本、非空） | §8.1 |
| CM-05 | 软件工具外链（`source_url`）仅经统一确认跳转页输出 | §9.1/§11.4 |
| CM-06 | 指南九字段必填集＝服务名称/指南类别/地点/开放时间/联系方式/责任来源或责任单位/维护方式/最后确认日期或更新时间（仅补充说明可选） | §10.1 |
| CM-07 | 正文 Block 白名单不含 RawHTML 全族（含 Legacy 变体），任何类型/字段零出现 | §11.1 |
| CM-08 | 部门账号不能新建自由标签（权限＋clean 拦截＋仅选择器三道闸） | §12；M4.3 |

（本文 M3.1/M3.2 范围断言即 CM-00–CM-08；状态机断言 PS-xx 与搜索映射断言分别属 M3.3/M3.4，不在本文。）

## 14. 内容生命周期状态机（M3.3）

### 14.1 适用对象与载体事实（零新增字段）

**适用对象＝§1.2 五类内容页**（`NoticePage`/`ArticlePage`/`MaterialPage`/`SoftwareToolPage`/`GuidePage`）。结构页（`HomePage`/`SectionPage`/`DepartmentContainerPage`）与 §1.3 受控数据（Snippet/设置）**不适用**本状态机：结构页是站点骨架，live 位保持 True、不配预约/到期运营动线（误下线结构页属运营事故，由 M4 权限治理防；非状态机语义缺口）；受控数据无内容生命周期——`FeaturedItem` 的生效窗口与 `SiteSettings` 紧急提示窗口是"展示窗口"语义（§15.4 终判），非生命周期状态。

载体事实（上游审计 §3.3 引证 `wagtail/models/draft_state.py:35-38`）：Wagtail 7.4.2（`requirements.txt` 冻结）Page 已内建 `DraftStateMixin`（`live`/`has_unpublished_changes`/`first_published_at`/`last_published_at`/`go_live_at`/`expire_at`）及修订/预览/锁能力，Page 与 Snippet 通用。**五类内容页不新增任何状态字段**——状态由内建列纯推导（§14.2），§5–§13 冻结的字段位与必填性零变化（本批为纯设计，零代码）。

### 14.2 状态集合与推导规则（纯计算，不落库）

五状态，按优先级自 Page/Revision 内建列与当前时刻推导（与 §7.1 `event_status` 同款"纯计算、不落库"口径；B 阶段落实为只读 property 与测试断言，不新增存储字段）：

| 状态 | 中文名 | 推导条件（优先级自上而下，先命中先得） |
| --- | --- | --- |
| S2 `live` | 已发布（在线） | `live=T ∧ expired=F`；子态 S2a 无未发布修订（`has_unpublished_changes=F`）／S2b 有未发布修订（编辑存草稿后） |
| S1 `scheduled` | 预约发布中 | `live=F ∧ 存在待执行预约修订`（修订级 `Revision.approved_go_live_at` 非空；未到点，或到点后任务窗口内待执行——窗口见 §16.3；涵盖从未发布页的首次预约与 expired/unpublished 页的重新预约；对象级 `go_live_at` 不参与判定，残留语义见下注） |
| S3 `expired` | 已到期 | `live=F ∧ expired=T`（到期任务已执行） |
| S4 `unpublished` | 已下线 | `live=F ∧ expired=F ∧ first_published_at 非空`（曾发布、被手动下线） |
| S0 `draft` | 草稿（从未发布） | `live=F ∧ expired=F ∧ first_published_at 空` |

注：live 页带未来 `expire_at` 属 S2 的属性（预约下线位点），**不单设状态**——任务执行前一律按 S2 可见，前台可见性判定不依赖该属性（§16.4）。`live=T ∧ expired=T` 不出现（E7 到期动作原子地同时置 `live=F`/`expired=T`），推导函数对合法数据总可判定。

S1 判定注记（对象级 `go_live_at` 残留语义；Wagtail 7.4.2 源码亲证，A3.2 设计审查 F-1 修复）：**E3 到点发布与 E7/E8 下线均不清除对象级 `go_live_at`**——发布动作全程无对象级清除，仅任务执行/转 live 时清修订级 `approved_go_live_at`（`publish_revision.py` L113-119/L134）；下线同仅清修订级（`unpublish.py` L78）；该对象列仅在编辑表单保存时重写。故"预约发布→到期/下线且期间无编辑"的常规序列会残留过去值，若以该列判 S1 将把 S3/S4 误判为预约中，并经 §16.4 HISTORICAL 谓词使过期通知漏出归档（PRD §7.1 风险）。S1 因此挂钩待执行修订——与官方语义同源：调度引擎工作集即按修订级 `approved_go_live_at` 取件（`publish_scheduled.py` L91-93），官方状态谓词 `scheduled_revision`/`approved_schedule`/`status_string` 同一定义（`draft_state.py` L73-92/L175-177）。据此三序列闭合：残留＋`expired=T` 正确判 S3；残留经 E8 手动下线正确判 S4；"仅存草稿＋填预约未点发布"（表单持久化对象列、修订级未登记，登记仅随发布动作 L116）判 S0/S4——均不误判 S1。修订级 `Revision.approved_go_live_at` 为内建列（`revisions.py` L113），§14.1"零新增字段"声明不变。

### 14.3 转换表（全边枚举，每边一条 PS 断言）

| # | 起点 → 终点 | 触发 | 执行者 | 语义要点 | 断言 |
| --- | --- | --- | --- | --- | --- |
| E1 | draft → live | 立即发布 | 部门账号（本部门内容，无需审批，PRD §8）／总管理员 | `first_published_at` 落定并持久（§5.1 冻结：改版重发不重置）；发布前过该类型全部 clean（含 §16.2 未来性校验） | PS-14 |
| E2 | draft → scheduled | 保存并设置未来 `go_live_at` | 同 E1 | 预约发布（PRD §7.1/§7.2）；预约期间前台不可见 | PS-15 |
| E3 | scheduled → live | `publish_scheduled` 到点自动执行 | 系统（无人工） | 到点可见存在任务周期级窗口（≤1 小时，§16.3；验收口径归 M5.1） | PS-16 |
| E4 | scheduled → 预约前原态（draft/unpublished/expired，按 §14.2 推导回落） | 取消预约（解除待执行修订——7.4.2 内建 unschedule 动作清修订级 `approved_go_live_at`；对象级 `go_live_at` 残留无害，§14.2 注） | 编辑者 | 解除后状态＝预约设置前的原态；操作机制 B 阶段实测留痕，约束在此冻结 | PS-17 |
| E5 | S2a → S2b | 保存修订（不发布） | 具编辑权者 | 产生修订记录（§15.1），live 不中断、前台内容不变 | PS-11 |
| E6 | S2b → S2a | 发布修订 | 同 E1 执行者 | `last_published_at` 更新；过 clean（§16.2） | PS-11 |
| E7 | live → expired | `expire_at` 到点＋`publish_scheduled` 执行 | 系统 | 带 `set_expired=True` 的 unpublish（审计 §3.3 引证 `wagtail/actions/unpublish.py:56-57`）：内容、修订、slug/URL 全保留，退出前台与默认列表；**仅对 live 页生效** | PS-18 |
| E8 | live → unpublished | 手动下线（unpublish） | 部门（仅本部门内容）／总管理员 | PRD §8"文章和资源可由部门手动下线"；通知亦可先于到期手动下线；前台即时不可见 | PS-19 |
| E9 | expired → live | 重新发布（立即） | 同 E1 执行者 | `expired` 位复位；NoticePage 须过 §16.2（新有效期在未来）——过期通知重新上线必须给新有效期 | PS-20 |
| E10 | unpublished → live | 重新发布（立即） | 同上 | 同 E9 校验口径 | PS-20 |
| E11 | expired／unpublished → scheduled | 重新预约（设置未来 `go_live_at`） | 同上 | 同 E9 校验口径先行（预约通知的 `expire_at` 亦须未来） | PS-20 |

**非法转换（表外全称断言，PS-21）**：一切未列边皆非法。显式反例与理由：

- draft → expired／draft → unpublished：从未在线，无到期/下线可言；到期任务仅处理 live 页（E7），unpublish 语义仅对 live 页成立。
- scheduled → expired／scheduled → unpublished：预约页非 live，`expire_at`/unpublish 均不生效；离态仅 E3（到点发布）或 E4（取消回落）。
- expired → unpublished：已离线，无再下线边；二者区别仅在下线成因（到期任务 vs 手动），均经 E9–E11 离态。
- 任何 → draft：`first_published_at` 持久非空后不可回退"从未发布"。
- live → scheduled：预约发布仅自非 live 态进入（E2/E11）；live 态下 `go_live_at` 无转换语义（不产生边，不另设校验——官方面板位点保留）。

**编辑与状态的正交声明**：expired/unpublished/scheduled 页允许继续编辑并保存修订——`has_unpublished_changes` 对 S1/S3/S4 同样成立，属修订史范畴（§15.1），**不是状态转换**；状态仅经 E1–E11 变更。

### 14.4 与活动状态（event_status）的正交声明

§7.1 `event_status`（即将开始/进行中/已结束）是**内容语义时间**的展示层推导，与本节**发布治理时间**的生命周期状态正交：活动已结束的页面仍可为 live（PRD §7.3 无"活动结束即下线"要求）。已结束活动的列表降权/归档与搜索展示策略（§7.3 延期项）＝前台消费口径，归 M5.2 可见性总表与 M3.4 索引映射，本文不预设（处置见 §19.2）。

## 15. 修订、预览与锁

### 15.1 修订（Page 内建，V1 全保留）

- 载体：Page 内建修订能力（`RevisionMixin` 家族，Page 与 Snippet 通用——审计 §3.3）；五类内容页零新增配置。PRD §5："内容修改使用 Wagtail 自带的基础修订历史，记录操作者和时间"——内建修订即完整满足，**V1 不自建修订/审计模型**。
- 行为语义：每次保存（存草稿、发布、预约）各产生一条修订记录（操作者＋时间戳）；发布动作在修订链上标记已发布版本；版本回退（rollback）为内建能力，回退产生新修订、不覆写历史。
- 保留政策：V1 全保留，不配置修订数上限或清理任务（PRD 无清理要求；修订体量的存储影响列入 M7.2 非功能基线观察项，本步不设阈值）。断言 PS-11。

### 15.2 预览（内建后台预览；V1 无任何匿名草稿通道）

- 后台预览：Page 内建（登录且具备该页编辑/预览权限者，可预览最新草稿修订）。
- 前台不可见性：draft／scheduled（未到点）／unpublished／expired 页对未登录访客一律不可达；预约页前台 404 且不入任何列表（§16.4 CURRENT_DEFAULT；运营验收口径归 M5.1 文档 §1，本文冻结语义）。
- 共享预览链接：V1 不提供任何免登录草稿预览通道；若所用 Wagtail 版本内建共享预览功能，B 阶段安全基线（M7.1）核验其默认状态并显式关闭留痕——本文不预设其默认值，以安全基线实测为准。
- Snippet/设置：无预览语义（保存即生效；推荐位/紧急提示的时效由 §15.4 窗口判定承载）。

### 15.3 锁（内建，默认行为）

保留内建锁定（`locked`/`locked_at`/`locked_by`）默认行为，V1 无自定义锁策略；锁定是编辑互斥提示，**不是发布闸**、不影响状态机（锁定的页仍可被具发布权者按 §14.3 转换——解锁权限面归 M4 权限矩阵）。

### 15.4 Snippet 侧 mixin 取舍终判（FeaturedItem 等不混入 DraftStateMixin）

| 模型 | `DraftStateMixin`（live/go_live_at/expire_at） | `RevisionMixin`／预览 | 终判理由 |
| --- | --- | --- | --- |
| `FeaturedItem` | **不混入** | 不启用 | ①生效窗口已由 M3.2 冻结字段承载（`start_at`/`end_at`＋`enabled`，§13.3）——再叠 `go_live_at`/`expire_at` 即双窗口双源漂移；②无草稿/发布流价值（仅总管理员即时运营，无协作评审场景，PRD §8/§9）；③审计 §3.3"用独立模型（含起止时间）即可"的本意＝时间窗口能力，冻结字段已等效达成，无需 mixin |
| `Department`／`Discipline`/`MaterialType`/`GuideCategory`/`Platform`／`Tag` | 不混入 | 不启用 | 词表与权限锚点无生命周期语义；总管理员直改即生效 |
| `SiteSettings` | 不混入 | 不启用 | 单例配置；紧急提示窗口（`alert_start_at`/`alert_end_at`，§13.4）是"展示窗口"语义，与 FeaturedItem 同口径 |

**FeaturedItem 展示有效性判定（语义冻结；前台消费实现归 B 阶段前台/M5.2）**：`enabled ∧ start_at ≤ now ≤ end_at ∧ 所指页 ∈ CURRENT_DEFAULT（§16.4）` 四条件同时成立才于首页展示；数量与顺序规则归 IA §7.2（§13.3 冻结口径不变，"数量固定、起止时间、仅总管理员"三要素齐）。断言 PS-13/PS-22。

## 16. 预约与到期字段映射（go_live_at / expire_at 一览）

### 16.1 逐模型一览表（冻结）

| 模型 | `go_live_at`（预约发布） | `expire_at`（到期） | 引源 |
| --- | --- | --- | --- |
| `NoticePage` | PublishingPanel 位点可用（§5.3 冻结） | **必填**（CM-01）＋**须晚于当前时刻**（§16.2 新增时间维语义） | PRD §7.1（预约发布＋有效期） |
| `ArticlePage` | 可用 | 可选、编辑表单默认空（"不默认设置下线时间"，§6 冻结）；若填写则须未来（§16.2） | PRD §7.2 |
| `MaterialPage` | 可用（内建透传） | **V1 clean 强制空** | PRD §7.4（无有效期要求）／§8（退场走手动下线） |
| `SoftwareToolPage` | 同 MaterialPage | 同上（强制空） | PRD §7.5／§8 |
| `GuidePage` | 同上 | 同上（强制空；与 02 S5.1 草案"指南不设"口径一致） | PRD §7.6／§8 |
| `FeaturedItem`／`SiteSettings`／词表／`Department` | 无（不混入，§15.4 终判；时效由各自冻结字段承载） | 无 | §13 |

两点口径说明：①**预约发布对五类内容页均可用**——PRD §7.1/§7.2 点名要求于通知/文章，其余三类无 PRD 禁令；内建能力零成本透传，加闸反需自定义代码，违背最简实现（禁项才是"无 PRD 要求即不设"，内建列的可用性不属扩围）。②**Material/Software/Guide 的 `expire_at` clean 强制空**沿用 §7.2 活动字段"校园纪事板块强制空"的同一模式：官方面板位点保留（§5.3 口径不变），值层拦截（防常青内容被误配到期而静默消失——指南/资料/软件无有效期语义，PRD §8 指定其退场方式＝部门手动下线 E8）；面板隐藏属 B 阶段表单定制。

### 16.2 发布未来性校验（新增语义；落实层＝clean）

- NoticePage：`expire_at` 非空（§5.2 已冻结）**且晚于当前时刻**——防"发布即已过期"的无效转换；编辑过期通知必然同步给出新有效期，E9/E10/E11 随 clean 自然强制。
- ArticlePage：`expire_at` 可空；若填写则须未来。
- 落实层＝各类型 `clean()`（发布动作经同一校验链，单一闸口）；B 阶段测试按 PS-20 断言（立即发布/重新发布/重新预约三路径各测）。

### 16.3 `publish_scheduled` 任务语义（模型层）

- 到点动作由官方管理命令 `publish_scheduled` 执行，官方建议**每小时**运行（审计 §3.3 引证 `docs/reference/management_commands.md:19-24`）：发布 `go_live_at` 到点的 scheduled 页（E3）；对 `expire_at` 到点的 live 页执行带 `set_expired=True` 的 unpublish（E7）。**到期任务仅处理 live 页**——draft/scheduled 页的 `expire_at` 不触发任何转换（§14.3 非法表）。
- 精度边界：到点可见/不可见存在最长 1 小时任务窗口。该窗口的验收口径、容器环境部署形态（独立 cron/任务容器）与错过到点的补偿语义**归 M5.1**（`PUBLISH_ARCHIVE_SCHEDULING.md` §1/§3）；本文只登记其存在，不展开。
- 断言 PS-16（E3）／PS-18（E7）。

### 16.4 到期与归档口径：CURRENT_DEFAULT / HISTORICAL / ARCHIVE（V1 边界终判）

三口径术语定义（供 M3.4/M5.1/M5.2 引用；查询实现归各自批次）：

| 口径 | 定义 | 消费位置 | 落地批次 |
| --- | --- | --- | --- |
| **CURRENT_DEFAULT**（当前有效集） | 状态 ∈ {S2 live} 的内容页（draft/scheduled 未到点/expired/unpublished 一律不含） | 前台路由（非本集具名 URL＝404）、首页、各板块默认列表——**V1 全部前台位置消费此集** | V1 即生效（本文冻结语义；模板/queryset 随 B 阶段前台落地） |
| **HISTORICAL**（历史归档集） | CURRENT_DEFAULT ∪ {S3 expired}；expired 条目须标注"已过期" | 各板块"历史归档"视图 | **M5.2**（`PUBLISH_ARCHIVE_SCHEDULING.md` §6/§7 总表） |
| **ARCHIVE-SEARCH**（归档搜索口径） | 站内搜索默认包含 expired 通知并标注 | 搜索结果 | **M5.2**（同上 §7）；索引字段映射归 M3.4（§20–§24，本文零预设） |
| **差异登记：HISTORICAL 消费位的具名 URL 放行**（M5.2 载体①补记行，§6.3-4 义务兑现） | HISTORICAL 同谓词（S2 ∪ S3）——五类内容页路由叶子判定对 S3 放行渲染（页首「已过期」横幅），S0/S1/S4 具名 URL 仍 404 | expired 内容页具名 URL（`PUBLISH_ARCHIVE_SCHEDULING.md` §6.3 载体①；B 阶段裁定随 arch/m5.2 实现留痕——commit 与测试注释） | **M5.2 已落地**（`LifecycleStateMixin.route` 覆写；与 CURRENT_DEFAULT 行"非本集具名 URL＝404"的字面差异即本行登记对象，该行语义不动） |

**R4 张力处置（PRD §7.1 第三句 vs Wagtail 默认 live-only——显式登记，禁止假装已解决）**：PRD §7.1"到期后自动退出首页和默认列表，但保留在历史归档及站内搜索中"（PRD §8"通知到期自动归档"同义）在 V1 拆为两层兑现——①**数据保留层（即时成立，本文冻结）**：expired＝带 `set_expired` 的 unpublish（E7），内容、全部修订、slug/URL 全保留、可随时重新发布（E9），"保留"自 V1 第一天为真（PS-24）；②**查询可见层（未解决，M5.2 契约）**：归档视图与"搜索含 expired"是视图级自定义（自定义 queryset 包含 `expired`＋标注——审计 §3.3"注意张力"/风险 R4：漏做即违反 PRD §7.1 验收），**在 M5.2 落地前，本仓库任何前台/搜索实现与文档不得声称已提供历史归档查询**；V1 现状＝CURRENT_DEFAULT 全覆盖，到期即前台不可见。该缺口在此登记为 M5.2 的输入，**本文不关闭它**（PS-26）。unpublished 恒不入三口径（PS-25；M5.2 §7 同口径，本文先冻结语义）。

### 16.5 M3.4 搜索可见性预留边界（仅语义定义，不做字段映射）

M3.4（§20–§24）可引用的本节锚点：①搜索可见性的**状态谓词**一律以 §14.2 推导与 §16.4 三口径为准，M3.4 不得另立可见性语义；②过期内容的搜索包含规则＝ARCHIVE-SEARCH 口径（细则 M5.2），M3.4 §24 只留指针（02 S3.4 已定）；③draft/scheduled/unpublished 永不入搜索消费集。`search_fields` 索引映射、筛选 facet、后端选型全部 DEFERRED_TO_M3_4，本文零预设。

## 17. 删除政策

### 17.1 默认路径：下线/到期，不删数据

PRD §8"内容默认下线或归档，不直接永久删除"——退场默认路径＝E8 手动下线或 E7 到期（两者数据零删除、修订全保留、可恢复，恢复边界见 §17.5）。**V1 不建**软删标记字段、回收站模型或"已删待清"中间态：unpublish/expired 即本项目语义上的软删除，不设第二套机制。

### 17.2 永久删除（仅总管理员，硬删，不可恢复）

- **执行权**：仅总管理员（PRD §8）；权限组配置与越权矩阵归 M4（PS-12 断言先行冻结，M4.3 测试）。部门账号对任何内容（含本部门）无删除权限，仅可 unpublish 自己内容。
- **适用范围**：测试数据、违法内容、明确无保留价值的记录（PRD §8 原文三情形，不得扩围）。
- **动作语义**：Wagtail 页面删除为数据库硬删——Page 行＋全部修订一并移除，**产品内不可恢复**；恢复仅存在于运维层（数据库备份恢复＋恢复演练，PRD §15），属运维事件而非产品能力。
- **留痕**：删除动作进入内建后台页面历史/操作日志（操作者＋时间）；V1 不自建删除审计模型（PRD §8 无此要求；M5.2 PA-05"产生审计记录"的验收载体＝内建日志，其口径 M5.2 定）。
- **纠错快速通道（PRD §11 末段处置，承接 §9.2 延期项）**：版权/安全投诉→总管理员**立即 unpublish（E8）**＋内部记录＝修订与操作日志天然留痕，核实后决定恢复（E10）或永久删除——"立即隐藏"用下线实现而非删除，与 §17.1 默认路径一致。
- **删除前影响面提示**：被推荐位引用的内容页删除时将连带移除 N 个推荐位（§17.3），后台应提示该影响（UX 细节 B 阶段；语义在此冻结）。

### 17.3 引用完整性（FK on_delete 交互终判）

| 引用方 → 被删对象 | on_delete（M3.2 已冻结） | 删除政策（本节终判） |
| --- | --- | --- |
| `FeaturedItem.content` → 内容页 | CASCADE（§13.3） | **推荐位随所指内容删除而同删，零悬挂引用**。02 S3.3 草案 CM-13 曾默认"阻止删除并提示"，本步终判**不采纳**：①§13.3 CASCADE＋"运营位无独立保留价值"已冻结，阻止删除需翻案冻结字段（本批禁改 §1–§13）；②违法内容须快速净除的动线不应被运营位阻塞；③CASCADE 后零悬挂即无完整性缺口。删除前影响面提示（§17.2）替代"阻止"作为操作者保护。断言 PS-13。 |
| 内容页/容器 `department` → `Department` | PROTECT（§4/§13.1） | 被任何内容/容器引用即拒删（ProtectedError）；**部门退场＝`is_active=False` 停用**（§13.1 冻结，既有内容展示保留部门名称）。从未被引用的部门可删（拦截自然放行）；已用部门原则上永不物理删除（slug 即 URL 部门段，删除断历史链）。断言 PS-27。 |
| `MaterialPage.discipline`/`material_type`、`GuidePage.category`、`SoftwareToolPage.platforms` → 四词表 | PROTECT（§8.1/§9.1/§10.1；现状代码实证） | 被引用不可删（内建拦截）；无引用可删（词表治理＝总管理员职责，无额外闸；后台拒绝信息即引用证据，词表退场先观察引用）。断言 PS-27。 |
| 内容页 `tags`（through）→ `Tag` | through 行 CASCADE（taggit 官方模式，现状代码实证） | 删除标签＝解除全部关联（through 行级联），**内容页本体零影响**；仅总管理员的低频词表治理操作。断言 PS-28。 |
| `NoticePage.image` → `wagtailimages.Image`／`attachments` → `wagtaildocs.Document` | SET_NULL／M2M | 删除内容页不影响媒体库资产（图片/文档是全站库资产非页面从属）；媒体库自身清理治理归运维，不在本政策。 |

### 17.4 容器与结构页删除约束

- `DepartmentContainerPage` 非空（其下有任何内容页）时**拒绝删除**——防整部门连带误删；须先迁移子内容或按 §17.2 逐条处理。约束在此冻结，实现（clean/hook 拦截）B 阶段留痕。断言 PS-29。
- `SectionPage`/`HomePage`：结构骨架，删除非 V1 运营运线；同一非空约束适用（板块页下有容器即拒）。断言 PS-29。
- 五类内容页均为叶子（§1.4 `subpage_types=[]`），**无子树连带删除面**——内容页删除仅自身（＋§17.3 连带规则）。

### 17.5 三态退场边界表（恢复边界；完整三态对比表归 M5.2 §8）

| 退场方式 | 数据 | 产品内恢复 | 执行者 |
| --- | --- | --- | --- |
| 到期（E7） | 全保留（内容＋修订＋slug/URL） | 可（E9 重新发布；通知须新有效期） | 系统触发；重发布由人执行 |
| 下线（E8） | 全保留 | 可（E10） | 部门（本部门）／总管理员 |
| 永久删除（§17.2） | 硬删（Page 行＋全部修订） | 不可（仅运维备份恢复） | 仅总管理员 |

## 18. 断言清单（PS 系列；B 阶段测试与 M4.3 越权矩阵对应）

**编号口径**：**PS-xx**（00 M3.3 v1.x 指定）。02 S3.3 草案编号 CM-10–CM-13 逐条映射为 PS-10–PS-13（别名留痕，内容一字不丢）；PS-14 起为本批增补。编号自 10 起，避开 02 S5.1 为 `PUBLISH_ARCHIVE_SCHEDULING.md` 预留的 PS-01–PS-05 数值区间（跨文档消歧处置见 §19.3 编号登记）。

| 断言 | 内容 | 落点 |
| --- | --- | --- |
| PS-10（＝CM-10） | 状态转换仅按 §14.3 表发生；表外转换全非法（含显式反例清单逐条不得发生） | §14.3；M4.3 |
| PS-11（＝CM-11） | 每次保存产生修订并记录操作者与时间；发布标记已发布修订；回退产生新修订不覆写历史 | §15.1 |
| PS-12（＝CM-12） | 页面 delete 权限仅总管理员组；部门账号仅可 unpublish 本部门内容（权限配置 M4 落实，断言先行冻结） | §17.2；M4.3 |
| PS-13（＝CM-13） | 推荐位引用被删内容＝CASCADE 连带同删、零悬挂；展示有效性四条件（`enabled` ∧ 起止窗口 ∧ 指向 ∈ CURRENT_DEFAULT） | §15.4/§17.3 |
| PS-14 | E1 立即发布：`first_published_at` 落定且持久（改版重发不重置） | §14.3 |
| PS-15 | E2 预约未到点：S1＝存在待执行修订（修订级 `approved_go_live_at` 非空，对象级 `go_live_at` 残留不参与判定）；前台 404 且不入任何列表；仅存草稿＋填预约未发布≠S1（判 S0/S4） | §14.2/§14.3 |
| PS-16 | E3 到点自动发布：`publish_scheduled` 执行后转 live（≤1 小时任务窗口内）；对象级 `go_live_at` 残留不清除，推导仍为 S2 | §14.2/§14.3/§16.3 |
| PS-17 | E4 取消预约仅回落预约前原态，不产生其他状态变更 | §14.3 |
| PS-18 | E7 到期仅经任务对 live 页生效（`set_expired` unpublish）；draft/scheduled 页永不因 `expire_at` 转换 | §14.3/§16.3 |
| PS-19 | E8 手动下线：部门仅本部门内容、总管理员任意；前台即时不可见 | §14.3 |
| PS-20 | 发布类边（E1/E9/E10/E11 及 E6）：NoticePage `expire_at` 非空且未来；ArticlePage 填写时须未来 | §16.2 |
| PS-21 | §14.3 表外全称非法（全称断言＋反例清单） | §14.3 |
| PS-22 | FeaturedItem 展示有效性＝四条件合取；数量固定与仅总管理员管理（§13.3/§15.4） | §15.4 |
| PS-23 | Material/Software/Guide 的 `expire_at` clean 强制空（官方面板位点保留） | §16.1 |
| PS-24 | expired 页内容、修订、slug/URL 零删除，可重新发布（数据保留层） | §16.4/§17.5 |
| PS-25 | V1 前台全部位置＝CURRENT_DEFAULT：draft/scheduled/unpublished/expired 不可见（URL 404＋不入列表）；unpublished 恒不入任何口径 | §16.4 |
| PS-26 | HISTORICAL/ARCHIVE-SEARCH 归 M5.2；落地前任何实现/文档不得声称已提供历史归档查询（缺口登记不可在 M5.2 前关闭） | §16.4 |
| PS-27 | Department/四词表被引用时删除被 PROTECT 拒（ProtectedError）；部门退场＝`is_active=False` | §17.3 |
| PS-28 | 删除 Tag 仅解除关联（through CASCADE），内容页本体零影响 | §17.3 |
| PS-29 | 非空容器/板块页删除被拒；内容页为叶子无子树删除面 | §17.4 |

（§13.5 尾注"状态机断言 PS-xx…不在本文"为 M3.2 时点口径留痕，自本批起由本节承载并取代；§1–§13 原文零改动。）

## 19. 可追溯性与 DEFERRED_TO_M3_3 处置表

### 19.1 引源对照

| 来源 | 消费 |
| --- | --- |
| PRD §5（内建修订）、§7.1/§7.2（预约/有效期）、§7.3（活动状态正交）、§8（发布/归档/删除全节）、§9（推荐位）、§11 末段（投诉下架）、§21（通知有效期/自动归档验收） | §14–§17 各节引源行 |
| 上游审计 §3.3（`DraftStateMixin` 位点／`publish_scheduled` 每小时／`set_expired` 语义／R4 张力）与风险清单 R4 | §14.1/§14.3/§16.3/§16.4 |
| 02 S3.3 规格行（§14–§18 结构与 CM-10–13） | §14–§18 结构对应＋别名映射 |
| M3.2 冻结项（§5.3 PublishingPanel、§13.3 CASCADE、§4/§13 词表与部门 PROTECT、§12 Tag through） | §16.1/§17.3 终判一律不翻案冻结字段 |

### 19.2 DEFERRED_TO_M3_3 标记逐项处置（rg 全量定位；本批纯设计，§1–§13 与代码内标记原文一律不动）

| 标记位点 | 延期内容 | 处置 |
| --- | --- | --- |
| CONTENT_MODEL L16（标记定义句） | 状态机/修订预览/删除政策归 M3.3 | 本批即归口；定义句作为历史口径保留，§1–§13 零改动 |
| L140（§4）/L372（§13.2） | 部门/词表引用解除与删除政策 | → §17.3 终判（PS-27/PS-28） |
| L158（§5.1）/L187（§6） | 通知/文章 `expire_at` 到期行为 | → §14（E7/E9）/§16.1–§16.2 |
| L175（§5.3） | PublishingPanel 位点行为语义 | → §14/§16 |
| L179（§5.4） | 预约发布、到期退出、历史归档与搜索保留（PRD §7.1 后三句） | → E2/E3（预约）、E7＋PS-25（退出）、§16.4（归档＝数据层 V1＋查询层 M5.2；搜索＝ARCHIVE-SEARCH＋映射 M3.4） |
| L214（§7.3） | 已结束活动列表降权/归档/搜索展示 | → §14.4 正交声明；消费口径归 M5.2 总表/M3.4，本文不预设 |
| L237（§8.1） | 文章/资源手动下线行为 | → E8/PS-19＋§16.1（三类强制空 PS-23） |
| L265（§9.2） | 版权/安全投诉立即隐藏与内部记录 | → §17.2 纠错快速通道（unpublish＋内建留痕） |
| `notices/models.py` L89/L208、`resources/models.py` L25、`guides/models.py` L21、`departments/models.py` L27（代码注释） | 同上各项 | 语义已由本文 §14–§17 承载；注释更新随 B 阶段实现（纯设计批次禁改代码） |
| `tests/` 两处 docstring | 测试注释 | 同上；PS 断言转正式测试随 B 阶段 |
| `docs/reviews/A3.1.*` 两处 | 审查报告历史记录 | 留档不改（历史时点口径） |
| A3.1 收口汇总中的"权限分组（M4）、前台消费正式切换" | 越界项 | **不属 M3.3**：权限分组→M4；前台消费（event_status/FeaturedItem/SiteSettings 模板正式切换）→B 阶段前台/M5.2；本文已留指针（§15.3/§15.4/§17.2） |

### 19.3 越界防御登记（本批明确不做）与编号登记

- **M5.1 不越界**：`publish_scheduled` 部署形态（cron/任务容器）、1 小时窗口的验收口径、推荐位排程细则与数量固定值——`PUBLISH_ARCHIVE_SCHEDULING.md` §1–§5（02 S5.1）。
- **M5.2 不越界**：归档视图与 URL 形态、可见性规则总表、下线/归档/删除三态对比表、PA-01–PA-06 断言——同文档 §6–§11；本文仅预冻结状态谓词与三口径术语供其引用（§16.4）。
- **M3.4 不越界**：`search_fields`/筛选 facet/搜索后端——本文仅留 §16.5 语义锚点。
- **M4 不越界**：权限组配置与越权矩阵执行——本文仅 PS-12 断言先行冻结。
- **编号登记**：02 S5.1 为调度文档预留 PS-01–PS-05，与 00 M3.3 v1.x 赋予本文的 PS 系列同名——本批以"本文编号自 PS-10 起"数值避让（两文档无重叠 ID），并建议 M5.1 批次将其断言改号（如 PAS-xx）或以文档前缀消歧（M5.1 批次裁定；本行即其输入登记）。

---

## 20. 搜索索引字段映射（search_fields，M3.4）

引源：PRD §10（搜索六个"至少覆盖"维度＋筛选）；02 §5 S3.4（§20–§24 结构行）；00 §10 M3.4；上游审计 §3.4；ADR-0001（C1：wagtail 7.4.2＋modelsearch 1.3.2，requirements.txt 锁定线内）；本文 §5–§13 字段表（只读承接）；现状代码与上游源码亲证（位点随文标注）。本批纯设计：零代码/零迁移/零测试——`search_fields` 属性落位（各内容页类体）与 `update_index` 接线均归 B 阶段（MB10）。

### 20.0 机制事实（wagtail 7.4.2 / modelsearch 1.3.2 源码亲证，本节全部设计的依据）

| # | 事实 | 位点 | 设计后果 |
| --- | --- | --- | --- |
| 1 | 基类 `Page.search_fields`＝`SearchField("title", boost=2)`＋`AutocompleteField("title")`＋`FilterField`×{title, id, live, owner, content_type, path, depth, locked, show_in_menus, first_published_at, last_published_at, latest_revision_created_at, locale, translation_key}；**无 `expired`、无 `slug`** | wagtail/models/pages.py:400-417 | 子类须自含再声明（接事实 2）；`expired` 须显式补 FilterField |
| 2 | 子类定义 `search_fields` 即**整体遮蔽**基类声明（Python 类属性遮蔽，无合并机制） | 同上＋语言事实 | §20.1 五页映射表逐项自含，"继承自基类"不构成可依赖项（PS-32 覆盖面） |
| 3 | 查询期字段集＝`queryset.model.get_searchable_search_fields()`（按查询集的模型类解析） | modelsearch backends/database/fallback.py:42-54、postgres.py:489-491 | 站内跨类型检索入口＝**逐内容类型查询后合并**（五类各查一次）；基类 `Page.objects…search()` 仅命中 title |
| 4 | DB fallback 后端逐字段 `__icontains` OR 匹配；**非 DB 字段项被跳过**（模型 `_meta` 取不到该列即略——含 related/调用型声明） | fallback.py:42-60 | E1 对 RelatedFields 文本（部门名/标签名/词表名）结构性缺席（§20.2 差异表，PoC 差异登记） |
| 5 | DB fallback 后端**不支持 boost**（触发官方 UserWarning 后忽略——裸 `warn()` 缺省类别）；支持 queryset `order_by`（HANDLES_ORDER_BY_EXPRESSIONS=True——仅指排序表达式不报错，保序成立条件见事实 6/7） | fallback.py:36, 62-67 | 权重档位仅 E2/E3 生效；§21.6 默认排序三方案一致可表达（经保序旋钮，事实 6/7） |
| 6 | PG 路径同支持 queryset `order_by`，但**默认调用（`order_by_relevance=True`）以相关度 rank 整体替换 queryset 排序且零告警**（check() 对 order_by 早退）；契约排序成立须显式 `.search(q, order_by_relevance=False)`，此时排序键走 check() 强制 FilterField（事实 7）；`SEARCH_CONFIG` 为后端参数（非字段契约项） | postgres.py:463, 675-690, 960 | §21.6 排序契约＝保序旋钮＋排序键 FilterField 声明，三方案一致可表达；E2/E3 差异仅在配置层 |
| 7 | 组合查询时，queryset 过滤涉及的字段/路径须有 FilterField（跨关系须 RelatedFields 内 FilterField），否则 FilterFieldError——**三后端同闸**（check() 为共享编译期闸，E1 fallback 同受；保序模式下排序键同须 FilterField，否则 OrderByFieldError） | modelsearch backends/base.py:89-201、234-237、369-442、795 | §20.1 FilterField 义务集（PS-32）：live/expired/path/first_published_at/department.slug/各词表 |
| 8 | StreamField（JSON 列）的 icontains 由 Django `JSONIContains` 支持（整列 JSON 文本子串） | django/db/models/fields/json.py:356 | E1 的 body 匹配＝存储 JSON 原文子串（含块类型键名——误命中面，§20.2/PoC 登记） |
| 9 | 后台页面选择器搜索以 `.autocomplete(q)` 消费 `AutocompleteField`；Snippet 选择器同类机制（无 Autocomplete 声明时回退 `.search()` 并告警） | wagtail/admin/views/chooser.py:459-464、wagtail/admin/forms/choosers.py:79-95 | `AutocompleteField("title")` 再声明＝确有当前消费（后台选择器）；前台无补全需求（PRD §10 无建议词条款）——全文唯一 Autocomplete 用点 |
| 10 | `wagtail.search.backends.database` 按连接 vendor 选实现（postgresql→PG FTS 路径；其余→fallback icontains） | modelsearch backends/database/__init__.py | E1/E2/E3 的配置触发方式归 M6.1 定稿（§22） |

现状衔接（只读登记，本批禁改代码）：`src/peiligo/settings/base.py:217-219` 已配 `wagtail.search.backends.database` 默认后端（与 §22 对接兼容）；`search/views.py` 为官方模板 stub——现读 `query` 参数（与 IA §9 的 `q` 不一致）、以基类 `Page.objects.live().search()` 仅搜 title（违反事实 3 的逐类型要求）。两者均属 MB10 按本文契约改造的落点。

### 20.1 逐页 search_fields 映射表（冻结）

声明形态全部为 wagtail/modelsearch 官方 API（`SearchField`/`FilterField`/`AutocompleteField`/`RelatedFields`＋queryset 谓词），**不写死任何后端专用实现**——PostgreSQL 专用路径零出现，E2/E3 仅经官方后端参数区分（§22）。权重档位：**高＝boost 2**（沿基类 title 既有值）／**中＝缺省不写 boost**／**低＝boost 0.5**——档位为语义冻结，具体数值＝B 阶段可微调留痕项；E1 忽略 boost（事实 5）。

**表 A：五页共同骨架（逐项再声明——事实 2，缺一即遮蔽丢失）**

| 声明 | 类别 | 语义与引源 |
| --- | --- | --- |
| `SearchField("title", boost=高)` | 检索 | 标题（PRD §10 标题维度；boost 沿基类值） |
| `AutocompleteField("title")` | 补全 | 后台页面选择器标题补全（事实 9，唯一 Autocomplete 用点） |
| `FilterField("live")`＋`FilterField("expired")` | 过滤 | CURRENT_DEFAULT_SEARCH 谓词两列（§21.5；基类无 expired——事实 1） |
| `FilterField("path")` | 过滤 | 板块维度（`descendant_of` 路径区间，§21.1 section） |
| `FilterField("first_published_at")` | 过滤 | §21.6 默认排序键——保序旋钮 `order_by_relevance=False` 下排序键须 FilterField（事实 6/7；Page 内建列，基类原有、遮蔽须再声明〔事实 1/2〕） |
| `RelatedFields("department", [SearchField("name"), FilterField("slug")])` | 检索＋过滤 | 发布部门：name 进检索文本（E2/E3；PRD §10 发布部门）；slug 为 dept 过滤键（IA §9.1） |

**表 B：逐页差异项（●＝声明；N=NoticePage A=ArticlePage M=MaterialPage S=SoftwareToolPage G=GuidePage）**

| 声明 | 类别 | N | A | M | S | G | 语义与引源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SearchField("summary", 中)` | 检索 | ● | ● | ● | —（§9.1 无字段声明） | —（§10.1 无字段声明） | 摘要（列表/搜索摘要位，§5.1/§6/§8.1） |
| `SearchField("body", 中)` | 检索 | ● | ● | ● | ● | —（无 StreamField，§10.1） | 正文文本（PRD §10 正文；S 为收窄白名单 SOFTWARE_TOOL_BLOCKS，同权） |
| `SearchField("event_location", 低)` | 检索 | ● | ● | — | — | — | 活动结构化字段贡献（EventFieldsMixin，§2/§7——无 EventPage）；活动地点为专名查询目标 | PRD §7.3/§10 |
| `SearchField("location", 中)`／`SearchField("opening_hours", 中)` | 检索 | — | — | — | — | ● | 校园指南结构化信息（**CM-21 验收锚点**：地点/开放时间可被搜索命中） |
| `SearchField("contact", 低)`／`SearchField("extra_notes", 低)` | 检索 | — | — | — | — | ● | 指南结构化信息补足（联系方式/补充说明；G 无正文，结构化文本即全部可检索面，CM-21 为其子集锚点） |
| `SearchField("license_note", 低)` | 检索 | — | — | — | ● | — | 授权/费用说明文本（PRD §7.5 六项之一；"免费/正版授权"类查询目标） |
| `RelatedFields("tags", [SearchField("name"), FilterField("slug"), FilterField("name")])` | 检索＋过滤 | ● | ● | ● | —（无标签字段） | —（同左） | 受控标签（§12）：name 进检索文本（E2/E3）；slug∪name 为 tag 过滤双通道（§21.2） |
| `RelatedFields("discipline", [SearchField("name"), FilterField("name")])` | 检索＋过滤 | — | — | ● | — | — | 学科·专业方向（受控类别，tag 值域之一，§13.2——词表无 slug，过滤键=name） |
| `RelatedFields("material_type", [SearchField("name"), FilterField("name")])` | 检索＋过滤 | — | — | ● | — | — | 资料类型（同上） |
| `RelatedFields("platforms", [SearchField("name"), FilterField("name")])` | 检索＋过滤 | — | — | — | ● | — | 适用平台（受控类别 M2M，tag 值域之一） |
| `RelatedFields("category", [SearchField("name"), FilterField("name")])` | 检索＋过滤 | — | — | — | — | ● | 指南类别（同上） |

容器与结构页处置（现状实证，A3.1 已落地）：`DepartmentContainerPage.search_fields = []`（departments/models.py，IA-04）——容器不入任何搜索；`HomePage`/`SectionPage` 保留基类默认声明（后台树内搜索/选择器仍可按 title 消费），但**不入站内搜索对象域**（§21.1 逐类型入口结构性排除，无需清空其索引）。Snippet/设置无公开 URL，不入搜索（ADR-0005 #7–#14）。

### 20.2 三方案语义差异表（同一字段契约的后端差异；M6.1 PoC 评分与 M7.2 的输入）

| 维度 | E1（DB fallback icontains） | E2（PG FTS＋simple） | E3（PG FTS＋zhparser/pg_jieba） |
| --- | --- | --- | --- |
| 匹配语义 | 逐字段子串（不区分大小写） | 词元匹配（simple 不分词，中文整串成单 token） | 中文分词词元匹配 |
| 自有列文本（title/summary/body/event_location/指南结构化文本/license_note） | ✓ 直接 icontains | ✓ 入索引 | ✓ 入索引 |
| RelatedFields 文本（部门名/标签名/四词表名） | **缺席**（事实 4——q=部门名/词表名仅经 title/正文文本间接命中） | ✓ 入索引 | ✓ 入索引 |
| boost 权重 | 忽略＋官方告警（事实 5） | ✓ | ✓ |
| 相关度排序 | 无（回退 queryset 排序） | ✓（ts_rank） | ✓ |
| StreamField body 匹配面 | JSON 存储原文子串（含块结构键——事实 8） | 索引化纯文本（构建期提取） | 同 E2 |
| FilterField 组合查询义务 | 须声明（check() 三后端同跑——事实 7） | 须声明（事实 7/PS-32） | 同 E2 |

上表不构成任何方案优劣预设——差异的实测裁决归 M6.1–M6.3/D7/ADR-0006（§22）。

### 20.3 无进索引声明（与 §5–§13 字段定义零冲突的排除清单）

以下不进 V1 站内索引：附件文件内容与文件名（二进制全文检索无 PRD 要求＝扩围；附件下载经详情页）；`external_url`/`source_url`/`event_registration_url`（URL 非用户查询目标，输出经 §11.4 跳转页）；`image`（媒体资产）；`slug`（非用户查询目标，title 已覆盖）；`seo_title`/`search_description`（promote 侧内建列——语义面向外部搜索引擎〔PRD §12〕，PRD §10 覆盖清单无此项，V1 不纳入，如需扩补＝B 阶段增补留痕，不破坏本契约）；`maintenance_mode`/`responsible_party`/`last_confirmed_on`（枚举码/展示元数据/日期——检索需求由 dept=、tag= 维度与默认排序承载）；活动起止时间戳（V1 无时间参数，§21.4；M5.2 如需时间过滤届时增补 FilterField，谓词预留不预设）。PS-30 的覆盖判定以 §20.1 表内字段为准。

## 21. 筛选维度契约（IA §9 承接；M2.2 依赖消费）

引源：IA §8（部门筛选语义）/§9（URL 规格）/§10（noindex 位点）/§11（空态四态）——M2.2 产物只读承接，本节不重定义 IA 冻结规格；PRD §10（按板块、部门和类别筛选）；02 §5 S3.4（§21/§22 行，含空态与过期指针落位）；00 §10 M3.4 v1.1（M2.2 依赖显式）。

### 21.1 载体、对象域与参数集（承接 IA §9.1）

| 载体 | URL 形态 | 生效参数 |
| --- | --- | --- |
| 全站搜索页（自定义视图，不入页面树；路径 `/search/` 现状已接 `search/views.py` stub——src/peiligo/urls.py:14；实现位 MB10；自定义视图先例＝外链跳转页 ADR-0005 #5） | `/search/?q=&section=&dept=&type=&tag=` | 五参数全 |
| 板块列表页（页面树节点，`SectionPage.serve`） | `/<板块>/?q=&dept=&type=&tag=` | 四参数；**板块维度由路径唯一决定——`?section=` 在板块页一律忽略** |

**搜索对象域＝五类内容页**（§1.2 正式名），逐类型查询入口（事实 3）结构性排除结构页/容器/Snippet/设置——与 type 参数五值域同构（下表）。跨类型合并与分页实现归 MB10；合并排序键＝`-first_published_at`（§21.6）。

| 参数 | 语义 | 取值（本批终判） | 非法处置 |
| --- | --- | --- | --- |
| q | 关键词 | 服务端检索 §20.1 声明字段（服务端过滤，ADR-0002）；空串＝不加检索条件（纯 ORM 过滤，不进搜索后端） | 空串＝不加条件 |
| section | 板块 | **仅五冻结 slug**：chronicle/events/materials/software/guide（IA §2；P4 伪板块页禁入合法值——仅认本五值，任何历史/伪板块 slug 一律未知值处置） | 视同未提供 |
| dept | 发布部门 | `Department.slug`（`is_active=True` 词表内——停用即退出筛选词表，§13.1/§17.3；停用 slug＝未知值处置，其内容仍按 §17.3 展示保留部门名） | 视同未提供 |
| type | 内容类型 | 正式标识五值（IA §9.1 工作名枚举随 M3.1 终判转正，单射）：notice↔NoticePage／article↔ArticlePage／material↔MaterialPage／software↔SoftwareToolPage／guide↔GuidePage（type=guide 与 section=guide 同形异位不冲突） | 视同未提供 |
| tag | 受控标签＋受控类别 | §21.2 终判 | 视同未提供 |

### 21.2 tag 单参数终判（IA §9.1 留判项）

判定结论：**单一 `tag` 参数足以表达 V1 全部需求，不细分参数**（IA §9.1 默认成立；本批不提最小改进——无证据需要）。

| 值命中词表 | 施加谓词（queryset 语义） | 适用类型 |
| --- | --- | --- |
| Tag（§12 受控标签） | `tags` 双通道：slug 精确 ∨ name 精确（中文标签 slug 由 taggit 生成规则可能退化，name 通道保底——双通道并集，确定性无优先级） | N/A/M |
| Discipline.name（§13.2） | `discipline__name` 精确 | M |
| MaterialType.name | `material_type__name` 精确 | M |
| GuideCategory.name | `category__name` 精确 | G |
| Platform.name | `platforms__name` 精确 | S |

- 词表 name 均 unique（§13.2/§12），值→谓词为确定性映射；**同名并集**规则：同一字面值命中多个词表（含 Tag.name 与类别词表撞名）时＝各命中谓词之并（OR）——无序、无优先级、可复算。
- 值的适用类型与 type=/路径板块不相符 → **合法空结果**（IA §11"筛选无匹配"空态），非错误、非 404。
- 单值语义：多值（`tag=a,b`）不属 V1（IA §9.1 未定义＝扩围）；运营如确需，走 IA 变更流程（00 §3），本批不提。
- 组合查询的 FilterField 声明（三后端同闸——事实 7）＝§20.1 表 B 各 RelatedFields（PS-32）；taggit 伪 M2M（through 模型）join 形态与 modelsearch 编译器 M2M 匹配的兼容性＝**B 阶段首个实测锚点**——如不匹配，回退＝tag 值预解析为命中对象主键集再 `pk__in` 过滤（契约层谓词语义不变，实现层等价改写）。

### 21.3 非法值、状态与空态消费（承接 IA §9.2/§10/§11）

全参数可选；非法值（未知 slug/词表外值/空值/格式非法）＝**视同未提供该参数**，页面 200 渲染——不 404/不 5xx/不渲染错误页；状态全在 URL（GET 可分享/可刷新/详情往返复原）；板块页忽略 section；默认排序中立（§21.6）。收录控制＝IA §10 #6/#7：筛选态与 `/search/`（含无参数态）一律 noindex＋canonical 指向去参基础 URL（IA-12 断言承接，实现位 MB13）。空态＝IA §11 四态承接：本契约绑定**全空态**（无结果无筛选时的引导文案）与**筛选无匹配态**（含清除筛选动作＋已选条件回显）两态的触发条件与动作；载入中/出错两态在服务端渲染语境的呈现细节归 MB9/MB10（契约不绑定异步形态）。

### 21.4 时间维度（要点承接：V1 不新增公开时间参数）

V1 **不新增任何公开时间参数**（五参数之外零参数）。时间语义的既有承载：默认排序＝发布时间倒序（§21.6）；近期活动按活动时间邻近＝首页层 3 列表（IA §7.1，非搜索参数）；已结束活动的搜索展示策略＝§14.4 正交声明（消费口径归 M5.2）。M5.2 HISTORICAL/ARCHIVE 如需时间参数→其批次走变更流程（本批登记，不预设）。

### 21.5 搜索可见性（§16.5 锚点逐条兑现——M3.4 不另立可见性语义）

**CURRENT_DEFAULT_SEARCH＝§16.4 CURRENT_DEFAULT 同一谓词**（`live ∧ ¬expired`；现状源码 `current_default_pages()`＝`Page.objects.live().filter(expired=False)`，notices/lifecycle.py）：

| 排除对象 | 依据 |
| --- | --- |
| draft（S0）／scheduled 未到点（S1）／unpublished（S4） | §16.5 ③（恒不入任何搜索口径；PS-25 承接） |
| expired（S3） | §16.4（V1 搜索不含 expired；ARCHIVE-SEARCH 归 M5.2，见下） |
| DepartmentContainerPage | `search_fields=[]`（§20.1 容器处置；IA-04） |
| HomePage/SectionPage | 搜索对象域结构性排除（§21.1） |
| Snippet/设置 | 无公开 URL（ADR-0005 #7–#14） |

与 M5.2 契约差异（显式登记；落地前任何实现/文档不得声称已提供——PS-26/PS-34）：**ARCHIVE-SEARCH**＝搜索默认**含 expired 通知并标注**（PRD §7.1"保留在……站内搜索中"的查询层兑现）——归 M5.2 `PUBLISH_ARCHIVE_SCHEDULING.md` §7；其落地形态预计＝同一字段契约＋放宽谓词（`FilterField("expired")` 已声明，§20.1——增补零结构变更），标注样式/入口细则 M5.2 定。unpublished 恒不入任何搜索口径（§16.4/PS-25）。

### 21.6 排序与组合执行模型

- 默认排序＝`-first_published_at`（IA §9.2 #4 发布时间倒序；施加筛选不改变）。**保序机制口径（三方案一致可表达的前提）**：E2/E3 默认调用（`order_by_relevance=True`）以相关度 rank 整体替换 queryset 排序且零告警（事实 6）——契约排序成立须显式 `.search(q, order_by_relevance=False)`（官方保序旋钮，三后端一致；E1 无相关度排序、本就回退 queryset 排序），且排序键须有 FilterField 声明（表 A `FilterField("first_published_at")`——check() 三后端无条件校验，事实 7；排序键入 PS-32 义务集）。在此口径下排序契约与后端选型解耦（事实 5/6）。相关度排序＝PoC 评分维度（M6.1"排序合理性 1–3 分"），不构成 V1 URL 契约；选型后如欲改默认排序＝走变更流程。
- 组合执行＝**filter-first**：queryset 先施加 §21.1–§21.2 全部维度过滤＋§21.5 可见性谓词，再 `.search(q)`（官方组合序，先过滤后检索）；q 空串＝不进搜索后端（纯 ORM）。FilterField 义务（三后端同闸——事实 7）＝§20.1 全表（PS-32）。

## 22. D7 三方案对接点（零胜者预设）

引源：00 §2.2 D7 行＋§13 M6.1–M6.3；02 §8 S6.1；上游审计 §3.4；ADR-0001（C1 锁定线内）。

| 方案 | 后端配置（M6.1 定稿） | 与本契约的关系 |
| --- | --- | --- |
| E1 | `wagtail.search.backends.database` 的 fallback 路径（icontains；vendor 触发方式＝M6.1 按事实 10 定） | 消费同一 §20.1 声明（非 DB 字段项被跳过＝§20.2 已登记差异，非契约分支） |
| E2 | 同后端 PG FTS 路径＋`SEARCH_CONFIG='simple'` | 同上（词元差异） |
| E3 | 同后端 PG FTS 路径＋zhparser 或 pg_jieba 扩展配置（可装性未知＝PRE-5；不可装记"环境不可行"） | 同上（中文分词差异） |

对接点声明（冻结）：①三方案**消费同一字段契约**（§20.1 表 A/B＋权重档位）——字段契约是方案无关层，任何方案不增删字段项（差异仅 §20.2 语义表）；②**零胜者预设**——达标裁决（hit@10 ≥90%／1000 档 p50<1s）与决策规则归 M6.1–M6.3；③**零 ADR-0006**——后端选型 ADR 由 M6.3 产出；④**零安装**——依赖安装仅限 M6.2 的 PoC venv/容器（OR-3 ②/G0）；⑤**零独立搜索服务**——三方案均不达标才评估独立服务（Elasticsearch/OpenSearch 类），且须项目负责人批准（D7 门；PRD §10 末段）；⑥V1 实现后端＝现状默认 `wagtail.search.backends.database`（settings/base.py:217-219），选型切换仅在 ADR-0006 Accepted 后进行。搜索性能口径＝M7.2 输入（§20.2 差异表供其引用）。

## 23. 金标集挂接点与 PoC 最小字段契约（02 S3.4 §23 行；S6.1 直接输入）

### 23.1 PoC 最小字段契约（五字段，字段名与 M6.1 引用严格一致——02 S3.4 测试要求）

| 契约字段 | 类型 | 从 §20/§5–§13 映射 |
| --- | --- | --- |
| title | CharField | Page.title（§5.1 等） |
| body | 纯文本长字段 | 正文文本：N/A/M/S＝StreamField 纯文本化；G＝结构化字段拼接（§20.1 表 B 之 G 列五项） |
| department | CharField 代号 | Department.slug（与 IA §4.1 URL 部门段同源） |
| tags | CharField 逗号分隔 | Tag.name 串（name 为主通道——中文标签主形态；slug 为 taggit 派生列不入 PoC 契约；N/A/M 三类型有标签） |
| category | CharField | 适用受控类别词表 name（M＝discipline/material_type；G＝category；S＝platforms；N/A＝空） |

数据规模分级＝**200／1000／5000** 三档（M6.1/M6.2 按此构造；覆盖分布〔≥5 部门代号/全部板块/≥20 标签〕与真实中文数据来源规则＝02 S6.1 §2，本文件不重复）。本批**不建任何真实数据集**（纯设计）。

### 23.2 金标集最小结构（挂接点；30 条本体归 M6.1）

每条金标＝四字段结构（JSON 形态示意，非数据本体）：

```json
{
  "query": "<查询串>",
  "expected_pages": ["<数据集内稳定页标识>"],
  "required_filters": {"section": "…", "dept": "…"},
  "notes": "<判定注记>"
}
```

- `query`：查询串（对应 q；覆盖类型沿 02 S6.1 §3——单字/双字词/专名/短语/长句/带筛选组合）；
- `expected_pages`：期望命中页（数据集内稳定标识——标识方案 M6.1 定，本批不建数据）；
- `required_filters`：绑定筛选参数（IA §9 参数子集；空对象＝纯 q 条）；
- `notes`：判定注记（如该条依赖部门名 q 覆盖〔§20.2 E1 已知缺席〕、分词边界、期望空结果等评分提示）；
- **字段契约引用方式**：金标集条目一律按 §23.1 契约字段名＋§21 参数名引用，不另行发明字段/参数名。30 条金标集本体＝M6.1 产出（POC_SEARCH_REPORT.md §3 随文入库）；B 阶段 MB10 以金标集固件化为自动化测试（03 计划 S10：金标中文用例）。

## 24. 断言清单、可追溯性与延期处置（M3.4）

### 24.1 断言清单（02 S3.4 草案编号 CM-20/CM-21 别名留痕，内容一字不丢）

编号承接 §18（PS-10–PS-29 已用）；本批自 **PS-30** 起（同 §19.3 数值避让口径，避开 02 S5.1 为调度文档预留的 PS-01–PS-05）。

| 断言 | 内容 | 落点 |
| --- | --- | --- |
| PS-30（＝CM-20） | 索引字段映射覆盖 PRD §10 六个"至少覆盖"维度逐条有落点：标题与正文→SearchField（§20.1）；板块→section＋FilterField("path")；内容类型→type 映射＋逐类型入口；发布部门→dept＋RelatedFields("department")；受控类别和标签→tag＋五词表 RelatedFields；校园指南结构化信息→G 列结构化 SearchField | §20/§21 |
| PS-31（＝CM-21） | 指南结构化字段（地点/开放时间）可被搜索命中（SearchField 声明；E1 直接 icontains、E2/E3 入索引） | §20.1 表 B |
| PS-32 | 五内容页 search_fields 自含组合查询 FilterField 义务（live/expired/path/first_published_at＋department.slug＋各自词表——排序键属义务集，§21.6）——§21 参数任意组合在三后端无 FilterFieldError/OrderByFieldError（check() 三后端同跑，事实 7；子类遮蔽基类陷阱由此覆盖；taggit join 形态＝B 阶段首个实测锚点） | §20.0-2/7、§20.1、§21.2、§21.6 |
| PS-33 | CURRENT_DEFAULT_SEARCH＝§16.4 CURRENT_DEFAULT 同谓词（live ∧ ¬expired）：draft/scheduled 未到点/expired/unpublished/容器/结构页/Snippet/设置一律不入 V1 搜索结果 | §21.5 |
| PS-34 | ARCHIVE-SEARCH（搜索含 expired 通知＋标注）归 M5.2；落地前任何实现/文档不得声称已提供；unpublished 恒不入任何搜索口径 | §21.5（PS-26 承接） |
| PS-35 | 参数契约＝IA §9 逐条：五参数全可选、非法值视同未提供（200 不 404/5xx）、板块页忽略 section、q 空串不加条件、状态全在 URL、默认排序发布时间倒序 | §21.1/§21.3/§21.6 |
| PS-36 | type 五值↔正式 Model 单射（notice/article/material/software/guide）；section 合法值仅五冻结 slug，P4 伪板块页禁入 | §21.1 |
| PS-37 | tag 单参数终判：值域＝Tag∪四类别词表、Tag 双通道 slug∪name、类别词表 name 精确、同名并集、类型不符＝合法空结果 | §21.2 |
| PS-38 | E1/E2/E3 消费同一 §20 字段契约（差异仅 §20.2 语义表）；boost E1 忽略；零胜者预设/零 ADR-0006/零安装/零独立搜索服务（D7 门） | §20.2/§22 |
| PS-39 | V1 无公开时间参数；时间语义＝默认排序＋首页活动列表承载 | §21.4 |
| PS-40 | 金标集条目结构＝query/expected_pages/required_filters/notes＋按 §23.1 契约字段与 §21 参数名引用；30 条本体归 M6.1 | §23 |

### 24.2 引源对照

| 来源 | 消费 |
| --- | --- |
| PRD §10（六覆盖/筛选维度/无结果提示/真实数据验证与独立服务门） | §20.1（PS-30）、§21（PS-35/37）、§22（E1–E3＋D7 门）、§21.3（IA §11 空态承接） |
| PRD §12（noindex 语境） | §20.3（seo_title/search_description 处置）、§21.3 |
| IA §8（部门筛选≠主页）/§9（五参数 URL 规格）/§10 #6-#7（noindex）/§11（四态） | §21.1–§21.3（IA-08/11/12 断言承接不重定义） |
| 02 §5 S3.4 行（§20–§24 结构/CM-20/21/空态/过期指针） | §20/§21（空态落位＝§21.3）/§22（D7 对接）/§23/§24.1（CM-20→PS-30、CM-21→PS-31 别名）/过期包含指针→§21.5（M3.3 §16.5 ② 预期的 §24 指针由 PS-34 承载） |
| 00 §10 M3.4（含 v1.1 M2.2 依赖显式） | 全批（§21 消费 IA §8/§9/§10） |
| ADR-0001（C1：wagtail 7.4.2＋modelsearch 1.3.2） | §20.0（源码位点）、§22 |
| ADR-0005（#5 自定义视图先例、#7–#14 Snippet 无公开 URL） | §21.1（/search/ 载体）、§21.5 |
| 上游审计 §3.4 | §20.0、§20.2、§22 |
| 本文 §16.5（M3.4 预留锚点①②③） | §21.5（逐条兑现） |

### 24.3 DEFERRED_TO_M3_4 标记处置（rg 全量定位；本批纯设计，§1–§19 与代码标记原文一律不动）

| 标记位点 | 延期内容 | 处置 |
| --- | --- | --- |
| CONTENT_MODEL L17（标记定义句） | search_fields/筛选契约归 M3.4 | 本批即归口；定义句历史口径保留（§1–§13 零改动，同 §19.2 先例） |
| L106（§1.4 条 4） | 搜索索引映射与筛选维度契约 | → §20/§21 |
| L174（§5.3） | promote_panels 内建列的搜索消费 | → §20.3 无进索引声明（seo_title/search_description 不进 V1 站内索引——面向外部搜索引擎语义；扩补＝B 阶段留痕） |
| L179（§5.4） | 搜索索引映射 | → §20 全节 |
| L537（§16.5） | M3.4 可引用锚点 | → §21.5 逐条兑现（①同谓词②ARCHIVE-SEARCH 指针③恒不入） |
| docs/reviews/*（历史审查报告 M3.4 提及） | 历史时点口径 | 留档不改 |
| `search/views.py` stub＋`src/peiligo/urls.py:14`＋`settings/base.py:217-219`（现状代码，无标记） | 官方模板起点 | 语义已由 §21/§22 承载；代码改造归 MB10（本批禁改代码） |

### 24.4 越界防御登记（本批明确不做）

- **M5.2 不越界**：ARCHIVE-SEARCH 细则（标注样式/入口/URL）、HISTORICAL 归档视图、可见性总表、PA 断言——本文仅 §21.5 差异登记＋谓词预留。
- **M6.x 不越界**：三组实验设计定稿、数据集构造规则细则、30 条金标集本体、评分口径、ADR-0006——本文仅 §23 契约/结构挂接＋§22 对接点。
- **B 阶段不越界**：search 视图/模板/分页/合并实现、boost 数值微调、update_index 接线、SEARCH_CONFIG/后端配置切换、tag 预解析回退实测——本文冻结契约语义。
- **M7.2 不越界**：搜索性能口径（§20.2 仅供引用）。
- **本批零代码/零迁移/零测试**（纯设计）；§1–§19 与全部代码零改动；单 commit 收口，未 push。

## 25. 首页轮播与轮播封面图（首页升级批次，2026-09-10）

**引源**：「首页升级 PRD」＝《Peiligo 首页增量升级产品需求文档》（2026-09-10 封口版）§10–§15；首页升级 Phase 2 架构模型冻结设计（下称"冻结决策 N"）；ADR-0007（Accepted）；**实现事实**：commit 21909e1（`home/models.py` CarouselItem、`src/peiligo/cover.py` CoverImageMixin、notices/resources/guides 三 app 迁移）＋ `tests/test_carousel_item.py`。本节为**事后同步**：数据模型已实现、已测试并经 Phase 3.5 审查收口，本节按真实模型落档；**轮播前台（SSR 模板与 JS）尚未实现**，归后续前端阶段（ADR-0007）——本节与 ADR-0007 均不声称轮播前台已上线。（**状态更新（2026-09-12，Phase 9.5 复核）**：轮播前台已于后续前端阶段实现——首页模板含轮播区块（`home/templates/home/home_page.html`），交互脚本 `static/js/carousel.js`（自动播放约 5.5 秒、`prefers-reduced-motion` 下停用自动播放、最多 5 条）；上句为 2026-09-10 落档时点口径，保留作历史。）

### 25.1 轮播封面图 `cover_image`（五类内容页统一可选字段）

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 轮播封面图 | `cover_image` | ForeignKey(`wagtailimages.Image`, null=True, blank=True, on_delete=SET_NULL, related_name="+")；经抽象 Mixin `peiligo.cover.CoverImageMixin` 单源挂五类内容页（实现形态：Mixin 仅挂五类，未引发内容模型重构——首页升级 PRD §12.1 优先项） | 可选 | 首页升级 PRD §12；冻结决策 |

- **适用对象**：五类内容页（§1.2 正式名）——`NoticePage`/`ArticlePage`/`MaterialPage`/`SoftwareToolPage`/`GuidePage`（commit 21909e1 实证五类均已挂载；字段表定点修订见 §25.4）。
- **语义**：首页轮播位引用站内内容时的**封面单一来源**——轮播项不重复配置站内标题与图片，直接取目标内容页 `cover_image`（冻结决策 5）；作者在正常内容编辑时上传，不为轮播重复上传站内 Banner（首页升级 PRD §12.2）。
- **可空与发布**：nullable/blank，不上传封面**不阻止发布**——普通内容无封面照常发布（首页升级 PRD §12.2）。
- **删除语义**：封面图删除仅 SET_NULL 置空，页面本体保留；`related_name="+"` 不建 Image→Page 反向关系。
- **尺寸提示**：推荐 1600×600（8:3）＝编辑界面 help_text 软提示；**无比例/尺寸硬校验**（首页升级 PRD §12.3）。
- **与既有 `image` 的关系（仅 Notice/Article）**：`image`（§5.1）仍是正文插图/题图列表位，`cover_image` 是首页轮播封面位——两者语义独立、可同时存在（冻结决策 14），不互改、不互替；本批未改写 §5.1 `image` 行任何语义。
- **前台消费**（轮播有/无封面的 Banner 呈现规则，首页升级 PRD §13）归后续前端阶段，本节不冻结模板细节；`cover_image` 不进站内搜索索引（§20.3 `image` 同类口径——媒体资产）。

### 25.2 CarouselItem（首页轮播项，Snippet）

**载体与定位**：`home.CarouselItem`，`register_snippet`（§1.3 表已增行）。**独立 Snippet，不复用 `FeaturedItem`**——轮播是首页顶部可点击 Banner 位，推荐位是标题/摘要列表位，职责不同、并存互不替代（首页升级 PRD §11：不得为轮播删除现有推荐功能；冻结决策）。不建独立"轮播文章"内容类型（首页升级 PRD §15 末句）。仅总管理员可管理（与 FeaturedItem 同一权限口径；越权测试实证见 `tests/test_carousel_item.py`）。

| 字段 | 属性 | 类型与约束 | 必填 | 引源 |
| --- | --- | --- | --- | --- |
| 站内内容页 | `internal_page` | ForeignKey(`wagtailcore.Page`, null=True, blank=True, on_delete=CASCADE, related_name="+")；选择器过滤仅五类内容页（`CAROUSEL_INTERNAL_PAGE_TYPES`——首页/板块/容器等结构页不可选，与 FeaturedItem 选择器同一集合） | 与 `external_url` 二选一（XOR） | 首页升级 PRD §11.1/§11.3；冻结决策 3/4 |
| 外部链接 | `external_url` | URLField(blank=True, validators=[`peiligo.link_validation.validate_external_url`])——**复用现有外链 validator，不重新实现**；外链确认跳转安全通道继续适用（首页升级 PRD §11.2） | 与 `internal_page` 二选一（XOR） | 首页升级 PRD §11.2/§11.3；冻结决策 3/7 |
| 外链标题 | `external_title` | CharField(max_length=255, blank=True)；外链项必填（clean 强制非空），站内项必须为空 | 外链项必填 | 首页升级 PRD §11.2；冻结决策 5 |
| 外链封面图 | `external_cover_image` | ForeignKey(`wagtailimages.Image`, null=True, blank=True, on_delete=SET_NULL, related_name="+")；站内项必须为空 | 外链项可选 | 首页升级 PRD §11.2；冻结决策 5/9 |
| 排序 | `sort_order` | PositiveSmallIntegerField(default=0)；`Meta.ordering = (sort_order, pk)`——重复排序值允许，pk 兜底稳定序（冻结决策 10） | 必填（有默认） | 首页升级 PRD §15；冻结决策 10 |

**校验（clean，已实现，断言载体＝`tests/test_carousel_item.py`）**：

1. **XOR**（冻结决策 3；首页升级 PRD §11.3）：`internal_page` 与 `external_url` 只能二选一，两者皆空或皆有效即 `ValidationError`；外链空白按空处理（strip 口径）。
2. **站内目标白名单**（冻结决策 4）：仅五类内容页（§1.2）；且目标须**当前可展示**——`lifecycle_state == LIFECYCLE_LIVE`（§16.4 CURRENT_DEFAULT 同一谓词，与 `FeaturedItem.is_on_display` 同口径；draft/scheduled/unpublished/expired 一律拒绝，零新增 lifecycle 规则）。
3. **站内项零重复配置**（冻结决策 5）：站内项的标题/URL/封面一律取自目标 Page（标题＝`Page.title`、URL＝页面 URL、封面＝目标页 `cover_image`）；`external_title` 与 `external_cover_image` 必须全空。
4. **外链项**：`external_title` 必填；`external_cover_image` 可选。
5. **容量上限**（冻结决策 11；首页升级 PRD §10.1/§15）：最多 5 条（`CAROUSEL_MAX_ITEMS`）——clean 拒第 6 条**新建**（exclude 自身 pk，编辑既有项不受限）；前台消费侧防御性最多取 5。

**删除语义**（冻结决策 8/9）：站内目标内容页删除 → 轮播项 **CASCADE** 随删（随目标消失，零悬挂）；外链封面图删除 → **SET_NULL** 置空、条目保留。

**前台消费边界**：0/1/2–5 项的渲染档位、自动播放、外链确认跳转页等前台行为归后续前端阶段（ADR-0007；首页升级 PRD §10/§13），本节不冻结、不预设。

### 25.3 与 FeaturedItem 的边界（并存，不混用）

| 维度 | `FeaturedItem`（§13.3/§15.4，零改动） | `CarouselItem`（本节） |
| --- | --- | --- |
| 职责 | 首页推荐位（呈现所指内容标题/摘要） | 首页顶部轮播 Banner 位（整图可点击） |
| 目标 | 仅站内五类内容页（单 FK） | 站内五类内容页 XOR 外链 |
| 文案/图片 | 无自有字段 | 站内项取目标页；外链项自带标题＋可选封面 |
| 时效 | `start_at`/`end_at`＋`enabled` 窗口 | 无窗口字段，即时配置 |
| 顺序 | 无排序字段（pk 序） | `sort_order`＋`pk` 稳定序 |
| 上限 | 展示前 3（前台消费侧） | 存量 ≤5（模型 clean） |

两者并存、互不替代；本节未修改 §13.3/§15.4 任何冻结语义。

### 25.4 本批修订登记（位点处置表）

| 位点 | 修订 | 依据 |
| --- | --- | --- |
| 文档信息·日期行 | 增补本批次记 | 文档惯例 |
| §1.3 受控数据清单 | 增补 `CarouselItem` 一行（V1 基线后新增 Snippet，无 ADR-0005 编号） | 首页升级 PRD §11/§15 |
| §5.1 字段表 | 增补 `cover_image` 行（ArticlePage 经 §6"逐行相同"同获） | 首页升级 PRD §12 |
| §8.1 无字段声明 | "无专属图片字段"修订为"无正文插图字段；`cover_image` 为唯一图片字段例外" | 同上 |
| §9.1 字段表＋无字段声明 | 同 §8.1 口径增补行与修订声明 | 同上 |
| §10.1 公共内建行＋无字段声明 | 增补 `cover_image` 说明；"无图片…字段"修订为"无附件/外部链接/标签字段＋cover_image 例外" | 同上 |
| 本节 §25 | 新增 | 首页升级 PRD §10–§15；commit 21909e1 |

§1–§24 其余内容零改动；§13"字段只到 M3.2 当前需要"的 M3.2 时点口径不变（`CarouselItem` 为该时点之后经首页升级批令新增的模型，不入 §13 各表）。
