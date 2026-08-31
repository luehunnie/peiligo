# G2-B 独立审查报告（项目冻结一致性检查）

## 结论：PASS（经一轮修复）

- 审查对象：`arch/g2-b-freeze-evidence` @ `20d66bb`（初轮）；修复轮 `5cc0390`（复审轮）
- 基线：`main` @ `0caece5`（0caece5c148346654552df998941dd807d28c482，G2-A 合并点＝G2_B_BASELINE）
- 审查者：独立 GLM 新会话（fresh-context subagent，不继承实现上下文；00_MASTER_PLAN §4.6 双口径；Orca 会话派发不可用→PROCESS_DEVIATION 已记录于 Evidence §7）
- 审查日期：初轮＋复审轮均 2026-09-01
- 变更文件（全程）：`docs/G2_FREEZE_EVIDENCE.md`（新增）——仅 docs/，零代码/settings/模板变更
- 初轮判定：**FAIL**（1 处必修＋4 项建议；冻结检查主体工作合格）
- 复审判定：**PASS**（必修与建议 5 项全部落实；复审对修复文本逐条新断言核验，未发现新的事实/分类错误）

> 本记录由实现会话依审查者两轮报告整理；§3 复审结论逐字取自审查者复审回复。

## 1. 初轮审查（@ 20d66bb，2026-09-01）

### 1.1 十项检查清单结果

| # | 检查项 | 结果 |
| --- | --- | --- |
| 1 | BASELINE 实测（local/origin/behind/ahead/变更范围）与 Evidence §1 一致 | ✅ |
| 2 | ADR_STATUS_MATRIX：六份 ADR 存在、状态明确、无未说明互相覆盖、无两个 Accepted ADR 相反结论 | ✅ |
| 3 | FREEZE_MATRIX：16 领域分类合法（FROZEN / FROZEN_WITH_IMPLEMENTATION_GAP / BLOCKED；「尚未实现」未误标 BLOCKED） | ✅ |
| 4 | HUMAN_PARAMETERS：23/23 HUMAN_CONFIRMED、G2_PENDING_PARAMETERS=0 三处一致、DEFERRED_DEPLOYMENT_DETAIL 未重算为 Pending | ✅ |
| 5 | IMPLEMENTATION_GAPS：只收有正式 Evidence 的未完成项、禁止凭想象增项 | ❌ → 必修（见 §1.2） |
| 6 | ARCHITECTURE_DECISIONS_PENDING：未决设计决策 0、治理残留分类正确 | ✅ |
| 7 | PROCESS_DEVIATION：expected/actual/independence 如实（Orca 不可用→fresh-context 独立会话） | ✅ |
| 8 | G2_MECHANICAL_RESULT：①–⑧ 逐条判定与证据相符 | ✅ |
| 9 | POST_G2_MODE：READ_ONLY_GAP_AUDIT_FIRST 论证成立（A 系列审查证明 MB 范围部分已实现） | ✅ |
| 10 | 边界：`git diff 0caece5..20d66bb --name-status` 仅 1 个 docs 文件 | ✅ |

特别核验：A. §5 缺口条目逐条溯源 SB/NFR/ADR/Mapping，无虚构项；B. §8 条件⑧（M0.3–M0.7 治理线未执行）的事实认定（两仓均无产物、D8 未裁决）经独立复核属实，分类为「门条件残留、Human 处置」正确。

### 1.2 必修项（初轮 FAIL 事由）

- **必修（发现1）** Evidence §5 缺口清单遗漏 SB 三处正式登记的 **SEC-16 强制改密** `NOT_IMPLEMENTED` 项（SB §2.4／§9 断言行／§12 追溯行／§14 Gap 登记），致 §5「完备性声明」失实。

### 1.3 建议项（非阻断）

1. **发现2** §6 宜补 SB §14 同批登记的项目负责人事项：R-05 用户/组管理无 DB 级审计裁决＋曾暴露令牌轮换。
2. **发现3** ADR-0005 一致性依据指针宜指向 CM §1.1 六类内容载体总表（与 IA §5 对照），而非仅 CM §13。
3. **发现4** ADR-0004 末行状态注记（「本回写最终以独立审查复跑＋G2 门确认为准」）宜在 §2 声明本轮 G2-B 审查即该注记所指复核载体。
4. **发现5** §5 宜说明 NFR §13 三个 `NEEDS_VERIFICATION` 领域（Browser/Responsive/Capacity）属验证/盘点类而非实现缺口、如何承接。

## 2. 修复轮（5cc0390，2026-09-01；1 个文件，+5/−4）

| 修复 | 落点 |
| --- | --- |
| 必修 | §5 #7 行并入 `LOGIN_RATE_LIMIT / FORCE_PASSWORD_CHANGE`：SEC-15（axes 未安装）＋SB-04/SEC-16（重置/首登强制改密未实现，SB §2.4/§9/§12/§14 四处证据）；§5 完备性声明收敛为「未发现列表之外的 `NOT_IMPLEMENTED` 证据支持项」口径 |
| 建议2 | §6 补「同批宜一并处置的项目负责人事项（SB §14 登记，非产品/架构设计决策）」：R-05 裁决（SB §7「开放（低）」）＋曾暴露令牌轮换（治理动作） |
| 建议3 | ADR-0005 行改为「CM §1.1 六类内容载体总表与 IA §5 载体表一致（受控数据侧详见 CM §13）」 |
| 建议4 | §2 新增注记条目：本轮 G2-B 独立审查即 ADR-0004 末行注记所指复核载体之一（落到 §3 PERMISSION_MODEL＝FROZEN 与 §8 条件② 16/16） |
| 建议5 | §5 末行补 NEEDS_VERIFICATION 三领域承接说明（Browser/Responsive＝NF-15 交付线执行、Capacity＝PP-18 上线前盘点；随 §9 底册承接，不另列行） |

## 3. 复审结论（@ 5cc0390，2026-09-01；审查者回复要点）

1. **发现1 PASS** — §5 #7 已并入 FORCE_PASSWORD_CHANGE，四处证据亲证真实（SB §2.4 末行／§9 SEC-16 行／§12 追溯行／§14 登记行）；完备性声明已收敛。
2. **发现2 PASS** — §6 新增条目落位；SB §7 R-05「开放（低）」与 §14 两行亲证在档。
3. **发现3 PASS** — ADR-0005 行指针改指 CM §1.1，标题逐字核实相符。
4. **发现4 PASS** — §2 注记条目在案（一处一行级小疵见下）。
5. **发现5 PASS** — §5 末行 NEEDS_VERIFICATION 承接说明与 NFR §13 对应行逐字一致。

**新事实错误检查** — 对修复文本逐条新断言核验：「重置/首登强制改密」有 SB §2.4 原文支撑（另见 M4-SECURITY-REVIEW:116、SB §7 R-06 行）；「与限速同批挂 MB」「SB §7 开放（低）」「NF-15 交付线」「PP-18 盘点」全部属实。**未发现新的事实/分类错误。**

**§1–§4/§7–§9 未动** — 修复 diff 三个 hunk 仅落 §2／§5／§6，其余各节逐字节未变。

**一处残留小疵（非阻断）** — 新条目引 `adr/0004:106`，实际注记在 **:105**（:106 为空行）——行号源自初轮报告引用、修复如实转录，引文内容逐字无误，属指针精度小疵，不构成事实错误。

**总判定：PASS**

## 4. 复审后微修（并入本记录提交，2026-09-01）

- 残留小疵顺手修正：Evidence §2 `adr/0004:106` → `adr/0004:105`（纯指针行号更正，零语义变化）。审查者已明确该项非阻断、总判定 PASS 在先。

## 5. 阻断性检查（两轮均零命中）

- 非 docs 文件变更：零（初轮 §1.1 #10、复审边界亲证 diff 仅 Evidence 一文件）
- BLOCKED 误标：零（16 域无一被标 BLOCKED；「尚未实现」全部归 FROZEN_WITH_IMPLEMENTATION_GAP）
- 无 Evidence 虚构缺口 / 凭想象增项：零（§5 逐条溯源核验）
- Human 参数改动/重算：零（23/23 与 G2_PENDING=0 未动；DEFERRED_DEPLOYMENT_DETAIL 未升格）
- AI 越权声称：零（全文仅 G2_READY_FOR_HUMAN_SIGNOFF 口径，无 Human Accepted/PASS 声称）

## 6. 证据命令

1. `git -C <repo> diff 0caece5..20d66bb --name-status` / `git diff 20d66bb..5cc0390 --name-status` / `git diff 0caece5..5cc0390 --name-status`
2. SEC-16 四处登记：`rg -n "SEC-16|SB-04" docs/SECURITY_BASELINE.md`（§2.4/§9/§12/§14）
3. ADR-0004 注记行号：`sed -n '104,106p' docs/adr/0004-*.md`（注记在 :105）
