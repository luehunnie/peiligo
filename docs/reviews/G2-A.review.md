# G2-A 独立审查报告（G2 Human 决策落档与文档一致性整理）

## 结论：PASS（经一轮修复）

- 审查对象：`arch/g2-a-human-decisions` @ `5bfe166`（初轮）；修复轮 `b869021`（复核轮）
- 基线：`main` @ `2984b20`（2984b20c95f0416a6fa570969f71b4109827d58a，M7.2 审查记录合并点）
- 审查者：独立 GLM 新会话（fresh-context subagent，不继承实现上下文；00_MASTER_PLAN §4.6 双口径）
- 审查日期：初轮 2026-08-31；复核轮 2026-09-01
- 变更文件（全程）：`docs/G2_HUMAN_DECISIONS.md`（新增）、`docs/SECURITY_BASELINE.md`、`docs/NON_FUNCTIONAL_REQUIREMENTS.md`、`docs/INFORMATION_ARCHITECTURE.md` —— 仅 docs/，零代码/settings/模板变更
- 初轮判定：**FAIL**（两处一行级必修残留 + 3 项建议；核心落档工作本身合格）
- 复核判定：**PASS**（必修①②与建议 3 项全部落实；范围与值核对通过）

> 本记录由实现会话依审查者两轮报告整理；§3 复核轮结论逐字取自审查者复核回复。

## 1. 初轮审查（@ 5bfe166，2026-08-31）

### 1.1 检查项结果

| # | 检查项 | 结果 |
| --- | --- | --- |
| 1 | 23 项 Human 决策（Q1–Q23，2026-08-31）全部落档，无遗漏、无重新询问、无自行改值 | ✅ |
| 2 | 确认值与 Human 原文数值逐字一致（20 MiB、12 字符、10 次/15 分钟、24h、1 年、≤30、≤10,000、12h、季度、200 KiB、3 条、30 天、Lax/Secure/HttpOnly、p50<1s/p95<2s、≤2s、5 分钟、<20%/<10%、30 天、100 并发、RTO≤4h） | ✅ |
| 3 | `G2_PENDING_PARAMETERS = 0` 三处一致（NFR §12 集中表、`G2_HUMAN_DECISIONS.md` 计数行、SB §13） | ✅ |
| 4 | `DEFERRED_DEPLOYMENT_DETAIL` 分类合理（PP-07/18/19/20/21/22 六项＝工程默认或部署细节；Q9 介质、Q10 CPU/RAM/IP/路径/VM·CT 同类；不冒认 HUMAN_CONFIRMED） | ✅ |
| 5 | 全文数值标注一致性（确认值出现处不得残留与确认值矛盾的未标注旧值） | ❌ → 必修①②（见 §1.2） |
| 6 | archive/noindex 口径与 PUBLISH §7 三消费位一致（M7.2 F-1 修复路径正确：HISTORICAL 归档视图＋ARCHIVE-SEARCH 搜索态＋具名 URL 直达；归档视图 noindex 义务已登记 NFR §3.2） | ✅ |
| 7 | 代码边界：`git diff 2984b20..5bfe166 --name-status` 仅 4 个 docs 文件 | ✅ |
| 8 | 无实现虚标：参数确认未改变四值实现状态标签（SATISFIED/PARTIAL/NOT_IMPLEMENTED/NEEDS_VERIFICATION 未因 G2-A 上调） | ✅ |

### 1.2 必修项（初轮 FAIL 事由；均一行级残留）

- **必修①** `docs/SECURITY_BASELINE.md` §2.3 设计要点（:104）：残留 `AXES_FAILURE_LIMIT=5` 而未标注被 Q3 确认值取代（紧邻 :103 已有正确确认句）。
- **必修②** `docs/NON_FUNCTIONAL_REQUIREMENTS.md` §1.3 p95 行（:65）与 NF-08 Pass condition（:388）：写作「搜索逐条 p95 ≤ 2s（Q17）」，Human 确认值为 **< 2s**（PP-23 :516 记录正确）。

### 1.3 建议项（非阻断）

1. `INFORMATION_ARCHITECTURE.md` :239「V1 默认槽位数由实现阶段在配置中给定并留痕，不写入本架构」与 :240 Q14 确认注（最多 3 条）存在字面张力，建议补「随 Q14 确认更新」。
2. NFR §12 PP-20（:513，日志保留期工程默认 ≤90 天）：建议部署评审时项目负责人复核一次。
3. NFR 文档信息 G2-A 行（:16）M7.2 修复注记仅列 F-1/F-2/F-4，建议补全 F-3/F-5/F-6。

## 2. 修复轮（b869021，2026-09-01）

| 修复 | 落点 |
| --- | --- |
| 必修① | SB §2.3 设计要点改 `AXES_FAILURE_LIMIT=10`（15 分钟窗口内 10 次）＋`AXES_COOLOFF_TIME=15 分钟`＋成功清零，显式标注「原示例值 5 已被 Q3 确认值取代」；axes 参数精确映射随 B 阶段接入留痕（SB:106 仍 `NOT_IMPLEMENTED`，无虚称实现） |
| 必修② | NFR :65 搜索逐条 p95 统一为「< 2s——Human 已确认（Q17）」；页面服务端 p95 ≤ 2s 显式标注「派生方法口径（非 Human 单独确认值）」；NF-08:388 Pass condition 改「p95 < 2s（Q17）」，与 PP-23:516 一致 |
| 建议1 | IA:239 改「V1 默认槽位数已经 Human 确认（2026-08-31，Q14）＝最多同时生效 3 条（见下注）；实现阶段在配置中给定并留痕」 |
| 建议2 | NFR PP-20 行增注「建议部署评审时项目负责人复核一次」 |
| 建议3 | NFR :16 补全为「M7.2 审查 F-1/F-2/F-3/F-4/F-5/F-6」 |

## 3. 复核结论（@ b869021，2026-09-01；审查者回复要点）

1. **必修① PASS** — SB:104 数值语义已改 Q3 确认值并显式标注取代关系；无虚称实现。
2. **必修② PASS** — NFR:65 与 NF-08:388 统一为确认值「< 2s（Q17）」；页面侧 ≤ 2s 已标注派生方法口径，与 PP-23:516 一致。
3. **建议1 PASS** — IA:239 张力消除，与下注及台账 Q14 对齐。
4. **建议2 PASS** — PP-20 复核提示在档。
5. **建议3 PASS** — F 注记补全。

**范围与值核对 PASS** — `git diff 5bfe166..b869021 --name-status` 仅 3 个 docs 文件（IA/NFR/SB；台账未动）；全量 diff 仅触及上述 5 处，Q3 确认句（SB:103）、Q17 确认值（NFR:64-65、PP-23）逐字未变，无值漂移、无新增冒认。

**总判定：PASS**

## 4. 阻断性检查（两轮均零命中）

- 非 docs 文件变更：零（§1.1 #7、§3 范围核对）
- 确认值人为改动/重新询问/自造数值：零（Q1–Q23 与 Human 2026-08-31 原文逐字一致）
- 正式文档互相矛盾：未发现（archive/noindex 三消费位口径对齐 PUBLISH §7；未触发「停止并报告 Human」条款）
- 实现状态虚标：零（G2-A 未上调任何四值标签）

## 5. 证据命令

1. `git -C <repo> diff 2984b20..5bfe166 --name-status` / `git diff 5bfe166..b869021 --name-status` / `git diff 2984b20..b869021 --name-status`
2. 残留扫描：`grep -n AXES_FAILURE_LIMIT docs/SECURITY_BASELINE.md`（仅存于取代标注）；`grep -n 'p95 ≤ 2s' docs/NON_FUNCTIONAL_REQUIREMENTS.md`（仅剩 :65 派生口径标注与 PP-23 RECOMMENDATION 历史列两处合法保留）
3. 台账核对：`docs/G2_HUMAN_DECISIONS.md` 计数行（23/23 HUMAN_CONFIRMED，G2_PENDING_PARAMETERS=0）
