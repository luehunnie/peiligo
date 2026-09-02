# Peiligo 重建文档索引（M0.2 基线）

- **路径基准**：本仓库根 `<LOCAL_PROJECT_PATH>_restart`，下表路径均为仓库根相对路径。
- 本文件为 M0.2 新增的文档索引；入库完整性与字节级保真凭据见 `docs/decisions/M0-2-BASELINE-MANIFEST.md`。
- `docs/reviews/M00.gpt-review.md` 不存在：G0 条件②（R3 级 GPT 压缩审查）已按一次性 R3_GPT_WAIVER 豁免（四要素记录见 `docs/decisions/D0_BASELINE_CONFIRMATION.md` §条件②）。

## PRD（产品需求）

| 文档 | 用途 |
| --- | --- |
| `docs/PRODUCT_REQUIREMENTS.md` | Peiligo 网站重建产品需求文档——V1 需求基线与范围权威来源。 |

## 审计

| 文档 | 用途 |
| --- | --- |
| `docs/PEILIGO_REBUILD_AUDIT.md` | Peiligo V1 重建综合只读审计报告——三份明细审计之上的重建决策依据。 |
| `docs/audit-report-old-peiligo.md` | 旧 peiligo 仓库只读审计报告——V1 需求基线核对、前端复用分类、骨架路径比较。 |
| `docs/audit-report-wagtail-upstream.md` | Wagtail 上游框架只读审计报告——版本核验、扩展点映射、结构建议。 |

## 计划

| 文档 | 用途 |
| --- | --- |
| `docs/plans/00_MASTER_PLAN.md` | 00 主计划——全阶段、全步骤唯一执行计划（M0.2 的引源）。 |
| `docs/plans/01_PRODUCT_GOVERNANCE_PLAN.md` | 01 产品与治理基线计划——治理线步骤（PG-S*）的源计划。 |
| `docs/plans/02_ARCHITECTURE_DOMAIN_PLAN.md` | 02 架构与领域计划——架构线步骤与领域模型设计源计划。 |
| `docs/plans/03_DELIVERY_OPERATIONS_PLAN.md` | 03 交付与运维实施规划——从干净项目骨架到正式上线的交付/运维源计划。 |

## 决策

| 文档 | 用途 |
| --- | --- |
| `docs/decisions/D0_BASELINE_CONFIRMATION.md` | D0 基线确认记录与决策台账——G0 批准固化（含 PRD 最终确认引用与 R3_GPT_WAIVER 四要素）。 |
| `docs/decisions/M0-2-BASELINE-MANIFEST.md` | M0.2 入库清单与保真核对记录——本次 Git 基线的完整性凭据。 |

## 审查

| 文档 | 用途 |
| --- | --- |
| `docs/reviews/M00.review.md` | M00 独立审查报告——00_MASTER_PLAN v1.4（G0 前最终稿）的独立审查记录。 |
| `docs/reviews/M0.1.review.md` | M0.1 独立审查报告——D0_BASELINE_CONFIRMATION（G0 批准固化产物）的独立审查记录。 |

---

索引覆盖：上表 12 个在库文档（11 个 M0.2 基线文件 + 本 manifest）+ 本索引自身；后续步骤（M0.3 起新增文档）应由对应步骤同步更新本索引。
