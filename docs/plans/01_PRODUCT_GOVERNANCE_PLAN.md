# 01 · 产品与治理基线计划（Product Governance Plan）

| 项目 | 内容 |
| --- | --- |
| 计划编号 | PG（Product Governance，治理线） |
| 文档状态 | 计划草案（待独立审查——v2.1：独立 GLM 新会话——+ 项目负责人批准后冻结） |
| 编写日期 | 2026-08-15 |
| 编写方式 | Orca 单步骤 Dispatch（单对话）；本步骤仅允许产出本文件 |
| 输入文档（均已完整读取） | `docs/PRODUCT_REQUIREMENTS.md`（457 行，下称 PRD）；`docs/PEILIGO_REBUILD_AUDIT.md`（下称综合审计）；`docs/audit-report-old-peiligo.md`（下称旧仓审计）；`docs/audit-report-wagtail-upstream.md`（下称上游审计） |
| 本计划覆盖 | 产品基线、AI 治理、文档基线、工作树与单步骤对话契约、秘密禁区、变更管理、阶段门 |
| 本计划不覆盖 | 版本/骨架/前端 ADR（决策门 D2–D4）、权限树原型（D5）、内容模型设计（D6）、中文搜索 PoC（D7）、外部上线门（D9）、B/C 阶段开发——由后续计划文件（02 起）承接 |
| 全局硬边界（每个步骤无条件继承） | ①禁止编写业务代码；②禁止项目初始化（`wagtail start`、npm init 等一律不做）；③禁止安装任何依赖；④禁止 PVE/生产服务器操作；⑤禁止 V1 扩围（新增需求一律进候选池） |

> **v2.1 治理基线同步修订（2026-08-18，经项目负责人特别授权；v1.4 治理一致性定向修复同日，FIX-01–FIX-10 落点见 00 §23.7）**：本文治理条款按《AI 开发工作流 v2.1》（Orca 控制面 + GPT-5.6 Sol 高级决策面 + GLM-5.3 主工程面）做最小一致性修订：独立审查改为"独立 GLM 新会话（一次覆盖**需求/架构审查维度**与**实现/测试/安全审查维度**双口径——FIX-06 命名，不以 R1/R2 指代审查维度）"，GPT 收缩为 R3/R4/Escalation/最终裁决，不常驻协调、不逐步审查。
>
> **FIX-07/FIX-10**：本文件**不是独立执行计划**——步骤编号、Gate、风险等级、仓库路径、模型职责和冲突裁决均以 00_MASTER_PLAN 为准（冲突裁决层级=00 §3.0 六级层级）；本文件只提供详细规格、测试断言和验收参考（Detail Specifications），不独立维护与 00 不同的 Gate/仓库路径/模型体系/审查体系/步骤生命周期；已被 00 覆盖的重复控制规则，其执行契约一律见 00_MASTER_PLAN 对应章节（本节仅补充领域要求）。
>
> **FIX-05**：审查记录统一写 `docs/reviews/PG-S<n>.review.md`（R3/R4 另落 `.gpt-review.md`）——`.codex-review.md`/`.claude-review.md` 已废止，本文步骤块内旧命名已按 v1.4 逐一改写；历史修订记录中的旧名仅作历史保留。
>
> **FIX-01/FIX-02**：唯一仓库=`peiligo_restart`（旧仓绝对路径见 OR-2，永久只读禁区）；GPT 不可用规则（R3 一次性 `R3_GPT_WAIVER`、R4 默认 BLOCKED）与风险级逐 Task 评估口径见 00 §4.6 规则 6/7。技术内容不变。

## 1. 计划目的与定位

综合审计已给出结论：**审计完成、开发禁止**，等待项目负责人确认基线（D0）。本计划把审计 §9 建议 DAG 中治理线的部分（A1/A2/A9 及 G0/G2 的治理输入）与审计 §7 文档差距清单中**不依赖技术决策**的部分，落成一组可派发、可验收、可回滚的单步骤任务。本计划所有产出物均为**文档与 Git 元数据**，不含任何业务代码。

与全局 DAG 的关系（综合审计 §9）：

- 本计划出口门 **PG-G2（治理基线确认）** 是全局 **G2（内容模型 + 权限 + 搜索 + 治理基线确认）** 的治理输入；技术线（A3–A8，即 D2–D7）由后续计划承接。
- 综合审计将 A9 排在 G1（架构冻结）之后；本计划将其细化为"PG-G0 之后即可启动"，理由：治理文档与架构 ADR 文件集不相交，符合 PRD §24.4"互不依赖、不写入共享文件的任务可并行"，且治理文档不冻结任何实现结构，不违反"G1 前不冻结实现结构"的约束。此细化点须在 PG-G0 门一并报项目负责人知悉。

## 2. 输入事实基线（执行本计划不得背离）

### 2.1 关键事实

1. **（Historical fact，2026-08-15 审计时事实，非当前执行规则）**基线文档（PRD + 三份审计）当时位于 `peiligo_restart` 工作区（**非 Git 仓库**），与 PRD §25 原文"唯一事实来源是 `peiligo` 仓库"冲突（综合审计 P0 风险第 1 条）。**当前执行规则**：M0.2 在 `peiligo_restart` 内 `git init` 基线入库（00 修订 2/15；FIX-01）；PRD §25 已按 v1.4 授权修订为 `peiligo_restart`。
2. **（Historical fact，2026-08-15 审计时事实）**旧 `peiligo` 仓库（绝对路径 `/Users/chenjunxian/vscode_projects/peiligo`，**永久只读禁区 OR-2**）：分支 `feat/m4-admin-auth` 上有 M4 认证半成品**零提交**躺在工作区；`git tag` 为空，PRD §18 原要求的旧实现只读归档标签**未建立**（P0 风险第 2 条）。**当前执行规则**：OR-2 旧仓永久只读即视为等效归档——不处置、不建 tag/branch/commit，该状态不阻塞本项目任何步骤（00 修订 1/13；FIX-01）。
3. AI 治理缺口（综合审计 §5）：双独立审查未制度化、文件写入互斥未制度化、`worker_done` 报告入库/脱敏规则未定义、CI 门禁未落地（CI 属后续 B6，不在本计划）。
4. 秘密暴露事件：Claude 配置中的敏感字段曾被调查命令读入 transcript（综合审计 §5.1，P0 风险第 4 条），已建议轮换曾暴露的令牌。
5. 决策门 D0–D9 由项目负责人独占裁决，**一次只处理一个**（综合审计 §8）。
6. PRD §26：本文档获最终确认前，只开展审计与治理准备，不编写业务代码。

### 2.2 本计划必须满足的 PRD 条款映射

| PRD 条款 | 对本计划的约束 |
| --- | --- |
| §1（基线冻结）、§20、§25 | 不扩围；新增需求默认进候选池；变更必须留记录 |
| §18 | （v1.4 修订后口径）仓库归属已统一为 `peiligo_restart` 唯一新 V1 项目仓库；旧仓永久只读（OR-2）即视为等效归档，不建只读标签或归档分支；测试填充数据不迁移 |
| §24 | 总控/工作组/单步骤单对话/独立审查（v2.1 风险分级）/worktree/阶段门全部制度化 |
| §24.2 | 每步骤明确单一目标、输入文档、可修改文件范围、验收命令、完成报告；后续步骤必须新对话 |
| §24.3 | 实现者不得作为唯一审查者；不允许两个代理并发修改同一文件集合 |
| §24.4 | 一步骤一 worktree；前一步未过验收，后续依赖步骤不得开始 |
| §25 | 文档清单、变更记录、候选池格式（提出人/动机/预期价值/影响范围/建议版本） |
| §26 | 开发前只做审计与治理类工作 |

## 3. 治理总则（对所有 PG 步骤生效）

### 3.1 角色与职责

| 角色 | 职责 | 禁止 |
| --- | --- | --- |
| 项目负责人（用户） | 唯一范围与基线裁决者；批准 PG-G0/G2 及全局 G0–G4 相关门；批准 V1 变更；GPT 不可用时按 00 §4.6 规则 6 处置（R3 可对一个具体 Task 发一次性 `R3_GPT_WAIVER`：TASK/REASON/HUMAN_APPROVAL/DATE，不可复用不可泛化；R4 默认 BLOCKED——无全局缺席旁路，FIX-02） | — |
| 总控（Orca 控制面） | 管理 Run/Task DAG/派发/SCOPE 登记/门记录/结论汇总 | 不写业务代码；不写步骤实现文件；不扩权 |
| 工作组总控（Orca，PG 组） | 本计划即一个工作组：定义步骤契约、转发 ask、落盘审查结论 | 同上 |
| 实现者（Claude Code / GLM-5.3，v2.1 主工程代理，默认 `high` 推理） | 按步骤契约完成调查、普通工程决策、实现与自测自审、证据压缩，发送 worker_done | 不得审查自己产出的步骤 |
| 独立审查者（独立 GLM 新会话） | 独立审查：一次覆盖需求/架构与实现/测试/安全双口径（只读 + 仅写本步骤审查记录文件） | 不得修改被审文件；不得继承实现对话 |
| GPT-5.6 Sol（v2.1 高级决策面） | R3/R4 压缩风险/架构审查、Escalation 裁决、最终高风险裁决 | 不常驻协调；不逐步审查；不做普通工程劳动 |

独立审查在实现者 worker_done 后派发（独立 GLM 新会话）；R3/R4 另按 00_MASTER_PLAN §4.6 追加 GPT 审查。

### 3.2 单步骤对话契约（通用规则，S4 固化进 `AI_WORKFLOW.md`）

1. **一步骤 = 一次 Orca Dispatch = 一个全新对话**；TASK 块注入单一目标与允许范围。
2. 对话只做本步骤；完成即发送 `worker_done`（恰好一次），随后停止，不自行延伸、不启动无关工作、不进入 sleep/poll 循环；后续修正必须新开 Dispatch（编号 `PG-Sn-fix`，复用原验收命令）。
3. 工作期间每 5 分钟发送心跳；对协调者提问只用 `orca orchestration ask`（禁止 AskUserQuestion 类本地交互）；**仅允许提出该步骤契约中明确列出的决策点**。
4. 越界请求（超出允许文件范围、新依赖、业务代码、PVE/生产操作、V1 扩围）一律拒绝并发送 escalation。
5. `worker_done` schema（本计划各步骤统一遵守）：

```bash
orca orchestration send --type worker_done \
  --subject "<短状态>" \
  --body "<3 句摘要：做了什么 / 发现什么 / 还剩什么，不得为空>" \
  --task-id <taskId> --dispatch-id <dispatchId> \
  --outcome succeeded|failed \
  --files-modified "<路径,逗号分隔>" \
  --report-path "<完整报告路径，可选>"
```

规则：必须同时携带 `taskId` 与 `dispatchId`；`outcome` 如实标注；失败不得只写在正文里。

### 3.3 工作树与文件互斥

- **peiligo_restart 仓库内**的步骤（M0.2 Git 化后 = 本文 S3–S9 的重映射，见 00 §4.4）：**一步骤一 worktree 一分支**，分支前缀 `gov/<ID>-<slug>`（00 修订 12），基于基线分支 `rebuild/v1` 创建；独立审查通过后由总控合并回基线，保留步骤边界。执行契约见 00 §4.4，本节仅补充领域要求（FIX-10）。
- Git 化前步骤（本文 S1=M0.1、S2 的记录部分，S2 已废止）：互斥靠"单文件允许范围 + 总控登记"（00 §4.4：M0.1 为 Git 化前唯一步骤）。
- **SCOPE 声明**：每个 Dispatch 必须显式列出允许写入路径；总控维护派发登记表（S4 起入库为 `docs/governance/DISPATCH_REGISTRY.md`，append-only）；路径重叠的派发直接拒绝。worktree 是第二道物理防线。
- 只读调查不建分支；纯 Git 元数据操作（打 tag）不建 worktree，但必须验证 `git status --porcelain` 操作前后一致。
- 本计划内的并行仅限 **S4‖S6‖S7‖S8**（文件集互不相交）；其余步骤串行。
- ~~旧仓库 `.gitignore` 对 `docs/ai/` 的排除保持不动~~（**FIX-01/v1.4 删除**：旧仓相关表述随 OR-2 旧仓永久只读一并废止）。`docs/ai/` 是否入 Git 由 M0.3 依 D8 裁决结果调整 **peiligo_restart** 的 `.gitignore`（FIX-03：M0.2 不预先写死忽略该目录）。

### 3.4 独立审查通用流程（v2.1 风险分级）

1. 触发：实现者 worker_done 后，总控派发独立审查 Dispatch（独立 GLM 新会话，**不得继承实现对话上下文**；实现者不得担任审查者）。
2. 审查记录路径：`docs/reviews/PG-S<n>.review.md`（命名按 00_MASTER_PLAN 修订 11 v1.3 口径）；R3/R4 步骤另落 `docs/reviews/PG-S<n>.gpt-review.md`（GPT 压缩风险/架构审查）。
3. 结论三档：`通过` / `有条件通过（列明修复项）` / `不通过`；阻塞项必须修复并复审，**最多 2 轮**，第 3 轮前 escalation。
4. 审查记录随步骤分支入库；**未获"通过"的步骤不得进入其所属门**，依赖它的后续步骤不得派发。
5. GPT 可用性规则（FIX-02/v1.4，执行契约全文见 00 §4.6 规则 6，本条仅摘引）：R0–R2 GPT 不参与、GPT 暂无额度不阻塞任何步骤与门；R3 重大裁决原则上等待 GPT Risk/Architecture Review，跳过仅限项目负责人对**一个具体 R3 Task** 发一次性 `R3_GPT_WAIVER`（记录 TASK/REASON/HUMAN_APPROVAL/DATE，不可复用、不可泛化，不存在全局自动替代规则）；R4 GPT 不可用时**默认 BLOCKED**，禁止任何全局 GPT 缺席旁路。

### 3.5 阶段门通用规则

- 门由总控记录（`docs/decisions/` 决策记录 + `PHASE_GATES.md` 状态表），需要项目负责人批准的门未经批准视为未通过。
- 门未通过时，依赖步骤不得派发（Task `--deps` 阻塞 + 总控纪律双保险）。
- 决策门（D 系列）一次只处理一个 ask。

## 4. 本计划局部 DAG（仅覆盖本文件步骤）

```text
PG-S1 D0 确认简报（→ M0.1）
  └─ PG-G0（=全局 G0 / D0：确认审计事实 + PRD 基线 + 文档迁入策略）
      └─〔PG-S2 M4 处置与旧实现归档（D1）：**已删除**——00 修订 1/OR-2 旧仓永久只读，见 §5 PG-S2 tombstone〕
          └─〔PG-G1（旧实现归档完成门）：**已删除**——随 PG-S2 废止，00 修订 1〕
              └─ PG-S3 Git 初始化与基线文档入库（→ M0.2：在 **peiligo_restart** 内 git init，非旧仓；00 修订 2/3）
                  ├─ PG-S4 AI_WORKFLOW + D8 裁决（步骤内恰好一次 ask）
                  │     └─ PG-S5 TASK_TEMPLATE
                  ├─ PG-S6 SECRETS_POLICY ─┐
                  ├─ PG-S7 角色权限矩阵    │（与 S4 并行；S4/S5/S6/S7/S8 文件集互不相交）
                  └─ PG-S8 变更管理+候选池 ┘
                        └─ PG-S9 阶段门定义 + 治理基线确认包（依赖 S4–S8 全部完成）
                            └─ PG-G2（治理基线确认门 → 并入全局 G2）
```

### 4.1 门定义

| 门 | 名称 | 准入条件 | 准出条件 | 批准人 |
| --- | --- | --- | --- | --- |
| PG-G0 | 审计与文档基线确认门（= 全局 G0 / D0） | S1 完成且独立审查通过，简报已呈报 | 负责人确认：①综合审计可作为事实基线；②PRD 基线内容确认（或附修订清单）；③文档迁入策略（默认：docs 直接进 `main`，备选：专用 docs 分支） | 项目负责人 |
| ~~PG-G1~~ | 旧实现归档完成门（A1+A2 / D1）——**已删除**（随 PG-S2 废止，00 修订 1；OR-2 旧仓永久只读即视为等效归档，不建归档 tag/分支） | — | — | — |
| PG-G2 | 治理基线确认门（A9 治理线，→ 全局 G2 的治理输入） | S3–S9 全部完成且各获独立审查通过（S2 已废止、S7 并入 M4.1 归架构线——00 §23.1） | S9 汇总包内全部验收命令输出在案、治理线 **7 份**独立审查记录在案（v1.4 口径，与 00 §6 G2 一致）、遗留项清单明确 | 项目负责人 |

### 4.2 并行与衔接说明

- S4、S6、S7、S8 可在 S3 合并后并行派发（四个分支文件集互不相交）；S5 依赖 S4 的术语与 schema；S9 依赖 S4–S8 全部。
- 技术线计划（02 起：D2–D4 ADR、权限树原型、内容模型、搜索 PoC）可在 PG-G0 通过后并行启动，与 PG 线文件集不相交；两线在全局 G2 汇合。
- 全局约束（综合审计 §9）：G0 之前不开发；G1 之前不冻结实现结构；G2 之前不进入主要开发；每个开发步骤独立 worktree 与单步骤对话；实现者不得担任唯一审查者。

## 5. 步骤详述

### PG-S1 · D0 确认简报

**阶段目标**（阶段 0「基线确认」）：把四份输入文档压缩为项目负责人可逐项裁决的确认包，触发全局 G0/D0，关闭"审计完成、开发禁止"前的最后一段信息差。

**前置依赖**：本计划获派发（无其他步骤依赖）。

**输入**（全部只读）：`docs/PRODUCT_REQUIREMENTS.md`；`docs/PEILIGO_REBUILD_AUDIT.md`；`docs/audit-report-old-peiligo.md`；`docs/audit-report-wagtail-upstream.md`。

**输出**：`docs/decisions/D0_CONFIRMATION_BRIEFING.md`（新建，`peiligo_restart` 工作区），必含：①综合审计四大结论与四条 P0 风险摘要；②PRD 逐章确认清单（§2–§23 每章一个"确认 / 修订（附修订意见）"待勾选行）；③决策门 D0–D9 一览表（每门：问题、选项、审计建议、裁决人）；④本次 G0 需裁决的三个子项（D0 本体、PRD 基线确认、文档迁入策略默认值）；⑤签字区（负责人、日期）。

**单步骤对话边界**：一次 Dispatch、一个新对话；只写上述一个文件；不得修改四份输入文档；允许恰好一次 ask——若发现四份输入文档之间存在事实矛盾，向总控提问记录方式（不得自行改写输入文档）；完成即 worker_done。

**允许修改的文件范围**：仅 `docs/decisions/D0_CONFIRMATION_BRIEFING.md`；禁止其他一切文件。

**验收命令**（在 `peiligo_restart` 执行，输出粘贴进完成报告）：

```bash
test -f docs/decisions/D0_CONFIRMATION_BRIEFING.md
# 十个决策门逐项出现
for g in D0 D1 D2 D3 D4 D5 D6 D7 D8 D9; do
  grep -qE "(^|[^A-Za-z0-9])${g}([^A-Za-z0-9]|$)" docs/decisions/D0_CONFIRMATION_BRIEFING.md \
    || { echo "missing gate ${g}"; exit 1; }
done
# 四条 P0 风险要点在场
for kw in 唯一事实 M4 互斥 凭据; do grep -q "$kw" docs/decisions/D0_CONFIRMATION_BRIEFING.md || exit 1; done
# 引用的本地文档路径真实存在
grep -oE '/Users/[^ )`]+\.md' docs/decisions/D0_CONFIRMATION_BRIEFING.md \
  | sort -u | while read -r p; do test -e "$p" || { echo "bad path $p"; exit 1; }; done
# 秘密零命中（临时规则，见本文 §7）
! grep -rInE '(SECRET|TOKEN|PASSWORD|API_KEY|dcap_|BEGIN (RSA|OPENSSH))[=: ]+[A-Za-z0-9_./+-]{8,}' docs/
```

**测试要求**：上述结构校验全过；简报中 ≥10 处事实断言可回链到输入文档原文（审查者抽查）；不引入任何新工具。

**独立审查·需求/架构审查维度**：核对简报每个"事实"均有输入文档出处、无虚构、无 V1 扩围暗示、决策门与综合审计 §8 一一对应（与实现/测试/安全审查维度由同一独立 GLM 新会话一次完成——FIX-06）。

**独立审查·实现/测试/安全审查维度**：逐条实际执行验收命令并核对输出；确认清单可被负责人独立填写（可操作性）；执行脱敏扫描；审查记录统一写 `docs/reviews/PG-S1.review.md`（FIX-05）。

**失败与回滚策略**：文件为新建，删除即回滚；审查发现事实错误 → 以勘误段重出（保留 v1 并标注），开 `PG-S1-fix`；禁止静默修改输入文档。

**完成条件**：验收命令全过 + 独立审查通过 + 简报经总控呈报负责人 → 进入 PG-G0 等待裁决。

---

### PG-S2 · M4 处置与旧实现归档（D1）——已废止（tombstone，FIX-01/v1.4）

> **本步骤已整体废止，不得派发、不得执行**（00 §3 修订 1：删除该步骤；OR-2 旧仓 `/Users/chenjunxian/vscode_projects/peiligo` 永久只读即视为等效归档）。
>
> - **D1 处置**：见 00 §2.2 决策门处置表——**撤销**（接受现状即闭环：不处置 M4 未提交工作、不建 `archive/m4-admin-auth` 分支、不建 `legacy/pre-rebuild-v0` 标签、不对旧仓执行任何 git 写操作；旧仓工作区/tag 状态不阻塞本项目任何步骤）。
> - 原步骤的全部可执行旧仓命令（`cd /Users/chenjunxian/vscode_projects/peiligo`、`git tag`/`git stash`/`git reset`/`git ls-tree` 系列与对应验收命令块）已按 FIX-01 删除，**不得在任何对话中恢复或执行**。
> - 旧仓审计时状态（2026-08-15：`feat/m4-admin-auth` 脏工作区、`git tag` 为空）为 **Historical fact**，仅见 `docs/audit-report-old-peiligo.md`（Historical Evidence，非当前执行规范——00 §3.0 第 5 级）。
> - 对应全局流程：G0 → M0.1 → **M0.2（peiligo_restart git init）**——中间无本步骤、无 PG-G1 门（00 §5.1 全局 DAG）。

---

### PG-S3 · Git 初始化与基线文档入库（→ 00 M0.2；v1.4 改写）

**阶段目标**（阶段 2「文档基线」）：关闭 P0 风险第 1 条——在 **peiligo_restart 内**完成首次 `git init` 与基线文档**字节级保真**入库（建立 `main` 与 `rebuild/v1` 基线分支与文档框架），使后续治理文档全部在 Git 内生产。执行契约见 00 §7 M0.2（修订 2/3）；本节仅补充领域要求（FIX-10）。

**前置依赖**：PG-G0 通过（M0.1 已完成 D0 基线记录）。

**输入**：`peiligo_restart/docs/` 全部基线文档（PRD、三份审计、00/01/02/03）+ M0.1 产物（D0 记录）+ M00 独立审查记录（`M00.review.md` 与 `M00.gpt-review.md` 如有）。

**输出**（`peiligo_restart` 仓库，全部为**新增**）：`.git/`、`main`（基线提交）、`rebuild/v1`、`.gitignore`（含 `poc/`、`.env*`、`__pycache__/`、`*.sqlite3`、`media/`；**不含 `docs/ai/`**——FIX-03：由 M0.3 依 D8 裁决调整）、`docs/README.md`（索引 + 命名规则 + 文档状态头规范）、`docs/adr/_template.md`（全项目单一 ADR 模板，00 修订 5）、`docs/decisions/M0-2-BASELINE-MANIFEST.md`（入库清单 + 保真核对记录）。

**单步骤对话边界**：一次 Dispatch；只做"init + 复制 + 框架文件撰写 + 提交"；入库内容**字节级保真**（cmp 校验），禁止顺手修改；无 ask；源文件缺失或命名冲突时 escalation 而非自行裁决；**不得对旧仓执行任何命令（OR-2）**。

**允许修改的文件范围**：仅上述输出清单（全部新建于 peiligo_restart）；既有基线文件只读（`git add` 不视为修改）。

**验收命令**（在 `peiligo_restart` 执行）：

```bash
git rev-parse --is-inside-work-tree && git status --porcelain   # 期望空
git branch --list 'main' 'rebuild/v1'                            # 期望两行
grep -q '^poc/' .gitignore && grep -q '^\.env' .gitignore
! grep -q 'docs/ai' .gitignore                                   # FIX-03：M0.2 不预先忽略 docs/ai/
# 秘密零命中（00 §4.5 v1.2 版正则，含裸 dcap_ 分支）
! grep -rInE '(SECRET|TOKEN|PASSWORD|API_KEY|dcap_|BEGIN (RSA|OPENSSH))[=: ]+[A-Za-z0-9_./+-]{8,}|dcap_[A-Za-z0-9][A-Za-z0-9_-]{7,}' docs/
```

**测试要求**：命令输出全贴；入库清单（M0-2-BASELINE-MANIFEST）行数 = 实际入库文件数；保真断言（清单逐项 cmp/diff 为空）；`docs/README.md` 索引与实际文件双向对账。

**独立审查·需求/架构审查维度**：核对入库集合与 G0 确认范围一致、无未确认文件混入；无任何旧仓操作（OR-2）；`.gitignore` 覆盖秘密禁区且不含 `docs/ai/`（FIX-03）；文档框架可承载 PRD §25 全部文档类型（与实现/测试/安全审查维度由同一独立 GLM 新会话一次完成——FIX-06）。

**独立审查·实现/测试/安全审查维度**：重跑全部验收命令；对入库全历史执行秘密扫描；索引对账；审查记录统一写 `docs/reviews/PG-S3.review.md`（FIX-05）。

**失败与回滚策略**：git 化失败 → `rm -rf .git` 后重来；保真校验失败 → 重新复制（禁止手工修补差异）；入库后发现泄密 → 废弃该历史、修正后重建并上报；框架文件缺陷 → `PG-S3-fix`。

**完成条件**：验收全过 + 独立审查通过 → 文档唯一事实源（peiligo_restart Git）就绪，S4 起所有文档在 Git 内生产。

---

### PG-S4 · AI_WORKFLOW.md（AI 治理总契约）+ D8 裁决

**阶段目标**（阶段 3「AI 治理契约」）：关闭综合审计 §5 治理缺口——把 PRD §24 的多代理拓扑、单步骤规则、独立审查（v2.1 风险分级）、文件互斥、worker_done schema 与留档范围固化为可执行契约。

**前置依赖**：S3 已合并。

**输入**：PRD §24；综合审计 §5/§5.1；本计划 §3；Orca 能力事实（Run、Task `--parent/--deps`、Gate、worktree、Dispatch、ask/check、worker_done）。

**输出**：
1. `docs/governance/AI_WORKFLOW.md`，必含章节：①角色拓扑（总控/工作组/实现者/独立审查查者）与 Orca Run–Task–Dispatch 映射表（含综合审计指出的缺口：总控 Run 与组内 Run/Task 的层级映射）；②单步骤单对话规则（引用并固化本计划 §3.2）；③worker_done schema 与"恰好一次"语义（含失败时 `--outcome failed` 义务）；④独立审查流程（v2.1 风险分级；触发、范围、结论档位、复审上限、留档路径）；⑤文件互斥：SCOPE 声明格式、`DISPATCH_REGISTRY.md` 登记规则、路径重叠拒绝；⑥worktree/分支命名约定（`pg/`、`arch/` 前缀）；⑦D8 入库范围落地表（何者入 Git、何者仅本地+索引方式）；⑧transcript/报告脱敏要求（引用 `SECRETS_POLICY.md`，允许先占位链接，S6 落地后回填）。
2. `docs/decisions/D8_AI_EVIDENCE_SCOPE.md`：D8 问题、三选项（A 治理文档+脱敏后报告入库，原始 transcript 不入库【默认推荐】；B 仅治理文档入库；C 全部仅本地——与"唯一事实源"冲突，须负责人显式接受）、裁决原文。
3. `docs/governance/DISPATCH_REGISTRY.md`：初始化登记表（列：步骤、Dispatch 标识、SCOPE、worktree/分支、状态），并回填本计划已完成步骤。

**单步骤对话边界**：一次 Dispatch；开头恰好一次 ask（D8 三选一）；之后按裁决撰写；完成即 worker_done。

**允许修改的文件范围**：仅上述三个新文件（worktree `pg/s4-ai-workflow`）。

**验收命令**：

```bash
for f in docs/governance/AI_WORKFLOW.md docs/decisions/D8_AI_EVIDENCE_SCOPE.md \
         docs/governance/DISPATCH_REGISTRY.md; do test -f "$f" || { echo "missing $f"; exit 1; }; done
for kw in 总控 工作组 单步骤 worker_done 独立审查 文件互斥 worktree 入库范围 脱敏; do
  grep -q "$kw" docs/governance/AI_WORKFLOW.md || { echo "missing ${kw}"; exit 1; }
done
grep -qE '裁决：[ABC]' docs/decisions/D8_AI_EVIDENCE_SCOPE.md
test "$(grep -c '^| PG-S' docs/governance/DISPATCH_REGISTRY.md)" -ge 3
```

**测试要求**：章节覆盖 grep 全过；registry 回填行数 ≥ 此前已完成步骤数；worker_done schema 字段与本计划 §3.2 逐字段一致（审查者比对表）。

**独立审查·需求/架构审查维度**：提供"PRD §24 逐条 ↔ 契约章节"与"综合审计 §5 差距逐项 ↔ 闭合方式"两张对账表；确认契约未赋予任何代理扩围/写业务代码/绕过门的能力；D8 裁决与记录一致（FIX-06 双维度口径）。

**独立审查·实现/测试/安全审查维度**：重跑验收命令；比对 schema 与本计划 §3.2；"新对话仅凭契约 + 模板即可开工"的可执行性演练（纸面）；审查记录统一写 `docs/reviews/PG-S4.review.md`（FIX-05）。

**失败与回滚策略**：文档分支 revert；D8 ask 超时 → escalation 挂起（不得缺省代决）；裁决为 C 时必须在 D8 记录中标注与 P0 唯一事实源风险的冲突由负责人接受。

**完成条件**：验收全过 + 独立审查通过。

---

### PG-S5 · TASK_TEMPLATE.md（单步骤任务契约模板）

**阶段目标**（阶段 3）：把本计划的 12 字段步骤结构产品化为治理线与技术线（02+ 计划）共用的派发模板，落实 PRD §24.2。

**前置依赖**：S4 已合并（术语与 schema 引用）。

**输入**：本计划 §3.2 与 §5 的 12 字段结构；`docs/governance/AI_WORKFLOW.md`。

**输出**：`docs/governance/TASK_TEMPLATE.md`，含：TASK 块骨架；12 字段填写规范（阶段目标/前置依赖/输入/输出/单步骤对话边界/允许修改的文件范围/验收命令/测试要求/独立需求·架构审查/独立实现·测试·安全审查/失败与回滚策略/完成条件）；SCOPE 声明段模板；验收命令段规范（必须可复制执行、零新依赖）；worker_done 报告模板；`-fix` 修正步骤模板；审查记录模板引用；一个完整示例（以 PG-S1 回填示范）。

**单步骤对话边界**：一次 Dispatch；无 ask；只产一个文件。

**允许修改的文件范围**：仅 `docs/governance/TASK_TEMPLATE.md`（worktree `pg/s5-task-template`）。

**验收命令**：

```bash
test -f docs/governance/TASK_TEMPLATE.md
for kw in 阶段目标 前置依赖 输入 输出 单步骤对话边界 允许修改的文件范围 验收命令 测试要求 \
          独立需求 独立实现 失败与回滚策略 完成条件; do
  grep -q "$kw" docs/governance/TASK_TEMPLATE.md || { echo "missing ${kw}"; exit 1; }
done
grep -q 'worker_done' docs/governance/TASK_TEMPLATE.md && grep -q 'SCOPE' docs/governance/TASK_TEMPLATE.md
grep -q 'PG-S1' docs/governance/TASK_TEMPLATE.md   # 含填好的示例
```

**测试要求**：12 字段齐全；示例步骤内容与 PG-S1 实际契约一致；对 `AI_WORKFLOW.md` 的交叉引用链接有效。

**独立审查·需求/架构审查维度**：模板覆盖 PRD §24.2 全部要求项（单一目标、输入文档、可修改范围、验收命令、完成报告）且无字段遗漏；审批链（实现→独立审查→门）在模板中可见（FIX-06 双维度口径）。

**独立审查·实现/测试/安全审查维度**：以 PG-S6 契约为样例做一次模板"干跑"填写检查；占位符与链接校验；审查记录统一写 `docs/reviews/PG-S5.review.md`（FIX-05）。

**失败与回滚策略**：单文件 revert；缺陷 → `PG-S5-fix`。

**完成条件**：验收全过 + 独立审查通过。

---

### PG-S6 · SECRETS_POLICY.md（秘密禁区与脱敏）

**阶段目标**（阶段 3）：关闭 P0 风险第 4 条——定义禁区路径、禁读/禁输出规则、提交前扫描、暴露事故处置与令牌轮换要求。

**前置依赖**：S3 已合并；与 S4/S7/S8 并行（文件集不相交）。

**输入**：综合审计 §5.1 事件（Claude 配置敏感字段曾被读入 transcript）与 P0 建议（轮换曾暴露令牌）；旧仓审计中的敏感面（`SESSION_SECRET`、`.env*`、数据库口令、`dcap_` 派发令牌、远端 URL）。

**输出**：`docs/governance/SECRETS_POLICY.md`，必含：①禁区路径清单（`.env` 与 `.env.*`、`*.pem`、`*id_rsa*`、`.git-credentials`、`.ssh/`、`.aws/`、`secrets/`、`credentials*`、`token*`、含 `dcap_`/`Bearer` 的命令行与配置、`~/.claude/settings*.json` 的敏感字段值、后端 `SESSION_SECRET` 类配置值、数据库连接口令）；②规则：禁止读取禁区文件进入 transcript；禁止在报告/文档/审查记录/提交信息中复制秘密值；引用只允许"路径 + 字段名"；③提交前扫描命令（纯 grep/git，零新依赖）与"零命中"要求；④报告脱敏正则清单；⑤事故处置流程：立即停止外发 → 记录事件（路径/时间/范围）→ 通知负责人 → 评估轮换（曾暴露令牌默认轮换）→ 复查已入 Git 内容；⑥审查者对每份产出物的脱敏复核义务。

**单步骤对话边界**：一次 Dispatch；无 ask；**撰写过程本身不得读取任何真实凭据文件**——内容仅依据审计报告与通用模式撰写，示例值一律使用明显占位符（如 `EXAMPLE_NOT_A_SECRET`）。

**允许修改的文件范围**：仅 `docs/governance/SECRETS_POLICY.md`（worktree `pg/s6-secrets`）。

**验收命令**：

```bash
test -f docs/governance/SECRETS_POLICY.md
for kw in 禁区 脱敏 轮换 事故 零命中; do
  grep -q "$kw" docs/governance/SECRETS_POLICY.md || { echo "missing ${kw}"; exit 1; }
done
# 文档给出的主扫描命令必须可直接运行（抽取第一段 bash 中的 grep 行执行）
awk '/```bash/{f=1;next}/```/{f=0}f&&/^grep|f&&/&&/grep/{print;exit}' docs/governance/SECRETS_POLICY.md | sh
# 自身与全库文档过扫描
! grep -rInE '(SECRET|TOKEN|PASSWORD|API_KEY|dcap_|BEGIN (RSA|OPENSSH))[=: ]+[A-Za-z0-9_./+-]{8,}' docs/
```

**测试要求**：扫描命令抽取执行通过；禁区清单覆盖审计点名的全部敏感面（审查者对照表）；四个载体（transcript、报告、Git、审查记录）均有对应规则。

**独立审查·需求/架构审查维度**：与综合审计 §5.1/P0 逐项对账；规则无漏洞载体；不与 D8 入库范围冲突（FIX-06 双维度口径）。

**独立审查·实现/测试/安全审查维度**：在临时目录构造假阳性/假阴性样例（仅用明显假占位值，验证后删除）验证扫描命令有效性；确认禁区清单不妨碍正常文档工作；审查记录统一写 `docs/reviews/PG-S6.review.md`（FIX-05）。

**失败与回滚策略**：revert；扫描命令自身缺陷 → 立即开 `PG-S6-fix`，禁止后续步骤带病沿用旧命令。

**完成条件**：验收全过 + 独立审查通过。

---

### PG-S7 · ROLE_PERMISSION_MATRIX.md（产品级角色权限矩阵）

**阶段目标**（阶段 4「产品与流程治理文档」）：落实综合审计 §7 文档差距第 2 项——从 PRD 推导角色×动作×对象矩阵，作为后续技术权限设计（D5，另计划）的产品侧输入。

**前置依赖**：S3 已合并（且 PRD 已按 PG-G0 裁决定稿）；与 S4/S6/S8 并行。

**输入**：PRD §4（四角色）、§5（认证与权限）、§8（发布/归档/纠错治理）、§20（负面清单）、§23（必测权限场景）。

**输出**：`docs/ROLE_PERMISSION_MATRIX.md`：主矩阵（学生访客/总管理员/部门岗位账号/技术维护人员 × 动作 × 对象，每格附 PRD 条款溯源）；负面权限区（明确"谁不可以做什么"，含 §20 全量映射）；待技术映射注记区（标注哪些格等待 D5 权限树与 D6 载体决策，**不含任何实现方案**）。

**单步骤对话边界**：一次 Dispatch；无 ask；只做产品语义（谁可做什么），不预判 Wagtail 权限实现（D5 未决，不得代决）。

**允许修改的文件范围**：仅 `docs/ROLE_PERMISSION_MATRIX.md`（worktree `pg/s7-roles`）。

**验收命令**：

```bash
test -f docs/ROLE_PERMISSION_MATRIX.md
for role in 学生访客 总管理员 部门岗位账号 技术维护人员; do
  grep -q "$role" docs/ROLE_PERMISSION_MATRIX.md || { echo "missing ${role}"; exit 1; }
done
for kw in '只能.{0,6}本部门' 置顶 永久删除 归档 密码重置 校园网; do
  grep -qE "$kw" docs/ROLE_PERMISSION_MATRIX.md || { echo "missing ${kw}"; exit 1; }
done
# 每个关键语义有 PRD 溯源（≥20 处条款引用）
test "$(grep -cE 'PRD §' docs/ROLE_PERMISSION_MATRIX.md)" -ge 20
grep -q '不开放公开注册' docs/ROLE_PERMISSION_MATRIX.md   # §20 负面清单在场
```

**测试要求**：PRD §4/§5/§8 中每个权限动词语义至少一格承载（审查者对账表）；PRD §23 五条必测权限场景一一对应到矩阵行并在文档中显式标注。

**独立审查·需求/架构审查维度**：逐格与 PRD 对照，无凭空权限、无遗漏关键限制（尤其"部门账号不得修改他部门内容/网站配置/账号/板块/置顶"）；不越 D5（不含实现方案）；无 V1 扩围权限（FIX-06 双维度口径）。

**独立审查·实现/测试/安全审查维度**：Markdown 表格语法渲染正确；抽查 ≥20 处溯源条款号在 PRD 中真实存在；无扩围措辞；审查记录统一写 `docs/reviews/PG-S7.review.md`（FIX-05；注意：00 修订 4 已将本步骤并入 M4.1 合并步，归架构线执行）。

**失败与回滚策略**：revert；若 PG-G0 附 PRD 修订 → 本步骤以修订版为准重算（故强依赖 PG-G0 先行）。

**完成条件**：验收全过 + 独立审查通过。

---

### PG-S8 · CHANGE_MANAGEMENT.md + REQUIREMENTS_BACKLOG.md（变更管理与需求候选池）

**阶段目标**（阶段 4）：落实 PRD §25 与综合审计 §7 第 9 项——变更记录流程、需求候选池、V1 冻结规则、安全修复例外通道。

**前置依赖**：S3 已合并；与 S4/S6/S7 并行。

**输入**：PRD §1（基线冻结原则）、§20、§25；综合审计 §7–§9。

**输出**：
1. `docs/governance/CHANGE_MANAGEMENT.md`：变更记录格式（编号、日期、提出人、类型、影响文件、批准人）；审批链（默认不进 V1，项目负责人独占批准）；安全缺陷与阻断上线问题的"先修复后补记录"例外流程；文档状态头生命周期（草案 → 已确认 → 已冻结 → 已废弃）。
2. `docs/REQUIREMENTS_BACKLOG.md`：候选池表（编号、提出人、动机、预期价值、影响范围、建议版本、状态）；以 PRD §20 已知候选项预填（如微信公众号推送、AI 检索、学生账号等，均标注"不进 V1（默认）"）。

**单步骤对话边界**：一次 Dispatch；无 ask；候选池只登记不裁决——任何"进入 V1"的决定留给负责人门，本步骤不得写入任何扩围承诺。

**允许修改的文件范围**：仅上述两个文件（worktree `pg/s8-change`）。

**验收命令**：

```bash
for f in docs/governance/CHANGE_MANAGEMENT.md docs/REQUIREMENTS_BACKLOG.md; do
  test -f "$f" || { echo "missing $f"; exit 1; }
done
for kw in 提出人 动机 预期价值 影响范围 建议版本; do
  grep -q "$kw" docs/REQUIREMENTS_BACKLOG.md || { echo "missing ${kw}"; exit 1; }
done
grep -qE '未经项目负责人批准' docs/governance/CHANGE_MANAGEMENT.md
grep -q '安全' docs/governance/CHANGE_MANAGEMENT.md && grep -q '补充变更记录' docs/governance/CHANGE_MANAGEMENT.md
grep -q '微信公众号' docs/REQUIREMENTS_BACKLOG.md
```

**测试要求**：变更记录条目格式可被本计划已发生的 D0/D1/D8 决定回填验证；例外流程含时序（修复 → 通报 → 补记录）；候选池预填项与 PRD §20 一一对应。

**独立审查·需求/架构审查维度**：与 PRD §25 逐句对账；冻结规则与 §1 一致；例外通道无被滥用来变相扩围的漏洞（FIX-06 双维度口径）。

**独立审查·实现/测试/安全审查维度**：表头可机械校验（grep 通过）；预填项与 §20 一致；全文无"顺带实现"式扩围措辞；审查记录统一写 `docs/reviews/PG-S8.review.md`（FIX-05）。

**失败与回滚策略**：revert；`PG-S8-fix`。

**完成条件**：验收全过 + 独立审查通过。

---

### PG-S9 · PHASE_GATES.md + 治理基线确认包

**阶段目标**（阶段 5「阶段门与准出」）：固化全局 G0–G4 门定义与记录机制（阶段门主题的落地），汇总本计划全部证据形成 PG-G2 门材料。

**前置依赖**：S4、S5、S6、S7、S8 全部完成且独立审查通过。

**输入**：本计划全部产出与治理线 6 份既有独立审查记录（S1、S3–S6、S8，v1.4 口径：每步一份；S2 已废止、S7 并入 M4.1 归架构线）；综合审计 §9 全局 DAG 与约束；PRD §24.4。

**输出**：
1. `docs/governance/PHASE_GATES.md`：全局 G0–G4 每门的准入/准出/批准人/记录文件/与 Orca Gate 映射；本计划 PG-G0/G1/G2 与全局门的映射表；门状态表（已过/待裁决）。
2. `docs/decisions/GP-G2_GATE_PACKAGE.md`：步骤 × 验收命令输出 × 独立审查结论汇总表；遗留项与移交清单（含：重建分支建立时必须携带 `docs/` 基线；CI 门禁属 B6；`docs/ai/` 入库与否按 D8 执行）。
3. `docs/README.md` 索引刷新（仅索引区，其余内容不动）。

**单步骤对话边界**：一次 Dispatch；无 ask；只汇总不改判（门裁决权仍属负责人）；发现前置步骤缺陷时 escalation 而非代改。

**允许修改的文件范围**：`docs/governance/PHASE_GATES.md`、`docs/decisions/GP-G2_GATE_PACKAGE.md`（新建）；`docs/README.md`（仅索引区追加/更新）（worktree `pg/s9-gates`）。

**验收命令**：

```bash
for f in docs/governance/PHASE_GATES.md docs/decisions/GP-G2_GATE_PACKAGE.md; do
  test -f "$f" || { echo "missing $f"; exit 1; }
done
for g in G0 G1 G2 G3 G4; do
  grep -qE "(^|[^A-Za-z0-9])${g}([^A-Za-z0-9]|$)" docs/governance/PHASE_GATES.md || { echo "missing ${g}"; exit 1; }
done
for s in S1 S3 S4 S5 S6 S8 S9; do
  grep -q "PG-${s}" docs/decisions/GP-G2_GATE_PACKAGE.md || { echo "missing PG-${s}"; exit 1; }
done
# 索引对账：README 提到的每个文档路径都存在
grep -oE 'docs/[A-Za-z0-9_/.-]+\.md' docs/README.md | sort -u \
  | while read -r p; do test -f "$p" || { echo "broken ${p}"; exit 1; }; done
# 审查记录齐全：治理线 7 步 × 每步 1 份 = 7 份（v1.4 口径：S2 已废止、S7 并入 M4.1 归架构线，
# 与 00 §6 G2"治理线 7 份"一致；命名按 00 修订 11 v1.3）
test "$(ls docs/reviews/PG-S*.review.md | wc -l | tr -d ' ')" = 7
```

**测试要求**：门定义与综合审计 §9 逐门一致（审查者对账）；门状态表与本计划实际进度一致；汇总包内链接全部有效；抽查 3 个步骤的验收输出与原始记录一致。

**独立审查·需求/架构审查维度**：门定义与 PRD §24.4、综合审计 §9 约束逐条一致（G0 前不开发、G1 前不冻结结构、G2 前不主开发、B 步骤独立 worktree、独立审查）；PG 门与全局门映射无错位（FIX-06 双维度口径；门定义以 00 §6 为准——FIX-10）。

**独立审查·实现/测试/安全审查维度**：重跑汇总包全部命令；抽查原始记录一致性；索引对账；审查记录统一写 `docs/reviews/PG-S9.review.md`（FIX-05）。

**失败与回滚策略**：revert；若门材料暴露前置步骤缺陷 → 开对应 `-fix` 步骤并重走独立审查，S9 顺延重做汇总。

**完成条件**：验收全过 + 独立审查通过 + 材料呈报负责人 → 触发 PG-G2 裁决；负责人批准后本计划关闭，治理线输出并入全局 G2。

## 6. 本计划自身的变更管理

- 本计划冻结（独立审查 + 负责人批准）后，任何步骤增删、范围调整、验收命令变更均须：在 `docs/governance/CHANGE_MANAGEMENT.md` 登记变更记录 → 负责人批准 → 修改本文件并更新 DAG → 受影响步骤重走独立审查。
- 步骤级缺陷修复不修改本计划，以 `PG-Sn-fix` 新 Dispatch 执行并复用原验收命令。
- 全局硬边界（本文档头表）不可通过本计划内任何步骤放宽。

## 7. 执行期立即生效的秘密禁区（临时规则，S6 固化前对本计划全部对话生效）

1. 禁止读取以下内容进入任何 transcript/报告：`.env*`、`*.pem`、`*id_rsa*`、`.git-credentials`、`.ssh/`、`.aws/`、`secrets/`、任何含 `SECRET/TOKEN/PASSWORD/API_KEY` 值的配置、Orca `dcap_` 派发令牌值、数据库口令。
2. 一切报告/文档/提交信息中引用秘密只允许"路径 + 字段名"，禁止复制值。
3. 每份产出提交前执行零依赖扫描并要求零命中：

```bash
! grep -rInE '(SECRET|TOKEN|PASSWORD|API_KEY|dcap_|BEGIN (RSA|OPENSSH))[=: ]+[A-Za-z0-9_./+-]{8,}' <目标目录>
```

4. 一旦发生暴露：立即停止外发 → 记录事件 → 通知负责人 → 曾暴露令牌默认建议轮换（综合审计 P0 处置要求）。

## 8. 整体完成定义（DoD）与移交

**本计划完成的判定**（全部满足）：

1. S1–S9 步骤全部完成（**S2 已废止不执行、S7 并入 M4.1 归架构线——00 §23.1**；本文治理线生效步骤 = S1、S3–S6、S8、S9 共 7 步，对应 00 M0.1–M0.7），各自验收命令全过且输出留档；
2. 治理线 7 份独立审查记录（每步骤一份，独立 GLM 新会话审查；上调 R3 时另含 GPT 审查记录）全部为"通过"（v1.4 口径，与 00 §6 G2 一致）；
3. PG-G0（= 全局 G0）、PG-G2（→ 全局 G2 治理输入）两门按 §4.1 定义通过并留有决策记录（PG-G1 已随 PG-S2 废止删除）；
4. 全部产出已合入 **`peiligo_restart` 仓库**（M0.2 Git 化，`rebuild/v1` 基线分支；无旧仓迁入动作——OR-2/FIX-01）；
5. 全程零违反全局硬边界（无业务代码、无项目初始化、无依赖安装、无 PVE/生产操作、无 V1 扩围）。

**移交**：

- 治理线输出（AI_WORKFLOW / TASK_TEMPLATE / SECRETS_POLICY / PHASE_GATES / 角色权限矩阵 / 变更管理与候选池 / 基线文档）作为全局 G2 的治理输入；
- 技术线计划（02 起：D2–D4 ADR、D5 权限树、D6 内容模型、D7 中文搜索 PoC）在 PG-G0 后即可按 TASK_TEMPLATE 起草与派发；
- 重建分支（B 阶段）建立时必须携带 `docs/` 基线（写入 GP-G2 移交清单）；
- 本文件状态头改为"已完成"，并在 `PHASE_GATES.md` 状态表登记关闭。
