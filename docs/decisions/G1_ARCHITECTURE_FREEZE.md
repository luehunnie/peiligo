# G1 · 架构冻结门收口记录（G1_ARCHITECTURE_FREEZE）

| 项目 | 内容 |
| --- | --- |
| 文件编号 | G1_ARCHITECTURE_FREEZE（G1 架构冻结门批准记录；按 `docs/adr/README.md` §1 收录范围声明，门批准记录属治理类，归 `docs/decisions/`） |
| 所属门 | G1 架构冻结门（M1.6 后触发；门定义 = 00_MASTER_PLAN §6 G1 行 = 02_ARCHITECTURE_DOMAIN_PLAN §3.7 全文，按 v1.4 状态模型修正） |
| 批准人 | 项目负责人（用户） |
| 批准日期 | 2026-08-18 |
| 收口基线 | `rebuild/v1` 基线 SHA = **a67888d**（收口前 HEAD，`git rev-parse --short HEAD` 核验）；本记录与五 ADR 状态翻转、ADR 索引/看板同步为同一提交 |
| 执行方式 | 单步骤 Dispatch（分支 `arch/g1-closeout`，基于 `rebuild/v1@a67888d`）；执行代理仅按项目负责人已作出的批准机械落盘，未代决任何状态（ADR README §4 硬规则） |
| 上游依据 | 00_MASTER_PLAN §2.1/§2.2（C1–C5、D2–D6 处置）、§6 G1 行；02 §3.7；`docs/reviews/M1.1–M1.6.review.md`（六份独立审查）；`docs/decisions/D0_BASELINE_CONFIRMATION.md` |

## 1. 门条件核对（00 §6 G1 行，逐条）

| # | 门条件 | 结论 | 证据 |
| --- | --- | --- | --- |
| 1 | 五 ADR 均以 Proposed 落盘、独立审查通过 | 满足 | M1.1–M1.6 六步各一份独立审查报告（路径见 §3）；五 ADR 文件均已以 Proposed 落盘（收口前状态，M1.2–M1.6 产物） |
| 2 | GPT G1 Risk/Architecture Review（M1.2–M1.6 合并 R3 级，00 §4 缺省） | **PASS**（项目负责人确认，2026-08-18） | 项目负责人于 G1 收口总控指令确认；结论以项目负责人确认为准 |
| 3 | Human Approval——项目负责人将五 ADR 状态正式设为 Accepted 并签字 | **PASS**（2026-08-18 项目负责人正式批准） | 本记录即批准（签字）载体；五 ADR 状态字段头与 ADR 索引/看板随本记录同步翻转 |
| 4 | ADR-0001 当日版本复核输出留档 | 满足 | ADR-0001"决策"节"当日版本复核"表 + "复核结论"（2026-08-18；摘要见本文件 §4） |
| 5 | V1 不做清单复核无扩围 | 满足 | 五 ADR"合规性"节均逐条核对 PRD §20 无扩围；本收口未触碰 PRODUCT_REQUIREMENTS |
| 6 | PRE 前置复核（02 §3.7 条件 3） | 满足 | PRE-1（D0 审计基线确认 + C1–C4 决策有效）已随 G0/D0 固化成立；PRE-2 已废止（00 修订 6）；PRE-3/PRE-4 已由 M0.2 解决，无降级事项 |

## 2. 五 ADR 状态快照（G1 批准时点）

| 编号 | 标题 | 终态 | 对应已确认决策 |
| --- | --- | --- | --- |
| ADR-0001 | 版本组合冻结（Wagtail 7.4.x LTS + Django 5.2 LTS + Python 3.13） | **Accepted** | C1（=D3） |
| ADR-0002 | 前端架构：Wagtail 服务端模板 | **Accepted** | C2（=D4） |
| ADR-0003 | 项目骨架：peiligo_restart 全新仓库干净 Wagtail 骨架 | **Accepted** | C5；**G1 批准即 D2 正式裁决记录**（02 §3.7 条件 1） |
| ADR-0004 | 部门权限容器树（不构成前台部门主页） | **Accepted** | C3（=D5） |
| ADR-0005 | 公开内容 Page / 受控数据 Snippet·设置 | **Accepted** | C4（=D6） |

ADR-0006（中文搜索后端）不在 G1 范围：保持 Proposed 预列占位，待 M6.3 落盘后经 G2 门（00 §2.2 D7）。

## 3. 独立审查报告路径（六份）

- `docs/reviews/M1.1.review.md`
- `docs/reviews/M1.2.review.md`
- `docs/reviews/M1.3.review.md`
- `docs/reviews/M1.4.review.md`
- `docs/reviews/M1.5.review.md`
- `docs/reviews/M1.6.review.md`

## 4. ADR-0001 当日版本复核留档说明（复核日期 2026-08-18）

全部官方 URL 当日访问核验，输出留档于 ADR-0001"当日版本复核"表与"复核结论"：

- **Wagtail**：7.4.x 线无晚于 7.4.2 的补丁 → 实际锁定 `wagtail==7.4.2`（区间 `>=7.4.2,<7.5` 满足）；
- **Django**：5.2.x 线最新安全补丁 **5.2.17**（2026-08-04，含 4 项 CVE 修复）→ B1 首次锁依赖落在 `>=5.2.17` 的 5.2.x（策略区间仍 `>=5.2,<5.3`）；
- **modelsearch**：1.3 线最新 1.3.2 → 实际锁定 `modelsearch==1.3.2`（区间 `>=1.3.2,<1.4` 满足）。

## 5. 通过后果与收口边界

- **通过后果**（00 §6 G1 行）：解锁 M2–M7；本记录即总控发布的 G1 记录（批准人、日期、ADR 状态快照——02 §3.7"通过后"）。
- **收口边界**：本步骤仅翻转五 ADR 状态字段头、同步 ADR 索引行与 §3 看板、落盘本治理记录；未改任何 ADR 决策正文，未触碰 PRODUCT_REQUIREMENTS / C1–C5 / 00–03 计划文档，未开始 M2 及其后任何步骤。
- **后续状态流转**（ADR README §4）：五 ADR 此后仅可经 `Accepted → Superseded`（被后续 ADR 取代时同步执行）流转，执行人为项目负责人；ADR-0004 决策 4 保留 S4.3 验证生效条件——M4.3 越权矩阵若发现不可修复缺陷，该 ADR 回 Proposed 并升级 D5 决策门重议（由项目负责人执行，代理不得代决）。
