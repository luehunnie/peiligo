# G2 冻结一致性检查（G2_FREEZE_EVIDENCE）

- **步骤**：G2-B · 项目冻结一致性检查（治理＋文档一致性＋阶段冻结检查；非开发任务）
- **日期**：2026-09-01；**G2_B_BASELINE**：`main` @ `0caece5`（0caece5c148346654552df998941dd807d28c482，G2-A 合并点）
- **边界**：本轮仅允许修改 `docs/`；不 push、不 PR；生产代码零变化
- **性质**：本文是冻结检查 Evidence，不复制 Security/NFR 文档正文；所有结论附证据指针

## 1. BASELINE（§2 Safety Check 实测 2026-09-01）

| 项 | 值 |
| --- | --- |
| branch | `main`（working tree clean） |
| local main | `0caece5`（HEAD = main = G2-A 合并提交） |
| origin/main | `cd6eca0`（= merge-base → origin/main 是 local main 祖先，无未知分叉） |
| behind / ahead | 0 / **12**（ahead 内容＝M7.1/M7.2 审查记录＋G2-A 四文档＋G2-A 审查记录，共 7 个 docs 文件，已逐一核对 `git diff origin/main..main --name-only`） |
| G2-A 状态 | 23/23 HUMAN_CONFIRMED、G2_PENDING_PARAMETERS=0、noindex 一致性 RESOLVED、生产代码零变化（`docs/reviews/G2-A.review.md` PASS 在案） |

结论：同步状态正常（M7＋G2-A 未 GitHub 收口属已知正常态），无异常，继续 G2-B。

## 2. ADR_STATUS_MATRIX（§6）

| ADR | STATUS | DECISION_SUMMARY | CONSISTENT |
| --- | --- | --- | --- |
| ADR-0001 | Accepted（2026-08-18 G1 门项目负责人批准） | 版本组合冻结：Wagtail 7.4.x LTS ＋ Django 5.2 LTS ＋ Python 3.13 | YES——与 C1 锁定口径及 SB §3 实测（Django 5.2.17）一致 |
| ADR-0002 | Accepted（2026-08-18 G1） | 前端架构＝Wagtail 服务端模板；关键内容不依赖 JS；meta/noindex 由模板与页面机制控制 | YES——NFR §1.3/§2 与 ADR-0002 引用一致 |
| ADR-0003 | Accepted（2026-08-18 G1＝D2 正式裁决） | 全新干净 Wagtail 骨架、settings 分层（base/dev/production/test）、不迁移旧数据 | YES——canonical `src/peiligo` 骨架与 settings 分层在库（SB §3.2/§5 引证） |
| ADR-0004 | Accepted（2026-08-18 G1） | 部门权限容器树：容器＝权限挂载点＋路由分组，前台 404，任何部门不建主页 | YES——M4.3 T01–T16 16/16＋IA §3/§8 禁令对照逐维一致 |
| ADR-0005 | Accepted（2026-08-18 G1） | 公开内容＝Page 树载体；受控数据（部门/词表/标签/推荐位/站点设置）＝Snippet·Settings，无公开独立 URL | YES——CM §13 与 IA §5 载体表一致 |
| ADR-0006 | Accepted（2026-08-31 M6.3 落盘、同日 G2 门项目负责人签收转 Accepted） | 中文搜索后端 SELECTED=E1（icontains 语义）；独立搜索服务评估 NOT REQUIRED；接受已知限制，生产正式接线后执行 §11.4 复验门方可视为生效 | YES——POC §6 D7 裁决逐字段转录、NFR §11 状态边界（选型 Accepted ≠ 实现已发生）自洽 |

- 六份 ADR 状态变更决策人均为项目负责人/门记录（`docs/adr/README.md` §4 代理不得代决）；无状态互相覆盖而未说明；**无两个 Accepted ADR 对同一问题给出相反结论**。
- 本轮不改任何 ADR（不重新设计）。

## 3. FREEZE_MATRIX（§7；FROZEN＝规则明确且实现基本对齐；FROZEN_WITH_IMPLEMENTATION_GAP＝规则与验收明确、实现未完；BLOCKED＝存在必须由 Human 决定的设计问题）

| 领域 | 分类 | 依据（证据指针） |
| --- | --- | --- |
| ARCHITECTURE | FROZEN | ADR-0001/0002/0003 Accepted；骨架/settings 分层/依赖锁定已实现并在库（SB §3/§5 引证 `base.py`/`production.py`） |
| INFORMATION_ARCHITECTURE | FROZEN_WITH_IMPLEMENTATION_GAP | IA §1–§13 冻结且树结构已实现（A2.1/A2.2 实现审查 PASS）；单篇 noindex 字段、跳转页、sitemap 终态属 MB12/MB13 未实现（NFR §3.3 PARTIAL） |
| CONTENT_MODEL | FROZEN | CM §1–§23 终判冻结；模型实现并经审查（A3.1–A3.3）、clean 族在库（SB §10-3）；Q14 推荐位数量＝B 阶段配置留痕项，非设计缺口 |
| PERMISSION_MODEL | FROZEN | 矩阵 §0–§6 冻结；T01–T16 16/16（M4.3）＋M4-SECURITY-REVIEW PASS＋ADR-0004 验证证据回写 |
| PUBLISH_LIFECYCLE | FROZEN_WITH_IMPLEMENTATION_GAP | PUBLISH §1–§5 语义冻结（go_live_at/expire_at/publish_scheduled 7.4.2 真实行为源码为证）；§6.1 历史归档视图 URL 留 B 阶段未实现 |
| ARCHIVE | FROZEN_WITH_IMPLEMENTATION_GAP | 三消费位口径冻结（PUBLISH §7＋NFR §3.2 G2-A 对齐）；板块历史归档视图未实现（noindex 义务随 MB8–MB9 验收登记） |
| SEARCH | FROZEN_WITH_IMPLEMENTATION_GAP | ADR-0006 Accepted＋搜索契约已实现（`search/services.py`＋契约测试族）；E1_PRODUCTION_WIRING=NOT_IMPLEMENTED（NFR §11） |
| UPLOAD_RULES | FROZEN_WITH_IMPLEMENTATION_GAP | PRD §11 白名单与 Q1=20 MiB 已确认；settings 仍 10MB 未对齐（`base.py:262`）、魔数校验未实现（SB §4.2 ③、SEC-17/18） |
| EXTERNAL_LINK_RULES | FROZEN_WITH_IMPLEMENTATION_GAP | §10-7 规则 1–7 冻结；scheme 收窄未落（SEC-20 PARTIAL）、确认跳转页未实现（SB-06/SEC-21 NOT_IMPLEMENTED） |
| PERFORMANCE_TARGETS | FROZEN_WITH_IMPLEMENTATION_GAP | NFR §1 口径冻结＋Q13/Q17/Q18/Q22 确认；测量环境未建、零实测（NFR §1.7 NOT_IMPLEMENTED） |
| ACCESSIBILITY_TARGETS | FROZEN_WITH_IMPLEMENTATION_GAP | NFR §2 范围/方法/九项必查冻结；axe 扫描与键盘走查未执行（NEEDS_VERIFICATION） |
| SEO | FROZEN_WITH_IMPLEMENTATION_GAP | IA §10 八行位点＋断言冻结（G2-A 复核一致）；noindex 字段/sitemap 生成终态未实现（IA-09/12 挂 MB12/MB13） |
| PRIVACY | FROZEN_WITH_IMPLEMENTATION_GAP | PRD §12 四项最小数据＋四禁止冻结；无统计/追踪代码＝合规现状；日志框架与保留期未配置（PP-20 DEFERRED＋NFR §4.5 PARTIAL） |
| BACKUP_RECOVERY | FROZEN_WITH_IMPLEMENTATION_GAP | Q9/Q11/Q12/Q21/Q23 口径与 §5.5 模板/Evidence 要求冻结；无生产环境、无备份任务、演练未执行（NFR §5.7 NOT_IMPLEMENTED） |
| MONITORING | FROZEN_WITH_IMPLEMENTATION_GAP | §6 六项口径冻结（Q3/Q19/Q20）；settings 无 LOGGING、无告警接线（NOT_IMPLEMENTED，B6/MB15 落地） |
| PRODUCTION_ENVIRONMENT_BASELINE | FROZEN_WITH_IMPLEMENTATION_GAP | Q10 架构基线（PVE＋Docker Compose＋PostgreSQL＋Caddy/HTTPS＋持久化）已确认；生产环境未建、`SECURE_*`/cookie 未接线（PP-19 部署细节 DEFERRED） |

**BLOCKED 领域：0。**「尚未实现」项全部属于 FROZEN_WITH_IMPLEMENTATION_GAP（规则与验收方式已明确），无一领域存在必须由 Human 决定的设计问题。

## 4. HUMAN_PARAMETERS（§8 机械核对）

- `docs/G2_HUMAN_DECISIONS.md`：Q1–Q23 **23/23 = HUMAN_CONFIRMED**，确认日期均＝2026-08-31（表行 23＋计数行「23/23」核对一致）。
- **G2_PENDING_PARAMETERS = 0**：三处在案一致（`G2_HUMAN_DECISIONS.md:31`、NFR §12 头注与 ：518 计数行、SB §13 头注 ：500）。
- NFR §12 集中表：HUMAN_CONFIRMED 17 项＋DEFERRED_DEPLOYMENT_DETAIL 6 项（PP-07/18/19/20/21/22）＝23；部署细节（CPU/RAM/IP/具体磁盘目录/具体 NAS/对象存储/具体 VM·CT）未计入 G2 Pending——口径正确，无重算。

## 5. IMPLEMENTATION_GAPS（§9；只收有正式 Evidence 的未完成项）

| # | Gap | Evidence |
| --- | --- | --- |
| 1 | E1_PRODUCTION_WIRING | NFR §11.2 `NOT_IMPLEMENTED`（`base.py:234` 仅通用 database 后端；`SELECTED_SEARCH_BACKEND` 零命中；ADR-0006 选型 Accepted ≠ 实现已发生） |
| 2 | UPLOAD_SIZE_ENFORCEMENT | SB §4.1/§13#1：`base.py:262` 仍 10MB，Q1=20 MiB 待 MB 阶段对齐 |
| 3 | MIME_VALIDATION / 4. FILE_SIGNATURE_VALIDATION | SB §4.2 层②无显式校验、层③魔数未接入（SEC-18 `NOT_IMPLEMENTED`） |
| 5 | EXTERNAL_REDIRECT_CONFIRMATION | SB §12/§14：跳转页未实现（SB-06/SEC-21；PRD §23 必测） |
| 6 | PRODUCTION_COOKIE_CONFIGURATION | SB §3.2 ★：`SESSION/CSRF _COOKIE_SECURE`、`SECURE_*` 一族未接线（目标值已确认 Q16/Q5/Q6/Q10） |
| 7 | LOGIN_RATE_LIMIT | SB §2.3：axes 未安装（SEC-15 `NOT_IMPLEMENTED`；Q3 参数已确认） |
| 8 | HSTS_FINAL_CONFIGURATION | SB §3.2/§14：SEC-24 未达标（Q5 先短后长，目标 1 年） |
| 9 | FEATURED_COUNT / EXPIRY_ALIGNMENT | IA §7.2：Q14（最多 3 条）/Q15（默认 30 天）已确认，随 MB8 配置留痕落地 |
| 10 | PERFORMANCE_VALIDATION | NFR §1.6/§1.7：测量环境未建、NF-01/02/07/09 零实测 |
| 11 | 100_CONCURRENT_USER_VALIDATION | NFR NF-08（PP-10=100 并发活跃用户）未执行 |
| 12 | ACCESSIBILITY_VALIDATION | NFR NF-03/04/10 未执行（axe＋键盘走查） |
| 13 | SEO_FINAL_ALIGNMENT | NFR NF-06/11：单篇 noindex 字段、sitemap 生成终态、跳转页未实现（MB12/MB13） |
| 14 | BACKUP_AUTOMATION / 15. BACKUP_SCHEDULE | NFR §5.1/NF-13：Q11 每 12 小时配套备份未实现（部署阶段） |
| 16 | BACKUP_RETENTION / 17. INDEPENDENT_BACKUP_COPY | NFR §5.6：Q21 保留 ≥30 天、Q9 本地副本＋独立存储副本未落地（介质 DEFERRED） |
| 18 | RESTORE_DRILL | NFR §5.4/§5.5/NF-05：季度演练与 RTO≤4h（Q12/Q23）未执行 |
| 19 | HEALTH_CHECK | NFR §6 行 1/NF-14：Q19 每 5 分钟拨测未落地 |
| 20 | MONITORING / 21. DISK_ALERT / 22. SCHEDULER_MONITORING | NFR §6：六项口径冻结但全部 `NOT_IMPLEMENTED`（含 Q20 磁盘阈值、publish_scheduled 告警 NF-16） |
| 23 | STRUCTURED_LOGGING | SB §6.2/NFR §4.3：settings 无 LOGGING 配置（事实），保留期 PP-20 工程默认随部署落地 |
| 24 | CI | SB §5/§12：CI 未建（MB15 承接：secret 扫描＋依赖检查） |
| 25 | CONTAINER / CADDY FINALIZATION | NFR §1.1：Q10 架构基线已确认；生产容器/Caddy/域名证书（PP-19）部署阶段落实 |

禁止凭想象增项：以上每项均有 SB/NFR/ADR/Mapping 正式出处；未发现列表之外的证据支持项。

## 6. ARCHITECTURE_DECISIONS_PENDING（§3-2/§9 交叉）

- **未解决的产品/架构设计决策：0。**G2 门 D0–D9 十决策全部处置在案（M00 审查 §A2 核对：D7→M6.3/ADR-0006 已收口，其余按各门落点完成）；六个 ADR 全部 Accepted 且自洽（§2）。
- **治理线残留（须 Human 在 G2 签收时处置，非设计阻塞）**：计划治理线步骤 **M0.3–M0.7**（AI_WORKFLOW＋D8 裁决、TASK_TEMPLATE、SECRETS_POLICY、CHANGE_MANAGEMENT、PHASE_GATES＋G2 治理确认包）在 canonical 与历史仓均无产物＝未执行（`docs/decisions/M0-2-BASELINE-MANIFEST.md:51` 明示 D8 未裁决；`docs/governance/` 不存在；reviews 无 M0.3–M0.7 记录）。项目实际按 D8 裁决前缺省运行（审查记录入 `docs/reviews/`——实际发生，32 份在案），且 00 §15 G2 触发条件含「M0.7 完成」→ **门条件⑧残留**，处置选项（执行/书面豁免/裁定已被 Rolling Implementation 路径实质取代）由项目负责人签收时定。另 00 §15 条件⑥「产出位于 peiligo_restart rebuild/v1」字面已被 SSOT 迁移取代（三方审计 2026-09-01 定论 canonical=peiligo；全部产出已在 canonical main 提交）——属已记录的历史性取代，非未决设计。

## 7. PROCESS_DEVIATION（§5）

- **expected**：独立可见 Orca Session `G2-B-freeze-evidence`（GLM-5.3）＋独立复核会话 `G2-B-freeze-review`＋可选 `G2-B-final-review`（GPT-5.6 Sol/Codex）。
- **actual**：本环境无 Orca Run/task 派发机制（G2-A 轮已实证：`orchestration dispatch` 需既有终端句柄、`worker-start` 需 Run/task，均不可用；MAX_ACTIVE_SESSION=1）。本会话执行冻结检查；独立复核由 **fresh-context 独立 GLM 子会话**承担（不继承实现上下文，对齐 00 §4.6 独立审查精神）；GPT/Codex 最终复核视本环境可用性执行，不可用则如实记录为未执行。
- **independence preserved: YES**（实现面=本会话；复核面=无实现上下文的独立会话；G2-A 同模式已运行一轮并被接受）。

## 8. G2_MECHANICAL_RESULT（00 §15 ＋ 02 §10 通过条件逐条）

| 条件 | 状态 | 说明 |
| --- | --- | --- |
| ① 八份文档＋ADR-0001–0006 状态正确 | **满足** | 八份全在 canonical `docs/`（IA/CM/矩阵/PUBLISH/SB/NFR/POC 权限/POC 搜索）；ADR 0001–0006 全 Accepted（§2） |
| ② T01–T16 16/16 或书面豁免 | **满足** | M4.3 16/16（SB §0.2、M4-SECURITY-REVIEW、POC_PERMISSION_REPORT 引证） |
| ③ ADR-0006 结论明确 | **满足** | Accepted（2026-08-31 签收）；SELECTED=E1、独立服务 NOT REQUIRED（§2） |
| ④ 可追溯性抽查无孤儿 | **满足（抽查口径）** | M7.2 审查 D1 系列（PRD §12–§17 逐条）＋G2-A 审查（文档一致性）在案；全量追溯审计不在 G2-B 范围 |
| ⑤ 待确认参数表逐项确认清零 | **满足** | G2_PENDING_PARAMETERS=0（§4） |
| ⑥ 全部产出已提交 | **满足（实质；字面已被取代）** | 字面指向 peiligo_restart rebuild/v1，已被 SSOT 迁移取代；全部产出在 canonical main 已提交（§1） |
| ⑦ 防扩围对照清零 | **满足（抽查口径）** | 02 附录 B 禁项：历轮审查（M7.2 D1、G2-A）零命中；IA §8.3 部门主页禁令对照在案 |
| ⑧ 治理输入（G2-GOVERNANCE-PACKAGE 验收输出、治理线审查记录、D8 落档） | **未满足（字面）** | M0.3–M0.7 未执行、D8 未裁决、PHASE_GATES/G2 治理包文件不存在（§6 治理线残留）；治理线 S1 审查在案（A1.1），其余 6 份计划口径记录缺 |

**机械结论**：①–⑤⑦ 满足，⑥ 实质满足（字面取代已记录），⑧ 未满足（治理线残留）→ G2 最终签收为 Human 职权（HUMAN_FINAL_SIGNOFF_REQUIRED=YES），签收时须对 ⑧ 残留作出处置。

## 9. POST_G2_MODE（§10）

**READ_ONLY_GAP_AUDIT_FIRST**——下一阶段不得原样重跑 MB1–MB18：canonical 已实现 MB 计划的相当部分（工程基座 A1、结构/前台 IA A2.1–A2.3、内容模型 A3.1–A3.3、权限与安全 M4 系、搜索契约、T01–T16 16/16），原样重跑将重复开发已完成功能。正确顺序：先做**只读 Implementation Gap Audit**，逐项判定 DONE / PARTIAL / NOT_DONE / OBSOLETE（以本文件 §5 清单＋SB §12/§14、NFR §13 Mapping 为底册），然后只实现 PARTIAL / NOT_DONE 项。本轮不开始 Gap Audit、不进入实现。
