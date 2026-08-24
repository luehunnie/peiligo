# Peiligo V1 重建综合只读审计报告

| 项目 | 结论 |
| --- | --- |
| 审计日期 | 2026-08-15 |
| 需求基线 | `/Users/chenjunxian/vscode_projects/peiligo_restart/docs/PRODUCT_REQUIREMENTS.md`（457 行，已完整阅读） |
| 审计范围 | 旧 `peiligo`、Wagtail 上游、AI 开发工作流 |
| 明确排除 | 业务开发、PVE 操作、旧站修改、V1 扩围、生产部署实施 |
| 编排记录 | Orca Run `run_2413efa7a810`；3 个独立 Claude Code / GLM-5.2 只读调查任务均已 `worker_done` |
| 当前状态 | 审计完成；等待项目负责人确认审计与文档基线，不进入开发 |

## 1. 总结结论

1. **项目骨架证据明确倾向在现有 `peiligo` 仓库的重建分支中建立干净 Wagtail 项目**。旧后端是 FastAPI/SQLAlchemy，和 PRD 指定的 Wagtail/Django 基座不同；无真实业务数据，强行在旧结构中演进不会显著减少 V1 工作量。
2. **前端架构证据倾向 Wagtail 服务端模板**。V1 是公开、内容驱动、低交互网站，服务端模板在预览、SEO、部署、缓存、无障碍和权限一致性方面路径更短。旧 Vue 前端仍有选择性复用价值，但不应成为架构基线。
3. **版本建议为 Wagtail 7.4.2 LTS + Django 5.2 LTS + Python 3.13**。截至审计日，8.0 只有 RC，7.4.2 是最新稳定补丁；该组合有较长的重叠维护窗口。最终仍须通过 PRD 的版本决策门冻结。
4. **PRD V1 未发现必须修改 Wagtail 核心的需求**。内容模型、发布排程、修订、权限、搜索、后台定制、模板和容器化均可通过官方模型、Mixin、StreamField、权限体系、hooks、ViewSets、contrib 与项目代码完成。
5. **AI 工具链具备执行 PRD §24 的大部分技术能力，但治理尚未达到开发准入条件**。Orca 已支持 Run、Task parent/deps、Gate、worktree、Dispatch 和 worker_done；Claude Code 已实际路由到 GLM-5.2。缺口在双独立审查、分层工作组映射、文件写入互斥、Git 内证据基线、秘密脱敏和 CI 门禁。
6. **本轮没有发现需要扩大 V1 的理由**。旧路线图中的 AI 搜索、复杂审核、学生账号、推送等均不得顺带进入 V1。

## 2. 旧项目事实与差距

### 2.1 仓库事实

- 当前旧项目为 Vue 3 + TypeScript + Vite SPA，后端为 FastAPI + SQLAlchemy + PostgreSQL。
- 当前分支 `feat/m4-admin-auth` 有未提交和未跟踪的 M4 认证工作；旧实现尚无只读 tag。
- 后端只形成公开内容列表、详情与健康检查；没有 Wagtail、完整后台、部门隔离、服务端搜索、附件、排程、归档、CI、Docker、备份或监控。
- `contents` 是一个通用表加 JSONB 扩展字段，与 PRD 明确要求的通知/文章独立类型、活动和指南结构化字段不一致。
- 前端搜索是拉取全量内容后的浏览器 `includes()` 过滤，不是 PRD 要求的站内搜索实现。
- 旧 SPA 缺少可验证的 SSR/meta/noindex 方案；Element Plus 全量引入但实际使用很少，存在体积风险。
- 后端测试隔离和数据库护栏思路较好，但前端没有测试框架，仓库没有 CI。

### 2.2 对 PRD 的主要缺口

| 领域 | 旧项目现状 | 审计判定 |
| --- | --- | --- |
| 技术基座 | FastAPI/Vue | 与 Wagtail/Django 基线不同 |
| 内容模型 | 单一 Content + JSONB | 需重新设计 |
| 部门岗位权限 | 无角色/部门字段与对象隔离 | 缺失 |
| 发布/归档/排程 | draft/published/offline 基础状态 | 核心规则缺失 |
| 搜索 | 前端内存子串过滤 | 不可作为 V1 搜索实现 |
| 附件/外链确认页 | 无上传；外链直接跳转 | 缺失/冲突 |
| SEO/无障碍 | 有少量 a11y 模式；无正式验证 | 部分资产可复用，能力未达标 |
| 部署运维 | 无 CI、容器、备份、监控 | 缺失 |

## 3. 可复用清单

### 3.1 可直接复用或作为规范复用

- CSS 变量、间距、字号、圆角、中文字体栈的设计令牌机制；具体品牌色必须按学校 VI 重定。
- skip-link、主内容地标、`:focus-visible`、`aria-current`、`aria-pressed` 等可访问性模式。
- 列表页的加载、错误重试、全空、筛选无结果四态交互规范。
- URL 驱动的搜索/筛选状态语义，可在服务端模板中以 query string 保留。
- 内容详情的信息顺序：面包屑、标题、元数据、摘要、正文、结构化补充信息、来源。
- 后端测试中的事务隔离、测试库护栏、不打印凭据等工程思想。

### 3.2 改造后复用

- 全局基础 CSS、卡片、元数据、空状态、页头页脚的视觉结构。
- 旧 Vue 组件作为模板结构和交互验收参考，而不是直接绑定为 V1 技术方案。
- 投稿/纠错/关于页面的部分文案；需改成统一工作邮箱、带标题和页面地址的反馈链接。
- API 错误语义和“不静默回退假数据”的原则；若采用服务端模板，具体 API client 不复用。
- 内容字段配置驱动思路；字段本身必须按 PRD 重建为受控模型。

### 3.3 应重新实现

- 整个 FastAPI 业务后端、Alembic 内容模型和自建管理员认证。
- 管理后台静态原型、Vue Router 路由层、Element Plus 全量集成。
- 前端内存搜索、旧通用 Content/JSONB 模型、直接外链实现。
- 与旧 M1/M2/M3 阶段绑定的原型文案、旧板块名称和测试填充数据。

## 4. Wagtail 上游审计

### 4.1 版本结论

- 本地官方上游 clone 位于 `/Users/chenjunxian/vscode_projects/Wagtail/wagtail`，`origin` 为官方 Wagtail 仓库。
- 本地 `main` 是 8.0 开发/预发布线，包含 `v8.0rc1`；不能把 `main` 或 RC 用作 V1 依赖。
- 截至审计日，官方稳定文档与 PyPI 均指向 **7.4.2**；7.4 是 LTS。
- 官方兼容矩阵：Wagtail 7.4 支持 Django 5.2/6.0 和 Python 3.10–3.14。
- 推荐 **Wagtail 7.4.2 LTS + Django 5.2 LTS + Python 3.13**；上线前仍应重新核验最新补丁和安全公告，只冻结 `7.4.x` 的具体补丁，不追踪 `main`。

官方证据：[Wagtail 7.4.2 升级兼容矩阵](https://docs.wagtail.org/en/stable-7.4.x/releases/upgrading.html)、[Wagtail 7.4 LTS 发布说明](https://docs.wagtail.org/en/stable-7.4.x/releases/7.4.html)、[Wagtail 发布过程](https://docs.wagtail.org/en/stable/releases/release_process.html)。

### 4.2 官方扩展方式

| PRD 能力 | 推荐官方机制 | 核心修改 |
| --- | --- | --- |
| 通知/文章/活动 | 独立 Page 模型、`parent_page_types` | 不需要 |
| 受控正文/图片/附件/表格 | `StreamField`、Block 白名单、RichText features、table_block | 不需要 |
| 修订、草稿、预约、到期 | Page 内建能力或 `RevisionMixin`/`DraftStateMixin` + `publish_scheduled` | 不需要 |
| 部门岗位权限 | Django Group + Wagtail 页面树权限/ownership；必要时自定义 permission policy | 不需要 |
| 结构化资源/指南 | Page 或 Snippet + ViewSet；取决于 URL、预览、权限和归档需求 | 不需要 |
| 搜索 | Wagtail/modelsearch 数据库或 PostgreSQL 后端 + 项目级筛选视图 | 不需要 |
| 后台定制 | hooks、ViewSets、Panels、内建 `zh_Hans` 翻译 | 不需要 |
| SEO | Django 模板 + sitemaps/redirects/settings + 项目 noindex 字段 | 不需要 |
| 外链确认页 | 项目级 Django view/template，目标 URL 严格校验 | 不需要 |
| 容器化 | `wagtail start` 项目模板与 Dockerfile 模式 | 不需要 |

### 4.3 需要谨慎的设计点

- **部门权限树**：建议用不对前台渲染为部门主页的部门容器节点承载权限，避免扁平树上 Publish 权限造成横向越权；这是技术/产品共同决策，不等于新增部门主页。
- **Page vs Snippet**：有独立 URL、SEO、预览、排程、归档搜索的内容倾向 Page；纯结构化词表/配置倾向 Snippet。不得为减少模型数量而把所有类型强行混用。
- **到期通知**：Wagtail 默认到期后不再 live；PRD 要求历史归档和站内搜索仍可查，必须有单独归档查询与测试。
- **中文搜索**：PostgreSQL 内建 FTS 不等于高质量中文分词。先用真实中文数据比较数据库 fallback/`icontains`、PostgreSQL `simple` 配置和可用扩展，再决定是否需要独立搜索服务。
- **附件 MIME**：官方扩展名/content-type 白名单仍需验证是否满足伪造 MIME 检查；必要时在项目层补魔数检测。

## 5. AI 工作流能力与差距

| PRD 治理能力 | 判定 | 事实与缺口 |
| --- | --- | --- |
| 总控 Codex | 已具备工具条件 | 可用 Orca Run/Gate；仍需只读权限和不写业务代码的硬边界 |
| 大步骤工作组 Codex | 部分支持 | Task `--parent/--deps` 可表达层级；文档未定义总控 Run 与组内 Run/Task 映射 |
| 单步骤单对话 | 已支持 | Dispatch 注入单一 Task，`worker_done` 后结束；需把“后续步骤必须新 Dispatch/新对话”写入模板 |
| Claude Code + GLM-5.2 主实现 | 已支持 | 本轮实际生效；模型名在当前 Claude Code 中仍显示为未知模型，需显式 model override/上下文配置核验 |
| 独立 Codex 需求/架构审查 | 部分支持 | 工具可开只读审查者，尚无固定清单和留档门禁 |
| 独立 Claude 代码/测试/安全审查 | 部分支持 | 工具可开独立 worker，历史阶段无稳定双审证据 |
| worktree/分支隔离 | 已支持 | Orca 支持 current/new-child/new-top-level；开发任务仍需按契约强制独立 worktree |
| 文件集合互斥 | 未制度化 | 没有用户态锁/租约流程；仅靠 worktree、SCOPE 清单和协调者纪律 |
| DAG/阶段门 | 已支持机制 | `--deps`、Gate、ready/blocked 均存在；项目尚未实例化 PRD 的正式三门 |
| worker_done/证据留档 | 部分支持 | 生命周期完备；报告是否入 Git、路径、脱敏与完整性校验未定义 |
| CI 合并门禁 | 未落地 | 旧仓库无 `.github/workflows`，不能满足 PRD §23 |

### 5.1 本轮暴露的治理风险

- Claude 配置中的敏感字段曾被调查命令读入 transcript；最终报告已脱敏，但证明现有 Evidence Packet 规则缺少“禁止读取/输出凭据文件”的硬规则。
- `docs/ai/` 被旧仓库 `.gitignore` 排除，PRD 又规定项目文档唯一事实来源为 `peiligo` 仓库，两者冲突。
- AI 工作流目录实际只有 Markdown 说明与图片，没有可执行模板、schema、lint 或自动核验脚本。
- 文档定义的是单一 Coordinator/Worker 模式，未完整覆盖 PRD 的“大步骤组内 Codex + 独立 Codex + 独立 Claude”拓扑。
- Cox 的规划能力与文档要求的“只做观察/记录”存在潜在职责冲突，需要项目级权限和流程约束。

## 6. 风险清单

| 优先级 | 风险 | 进入开发前要求 |
| --- | --- | --- |
| P0 | PRD 与治理文档不在 `peiligo` Git 唯一事实源中 | 先确认基线，再迁入并版本化 |
| P0 | 旧 `feat/m4-admin-auth` 工作区不干净，归档 tag 尚未建立 | 由用户决定保留或废弃 M4，再归档；本审计不操作 |
| P0 | 文件写入互斥、双独立审查、CI 门禁未落地 | 建 Task 契约、worktree 策略、双审 DAG 和最小 CI |
| P0 | 凭据可能进入代理 transcript/Evidence Packet | 增加禁止路径、输出脱敏、secret scan 与事故处置规范；建议轮换曾暴露的相关令牌 |
| P1 | 部门权限模型若用扁平页面树，可能横向发布/下线 | 内容模型冻结前做权限原型和越权测试 |
| P1 | 中文搜索质量未知 | 真实数据 PoC，未达标前不引入独立搜索服务 |
| P1 | 到期内容默认不可见与历史搜索要求存在语义差 | 明确归档查询、索引策略和验收测试 |
| P1 | 旧 SPA/Element Plus 直接继承会增加 SEO、部署、性能成本 | 前端决策门先行，不按复用行数选架构 |
| P2 | 附件伪造 MIME 检查深度未确认 | 技术设计阶段做样本测试 |
| P2 | 生产服务器、PG 扩展、邮箱、学校 VI 均未知 | 保持为外部决策门，不阻塞只读文档准备 |

## 7. 文档差距清单

在开发准入前，建议在 `peiligo` 仓库中形成并由项目负责人确认以下文档；这里只提出缺口，不在本轮擅自改写基线：

1. 已确认版 `PRODUCT_REQUIREMENTS.md`。
2. `ROLE_PERMISSION_MATRIX.md`：总管理员、部门岗位账号、技术维护者的动作和对象范围。
3. `CONTENT_MODEL.md`：Page/Snippet 选择、字段、状态、归档、排程和搜索索引。
4. `INFORMATION_ARCHITECTURE.md`：五板块与权限容器树，明确容器节点不是部门主页。
5. `NON_FUNCTIONAL_REQUIREMENTS.md`：性能、WCAG、SEO、隐私、备份、恢复、监控的测量口径。
6. `ACCEPTANCE_CRITERIA.md`：PRD §21/§23 的可执行场景与命令。
7. ADR：版本组合、前端架构、项目骨架、权限树、Page/Snippet、中文搜索。
8. `AI_WORKFLOW.md` 与 `TASK_TEMPLATE.md`：单步骤契约、文件清单、秘密禁区、worker_done schema、双独立审查与阶段门。
9. 需求候选池与变更记录；未经批准默认不进 V1。

## 8. 待决策门（按顺序，一次只处理一个）

1. **D0 审计与文档基线确认**：确认本报告是否可作为后续逐项决策的事实基线。
2. **D1 旧 M4 工作区处置**：保留提交归档，还是明确废弃后归档旧实现。
3. **D2 项目骨架**：同仓库干净 Wagtail 骨架，还是重开 PRD 技术基线继续旧结构。
4. **D3 Wagtail 版本**：冻结 7.4.x LTS / Django 5.2 LTS / Python 3.13 的策略与具体补丁复核时点。
5. **D4 前端架构**：Wagtail 服务端模板，还是 Vue 前后端分离。
6. **D5 权限树结构**：部门权限容器节点，还是扁平树 + 自定义对象权限。
7. **D6 Page / Snippet 分配**：逐类内容的 URL、预览、排程、权限和归档载体。
8. **D7 中文搜索**：真实数据 PoC 结果后选数据库 fallback、PG 配置/扩展或独立服务。
9. **D8 AI 治理入库范围**：哪些报告、transcript 摘要、Cox 状态进入 Git，哪些仅保留本地且如何索引。
10. **D9 外部上线门**：生产服务器、仓库可见性、统一邮箱、学校 VI、软件资源合规。

## 9. 建议阶段 DAG

```text
A0 审计事实确认
  └─G0 用户确认审计/文档基线
      ├─A1 旧 M4 处置决定
      │   └─A2 旧实现归档 tag/只读分支（之后才可执行）
      ├─A3 版本 ADR
      ├─A4 项目骨架 ADR
      └─A5 前端架构 ADR
          └─G1 架构冻结
              ├─A6 权限树原型与越权测试
              ├─A7 内容模型/Page-Snippet 设计
              ├─A8 中文搜索真实数据 PoC
              └─A9 AI 工作流契约、秘密脱敏、双审与 CI 门禁设计
                  └─G2 内容模型 + 权限 + 搜索 + 治理基线确认
                      ├─B1 干净项目骨架与环境基线
                      ├─B2 核心内容模型/权限（依赖 B1）
                      ├─B3 发布/归档/排程（依赖 B2）
                      ├─B4 前台模板/搜索/筛选（依赖 B2、A8）
                      ├─B5 附件、外链确认页、SEO/a11y（依赖 B2、B4）
                      └─B6 CI、容器、备份、监控（依赖 B1，可与 B3-B5 的不相交文件并行）
                          └─G3 自动化门禁 + 双独立审查
                              └─C1 预发布试运行（1–2 部门，建议 2 周）
                                  └─G4 项目负责人最终验收
```

约束：G0 之前不开发；G1 前不冻结实现结构；G2 前不进入主要开发；每个 B 步骤使用独立 worktree/分支和单步骤对话；实现者不得担任唯一审查者；任何并行写任务必须文件集合不相交。

## 10. 审计边界声明

- 未操作 PVE、生产服务器或旧站运行环境。
- 未修改 `/Users/chenjunxian/vscode_projects/peiligo` 和 `/Users/chenjunxian/vscode_projects/Wagtail/wagtail`。
- 未编写业务代码，未运行会改变 AI 工作流状态的实验。
- 本工作区新增的三份 Markdown 仅为审计输出，不代表 PRD 或 ADR 已获项目负责人确认。
- 在项目负责人确认 D0 前，保持“审计完成、开发禁止”的状态。
