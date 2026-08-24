# Peiligo 重建 · 02 架构与领域计划（ARCHITECTURE_DOMAIN_PLAN）

| 项目 | 内容 |
| --- | --- |
| 计划编号 | 02（接续审计阶段的只读事实工作，本计划为首个"写文档"计划） |
| 计划状态 | 待总控（Orca）与项目负责人评审批准（v2.1 治理条款已同步，见下方横幅） |
| 编制日期 | 2026-08-15 |
| 编制依据 | `docs/PRODUCT_REQUIREMENTS.md`（PRD，457 行，完整读取）；`docs/PEILIGO_REBUILD_AUDIT.md`（综合审计）；`docs/audit-report-old-peiligo.md`（旧站审计）；`docs/audit-report-wagtail-upstream.md`（上游审计） |
| 覆盖范围 | 仅：架构冻结、信息架构、内容模型、权限原型、发布归档排程、搜索真实数据 PoC、安全与非功能基线 |
| 明确排除 | 业务代码并入 V1、正式项目骨架（B1）、正式依赖锁定、PVE/生产操作、V1 扩围、AI 治理契约设计（A9，另行计划）、V1 级 `ACCEPTANCE_CRITERIA.md`（B 阶段前另行编制） |

> **执行治理（对被派发的执行代理；v2.1 同步修订 + v1.4 FIX-06/FIX-07/FIX-10）**：本计划按 PRD §24 治理执行——每个步骤 = 一次独立 Dispatch = 一次独立对话，完成即 `worker_done` 结束；后续步骤必须新开对话，不得原对话延伸。每步骤（风险分级 R1+，见 00_MASTER_PLAN §4.6）经**独立审查（独立 GLM 新会话，一次覆盖"需求/架构审查维度"与"实现/测试/安全审查维度"——FIX-06 命名；本文各步骤块中"两维"即指此两维度，不以 R1/R2 指代审查维度）**方可标记 Accepted。实现者不得作为唯一审查者。禁止并发修改同一文件集合。风险分级与审查文件命名（`<步骤ID>.review.md` / `.gpt-review.md`）以 00 §4.6 与修订 11（v1.3）为准。**FIX-07/FIX-10：本文件不是独立执行计划**——步骤编号、Gate、风险等级、仓库路径、模型职责和冲突裁决均以 00_MASTER_PLAN 为准（冲突裁决层级=00 §3.0 六级层级）；本文件只提供详细规格、测试断言和验收参考（Detail Specifications），已被 00 覆盖的控制规则其执行契约一律见 00 对应章节。

**目标**：以已确认的四项技术决策为基线，产出架构与领域阶段的全部设计文档与两个丢弃式验证原型（权限容器树越权测试、中文搜索真实数据 PoC），在 G2 门冻结内容模型、权限模型、搜索后端与非功能基线，使 B 阶段（干净骨架建设）可以开工。

**架构**：Wagtail 服务端模板单栈；站点树 = 首页 → 五板块 → 部门权限容器节点（前台 404，不构成部门主页）→ 内容页；公开内容类型全部为 Page，部门/受控分类/标签词表/推荐位为 Snippet，站点级配置用 `wagtail.contrib.settings`；不修改 Wagtail 核心。

**技术栈（冻结值，见 ADR-0001）**：Wagtail `>=7.4.2,<7.5`（7.4 LTS 线）+ Django `>=5.2,<5.3`（5.2 LTS）+ Python 3.13；搜索后端待 PoC 后由 ADR-0006 冻结。

---

## 0. 已确认决策与全局约束

### 0.1 已确认决策（本项目负责人已拍板，本计划只记录与展开，不重开）

| # | 决策 | 落点 |
| --- | --- | --- |
| C1 | Wagtail 7.4.x LTS + Django 5.2 LTS + Python 3.13 | ADR-0001（S1.2） |
| C2 | 前端采用 Wagtail 服务端模板（Django 模板，无 SPA） | ADR-0002（S1.3） |
| C3 | 部门权限采用容器树（各部门容器节点承载权限），且容器节点**不得形成前台部门主页** | ADR-0004（S1.5）、S2.1、S4.2/S4.3 |
| C4 | 公开内容使用 Page；部门、受控分类、标签、配置使用 Snippet 或设置模型 | ADR-0005（S1.6）、S3.1 |

项目骨架已确认为 **C5：peiligo_restart 全新仓库干净 Wagtail 骨架**（不继承旧仓任何 Git 历史/分支/工作区——00 §2.1/OR-1/OR-2，FIX-01）。ADR-0003 以 Proposed 状态落盘，在 G1 门由项目负责人正式设为 Accepted（= D2 正式裁决记录；FIX-04 统一状态模型：Human Confirmed → ADR 以 Proposed 落盘 → G1 设 Accepted，见 S1.4）。

### 0.2 全局约束（每个步骤的要求都隐含包含本节）

1. **版本**：Wagtail `>=7.4.2,<7.5`；Django `>=5.2,<5.3`；Python 3.13.x；搜索实现经 `modelsearch>=1.3.2,<1.4`（Wagtail 7.4 拆分依赖）。不追踪 Wagtail `main`，不采用 8.0 线（含 2026-08-25 计划发布的 8.0.0，见上游审计 R5）。
2. **不改核心**：任何步骤不得提出修改 Wagtail 核心或打补丁；如声称官方扩展点不满足，必须停下升级为决策门（PRD §3）。
3. **无部门主页（硬约束）**：部门容器节点在前台必须 404（或等效不可达），不得出现在导航、站点地图、默认列表与默认搜索结果中；"部门筛选结果"不是部门主页（PRD §6、§20）。
4. **载体纪律**：公开内容 = Page；部门/受控分类/标签词表/推荐位 = Snippet；站点级配置 = settings 模型。通知与文章是两种独立 Page 类型，不得单一模型混用（PRD §7.2）。
5. **V1 不做清单（PRD §20 全文有效）**：学生账号/注册/个性化、主动推送、复杂审批流、站内报名、AI 功能、原生 App、多语言发布、部门独立主页、评论点赞收藏投稿、第三方链接自动巡检、独立课程库、零停机高可用——任何步骤不得以任何理由引入。微信公众号推送不进 V1。
6. **本计划阶段只允许两类产物**：`docs/` 下设计文档；**peiligo_restart 仓库内**的丢弃式 PoC 目录 `poc/permissions/` 与 `poc/search/`（`.gitignore` 忽略、含 `DISPOSABLE.md` 标记，验收后由总控归档或删除——FIX-08/00 修订 7：PoC 不得位于执行仓库同级或项目位置之外）。禁止：把 PoC 代码并入正式分支、创建正式项目骨架、在正式环境装依赖、触碰 PVE/生产、对旧 `peiligo` 仓库执行任何操作（OR-2 永久只读）或修改 `/Users/chenjunxian/vscode_projects/Wagtail/wagtail` 上游 clone。（滚动实现注 2026-08-18：已冻结并通过对应门、不依赖未来未决设计的内容允许提前进入正式实现——旧禁令「G2 前禁止正式代码/骨架/依赖锁定」按 `docs/decisions/ROLLING_IMPLEMENTATION_POLICY.md` 最小同步；本条对其余内容及本计划各步骤自身产物约束不变。）
7. **中文**：全部文档使用简体中文；模型/代码标识符用英文；板块中文名以 PRD §6 为准一字不差（旧站 3 个不一致命名弃用，见旧站审计 R12）。
8. **秘密纪律**：任何步骤不得读取、复制或输出凭据文件与环境变量值；报告中出现的配置只能含键名与占位（综合审计 §5.1 P0 风险的落地规则）。
9. **文件互斥**：同一时间窗内并行的步骤，其允许修改文件集合必须不相交（PRD §24.3/§24.4）。

### 0.3 外部前置条件（不在本计划步骤内，由总控/项目负责人负责）

| # | 前置 | 责任 | 未就绪时的降级 |
| --- | --- | --- | --- |
| PRE-1 | D0 审计基线确认 + C1–C4 决策有效（本次派发已隐含） | 项目负责人 | 计划不得开工 |
| ~~PRE-2~~ | **已废止**（00 修订 6：D1 处置=撤销；OR-2 旧仓永久只读即视为等效归档，不建 tag/分支——FIX-01） | — | — |
| PRE-3 | 执行仓库就绪：`peiligo_restart` 已 Git 化（00 M0.2：`git init` + 基线入库 + `rebuild/v1` 基线分支，修订 2/3/6） | 总控 | 未就绪时全部步骤在当前文档工作区 `peiligo_restart` 执行；所有产出只使用 `docs/`、`poc/` 相对路径；"全部产出位于 `rebuild/v1` 并已提交"列入 G2 检查表（条件 6 按修订 16） |
| ~~PRE-4~~ | **已由 00 M0.2 解决**（peiligo_restart Git 化为正式治理步骤；Historical 注：2026-08-15 编制本计划时该目录尚非 Git 仓库） | — | M0.2 完成后本前置自动成立 |
| PRE-5 | PoC 执行机可装 Python 3.13 venv 与本地 PostgreSQL（Docker 一次性容器即可）；zhparser 可装性未知（上游审计 U1），仅影响实验三 | 总控 | 实验三标记"环境不可行"并记录，不阻塞 E1/E2 |

---

## 1. 阶段总表与全局 DAG

### 1.1 阶段与步骤总表

| 阶段 | 步骤 | 标题 | 产出（入库） | 依赖 |
| --- | --- | --- | --- | --- |
| P1 架构冻结 | S1.1 | ADR 机制、模板与决策索引 | `docs/adr/README.md`、`docs/adr/_template.md` | PRE-1 |
| | S1.2 | ADR-0001 版本组合冻结 | `docs/adr/0001-wagtail-django-python-versions.md` | S1.1 |
| | S1.3 | ADR-0002 前端架构：服务端模板 | `docs/adr/0002-server-side-templates.md` | S1.1 |
| | S1.4 | ADR-0003 项目骨架：同仓库干净骨架 | `docs/adr/0003-clean-wagtail-skeleton.md` | S1.1 |
| | S1.5 | ADR-0004 部门权限容器树 | `docs/adr/0004-department-permission-container-tree.md` | S1.1 |
| | S1.6 | ADR-0005 Page/Snippet 分配 | `docs/adr/0005-page-vs-snippet-allocation.md` | S1.1 |
| | **G1** | **架构冻结门** | G1 记录（ADR 状态 + 批准记录） | S1.2–S1.6 |
| P2 信息架构 | S2.1 | 站点树、五板块与容器树结构 | `docs/INFORMATION_ARCHITECTURE.md` §1–§5 | G1 |
| | S2.2 | 导航、首页优先级、部门筛选与 SEO 位点 | `docs/INFORMATION_ARCHITECTURE.md` §6–§11 | S2.1 |
| P3 内容模型 | S3.1 | 类型清单与载体分配 | `docs/CONTENT_MODEL.md` §1–§4 | G1、S2.1 |
| | S3.2 | 字段级定义 + StreamField 白名单 + 受控标签 | `docs/CONTENT_MODEL.md` §5–§13 | S3.1 |
| | S3.3 | 状态机、修订、预览与删除政策 | `docs/CONTENT_MODEL.md` §14–§19 | S3.2 |
| | S3.4 | 搜索索引映射与筛选维度契约 | `docs/CONTENT_MODEL.md` §20–§24 | S3.2 |
| P4 权限 | S4.1 | 角色权限矩阵 | `docs/ROLE_PERMISSION_MATRIX.md` | G1、S2.1、ADR-0004/0005 |
| | S4.2 | 权限容器树原型构建（丢弃式） | （PoC 目录，不入库） | S4.1 |
| | S4.3 | 越权测试矩阵执行与报告 | `docs/POC_PERMISSION_REPORT.md` | S4.2 |
| P5 发布归档排程 | S5.1 | 预约发布与排程语义 | `docs/PUBLISH_ARCHIVE_SCHEDULING.md` §1–§5 | S3.3 |
| | S5.2 | 到期归档与历史搜索语义 | `docs/PUBLISH_ARCHIVE_SCHEDULING.md` §6–§10 | S5.1、S3.4 |
| P6 搜索 PoC | S6.1 | PoC 方案、数据集与评分口径 | `docs/POC_SEARCH_REPORT.md` §1–§4（方案章） | S3.4、ADR-0001 |
| | S6.2 | 环境与三组实验执行 | （PoC 目录 + 原始结果，不入库；结果摘录进报告 §5） | S6.1、PRE-5 |
| | S6.3 | 评估与 ADR-0006 决策 | `docs/POC_SEARCH_REPORT.md` §5–§8、`docs/adr/0006-chinese-search-backend.md` | S6.2 |
| P7 安全与非功能基线 | S7.1 | 安全基线 | `docs/SECURITY_BASELINE.md` | S3.2、S4.1 |
| | S7.2 | 非功能基线 | `docs/NON_FUNCTIONAL_REQUIREMENTS.md` | S2.2、S3.4、S5.1 |
| | **G2** | **架构与领域基线确认门** | G2 记录 | P2–P7 全部 |

### 1.2 全局 DAG

```text
PRE-1..5（外部前置）
   │
   ▼
S1.1 ──► S1.2 ┐
   ├──► S1.3  │
   ├──► S1.4  ├──► G1 架构冻结门
   ├──► S1.5  │
   └──► S1.6 ┘
              │
     ┌────────┼───────────────┐
     ▼        │               │
   S2.1       │               │
     ├────► S2.2              │
     │        │               │
     ├────► S3.1 ──► S3.2 ──► S3.3 ──► S5.1 ──► S5.2
     │                │  └────► S3.4 ──► S6.1 ──► S6.2 ──► S6.3（含 ADR-0006）
     │                │         └────────► S7.2
     │                └────────────────► S7.1（另需 S4.1）
     └────► S4.1 ──► S4.2 ──► S4.3
              │
              └（S4.1 亦供 S7.1）
                        │
                        ▼
   G2 基线确认门（P2–P7 全部 Accepted + 项目负责人确认）
                        │
                        ▼
   B 阶段（B1 干净骨架起，另编 03 计划，本计划范围外）
```

**并行规则**：G1 之后，`{S3.x 链}`、`{S4.x 链}`、`{S2.2}`（在 S2.1 后）可在不同 Dispatch 中并行，前提是文件集合不相交（S2.2 与 S3.1 依赖 S2.1 完成后的同一文件？否——S2.2 改 `INFORMATION_ARCHITECTURE.md`，S3.1 改 `CONTENT_MODEL.md`，不相交，可并行）。S4.2/S4.3 与 S6.2 分别在两个 PoC 目录工作，与任何 `docs/` 步骤并行均安全。

---

## 2. 通用执行契约（所有步骤隐含遵守，各步骤不再重复）

### 2.1 单步骤对话边界（Single-Step Contract）

1. 一个步骤 = 一次 Dispatch = 一个新对话；对话内只读本步骤"输入"列出的文件与本节要求的基线文档（PRD + 两份审计明细 + 综合审计，按需）。
2. 对话内只允许创建/修改本步骤"允许修改文件范围"内的文件；读其他文件须为只读引用。
3. 完成验收命令全过 + 提交留档 + 发起独立审查后，`worker_done` 结束；**禁止**在同一对话内顺手做下一步、重构别人的文档、扩大范围。
4. 有疑问用 `orca orchestration ask` 向总控提问，不得自行假设产品取舍（PRD §26 末条）；涉及 V1 范围的取舍一律升级。
5. 心跳：执行期间每 5 分钟一次 `heartbeat`。

### 2.2 提交与留档

- 执行仓库为 Git 时：每步骤一个提交，格式 `docs(<步骤ID>): <一句话>`（例：`docs(S3.2): 内容模型字段级定义`）。PoC 目录（`poc/`，位于 peiligo_restart 内、`.gitignore` 忽略——FIX-08/修订 7）禁止提交入库。
- 非 Git（PRE-4 未完成）：步骤报告（worker_done body）必须列出全部产出路径 + 每文件行数，由总控登记清单。
- 独立审查记录：独立审查者（GLM 新会话）输出一份审查记录（`docs/reviews/<步骤ID>.review.md`，含需求/架构与实现/测试/安全两维结论 Accept / 退回 + 逐条意见；R3/R4 另落 `.gpt-review.md`——00 §4.6 口径），由总控保存于其编排记录；结论摘要有争议时升级项目负责人。

### 2.3 步骤状态流转

`Draft（实现者完成）→ 独立审查（独立 GLM 新会话，只读；一次覆盖需求/架构与实现/测试/安全两维）→ Accepted`。审查退回：由**新 Dispatch**（同文件范围）修复后重审；实现者不得审查自己的产出。

### 2.4 测试要求分级

- **文档步骤（P1–P3、S4.1、S5、S6.1/S6.3、P7）**：测试要求 = ① 验收命令全过；② 文档含"可追溯性表"（文档条目 ↔ PRD 条款，格式 `条目 | PRD §`）；③ 文档含"测试断言清单"附录（为 B 阶段自动化测试预写断言，格式 `断言ID | 对象 | 断言 | PRD §`；本计划在各步骤中给出必含断言，文档可增不可减）。
- **PoC 步骤（S4.2、S4.3、S6.2）**：可执行测试套件，命令与期望输出在该步骤内明确；PoC 代码为丢弃式，不迁移入 V1，但其测试断言清单必须回写入对应入库文档。

### 2.5 失败回滚（通用）

- 步骤级：Git 仓库中 `git revert <该步骤提交>`（或 `git checkout <上一 Accepted 提交> -- <文件>`）；非 Git 工作区由总控按登记清单删除/恢复该步骤产物。回滚后该步骤回到 Draft，其下游依赖步骤禁止开工。
- 阶段级：G1 未过 → P1 内循环修复，P2 之后全部阻塞；G2 未过 → 仅退回未达标文档所属步骤，不推翻整阶段。
- 决策级：若 S4.3 发现容器树存在不可修复越权面，或 S6.3 三组实验全不达标：升级项目负责人（分别对应决策门 D5 重开、D7 独立搜索服务评估），本计划相关步骤暂停等待裁决，已 Accepted 的受影响 ADR 回到 Proposed。

### 2.6 阶段门定义

- **G1（架构冻结门）**：见 §3.7。通过前不冻结任何实现结构（综合审计 §9 约束）。
- **G2（架构与领域基线确认门）**：见 §10。通过前不进入 B 阶段主要开发（PRD §24.4）。（滚动实现注 2026-08-18：G2 仍为完整架构领域准备门，但非一切正式代码的绝对起点——已冻结过门且不依赖未决设计的内容可提前正式实现，见 `docs/decisions/ROLLING_IMPLEMENTATION_POLICY.md`。）

---

## 3. 阶段 P1：架构冻结（目标门 G1）

### S1.1 ADR 机制、模板与决策索引

- **目标**：建立 ADR（架构决策记录）机制：索引页、模板、六项决策的状态看板，使 S1.2–S1.6 与 S6.3 有统一的记录格式与状态流转（Proposed → Accepted；回退时 Rejected/Superseded）。
- **依赖**：PRE-1；输入为综合审计 §7（文档差距清单第 7 项）与 §8（决策门清单）。
- **局部 DAG**：PRE-1 → **S1.1** → S1.2、S1.3、S1.4、S1.5、S1.6、S6.3。
- **输入 → 输出**：输入 `docs/PEILIGO_REBUILD_AUDIT.md` §7–§8、PRD §19/§25。输出 `docs/adr/README.md`（索引 + 状态看板 + 状态流转规则）与 `docs/adr/_template.md`。
- **单步骤对话边界**：一次对话完成两个文件的创建；不写任何具体 ADR 内容（那是 S1.2–S1.6 的事）；不创建 `docs/adr/` 以外文件。
- **允许修改文件范围**：`docs/adr/README.md`、`docs/adr/_template.md`（均新建）。
- **执行子步骤**：
  - [ ] 读取综合审计 §7–§8
  - [ ] 写 `_template.md`：字段含 编号/标题/状态/日期/决策人/背景/决策/依据（含证据引用）/影响/复核时点/关联决策
  - [ ] 写 `README.md`：ADR 目录表（0001–0006 六行，0006 状态"未启动"）+ 状态看板 + "决策人只能是项目负责人或其书面授权，代理不得代决"声明
  - [ ] 验收命令 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/README.md && test -f docs/adr/_template.md
    grep -q '0006' docs/adr/README.md && grep -qE 'Proposed|Accepted' docs/adr/_template.md
    grep -c '^| 00' docs/adr/README.md          # 期望 ≥ 6（六项决策行）
    git status --porcelain                       # 期望仅出现上述两个新文件
    ```
- **测试要求**：文档步骤通用要求；本步骤可追溯性表覆盖 PRD §25（文档与变更管理）与综合审计 §7 第 7 项。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——状态流转是否覆盖"代理不得代决"、六项决策与综合审计 §7/§8 一一对应；实现/测试/安全面——模板字段完备性、索引表可维护性。
- **失败回滚**：删除 `docs/adr/` 两文件（或 revert 提交）；S1.2–S1.6 阻塞。
- **阶段门**：P1 内部前置；完成是 S1.2–S1.6 的开工条件，最终汇入 G1。

### S1.2 ADR-0001 版本组合冻结（Wagtail 7.4.x LTS + Django 5.2 LTS + Python 3.13）

- **目标**：把 C1 决策落成 ADR：冻结版本策略、支持窗口证据、8.0 取舍、补丁复核时点与复核命令，使后续所有步骤与 B1 有唯一版本依据。
- **依赖**：S1.1；上游审计 §2、§6 R5/R6/R8。
- **局部 DAG**：S1.1 → **S1.2** → G1；下游 S6.1/S6.2（PoC 环境按此版本）、B1（后续计划）。
- **输入 → 输出**：输入上游审计 §2（版本核验）与 §6（风险）。输出 `docs/adr/0001-wagtail-django-python-versions.md`，必含：① 冻结组合 `Wagtail >=7.4.2,<7.5`、`Django >=5.2,<5.3`、`Python 3.13.x`；② 支持窗口（Wagtail 7.4 LTS → 2027-11-02；Django 5.2 LTS → 2028-04；Python 3.13 → 2029-10）；③ 不采 8.0 的理由（RC/首发无补丁沉淀、支持窗口短、V1 无前后端分离诉求）；④ `modelsearch>=1.3.2,<1.4` 联动说明；⑤ 复核时点：G1 冻结时、B1 骨架建立时、每季度评估、上线前（PRD §17）；⑥ 复核命令（见验收命令）。
- **单步骤对话边界**：一次对话；只新建该 ADR 文件并更新 `docs/adr/README.md` 状态行；不得修改其他 ADR 或文档；线上核验只读。
- **允许修改文件范围**：`docs/adr/0001-wagtail-django-python-versions.md`（新建）、`docs/adr/README.md`（仅状态行）。
- **执行子步骤**：
  - [ ] 执行验收命令中的三个 PyPI 核验，记录当日实际输出
  - [ ] 按模板写 ADR（状态 Proposed，G1 时改 Accepted）
  - [ ] 更新 README 状态行 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0001-wagtail-django-python-versions.md
    grep -qE '7\.4' docs/adr/0001-*.md && grep -q '5\.2' docs/adr/0001-*.md && grep -q '3\.13' docs/adr/0001-*.md
    grep -qE '8\.0' docs/adr/0001-*.md        # 必须含对 8.0 的明确取舍
    grep -c '复核' docs/adr/0001-*.md          # 期望 ≥ 3
    # 当日事实核验（输出粘贴进 ADR"依据"）：
    curl -s https://pypi.org/pypi/wagtail/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"
    curl -s https://pypi.org/pypi/django/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"
    ```
    说明：若核验发现 7.4.x 有更新补丁（如 7.4.3），ADR 记录该事实并保持 `>=7.4.2,<7.5` 策略；若发现 7.4 线意外终止支持（低概率），停下升级，不得代决。
- **测试要求**：可追溯性表覆盖 PRD §19 决策门 2、§17 升级节奏；断言清单含"B1 时依赖清单必须与本 ADR 一致"。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——版本证据链与 PRD §17/§19 的符合性、8.0 取舍理由成立；实现/测试/安全面——复核命令可执行、约束表达式正确（`<7.5`、`<5.3`）。
- **失败回滚**：revert 该 ADR；README 状态行回"未启动"；G1 无此项则不通过。
- **阶段门**：G1 检查表第 1 项。

### S1.3 ADR-0002 前端架构：Wagtail 服务端模板

- **目标**：把 C2 决策落成 ADR：记录服务端模板选择、旧前端资产三类复用收割清单的落点（不复制清单本体，引用旧站审计 §5），并声明对构建链的影响（无独立 SPA 构建；静态资源经 Django static）。
- **依赖**：S1.1；旧站审计 §5–§6、上游审计 §3.5。
- **局部 DAG**：S1.1 → **S1.3** → G1；下游 S2.1/S2.2（IA 以模板渲染为前提）、B4（后续计划）。
- **输入 → 输出**：输入旧站审计 §5（复用分类）与上游审计 §3.5（模板一等公民）。输出 `docs/adr/0002-server-side-templates.md`，必含：① 决策（服务端模板）；② 论据（SEO/预览/缓存/无障碍/部署路径更短；V1 前台无登录低交互；7.4 API v2 只读不足以支撑 SPA 治理后台）；③ 旧前端收割方式：直接复用层（设计令牌机制、a11y 模式、四态规格、URL 筛选语义）→ 移植进 B 阶段模板；改造复用层（结构/文案）→ 重写参考；重写层（路由/EP/内存搜索）→ 不迁移；④ 影响与边界（学校 VI 色值待定，引用旧站审计 U2；品牌色必须按学校 VI 重定）。
- **单步骤对话边界**：一次对话；只新建该 ADR + 改 README 状态行。
- **允许修改文件范围**：`docs/adr/0002-server-side-templates.md`（新建）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 读旧站审计 §5–§6、上游审计 §3.5
  - [ ] 写 ADR（决策人记录为项目负责人，依据含两审计条目号）
  - [ ] 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0002-server-side-templates.md
    grep -qE '服务端模板' docs/adr/0002-*.md
    grep -qE '直接复用|改造复用|重新实现' docs/adr/0002-*.md   # 三档收割必须出现
    grep -q 'audit-report-old-peiligo' docs/adr/0002-*.md      # 必须引用旧站审计
    grep -c 'PRD §' docs/adr/0002-*.md                          # 期望 ≥ 3
    ```
- **测试要求**：可追溯性表覆盖 PRD §19 决策门 1、§12、§13；断言清单含"B 阶段模板页必须复用 skip-link/:focus-visible/四态规格（对应旧站审计 §5.1 条目）"。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——是否残留任何 SPA 依赖假设、与 C2 一致；实现/测试/安全面——复用三档引用是否准确对应旧站审计条目。
- **失败回滚**：revert；README 状态行回退；G1 缺项。
- **阶段门**：G1 检查表第 2 项。

### S1.4 ADR-0003 项目骨架：peiligo_restart 全新仓库干净 Wagtail 骨架（Proposed，G1 批准转 Accepted；修订 8/C5）

- **目标**：把骨架决策落成 ADR-0003（= 已确认决策 **C5** / 决策门 D2），状态 **Proposed**，在 G1 门由项目负责人正式设为 **Accepted**——FIX-04 统一状态模型：Human Confirmed（C5）→ ADR 以 Proposed 落盘 → G1 设 Accepted；批准后 B 阶段按 `wagtail start` + 按域拆 app 执行（执行本身在 MB1，不属本计划；语义按 00 修订 8）。
- **依赖**：S1.1；旧站审计 §6、上游审计 §4。
- **局部 DAG**：S1.1 → **S1.4** → G1（正式批准点）。
- **输入 → 输出**：输入两审计的骨架比较章节。输出 `docs/adr/0003-clean-wagtail-skeleton.md`，必含：① 决策（**peiligo_restart 全新仓库**内建干净骨架，不继承旧仓任何 Git 历史/分支/工作区——C5/修订 8/FIX-01）；② 证据（旧后端 FastAPI/SQLAlchemy 与 Wagtail 基座无共享栈、V1 功能覆盖率趋近零、无真实数据迁移负担、PRD §18（v1.4 修订后口径）策略）；③ 路径 A（原结构重构）的否决理由（等于重开技术基线）；④ 上游审计 §4 的 app 拆分建议（`notices/resources/guides/departments/frontend` 等）作为 B1 输入引用；⑤ 前置：PRE-2 已废止（00 修订 6，OR-2 旧仓永久只读即等效归档）——无旧仓归档前置；Git 基线 = 00 M0.2 peiligo_restart 入库（`rebuild/v1`）。
- **单步骤对话边界**：一次对话；只新建该 ADR + README 状态行；不得执行任何 `wagtail start` 或仓库分支操作。
- **允许修改文件范围**：`docs/adr/0003-clean-wagtail-skeleton.md`（新建）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 读旧站审计 §6、上游审计 §4、综合审计 §1/§8
  - [ ] 写 ADR（状态 Proposed，"决策人"字段注明"待 G1 项目负责人批准"）
  - [ ] 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0003-clean-wagtail-skeleton.md
    grep -qE 'Proposed' docs/adr/0003-*.md          # 必须保持 Proposed 直到 G1
    grep -qE 'peiligo_restart' docs/adr/0003-*.md    # C5/修订 8：全新仓库语义（FIX-01）
    grep -q 'wagtail start' docs/adr/0003-*.md
    grep -c 'PRD §' docs/adr/0003-*.md               # 期望 ≥ 2（§18 等）
    ```
- **测试要求**：可追溯性表覆盖 PRD §18、§19 决策门 3；断言清单含"B1 骨架 app 划分必须与 ADR 引用的拆分建议一致或记录偏离理由"。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——证据引用真实、未越权代决（状态必须 Proposed）；实现/测试/安全面——与 ADR-0001/0002 无矛盾。
- **失败回滚**：revert；若项目负责人在 G1 否决路径 B，则本计划 P2–P7 全部作废并升级重排（决策级回滚，见 §2.5）。
- **阶段门**：G1 检查表第 3 项（批准动作本身发生在 G1）。

### S1.5 ADR-0004 部门权限容器树（不构成前台部门主页）

- **目标**：把 C3 决策落成 ADR：部门权限容器树方案（上游审计 §3.2 方案 a），记录与扁平树方案的比较、否决理由（Publish 权限横向越权面）、"容器节点不得形成前台部门主页"的实现含义，并把"须经 S4.2/S4.3 原型验证"写为该 ADR 的生效条件。
- **依赖**：S1.1；上游审计 §3.2、综合审计 §4.3/§6 P1 风险。
- **局部 DAG**：S1.1 → **S1.5** → G1；下游 S2.1（树形态）、S4.1/S4.2/S4.3（矩阵与验证）。
- **输入 → 输出**：输入上游审计 §3.2。输出 `docs/adr/0004-department-permission-container-tree.md`，必含：① 决策（每板块下按部门建容器节点，权限挂容器向子树传播；内容页以容器为唯一父级）；② 硬约束：容器节点前台 404、不入导航/sitemap/默认列表/默认搜索，URL 可含部门段但该 URL 不渲染任何部门聚合页（细则留给 S2.1）；③ 方案 b（扁平 + ownership + explorer 过滤）否决理由：Publish 与 Edit 独立导致横向发布/下线面（上游审计原文引用）；④ Snippet 侧简化假设：V1 部门账号不持有任何 Snippet 权限（词表/部门/推荐位均总管理员管理，待 S4.1 矩阵确认）；⑤ 生效条件：S4.3 越权矩阵全绿。
- **单步骤对话边界**：一次对话；只新建该 ADR + README 状态行；不写测试代码（S4.2 的事）。
- **允许修改文件范围**：`docs/adr/0004-department-permission-container-tree.md`（新建）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 读上游审计 §3.2、PRD §4.3/§5/§6/§20
  - [ ] 写 ADR → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0004-department-permission-container-tree.md
    grep -qE '容器' docs/adr/0004-*.md && grep -qE '404|不可达' docs/adr/0004-*.md
    grep -qE '部门主页' docs/adr/0004-*.md          # 必须显式否定部门主页
    grep -qE 'Publish' docs/adr/0004-*.md           # 必须含方案 b 否决理由
    grep -q 'S4.3' docs/adr/0004-*.md               # 必须含生效条件
    ```
- **测试要求**：可追溯性表覆盖 PRD §4.3、§5、§6、§20"部门独立主页"禁项；断言清单即 T01–T16 的雏形（正式清单在 S4.1）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——"容器≠部门主页"语义与 PRD §6 一致、无扩围；实现/测试/安全面——技术表述与上游审计 §3.2 一致（权限传播、Publish/Edit 独立性）。
- **失败回滚**：revert；若 S4.3 证伪，ADR 回 Proposed 并触发决策级升级（D5 重开）。
- **阶段门**：G1 检查表第 4 项；S4.3 结果回写其附录。

### S1.6 ADR-0005 公开内容 Page / 受控数据 Snippet·设置

- **目标**：把 C4 决策落成 ADR：逐类内容的载体分配原则表，作为 S3.1 的直接输入，并固化"不为减少模型数量强行混用"（PRD §7.2）。
- **依赖**：S1.1；上游审计 §3.1/§4.3、综合审计 §4.3。
- **局部 DAG**：S1.1 → **S1.6** → G1；下游 S3.1（细化到字段）、S4.1（Snippet 权限简化依据）。
- **输入 → 输出**：输入上游审计 §3.1。输出 `docs/adr/0005-page-vs-snippet-allocation.md`，必含分配原则表：**Page** = 通知、文章（含活动结构化字段变体）、学习资料条目、软件与工具条目、校园指南条目（判据：公开内容、独立 URL、SEO/预览/排程/归档需求）；**Snippet** = Department（部门）、学科·专业方向词表、资料类型词表、指南类别词表、适用平台词表、FeaturedItem（首页推荐位，含起止时间）；**settings** = 紧急提示、统一反馈邮箱、跳转页文案等站点级配置；每行附判据与 PRD 条款。
- **单步骤对话边界**：一次对话；只新建该 ADR + README 状态行；字段级设计留给 S3.2。
- **允许修改文件范围**：`docs/adr/0005-page-vs-snippet-allocation.md`（新建）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 读上游审计 §3.1、PRD §7 全节
  - [ ] 写分配原则表 ADR → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0005-page-vs-snippet-allocation.md
    for kw in 通知 文章 学习资料 软件与工具 校园指南 部门 推荐位; do grep -q "$kw" docs/adr/0005-*.md || echo "缺: $kw"; done
    grep -q 'Snippet' docs/adr/0005-*.md && grep -q 'settings' docs/adr/0005-*.md
    grep -c 'PRD §7' docs/adr/0005-*.md        # 期望 ≥ 6（逐类引用）
    ```
- **测试要求**：可追溯性表逐行覆盖 PRD §7.1–§7.6；断言清单含"任何后续设计不得把上述 Snippet 项改为公开 URL 内容，反之亦然——变更须新 ADR"。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——与 C4 一字不差、无第三种载体发明；实现/测试/安全面——判据列完备（URL/SEO/排程/权限四维）。
- **失败回滚**：revert；S3.1 阻塞。
- **阶段门**：G1 检查表第 5 项。

### G1 架构冻结门（阶段门）

**通过条件（全部满足）**：
1. S1.2–S1.6 五份 ADR 独立审查通过且状态可转 Accepted；ADR-0001/0002/0004/0005 由项目负责人对已确认决策 C1–C4 签字记录（ADR 头"决策人/日期"）；ADR-0003 由项目负责人在 G1 作出 D2 正式裁决（默认按证据批准；否决则触发 §2.5 决策级回滚）。
2. ADR-0001 当日版本复核输出已留档（PyPI 事实 + 官方发布日程 URL）。
3. 复核 PRE-1 状态并记录（PRE-2 已废止——00 修订 6；PRE-3/PRE-4 已由 00 M0.2 解决/重定义，未就绪不阻塞 G1，但登记降级方案）。
4. 重申 V1 不做清单（PRD §20）无任何扩围。
**通过后**：解锁 P2–P7；总控发布 G1 记录（批准人、日期、ADR 状态快照）。
**未通过**：P1 内退回对应 ADR 步骤循环；P2 之后全部保持阻塞。

---

## 4. 阶段 P2：信息架构（依赖 G1）

### S2.1 站点树、五板块与部门容器树结构

- **目标**：产出 `docs/INFORMATION_ARCHITECTURE.md` 前半（§1–§5）：完整站点树、五板块定义、部门容器树结构与"非部门主页"实现规则、URL 方案、页面类型挂载约束汇总，作为 S3/S4 的结构输入。
- **依赖**：G1（ADR-0002/0004/0005）；PRD §6、§9；综合审计 §4.3。
- **局部 DAG**：G1 → **S2.1** → S2.2、S3.1、S4.1、S4.2。
- **输入 → 输出**：输入 PRD §6/§9、ADR-0004/0005、旧站审计 §5.1（URL 筛选规格）。输出 `docs/INFORMATION_ARCHITECTURE.md`：
  - §1 站点树总图（首页 → 五板块页 → 部门容器节点 → 内容页，共 4 层；含树形 ASCII 图与示例路径）；
  - §2 五板块定义（中文名冻结：校园纪事/校园活动/学习资料/软件与工具/校园指南；一句话定位；明确弃用旧站 3 个不一致命名，引用旧站审计 R12）；
  - §3 部门容器树规则（每板块下按部门建容器；容器 = 权限挂载点 + 路由分组；**前台 404**；不出现在导航、sitemap、默认列表、默认搜索；部门字段仅作元数据与筛选维度）；
  - §4 URL 方案（决策 + 理由：方案 A 默认——URL 含部门段如 `/chronicle/<dept>/<slug>/`，容器段不渲染任何页面；方案 B——无部门段需覆写 URL 生成，复杂度高，记录为否决候选；slug 用 ASCII 拼音/英文，规范细则；板块 slug 建议 `chronicle/events/materials/software/guide`，标记为可被 B 阶段微调的默认值）；
  - §5 页面类型挂载约束汇总表（每种内容 Page 的 `parent_page_types` 目标 = 部门容器；容器与板块页的 `subpage_types` 白名单——直接喂给 S3.1/S4.2）；
  - §12 可追溯性表（本步骤先建表骨架并填 §1–§5 行）。
- **单步骤对话边界**：一次对话；只新建 `INFORMATION_ARCHITECTURE.md`；不改 ADR、不写字段表（S3.2）。
- **允许修改文件范围**：`docs/INFORMATION_ARCHITECTURE.md`（新建）。
- **执行子步骤**：
  - [ ] 读 PRD §6/§9、ADR-0002/0004/0005、旧站审计 §5.1
  - [ ] 按 §1–§5 + §12 清单起草
  - [ ] 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/INFORMATION_ARCHITECTURE.md
    for s in 校园纪事 校园活动 学习资料 软件与工具 校园指南; do grep -q "$s" docs/INFORMATION_ARCHITECTURE.md || echo "缺板块: $s"; done
    grep -qE '404' docs/INFORMATION_ARCHITECTURE.md
    grep -qE '不是部门主页|不构成部门主页|无部门主页' docs/INFORMATION_ARCHITECTURE.md
    grep -q 'parent_page_types' docs/INFORMATION_ARCHITECTURE.md
    grep -c 'PRD §' docs/INFORMATION_ARCHITECTURE.md        # 期望 ≥ 8
    git status --porcelain                                    # 期望仅该文件
    ```
- **测试要求**：断言清单（入文档附录 §13，本步骤先建附录并写入）：IA-01 板块中文名与 PRD §6 完全一致；IA-02 容器 URL GET 返回 404；IA-03 容器不出现在 sitemap.xml；IA-04 容器不出现在默认搜索结果；IA-05 板块 slug 命中 §4 表。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——§3 与 PRD §6"任何部门均不建立独立主页"逐句对得上；URL 方案未偷换概念；实现/测试/安全面——§5 约束表与 ADR-0004/0005 无冲突、树图与约束表自洽。
- **失败回滚**：revert 该文件；S2.2/S3.1/S4.1/S4.2 阻塞。
- **阶段门**：G2 检查表"信息架构"项的组成之一。

### S2.2 导航、首页信息优先级、部门筛选与 SEO/noindex 位点

- **目标**：完成 `INFORMATION_ARCHITECTURE.md` 后半（§6–§11）：全局导航与面包屑、首页四层信息优先级与推荐位/紧急提示位点、部门筛选语义（≠部门主页）、搜索与筛选的 URL 状态规格、SEO/noindex 位点。
- **依赖**：S2.1；PRD §9、§10、§12。
- **局部 DAG**：S2.1 → **S2.2** → S7.2；汇入 G2。
- **输入 → 输出**：输入 S2.1 版本、PRD §9/§10/§12、旧站审计 §5.1（四态与 URL 筛选规格、面包屑结构）。输出增补：§6 全局导航与面包屑（五板块 + 首页 + 关于/反馈入口；面包屑路径含板块不含容器段或含容器段的展示规则——按 §4 方案 A 决定并写死）；§7 首页信息优先级（1 紧急/重要提示 → 2 最新有效通知 → 3 近期活动 → 4 板块入口与其他；推荐位与紧急提示的展示位点、数量固定原则）；§8 部门筛选语义（筛选结果 URL 形态、标题文案规则——"XX 部门发布的内容（筛选结果）"而非部门主页；PRD §6 原文引用）；§9 搜索与筛选 URL 状态规格（`?q=&section=&dept=&type=&tag=` 的 query string 语义、非法值回退全部、可分享可刷新——移植旧站规格并中文化）；§10 SEO/noindex 位点（默认可收录、单篇 noindex 字段位点、sitemap/redirects 贡献位）；§11 无结果/空态规格落点（引用旧站四态规格）。并补全 §12 可追溯性行、§13 断言（IA-06 导航不含部门入口；IA-07 面包屑与 §4 方案一致；IA-08 筛选页 title 不含"主页"字样；IA-09 noindex 单篇生效）。
- **单步骤对话边界**：一次对话；只编辑 `INFORMATION_ARCHITECTURE.md` §6–§13；不改 §1–§5（发现问题走 ask 或记入"遗留问题"小节）。
- **允许修改文件范围**：`docs/INFORMATION_ARCHITECTURE.md`（仅 §6 起的增补）。
- **执行子步骤**：
  - [ ] 读 PRD §9/§10/§12、旧站审计 §5.1、S2.1 版本全文
  - [ ] 增补 §6–§13 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    grep -q '紧急' docs/INFORMATION_ARCHITECTURE.md && grep -q '置顶\|推荐位' docs/INFORMATION_ARCHITECTURE.md
    grep -qE '\?q=|query' docs/INFORMATION_ARCHITECTURE.md
    grep -q 'noindex' docs/INFORMATION_ARCHITECTURE.md
    grep -q '面包屑' docs/INFORMATION_ARCHITECTURE.md
    test "$(grep -c '^## ' docs/INFORMATION_ARCHITECTURE.md)" -ge 13
    ```
- **测试要求**：断言 IA-06–IA-09 写入附录；可追溯性表补 PRD §9/§10/§12 行。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——首页优先级与 PRD §9 逐层对应；部门筛选文案不构成"部门主页"暗示；实现/测试/安全面——§9 query 语义与旧站规格的移植无丢失、§6 与 §4 URL 方案无矛盾。
- **失败回滚**：revert 本次增补（保留 S2.1 版本）；S7.2 阻塞。
- **阶段门**：与 S2.1 合成 G2"信息架构"项。

---

## 5. 阶段 P3：内容模型（依赖 G1；S3.1 另依赖 S2.1）

### S3.1 内容类型清单与 Page/Snippet 载体分配

- **目标**：产出 `docs/CONTENT_MODEL.md` §1–§4：全部内容与受控数据类型的清单、载体分配细化（承接 ADR-0005 原则到逐类型）、树位置约束（承接 S2.1 §5）、推荐位与紧急提示的载体确认。
- **依赖**：G1、S2.1；ADR-0005。
- **局部 DAG**：S2.1 → **S3.1** → S3.2；（与 S2.2 可并行，文件不相交）。
- **输入 → 输出**：输入 ADR-0005、`INFORMATION_ARCHITECTURE.md` §1–§5、PRD §7。输出 `docs/CONTENT_MODEL.md`：
  - §1 类型总清单表（类型 | 中文/英文名 | 载体 | 板块 | 树父级 | PRD 条款）：NoticePage 通知（纪事/活动）、ArticlePage 文章（纪事/活动）、StudyMaterialPage 学习资料条目（学习资料）、SoftwareToolPage 软件与工具条目（软件与工具）、GuideEntryPage 校园指南条目（校园指南）——均 Page；Department、Discipline、MaterialType、GuideCategory、Platform、FeaturedItem——均 Snippet；SiteSettings——settings；
  - §2 活动结构化字段的承载决策（默认候选：EventFieldsMixin 供纪事/活动板块下的通知/文章附加活动字段，避免发明第三内容类型与 PRD §7.2"两种独立类型"冲突；本步骤必须给出采纳或否决的结论与理由）；
  - §3 推荐位与紧急提示载体确认（FeaturedItem：Snippet，数量固定、带起止时间、仅总管理员——承接 ADR-0005；紧急提示：SiteSettings 字段）；
  - §4 部门字段规范（所有内容 Page 含 `department = ForeignKey(Department)`，前台仅展示部门名称——PRD §4.3/§6）；
  - §25 可追溯性表（先建并填 §1–§4 行）。
- **单步骤对话边界**：一次对话；只新建 `CONTENT_MODEL.md`；字段级细节（类型/必填/校验）留给 S3.2。
- **允许修改文件范围**：`docs/CONTENT_MODEL.md`（新建）。
- **执行子步骤**：
  - [ ] 读 ADR-0005、IA §1–§5、PRD §7.1–§7.2
  - [ ] 起草 §1–§4 + §25 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/CONTENT_MODEL.md
    for kw in NoticePage ArticlePage StudyMaterialPage SoftwareToolPage GuideEntryPage Department FeaturedItem SiteSettings; do grep -q "$kw" docs/CONTENT_MODEL.md || echo "缺: $kw"; done
    grep -q 'EventFieldsMixin' docs/CONTENT_MODEL.md
    grep -c 'ADR-0005' docs/CONTENT_MODEL.md      # 期望 ≥ 5
    ```
- **测试要求**：断言清单（附录 §26，本步骤建）：CM-00 每种公开内容类型均为 Page 且父级只能是本部门容器（综合 ADR-0004/0005）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——清单与 PRD §6/§7 一一对应、无多余类型、无遗漏类型；实现/测试/安全面——命名与 ADR-0005 判据一致、EventFieldsMixin 决策理由成立。
- **失败回滚**：revert 该文件；S3.2 阻塞。
- **阶段门**：G2"内容模型"项组成之一。

### S3.2 字段级模型定义（六类内容 + StreamField 白名单 + 受控标签）

- **目标**：产出 §5–§13：每类内容的字段表（字段 | 类型 | 必填 | 约束/校验 | PRD 条款）、StreamField block 白名单、RichText features 收窄清单、受控标签机制。
- **依赖**：S3.1；PRD §7.1–§7.7；上游审计 §3.1。
- **局部 DAG**：S3.1 → **S3.2** → S3.3、S3.4、S5.1、S7.1。
- **输入 → 输出**：输入 S3.1 版本、PRD §7、上游审计 §3.1（StreamField/RichText features/taggit）。输出增补：
  - §5 通知 NoticePage 字段表：标题、摘要、正文（StreamField）、所属板块（由树位置推导，说明推导规则）、发布部门（FK Department）、发布时间、**有效期 `expire_at`（必填）**、图片、附件、外部链接、受控标签（PRD §7.1 逐条）；
  - §6 文章 ArticlePage：同通知去掉有效期必填（可不设下线时间，PRD §7.2）；
  - §7 活动结构化字段（EventFieldsMixin，若 S3.1 采纳）：开始时间、结束时间（成对校验，结束 ≥ 开始）、活动地点、线上标记（布尔，线上时地点展示"线上"）、报名链接（可选，URL，输出必须经跳转页包装）、活动状态三态计算规则（按当前时间对比起止：即将开始/进行中/已结束——PRD §7.3）；
  - §8 学习资料 StudyMaterialPage：学科·专业方向（FK Discipline）、资料类型（FK MaterialType）、关键词标签（受控标签）、标题/摘要/正文、外部链接与附件（PRD §7.4；明确不做课程库）；
  - §9 软件与工具 SoftwareToolPage：名称、用途说明、适用平台（M2M Platform）、来源链接或网盘链接（输出必须经统一确认跳转页）、授权或费用说明、发布时间或最后更新时间（PRD §7.5；不托管安装包）；
  - §10 校园指南 GuideEntryPage：九字段一字不差——服务名称、指南类别（FK GuideCategory）、地点、开放时间、联系方式、补充说明、责任来源或责任单位、维护方式、最后确认日期或更新时间（PRD §7.6）；
  - §11 StreamField block 白名单：标题（CharBlock 级）、段落（RichTextBlock features 收窄——给出具体 features 清单，如 `bold italic link ol ul`，不含 image/无 h1？——由本步骤按学校 VI 与 a11y 给出并说明）、图片（ImageChooserBlock）、附件（DocumentChooserBlock）、表格（`wagtail.contrib.table_block`）、外部链接（URLBlock，输出经跳转页）；**无 RawHTMLBlock**；普通部门账号不得输入任意 HTML/CSS（PRD §7.7）；
  - §12 受控标签机制：`ClusterTaggableManager`（taggit）；词表仅总管理员可增改；部门账号表单只能从既有标签选择（给出机制选项与推荐：受控 Tag 源/choice 限定，结论由本步骤定并说明）；
  - §13 Snippet 字段表（Department：名称/代号/排序/停用；Discipline/MaterialType/GuideCategory/Platform：名称/排序；FeaturedItem：指向内容、起止时间、启用；SiteSettings：紧急提示文案与起止、统一反馈邮箱、跳转页文案）；
  - §25 可追溯性行补全；§26 断言追加：CM-01 通知必填集含有效期；CM-02 通知/文章父级仅纪事/活动板块的本部门容器；CM-03 活动状态三态按时间正确计算；CM-04 学习资料学科/类型必为受控 FK；CM-05 软件工具外链仅经跳转页输出；CM-06 指南九字段必填集；CM-07 正文白名单不含 RawHTML；CM-08 部门账号不能新建自由标签。
- **单步骤对话边界**：一次对话；只编辑 `CONTENT_MODEL.md` §5–§13、§25–§26 对应行。
- **允许修改文件范围**：`docs/CONTENT_MODEL.md`（§5 起的增补与附录补行）。
- **执行子步骤**：
  - [ ] 读 PRD §7 全节、上游审计 §3.1、S3.1 版本
  - [ ] 逐类写字段表（每字段一行含 PRD 条款号）
  - [ ] 写白名单与标签机制 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    for kw in expire_at 服务名称 开放时间 维护方式 适用平台 授权; do grep -q "$kw" docs/CONTENT_MODEL.md || echo "缺: $kw"; done
    grep -q 'RawHTML' docs/CONTENT_MODEL.md            # 必须显式禁止
    grep -q 'taggit\|ClusterTaggableManager' docs/CONTENT_MODEL.md
    grep -q 'table_block' docs/CONTENT_MODEL.md
    grep -qE '即将开始|进行中|已结束' docs/CONTENT_MODEL.md
    test "$(grep -c '^| ' docs/CONTENT_MODEL.md)" -ge 60   # 字段表行数下限
    ```
- **测试要求**：断言 CM-01–CM-08 全部写入附录；每张字段表行内 PRD 条款号可 grep（抽查命令：`grep -c 'PRD §7' docs/CONTENT_MODEL.md` ≥ 20）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——逐字段对照 PRD §7.1–§7.6 无缺失无添加（尤其指南九字段、通知有效期必填、文章无必填下线）；实现/测试/安全面——类型选择合理（日期时间用 DateTimeField、受控维度一律 FK/M2M 不用自由文本）、白名单与"部门账号无任意 HTML"一致。
- **失败回滚**：revert 本次增补，回到 S3.1 版本；S3.3/S3.4/S5.1/S7.1 阻塞。
- **阶段门**：G2"内容模型"项组成之一。

### S3.3 状态机、修订、预览与删除政策

- **目标**：产出 §14–§19：内容生命周期状态机（draft/live/expired/unpublished）、修订与预览与锁、预约/到期字段映射、永久删除政策。
- **依赖**：S3.2；PRD §5（修订）、§8（发布/归档/删除）；上游审计 §3.3。
- **局部 DAG**：S3.2 → **S3.3** → S5.1、S7.1；汇入 G2。
- **输入 → 输出**：输入 S3.2 版本、上游审计 §3.3（DraftStateMixin/RevisionMixin/expire 语义）。输出增补：§14 状态机图与转换表（draft → live（发布/预约到点）；live → expired（到期任务）；live → unpublished（手动下线）；expired/unpublished 可重新发布回 live；非法转换列举）；§15 修订/预览/锁（Page 内建；Snippet 侧决策：FeaturedItem 等是否混入 `DraftStateMixin`——推荐位需要起止时间生效，给出 mixin 取舍结论）；§16 预约与到期字段映射（`go_live_at`/`expire_at` 一览表，通知 expire_at 必填、文章可选、推荐位必填起止）；§17 永久删除政策（仅总管理员；部门仅可 unpublish 自己内容；删除前需确认无关联推荐位引用——引用完整性规则）；§18 测试断言：CM-10 状态转换仅按 §14 表；CM-11 每次保存产生修订并记录操作者与时间；CM-12 delete 权限仅总管理员组；CM-13 推荐位引用被删内容时的行为规则（本步骤定，默认：阻止删除并提示）；§19 可追溯性行。
- **单步骤对话边界**：一次对话；只编辑 §14–§19 与附录补行。
- **允许修改文件范围**：`docs/CONTENT_MODEL.md`（§14 起增补）。
- **执行子步骤**：
  - [ ] 读 PRD §5/§8、上游审计 §3.3、S3.2 版本
  - [ ] 写状态机与政策 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    grep -qE 'draft|live|expired' docs/CONTENT_MODEL.md
    grep -q 'go_live_at' docs/CONTENT_MODEL.md && grep -q 'expire_at' docs/CONTENT_MODEL.md
    grep -q 'RevisionMixin\|修订' docs/CONTENT_MODEL.md
    grep -qE '总管理员' docs/CONTENT_MODEL.md          # 永久删除权限表述
    grep -q 'publish_scheduled' docs/CONTENT_MODEL.md || grep -q 'publish_scheduled' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    ```
- **测试要求**：断言 CM-10–CM-13 写入附录；状态机图为可测试的转换表（每行 = 一条 B 阶段测试用例来源）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——状态集合与 PRD §8"默认下线或归档、不直接永久删除"一致；实现/测试/安全面——mixin 映射与上游审计 §3.3 事实一致（expired = set_expired 的 unpublish，内容保留）。
- **失败回滚**：revert 本次增补；S5.1/S7.1 阻塞。
- **阶段门**：G2"内容模型"项组成之一。

### S3.4 搜索索引映射与筛选维度契约

- **目标**：产出 §20–§24：每类内容进搜索索引的字段映射、筛选 facet 清单、空态规格落点、以及供 S6 PoC 直接使用的"最小字段契约"。
- **依赖**：S3.2；PRD §10；上游审计 §3.4。
- **局部 DAG**：S3.2 → **S3.4** → S6.1、S7.2、S5.2；汇入 G2。
- **输入 → 输出**：输入 S3.2 版本、PRD §10。输出增补：§20 索引字段映射表（类型 | 进索引字段：标题/摘要/正文文本/部门名称/标签/类别/指南结构化字段——`search_fields` 设计）；§21 筛选 facet 清单与 PRD §10 逐条对照（板块、部门、内容类型、学科、资料类型、指南类别、标签；搜索结果页支持组合筛选）；§22 无结果提示与四态规格落点（引用 IA §11）；§23 **PoC 最小字段契约**：`title（CharField）、body（纯文本长字段）、department（CharField 代号）、tags（CharField 逗号分隔）、category（CharField）` + 数据规模分级 200/1000/5000——S6.2 按此构造数据集；§24 过期内容的搜索包含规则引用（细则在 S5.2，此处只留指针）；§25–§26 补行：CM-20 索引字段覆盖 PRD §10 全部维度；CM-21 指南结构化字段（地点/开放时间）可被搜索命中。
- **单步骤对话边界**：一次对话；只编辑 §20–§24 与附录。
- **允许修改文件范围**：`docs/CONTENT_MODEL.md`（§20 起增补）。
- **执行子步骤**：
  - [ ] 读 PRD §10、S3.2 版本、上游审计 §3.4
  - [ ] 写映射表与契约 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    grep -q 'search_fields' docs/CONTENT_MODEL.md
    for kw in 板块 部门 内容类型 标签; do grep -q "$kw" docs/CONTENT_MODEL.md || echo "缺 facet: $kw"; done
    grep -q 'PoC' docs/CONTENT_MODEL.md && grep -q '200' docs/CONTENT_MODEL.md && grep -q '5000' docs/CONTENT_MODEL.md
    grep -c 'PRD §10' docs/CONTENT_MODEL.md     # 期望 ≥ 3
    ```
- **测试要求**：断言 CM-20/CM-21 写入；§23 契约字段名与 S6.1 引用严格一致（本计划内一致性由独立审查把关——00 v1.4 审查维度口径，FIX-06）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——facet 清单与 PRD §10 六个"至少覆盖"逐条对上；实现/测试/安全面——索引字段与 §5–§13 字段表无悬空引用。
- **失败回滚**：revert 本次增补；S6.1/S5.2/S7.2 阻塞。
- **阶段门**：G2"内容模型"项完成（S3.1–S3.4 齐）。

---

## 6. 阶段 P4：权限矩阵与容器树原型（依赖 G1 + S2.1；可与 P3 并行）

### S4.1 角色权限矩阵（ROLE_PERMISSION_MATRIX.md）

- **目标**：产出角色 × 对象 × 动作的完整权限矩阵文档，并映射到 Wagtail/Django 实现机制（组、树权限挂载、collection、panel permission），作为 S4.2 原型配置的唯一依据与 B2 的实现规约。
- **依赖**：G1、S2.1；ADR-0004/0005；PRD §4、§5、§8。
- **局部 DAG**：S2.1 → **S4.1** → S4.2、S7.1；汇入 G2。
- **输入 → 输出**：输入 PRD §4.2–§4.4/§5/§8、ADR-0004/0005、上游审计 §3.2。输出 `docs/ROLE_PERMISSION_MATRIX.md`：
  - §1 角色定义（总管理员、部门岗位账号〔每部门至多一个、属岗位不属个人、交接即重置凭据〕、技术维护人员、未登录访客）；
  - §2 主矩阵（对象行：本部门内容页〔六类〕、他部门内容页、板块页与容器节点、Department/词表/FeaturedItem 等 Snippet、SiteSettings、图片与文档〔按 Collection〕、用户与组、置顶/推荐位、永久删除；动作列：查看/创建/编辑/发布/下线/归档/删除/管理；四角色逐一填 允许/禁止 + PRD 条款号）；
  - §3 Wagtail 实现映射（部门组 = Group + 容器节点 Add/Edit/Publish/Lock 权限；总管理员 = 管理员组 + superuser 边界说明；置顶字段 = `FieldPanel(permission=...)` 面板级权限；图片/文档 = 每部门一个 Collection；部门账号零 Snippet 权限〔确认或修订 ADR-0004 §④ 假设〕）；
  - §4 账号生命周期（创建/停用/重置/交接强制改密流程；密码重置后强制修改；无长期统一默认密码）；
  - §5 访问边界（后台仅校园网/VPN、HTTPS、限速、强密码——细则引用 S7.1，此处只留权限相关条目）；
  - §6 测试断言清单 = T01–T16 全表（见 S4.2，矩阵行 ↔ 测试 ID 双向索引）；
  - §7 可追溯性表。
- **单步骤对话边界**：一次对话；只新建该文档；不建任何代码/账号。
- **允许修改文件范围**：`docs/ROLE_PERMISSION_MATRIX.md`（新建）。
- **执行子步骤**：
  - [ ] 读 PRD §4/§5/§8、ADR-0004/0005、上游审计 §3.2
  - [ ] 写 §1–§7 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/ROLE_PERMISSION_MATRIX.md
    for kw in 总管理员 部门岗位 技术维护 未登录; do grep -q "$kw" docs/ROLE_PERMISSION_MATRIX.md || echo "缺角色: $kw"; done
    grep -q 'Collection' docs/ROLE_PERMISSION_MATRIX.md && grep -q 'FieldPanel' docs/ROLE_PERMISSION_MATRIX.md
    grep -qE 'T01|T16' docs/ROLE_PERMISSION_MATRIX.md
    test "$(grep -c '^| ' docs/ROLE_PERMISSION_MATRIX.md)" -ge 40
    ```
- **测试要求**：断言清单 T01–T16 全表落档；每矩阵单元格有 PRD 条款号或"由 PRD 推导"标注。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——矩阵与 PRD §4.2/§4.3 逐句一致（部门"只能创建、编辑、发布、下线和归档本部门内容"六个动词逐一对上；不得修改其他部门/配置/账号/板块/置顶）；实现/测试/安全面——实现映射与上游审计 §3.2 事实一致（Add=只编辑删除自己拥有的页面、Publish 与 Edit 独立、Snippet 模型级权限）。
- **失败回滚**：revert 该文件；S4.2/S7.1 阻塞。
- **阶段门**：G2"权限"项组成之一。

### S4.2 权限容器树原型构建（丢弃式）

- **目标**：在 **peiligo_restart 仓库内**的丢弃目录 `poc/permissions/`（FIX-08/00 修订 7）中，按 ADR-0004/S4.1 构建最小 Wagtail 原型（容器树 + 组 + 权限 + collections + T01–T16 测试），为 S4.3 执行越权测试提供环境。**原型代码 git 忽略、不入库、不并入 V1。**
- **依赖**：S4.1（矩阵与 T 表）；ADR-0001（版本）；PRE-5。
- **局部 DAG**：S4.1 → **S4.2** → S4.3；（与 S3.x、S5、S6 文档步骤可并行）。
- **输入 → 输出**：输入 `ROLE_PERMISSION_MATRIX.md`、ADR-0001/0004。输出：`peiligo_restart` 内 `poc/permissions/` 丢弃项目（git 忽略，含 `DISPOSABLE.md` 首行声明"丢弃式验证，禁止并入任何正式分支"），内含：Python 3.13 venv；Wagtail `>=7.4.2,<7.5` + Django `>=5.2,<5.3`；模型——五个板块页（可用一个 SectionPage 类型五实例或五子类，按 S2.1 §5）、DepartmentContainerPage（`serve()` 直接 `Http404`）、NoticePage、ArticlePage、EventFieldsMixin、Department/FeaturedItem Snippet、SiteSettings；组——admins / dept_A / dept_B（按 S4.1 §3 映射配置树权限与 collections）；种子——2 部门 × 每板块容器 + 若干通知/文章；测试套件 `tests/test_permissions.py` 实现 T01–T16（用 `WagtailPageTestCase`/`TestCase` + `self.login()`）。
- **T01–T16 必含测试表**（S4.1 §6 同表）：

  | ID | 断言 | PRD |
  | --- | --- | --- |
  | T01 | dept_A 可在本部门"纪事"容器下创建通知 | §4.3 |
  | T02 | dept_A 在 dept_B 容器下创建被拒 | §4.3 |
  | T03 | dept_A 编辑 dept_B 页面被拒 | §4.3 |
  | T04 | dept_A 发布 dept_B 页面被拒 | §4.3 |
  | T05 | dept_A 下线 dept_B 页面被拒 | §4.3 |
  | T06 | dept_A 删除（含自己）页面被拒；仅管理员可删 | §8 |
  | T07 | 管理员可删除与永久下线任意内容 | §4.2 |
  | T08 | dept_A 无任何 Snippet 管理入口（Department/FeaturedItem） | §4.3 |
  | T09 | dept_A 改 FeaturedItem 被拒（推荐位仅总管理员） | §8 |
  | T10 | dept_A 编辑界面看不到/不能改置顶字段（panel permission） | §8 |
  | T11 | dept_A 不能创建/停用账号；管理员可以 | §4.2 |
  | T12 | 匿名 GET 部门容器 URL → 404（非部门主页） | §6/§20 |
  | T13 | dept_A 后台页面浏览器列表只见本部门容器子树 | §4.3 |
  | T14 | dept_A 不能编辑 dept_B Collection 中的图片；本部门 Collection 可以 | §4.3 |
  | T15 | dept_A 不能访问 SiteSettings（紧急提示） | §4.2 |
  | T16 | 通知挂到"校园指南"等错误板块容器被拒（parent 约束） | §7.1 |

- **单步骤对话边界**：一次对话；只在 `poc/permissions/` 丢弃目录内创建文件；**禁止**在该目录外创建任何文件（含 `docs/` 与骨架位置）、禁止 git 提交到正式分支；依赖安装仅发生于该目录 venv（本步骤的既定目的，G0 后按 OR-3 ② 解禁）。
- **允许修改文件范围**：`poc/permissions/**`（peiligo_restart 内，git 忽略，新建；本步唯一可写位置）；`docs/` 与正式骨架 0 文件。
- **执行子步骤**：
  - [ ] 建目录 + `DISPOSABLE.md` + venv + 安装 ADR-0001 版本（记录实际安装版本）
  - [ ] `wagtail start` 最小项目（仅本地开发 settings；数据库：首选本机 Docker `postgres:16` 一次性容器，不可用时 sqlite 仅作冒烟并在报告注明）
  - [ ] 写模型/组/权限/collections/种子
  - [ ] 写 `tests/test_permissions.py` T01–T16
  - [ ] `pytest -q` 全绿（若有红：修复原型配置——修复的是原型，不是矩阵；若矩阵本身错，停下 ask）
  - [ ] worker_done（报告路径 + 测试统计）
- **验收命令**（在 peiligo_restart 根的 `poc/permissions/` 内）：
    ```bash
    test -f DISPOSABLE.md
    ./.venv/bin/python -m pip freeze | grep -iE '^wagtail==7\.4\.'   # 期望 7.4.x
    ./.venv/bin/python -m pip freeze | grep -iE '^Django==5\.2\.'   # 期望 5.2.x
    ./.venv/bin/python -m pytest tests/ -q          # 期望 16 passed
    # 正式仓库侧范围检查（在 peiligo_restart 根执行）：
    git status --porcelain                           # 期望空（poc/ 已被 .gitignore 忽略）
    ```
- **测试要求**：T01–T16 全部实现且通过；测试不得跳过（`skip` 视为失败）；每条测试 docstring 标注矩阵行号与 PRD 条款。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——测试断言与矩阵逐行对应、无漏测横向越权面；实现/测试/安全面——测试有效性（真的走权限层而非绕过；`self.login()` 用户确在目标组；T12 断言的是 HTTP 404）。
- **失败回滚**：删除整个 `poc/permissions/` 目录；S4.3 阻塞；无正式仓库污染需清理（验收命令已验证）。
- **阶段门**：G2"权限"项组成之一；产物供 S4.3 消费。

### S4.3 越权测试矩阵执行与报告（POC_PERMISSION_REPORT.md）

- **目标**：在 S4.2 原型上正式执行 T01–T16，采集逐条证据输出，写入入库报告，给出"容器树方案验证通过/存在越权面"结论并回写 ADR-0004 附录。
- **依赖**：S4.2。
- **局部 DAG**：S4.2 → **S4.3** → G2；结论回写 ADR-0004（仅附录与状态行）。
- **输入 → 输出**：输入 `poc/permissions/`（只读运行）。输出 `docs/POC_PERMISSION_REPORT.md`：① 环境记录（版本实测、DB 类型、日期）；② T01–T16 结果表（ID | 结果 | 证据摘录〔pytest 输出关键行〕）；③ 结论（通过 / 列出失败项与初判原因）；④ 对 ADR-0004 与 ROLE_PERMISSION_MATRIX 的修订建议（如有）；⑤ 附录：复现命令。同时更新 ADR-0004 附录"验证记录"与 `docs/adr/README.md` 状态行。
- **单步骤对话边界**：一次对话；对 PoC 目录只读+运行（不得改原型代码——若测试需修复，退回 S4.2 新 Dispatch）；入库只写报告 + ADR 附录/状态。
- **允许修改文件范围**：`docs/POC_PERMISSION_REPORT.md`（新建）、`docs/adr/0004-*.md`（仅附录与状态）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 干净重跑：`pytest -v` 采集完整输出
  - [ ] 写报告四节 + 附录
  - [ ] 回写 ADR-0004 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/POC_PERMISSION_REPORT.md
    for t in T01 T05 T10 T12 T16; do grep -q "$t" docs/POC_PERMISSION_REPORT.md || echo "缺: $t"; done
    grep -qE '通过|越权' docs/POC_PERMISSION_REPORT.md
    grep -q 'S4.3' docs/adr/0004-*.md || grep -q '验证记录' docs/adr/0004-*.md
    cd poc/permissions && ./.venv/bin/python -m pytest tests/ -q   # 复跑期望 16 passed（证据可复现）
    ```
- **测试要求**：16/16 通过 = 通过；任一失败即报告"未通过 + 原因"，ADR-0004 保持/回到 Proposed，升级决策级处理（§2.5）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——结论与结果表一致、失败项无粉饰；实现/测试/安全面——证据摘录真实可复现（审查者重跑一条抽查）。
- **失败回滚**：revert 报告与 ADR 回写；若结论为"存在越权面"，触发 D5 重开升级，P4 冻结待裁决。
- **阶段门**：G2"权限原型通过"检查项（硬性 16/16 或项目负责人书面豁免）。

---

## 7. 阶段 P5：发布、归档与排程（依赖 S3.3）

### S5.1 预约发布与排程语义（PUBLISH_ARCHIVE_SCHEDULING.md 前半）

- **目标**：产出 §1–§5：预约发布、推荐位排程、到期自动下线的完整语义与运维安排（`publish_scheduled` 任务在容器环境中的安排），并预写 B 阶段测试断言。
- **依赖**：S3.3；PRD §7.1/§7.2（预约）、§8、§9（推荐位起止）；上游审计 §3.3。
- **局部 DAG**：S3.3 → **S5.1** → S5.2、S7.2；汇入 G2。
- **输入 → 输出**：输入 S3.3 版本、上游审计 §3.3。输出 `docs/PUBLISH_ARCHIVE_SCHEDULING.md`：§1 预约发布语义（`go_live_at`；未到时间：前台 404、不出现在任何列表；到点：`publish_scheduled` 执行后 live——**任务每小时运行**〔官方建议〕，因此"到点可见"存在最长 1 小时窗口，本文档必须显式记录该窗口并作为验收口径；容器环境安排：独立 cron/任务容器，B6 落地）；§2 首页推荐位排程（FeaturedItem 起止时间语义、数量固定值——默认建议 6，标记"项目负责人确认"；仅总管理员管理，部门申请走邮箱，PRD §8）；§3 到期自动下线（`expire_at` 到点 → 带 `set_expired` 的 unpublish；内容与修订保留；通知必填有效期、文章可选、指南不设）；§4 手动下线（unpublish）语义与归档的关系指针（细则 S5.2）；§5 测试断言：PS-01 预约未到前台 404 且不入列表；PS-02 `publish_scheduled` 执行后到点内容 live；PS-03 推荐位仅在起止窗口内于首页展示；PS-04 推荐位数量不超过固定上限；PS-05 到期执行后内容退出首页与默认列表；可追溯性表 §11。
- **单步骤对话边界**：一次对话；只新建该文档；归档/搜索语义留 S5.2。
- **允许修改文件范围**：`docs/PUBLISH_ARCHIVE_SCHEDULING.md`（新建）。
- **执行子步骤**：
  - [ ] 读 PRD §7/§8/§9、上游审计 §3.3、S3.3 版本
  - [ ] 写 §1–§5 + §11 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/PUBLISH_ARCHIVE_SCHEDULING.md
    grep -q 'go_live_at' docs/PUBLISH_ARCHIVE_SCHEDULING.md && grep -q 'expire_at' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    grep -q 'publish_scheduled' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    grep -q '小时' docs/PUBLISH_ARCHIVE_SCHEDULING.md        # 窗口口径必须显式
    grep -qE 'PS-0[1-5]' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    ```
- **测试要求**：断言 PS-01–PS-05 落档；§1 的窗口口径是 B 阶段测试的时间容差依据。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——与 PRD §7.1/§8/§9 逐条一致，推荐位"数量固定、起止时间、仅总管理员"三要素齐；实现/测试/安全面——与上游审计 §3.3 事实一致（每小时建议、set_expired 语义）。
- **失败回滚**：revert 该文件；S5.2/S7.2 阻塞。
- **阶段门**：G2"发布归档排程"项组成之一。

### S5.2 到期归档与历史搜索语义（后半）

- **目标**：产出 §6–§10：解决综合审计 R4/上游审计 R4 的核心张力——Wagtail 默认到期即不可见 vs PRD §7.1"到期后保留在历史归档及站内搜索中"，给出归档查询、默认列表、搜索三处的可见性规则与断言。
- **依赖**：S5.1、S3.4。
- **局部 DAG**：S5.1 → **S5.2** → G2、S7.2（引用）。
- **输入 → 输出**：输入 S5.1 版本、S3.4 版本、PRD §7.1/§8、上游审计 §3.3"注意张力"。输出增补：§6 归档区语义（每板块设"历史归档"视图：queryset 含 `expired` 页面并标注"已过期"徽标；URL 形态 `/chronicle/archive/` 之类——形态留给 B4，此处定语义）；§7 可见性规则总表（首页：仅 live 且未过期；板块默认列表：仅 live；归档列表：live + expired，expired 标注；**站内搜索：默认包含 expired 通知**〔PRD §7.1 原文〕，搜索结果对 expired 条目标注；未发布/已下线（unpublished）：任何前台位置与搜索均不可见）；§8 下线 vs 归档 vs 永久删除三态对比表（谁可执行、内容是否保留、是否可搜索）；§9 纠错下架快速通道（版权/安全投诉：总管理员立即 unpublish + 内部记录，PRD §11）；§10 测试断言：PA-01 到期后退出首页与默认列表；PA-02 归档列表可见且带"已过期"标注；PA-03 站内搜索默认命中过期通知；PA-04 手动下线内容前台 404 且搜索不可见；PA-05 永久删除仅总管理员且产生审计记录；PA-06 未发布草稿任何匿名路径不可达；§11 可追溯性补行。
- **单步骤对话边界**：一次对话；只编辑 §6 起增补。
- **允许修改文件范围**：`docs/PUBLISH_ARCHIVE_SCHEDULING.md`（§6 起增补）。
- **执行子步骤**：
  - [ ] 读 PRD §7.1/§8/§11、上游审计 §3.3、S5.1/S3.4 版本
  - [ ] 写 §6–§11 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    for kw in 已过期 归档 搜索 下线 永久删除; do grep -q "$kw" docs/PUBLISH_ARCHIVE_SCHEDULING.md || echo "缺: $kw"; done
    grep -qE 'PA-0[1-6]' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    grep -q 'expired' docs/PUBLISH_ARCHIVE_SCHEDULING.md
    test "$(grep -c '^## ' docs/PUBLISH_ARCHIVE_SCHEDULING.md)" -ge 11
    ```
- **测试要求**：断言 PA-01–PA-06 落档（对应 PRD §23"通知到期后自动归档""未发布或已下线内容不会公开展示"两条必测项的设计源）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——§7 总表与 PRD §7.1 原文"到期后自动退出首页和默认列表，但保留在历史归档及站内搜索中"逐句对齐；实现/测试/安全面——与 CONTENT_MODEL §14 状态机、S3.4 §24 指针无矛盾。
- **失败回滚**：revert 本次增补，回到 S5.1 版本；S7.2 的引用悬挂时同步修复（新 Dispatch）。
- **阶段门**：G2"发布归档排程"项完成（S5.1+S5.2 齐）。

---

## 8. 阶段 P6：中文搜索真实数据 PoC（依赖 S3.4；环境 PRE-5）

### S6.1 PoC 方案、数据集与评分口径（POC_SEARCH_REPORT.md 方案章）

- **目标**：产出 `docs/POC_SEARCH_REPORT.md` §1–§4：三组实验设计、真实中文数据集构造规则、查询集与评分口径、达标阈值与决策规则——使 S6.2 可机械执行、S6.3 可机械裁决（对应 PRD 决策门 4、综合审计 D7、上游审计 §3.4）。
- **依赖**：S3.4（最小字段契约）、ADR-0001（版本）；上游审计 §3.4/§6 R1。
- **局部 DAG**：S3.4 → **S6.1** → S6.2；汇入 G2。
- **输入 → 输出**：输入 `CONTENT_MODEL.md` §23、上游审计 §3.4。输出 `docs/POC_SEARCH_REPORT.md`：
  - §1 实验设计：E1 = Wagtail DB 后端（`wagtail.search.backends.database`，fallback 即 `icontains` 子串匹配）；E2 = PostgreSQL 后端 + `SEARCH_CONFIG='simple'`；E3 = PostgreSQL + `zhparser`（或 `pg_jieba`）扩展〔可装性未知，PRE-5；不可装则记录"环境不可行"〕；备选记录：pg_trgm 模糊匹配（上游审计提及，仅作附注不单独成组）；
  - §2 数据集构造规则（真实中文数据，禁个人敏感信息）：来源三档——a) 项目负责人/总管理员提供的真实历史通知脱敏文本（首选）；b) 学校官网**公开**通知的标题与正文摘录（去除人名/工号/电话）；c) 合成文本仅用于放量至 5000 档，不参与质量评分；规模分级 200 / 1000 / 5000；字段按 §23 契约（title/body/department/tags/category）；覆盖分布要求：≥5 个部门代号、全部板块、≥20 个标签；
  - §3 查询集（固定 30 条，写入文档表格）：覆盖类型——单个汉字、常用双字词、专有名词（部门名/建筑名）、短语（4–8 字）、长句（>10 字）、带筛选组合（q+板块、q+部门）；
  - §4 评分口径与阈值：指标 = 目标命中@10（人工判定）、目标召回、排序合理性（1–3 分）、延迟 p50/p95（`update_index` 后查询计时，每查询 20 次取中位）；**达标线：≥90% 查询目标命中@10 且 1000 档 p50 < 1s**（对齐 PRD §14）；决策规则：E1 达标 → 选 E1（最简单）；E1 不达标而 E2 达标 → 选 E2；E1/E2 均不达标 → 看 E3；三者均不达标或 E3 环境不可行且 E1/E2 不达标 → 结论"评估独立搜索服务（Elasticsearch/OpenSearch 官方后端）"，**升级项目负责人裁决（PRD 决策门 4：只有验证不达标时才评估独立搜索服务）**；
  - §8 可追溯性（本步骤建表并填 §1–§4 行）。
- **单步骤对话边界**：一次对话；只新建报告的方案章；不装环境、不跑实验。
- **允许修改文件范围**：`docs/POC_SEARCH_REPORT.md`（新建，仅方案章）。
- **执行子步骤**：
  - [ ] 读 CONTENT_MODEL §23、上游审计 §3.4、PRD §10/§14
  - [ ] 写 §1–§4 + §8 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/POC_SEARCH_REPORT.md
    for kw in E1 E2 E3 icontains simple zhparser; do grep -q "$kw" docs/POC_SEARCH_REPORT.md || echo "缺: $kw"; done
    grep -qE '90%' docs/POC_SEARCH_REPORT.md && grep -qE 'p50' docs/POC_SEARCH_REPORT.md
    test "$(grep -cE '^\| Q[0-9]' docs/POC_SEARCH_REPORT.md)" -ge 30   # 30 条查询表
    ```
- **测试要求**：断言清单（§9，本步骤建）：SE-01 查询集 30 条与 §3 表一致；SE-02 评分可由第三方按 §4 重算。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——决策规则与 PRD §10"首版优先评估 PostgreSQL 与 Wagtail 自带搜索能力；只有验证不达标时才评估独立搜索服务"逐句一致；数据集规则不违反 PRD §11 隐私；实现/测试/安全面——三组实验与上游审计 §3.4 的技术事实一致、指标定义无歧义。
- **失败回滚**：revert 方案章；S6.2 阻塞。
- **阶段门**：G2"搜索 PoC"项组成之一。

### S6.2 PoC 环境与三组实验执行（丢弃目录）

- **目标**：在 **peiligo_restart 仓库内**的丢弃目录 `poc/search/`（FIX-08/00 修订 7）搭建最小 Wagtail + PostgreSQL（真实 FTS 条件）环境，按 S6.1 方案执行 E1/E2（/E3），采集原始指标，摘录入报告 §5。
- **依赖**：S6.1、PRE-5；ADR-0001。
- **局部 DAG**：S6.1 → **S6.2** → S6.3；（与文档步骤并行安全）。
- **输入 → 输出**：输入 S6.1 方案章、§23 字段契约、数据集文件（若负责人已提供则用之；否则按 §2 b/c 档构造并在报告注明构成比例）。输出：`peiligo_restart` 内 `poc/search/`（git 忽略，含 `DISPOSABLE.md`；Python 3.13 venv；Wagtail/Django 按 ADR-0001；本机 Docker `postgres:16` 一次性容器〔E2/E3 需真 PG；E1 可同库跑 DB 后端〕；最小模型按 §23 契约五字段；数据装载脚本 `load_data.py`；计时基准脚本 `bench.py` 输出 `results/e{1,2,3}_{scale}.json`）；报告增补 §5 实验记录（环境实测版本、每组每档的原始指标表摘录、E3 可行性结论）。
- **单步骤对话边界**：一次对话；`poc/search/` 丢弃目录内自由构建；入库仅改报告 §5；不碰仓库其他文件；**不安装任何独立搜索服务**（那是 E1–E3 全不达标后的另案）。
- **允许修改文件范围**：`poc/search/**`（peiligo_restart 内，git 忽略，新建）、`docs/POC_SEARCH_REPORT.md`（仅 §5）。
- **执行子步骤**：
  - [ ] 建目录 + DISPOSABLE + venv + 装依赖（记录实测版本）
  - [ ] 起本机 PG 容器 + `wagtail start` 最小项目 + §23 契约模型 + `search_fields`
  - [ ] 构造/导入数据集（200/1000/5000 三档）并 `update_index`
  - [ ] E1：DB 后端跑 30 查询 × 3 档计时与命中记录
  - [ ] E2：切 PG 后端 + `SEARCH_CONFIG='simple'`，重复
  - [ ] E3：装 zhparser（可行则），配置自定义配置，重复；不可行则记录原因
  - [ ] 结果 JSON 汇总 → 写报告 §5 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**（在 peiligo_restart 根的 `poc/search/` 内）：
    ```bash
    test -f DISPOSABLE.md
    ./.venv/bin/python -m pip freeze | grep -iE '^wagtail==7\.4\.' && ./.venv/bin/python -m pip freeze | grep -iE '^Django==5\.2\.'
    ls results/ | wc -l          # 期望 ≥ 6（e1/e2 × 三档；E3 可行则 9）
    ./.venv/bin/python manage.py update_index && ./.venv/bin/python bench.py --smoke   # 冒烟可复跑
    # 正式仓库侧（在 peiligo_restart 根执行）：
    git status --porcelain                  # 期望仅 docs/POC_SEARCH_REPORT.md 变更（poc/ 已被忽略）
    ```
- **测试要求**：每档每后端的 30 查询完整记录（含原始命中列表 JSON）；计时方法固定（每查询 20 次取中位）且写入 §5；**质量评分留待 S6.3 由独立人工/代理判定**，本步骤只采原始命中。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——实验与 §1 设计一致、无偷换后端/配置；实现/测试/安全面——数据集构成与 §2 规则一致、计时脚本无系统性偏差（如未预热偏差需说明）。
- **失败回滚**：删除 `poc/search/`；revert 报告 §5；S6.3 阻塞。
- **阶段门**：G2"搜索 PoC"项组成之一。

### S6.3 结果评估与 ADR-0006 中文搜索决策

- **目标**：按 §4 口径对 S6.2 原始结果做质量判定，写报告 §6–§7（评估与结论），并起草 ADR-0006（中文搜索后端决策，Proposed，G2 批准），完成"未达标→独立服务评估"的升级判断。
- **依赖**：S6.2。
- **局部 DAG**：S6.2 → **S6.3** → G2；下游 B2/B4（后续计划按 ADR-0006 实现）。
- **输入 → 输出**：输入 S6.2 报告 §5 与 `results/*.json`。输出：报告增补 §6 质量评估表（30 查询 × 后端：命中@10、召回、排序分、判定人）；§7 结论与建议（按 S6.1 §4 决策规则机械推导，给出选择与理由、残余风险如无相关度排序的影响说明）；ADR-0006（决策：选定后端 + 配置要点 + `update_index` 运维安排指针 + 不达标的升级路径记录；状态 Proposed）；`docs/adr/README.md` 状态行；§8 可追溯性补全、§9 断言 SE-03 所选后端与 CONTENT_MODEL §20 映射兼容。
- **单步骤对话边界**：一次对话；质量判定由本步骤执行者初判 + 独立审查复判（实现/测试/安全维抽查 ≥10 查询重判）；只改报告与两处 ADR 文件。
- **允许修改文件范围**：`docs/POC_SEARCH_REPORT.md`（§6 起增补）、`docs/adr/0006-chinese-search-backend.md`（新建）、`docs/adr/README.md`（状态行）。
- **执行子步骤**：
  - [ ] 逐查询判定命中@10 与排序分（记录判定依据行）
  - [ ] 汇总指标 vs 阈值 → 按 §4 规则推导结论
  - [ ] 写 §6/§7 + ADR-0006 → 验收 → 提交 → 独立审查（含抽查复判）→ worker_done
- **验收命令**：
    ```bash
    test -f docs/adr/0006-chinese-search-backend.md
    grep -qE 'E1|E2|E3' docs/adr/0006-*.md
    grep -qE 'Proposed' docs/adr/0006-*.md            # G2 批准前保持 Proposed
    grep -qE '独立搜索|不达标' docs/POC_SEARCH_REPORT.md || grep -qE '选定|达标' docs/POC_SEARCH_REPORT.md
    test "$(grep -cE '^\| Q[0-9]' docs/POC_SEARCH_REPORT.md)" -ge 30
    ```
- **测试要求**：评估表 30 行齐；每行有判定人/依据；阈值判定可重算（独立审查抽查复算——FIX-06 口径）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——决策推导严格遵循 S6.1 §4 规则与 PRD §10 约束（不擅自引入独立服务）；实现/测试/安全面——抽查 ≥10 查询复判命中与排序分，偏差 >20% 则退回。
- **失败回滚**：revert 报告增补与 ADR-0006；若结论触发"独立服务评估"，升级项目负责人（决策门 D7），PoC 结论保留留档。
- **阶段门**：G2"搜索后端决策"检查项。

---

## 9. 阶段 P7：安全与非功能基线（依赖见各步）

### S7.1 安全基线（SECURITY_BASELINE.md）

- **目标**：产出 `docs/SECURITY_BASELINE.md`：把 PRD §5/§11/§12/§17 的安全要求与综合审计 P0 风险落成可执行的安全设计基线，供 B 阶段实现与审查引用。
- **依赖**：S3.2（附件字段）、S4.1（账号与权限）；PRD §5/§11/§17；综合审计 §5.1/§6。
- **局部 DAG**：S3.2 + S4.1 → **S7.1** → G2；下游 B5/B6。
- **输入 → 输出**：输入 PRD §5/§11/§12/§17、ROLE_PERMISSION_MATRIX、综合审计 P0/P2 风险行。输出章节：§1 后台访问控制（仅校园网/VPN：反代 ACL vs Django 中间件两方案对比 + 推荐 + `X-Forwarded-For` 信任链注意事项；HTTPS 强制）；§2 认证与账户（`AUTH_PASSWORD_VALIDATORS` 四项配置样例；登录限速方案候选 django-axes 及参数建议〔默认 5 次/15 分钟，标记确认〕；密码重置后强制改密机制设计；岗位账号交接流程引用矩阵 §4）；§3 传输与响应头（Django `SECURE_*` 清单、HSTS、CSP 基线方向、X-Frame-Options）；§4 附件与上传（允许类型白名单：PDF/DOC/DOCX/XLS/XLSX/PPT/PPTX/PNG/JPG/WEBP；大小上限默认 20MB 标记确认；扩展名 + content-type + **魔数** 三级校验设计〔回应上游审计 R7：官方设置只覆盖前两级，魔数检测为项目层补充〕；危险扩展名黑名单；禁止上传敏感数据名单〔密码/个人敏感信息/成绩名单〕）；§5 秘密与配置（环境变量外置、不入 Git、`.env.example` 只含键名；**代理/脚本禁区规则：任何工作流不得读取或输出凭据文件与环境变量值**——综合审计 P0 落地；建议轮换曾暴露令牌）；§6 审计与日志（Wagtail log_actions + 修订历史 ≥1 年；日志脱敏规则：不记密码/敏感附件内容；异常登录监控点）；§7 已知风险登记表（引用两审计 R 清单中安全相关行 + 本基线处置状态）；§8 可追溯性表；§9 断言清单：SB-01 后台非校园网访问被拒（验证方法）；SB-02 弱密码被拒；SB-03 连续失败登录触发限速；SB-04 重置后未改密不能进行其他操作；SB-05 伪造扩展名/魔数不符文件被拒；SB-06 外链经确认跳转页且显示域名/来源/时间/声明（PRD §7.5）。
- **单步骤对话边界**：一次对话；只新建该文档；实现一律留 B 阶段。
- **允许修改文件范围**：`docs/SECURITY_BASELINE.md`（新建）。
- **执行子步骤**：
  - [ ] 读 PRD §5/§11/§12/§17、ROLE_PERMISSION_MATRIX、综合审计 §5.1/§6
  - [ ] 写 §1–§9 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/SECURITY_BASELINE.md
    for kw in 校园网 VPN 限速 强制改密 魔数 白名单 审计; do grep -q "$kw" docs/SECURITY_BASELINE.md || echo "缺: $kw"; done
    grep -q 'AUTH_PASSWORD_VALIDATORS' docs/SECURITY_BASELINE.md
    grep -qE 'SB-0[1-6]' docs/SECURITY_BASELINE.md
    grep -c 'PRD §' docs/SECURITY_BASELINE.md      # 期望 ≥ 10
    ```
- **测试要求**：断言 SB-01–SB-06 落档（B 阶段安全测试的设计源，对应 PRD §23"外部资源链接经过确认跳转页"等必测项）。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——与 PRD §5/§11 逐条对照无缺失（后台限网、HTTPS、限速、强密码、强制改密、附件校验、禁传敏感数据、纠错下架通道〔引用 S5.2 §9〕）；实现/测试/安全面——方案技术可行性（django-axes 兼容性注意、魔数检测实现层级、中间件 vs 反代的信任链）。
- **失败回滚**：revert 该文件；G2 缺项。
- **阶段门**：G2"安全基线"检查项。

### S7.2 非功能基线（NON_FUNCTIONAL_REQUIREMENTS.md）

- **目标**：产出 `docs/NON_FUNCTIONAL_REQUIREMENTS.md`：性能、可访问性、SEO、隐私、备份恢复、监控、浏览器与响应式的**测量口径**（PRD §14"具体测量方法和数据规模在技术设计阶段确定"——本步骤即该确定动作）。
- **依赖**：S2.2（SEO/noindex 位点）、S3.4（搜索性能口径）、S5.1（排程运维）；PRD §12–§17。
- **局部 DAG**：S2.2 + S3.4 + S5.1 → **S7.2** → G2；下游 B4–B6。
- **输入 → 输出**：输入 PRD §12–§17、IA 文档、上游审计 §3.7。输出章节：§1 性能（测量环境=预发布同级配置；数据规模分级沿用 200/1000/5000；指标定义："主要页面核心内容约 2 秒内可见"＝Lighthouse FCP ≤ 2s 且服务端渲染无阻塞脚本；"普通搜索约 1 秒内返回"＝服务端 p50 < 1s（沿用 S6.1 口径）；首页图片/附件预览/脚本预算：图片懒加载 + 单页脚本预算默认 ≤ 200KB 未压缩标记确认；工具：Lighthouse + 服务端计时中间件）；§2 可访问性 WCAG 2.2 AA（检查方法＝axe DevTools 扫描页面清单〔首页/板块列表/详情/搜索结果/指南/跳转页/404〕+ 键盘走查清单〔Tab 顺序/焦点可见/skip-link/表单标签〕+ 必查项清单来自旧站审计 §5.1 a11y 资产）；§3 SEO 与 noindex（默认可收录、单篇 noindex 字段、sitemap/redirects、meta 规范）；§4 隐私与统计（匿名最小化指标清单：页面访问/搜索词/无结果搜索/筛选使用；无 Cookie 画像、不记个人浏览历史、无广告追踪；自托管分析为候选方向、选型留 B 阶段决策）；§5 备份与恢复（DB+媒体配套每日备份、RPO ≤ 24h；恢复演练步骤模板 + 频次默认建议：每季度全量演练 + 版本发布前额外备份〔PRD §15〕；审计日志 ≥ 1 年）；§6 监控五项（存活/应用错误/磁盘/备份结果/异常登录——含异常登录判定口径；实现工具不锁定，B6 落地）；§7 浏览器与响应式（当前+前一主要版本 Chrome/Edge/Firefox/Safari，不支持 IE；移动端验收三任务：阅读/搜索/筛选——PRD §2/§13）；§8 容量假设（部门数量与内容量级假设——上游审计 U2 未决：登记默认假设〔≤30 部门、V1 内容 ≤ 1 万条〕并标记"项目负责人确认"）；§9 可追溯性表；§10 断言清单：NF-01 首页 FCP ≤ 2s（1000 档）；NF-02 搜索 p50 < 1s（1000 档）；NF-03 axe 扫描清单页零严重问题；NF-04 键盘走查清单全过；NF-05 恢复演练按模板可完成；NF-06 单篇 noindex 生效。
- **单步骤对话边界**：一次对话；只新建该文档。
- **允许修改文件范围**：`docs/NON_FUNCTIONAL_REQUIREMENTS.md`（新建）。
- **执行子步骤**：
  - [ ] 读 PRD §12–§17、IA、S3.4/S5.1/S6.1 口径、旧站审计 §5.1
  - [ ] 写 §1–§10 → 验收 → 提交 → 独立审查 → worker_done
- **验收命令**：
    ```bash
    test -f docs/NON_FUNCTIONAL_REQUIREMENTS.md
    for kw in WCAG 2.2 AA 24 备份 监控 noindex 无结果; do grep -q "$kw" docs/NON_FUNCTIONAL_REQUIREMENTS.md || echo "缺: $kw"; done
    grep -qE 'NF-0[1-6]' docs/NON_FUNCTIONAL_REQUIREMENTS.md
    grep -q '假设' docs/NON_FUNCTIONAL_REQUIREMENTS.md     # 容量假设必须显式登记
    grep -c 'PRD §' docs/NON_FUNCTIONAL_REQUIREMENTS.md    # 期望 ≥ 12
    ```
- **测试要求**：断言 NF-01–NF-06 落档；所有"默认值待确认"参数集中登记成一表（参数 | 默认 | 依据 | 确认人），G2 时由项目负责人一次性确认。
- **独立审查（独立 GLM 新会话；两维）**：需求/架构面——与 PRD §12–§17 逐条对照（备份每日/24h、监控五项、WCAG AA、浏览器矩阵、性能双目标）；实现/测试/安全面——口径可测量无歧义（FCP 定义、计时方法、axe 清单页与 IA 页面清单一致）。
- **失败回滚**：revert 该文件；G2 缺项。
- **阶段门**：G2"非功能基线"检查项。

---

## 10. G2 架构与领域基线确认门（终门）

**通过条件（全部满足，缺一不可）**：
1. **文档齐备且 Accepted**：`INFORMATION_ARCHITECTURE.md`、`CONTENT_MODEL.md`、`ROLE_PERMISSION_MATRIX.md`、`PUBLISH_ARCHIVE_SCHEDULING.md`、`SECURITY_BASELINE.md`、`NON_FUNCTIONAL_REQUIREMENTS.md`、`POC_PERMISSION_REPORT.md`、`POC_SEARCH_REPORT.md` + ADR-0001–0006（0001–0005 Accepted；0006 由项目负责人在 G2 批准转 Accepted）。
2. **权限原型**：T01–T16 全绿（16/16）或项目负责人书面豁免个别项并记录理由。
3. **搜索决策**：ADR-0006 结论明确；若为"评估独立搜索服务"，G2 不得关闭，先走决策门 D7。
4. **可追溯性**：全部文档可追溯性表经独立审查抽查完整（FIX-06 口径）（PRD 条款无孤儿——每条相关 PRD 要求至少映射到一个文档条目）。
5. **待确认参数表清零**：S7.2 §10 及各文档"默认值待确认"参数（推荐位数量、限速参数、附件上限、脚本预算、容量假设等）由项目负责人逐项确认。
6. **唯一事实源**：全部产出位于 `peiligo_restart` 仓库 `rebuild/v1` 分支并已提交（00 修订 16；综合审计 P0 风险由 M0.2 入库闭合——FIX-01）。
7. **无扩围复核**：对照附录 B 清零（无任何步骤引入 PRD §20 禁项）。

**通过后**：总控编制 03 计划（B 阶段：B1 干净骨架起），本计划关闭。
**未通过**：按 §2.5 阶段级回滚退回对应步骤；G2 记录未满足项清单。

---

## 11. 计划自检记录（编制者已执行）

- **覆盖矩阵**：架构冻结→P1/G1；信息架构→P2；内容模型→P3；权限原型→P4；发布归档排程→P5；搜索真实数据 PoC→P6；安全与非功能基线→P7+G2。七项全域覆盖，无越域步骤。
- **占位符扫描**：全文无 TBD/TODO/待补类空任务；所有"待确认"均为带默认值与确认人的显式参数（G2 第 5 项集中清零）或外部决策门（D2/D7/D8/D9，均登记归属）。
- **一致性**：步骤 ID（S1.1–S7.2）、文档路径、断言 ID（IA/CM/PS/PA/T/SE/SB/NF）与各验收命令 grep 目标一一对应；§23 PoC 契约字段与 S6.1/S6.2 引用一致。
- **PRD 必测项映射**：PRD §23 五条必测 → CM-08/矩阵（部门隔离）、PA-01/PS-05（到期归档）、T11（账号与置顶管理）、SB-06/CM-05（跳转页）、PA-04/PA-06（未发布不可见）。

## 附录 A：产出文件清单（全部入库路径）

`docs/adr/{README.md,_template.md,0001-wagtail-django-python-versions.md,0002-server-side-templates.md,0003-clean-wagtail-skeleton.md,0004-department-permission-container-tree.md,0005-page-vs-snippet-allocation.md,0006-chinese-search-backend.md}`；`docs/INFORMATION_ARCHITECTURE.md`；`docs/CONTENT_MODEL.md`；`docs/ROLE_PERMISSION_MATRIX.md`；`docs/PUBLISH_ARCHIVE_SCHEDULING.md`；`docs/SECURITY_BASELINE.md`；`docs/NON_FUNCTIONAL_REQUIREMENTS.md`；`docs/POC_PERMISSION_REPORT.md`；`docs/POC_SEARCH_REPORT.md`。丢弃目录（不入库，`.gitignore` 忽略）：`poc/permissions/`、`poc/search/`（**peiligo_restart 仓库内**——FIX-08/00 修订 7；G2 后按综合审计 D8 裁决归档或删除）。

## 附录 B：V1 防扩围对照（PRD §20 全项 + 相关禁令）

学生账号/注册/个性化推荐；邮件/微信公众号等主动推送；复杂审批流；在线报名/申请/缴费/材料提交；AI 自动写作/分类/审核/发布；原生 App；多语言发布；**部门独立主页（含任何以"部门主页"形态出现的聚合页——部门筛选结果页必须有别于主页语义）**；评论/点赞/收藏/学生投稿；第三方网盘或资源链接自动巡检/爬虫；独立课程管理系统；零停机与复杂高可用。另：本计划全程禁止修改 Wagtail 核心、禁止业务代码并入、禁止正式骨架与依赖锁定（丢弃 PoC 目录除外）、禁止 PVE/生产操作、禁止迁移旧站测试填充数据（PRD §18）。（滚动实现注 2026-08-18：「正式骨架与依赖锁定」禁令按 `docs/decisions/ROLLING_IMPLEMENTATION_POLICY.md` 最小同步——已冻结过门且不依赖未决设计的内容可提前正式实现。）
