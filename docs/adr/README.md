# ADR 目录 · 收录范围、索引与状态机制

| 项目 | 内容 |
| --- | --- |
| 建立步骤 | M1.1 · ADR 机制、模板与决策索引（00_MASTER_PLAN §8 M1.1；引源 02 §3 S1.1；分支 `arch/m1.1-adr-mechanism`，修订 12 前缀） |
| 建立日期 | 2026-08-18 |
| 模板 | `docs/adr/_template.md`——全项目唯一 ADR 模板（00 §3.1 修订 5：01 PG-S4 的 `docs/adr/TEMPLATE.md` 已并入，项目内不存在第二个模板） |
| 上游依据 | 00_MASTER_PLAN §2（C1–C5、D0–D9 决策门处置）、§3.1 修订 5/12、§4.4 共享文件、§6 门定义、§8 M1.1；02_ARCHITECTURE_DOMAIN_PLAN §3 S1.1 |
| G1 门状态 | **已通过**（2026-08-18 项目负责人批准；治理记录：[docs/decisions/G1_ARCHITECTURE_FREEZE.md](../decisions/G1_ARCHITECTURE_FREEZE.md)） |

## 1. 收录范围声明（v1.1 口径）

本目录（`docs/adr/`）**仅收录技术架构决策**——V1 范围即下表预列的 ADR-0001–0006，此外不收录任何其他内容。

以下**治理 / 流程类决策记录一律归 `docs/decisions/`，不得写入本目录**（两类决策记录混放会造成口径漂移）：

- **D0 基线**：`docs/decisions/D0_BASELINE_CONFIRMATION.md`（已入库）及 M0.2 入库清单 `docs/decisions/M0-2-BASELINE-MANIFEST.md`；
- **D8**：AI 治理入库范围裁决记录（M0.3 步骤内恰好一次 ask 的裁决落档）；
- **PHASE_GATES**：阶段门定义与状态表（M0.7）；
- **G2 治理确认包**：M0.7 汇总包；
- 其余治理 / 流程决策（决策门裁决记录、门批准记录、治理政策等）。

判定规则：决策对象是**系统架构的技术形态**（版本组合、骨架结构、前端架构、权限结构、内容载体、搜索后端）→ ADR；决策对象是**项目如何被治理与推进**（阶段门、流程、入库范围、角色权限制度）→ `docs/decisions/`。判定有疑义时上报项目负责人裁决，代理不得自行取舍。

## 2. ADR 索引（预列 0001–0006）

| 编号 | 标题 | 状态 | 日期 | 对应已确认决策 | 落盘步骤 · 文件名 | 转 Accepted 门 |
| --- | --- | --- | --- | --- | --- | --- |
| 0001 | 版本组合冻结（Wagtail 7.4.x LTS + Django 5.2 LTS + Python 3.13） | Accepted | 2026-08-18 | C1（=D3） | M1.2 · [0001-wagtail-django-python-versions.md](0001-wagtail-django-python-versions.md) | G1 |
| 0002 | 前端架构：Wagtail 服务端模板 | Accepted | 2026-08-18 | C2（=D4） | M1.3 · `0002-server-side-templates.md` | G1 |
| 0003 | 项目骨架：peiligo_restart 全新仓库干净 Wagtail 骨架 | Accepted | 2026-08-18 | C5/D2 | M1.4 · `0003-clean-wagtail-skeleton.md` | G1（=D2 正式裁决记录） |
| 0004 | 部门权限容器树（不构成前台部门主页） | Accepted | 2026-08-18 | C3（=D5） | M1.5 · `0004-department-permission-container-tree.md` | G1 |
| 0005 | 公开内容 Page / 受控数据 Snippet·设置 | Accepted | 2026-08-18 | C4（=D6） | M1.6 · `0005-page-vs-snippet-allocation.md` | G1 |
| 0006 | 中文搜索后端 | Proposed | 2026-08-31 | D7（保留决策门，待 M6.3 PoC 裁决） | M6.3 · [0006-chinese-search-backend.md](0006-chinese-search-backend.md) | M6.3 落盘 → G2 |

预列说明：

- 本表由 M1.1 一次性预列六行；各 ADR 正文分别由 M1.2–M1.6 与 M6.3 撰写，**M1.1 不撰写任何具体 ADR 内容**。
- 预列行在对应 ADR 文件落盘前即为 Proposed 占位；文件落盘后仍为 Proposed，直至相应门（G1 / G2）由项目负责人批准转 Accepted。
- "日期"列由各撰写步骤在 ADR 落盘时填入首落盘日期。
- 0001–0005 的决策内容已由项目负责人确认（C1–C5 冻结，不得重开），ADR 仅做固化与论证记录；0006 为唯一真正待裁决项（D7：三方案 PoC 达标即选简单者，均不达标才评估独立搜索服务，且须项目负责人批准）。

## 3. 状态看板

统计时点：2026-08-18（G1 架构冻结门收口后；0001–0005 经项目负责人批准由 Proposed 转 Accepted）。

| 状态 | 数量 | 编号 |
| --- | --- | --- |
| Proposed | 1 | 0006（已落盘 Proposed，待 G2） |
| Accepted | 5 | 0001、0002、0003、0004、0005（2026-08-18 G1 门批准） |
| Superseded | 0 | — |
| Rejected | 0 | — |

## 4. 状态流转规则

状态机：`Proposed → Accepted`（门批准）；`Proposed → Rejected`（门否决或决策被推翻）；`Accepted → Superseded`（被后续 ADR 取代，新 ADR 须显式引用被取代者及其编号）。Rejected 与 Superseded 为终态留档：文件不删除、编号不复用。

| 流转 | 触发条件 | 执行人 |
| --- | --- | --- |
| Proposed → Accepted | 0001–0005：G1 架构冻结门通过；0006：M6.3 裁决落盘后经 G2 门 | 项目负责人（在门记录中设定并签字） |
| Proposed → Rejected | 门审查否决，或项目负责人明示否决 | 项目负责人 |
| Accepted → Superseded | 取代它的 ADR 转 Accepted 时同步执行 | 项目负责人 |

**流转权限（硬规则）：ADR 状态变更的决策人只能是项目负责人或其书面授权人；执行代理（AI）不得代决，不得自行改写任何 ADR 状态。** 代理在步骤内仅允许：以 Proposed 新建 ADR、按门批准结果同步本索引状态行与看板（见 §5）。

## 5. 维护规则

- 本文件为**共享文件**（00 §4.4）：M1.2–M1.6 与 M6.3 各步骤**仅允许更新本索引中自己那一行的状态 / 日期列及 §3 看板计数**；收录范围（§1）与流转规则（§4）不得由步骤代理修改。
- 新建 ADR 必须从 `docs/adr/_template.md` 复制，五节结构与状态字段头不得增删改名。
- 状态行更新时，须在对应 ADR 文件的状态字段头同步同一状态与变更日期；两处一致方为更新完成。
- 收录范围变更（如 V2 新增 ADR-0007+）属治理决策，须项目负责人批准后进行。
