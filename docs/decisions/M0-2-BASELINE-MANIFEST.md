# M0.2 入库清单与基线保真核对（M0-2-BASELINE-MANIFEST）

- **步骤**：M0.2 Git 初始化与文档基线入库（`docs/plans/00_MASTER_PLAN.md` §7 M0.2；引源 01 §5 PG-S3 按修订 2/3）。
- **日期**：2026-08-18。
- **执行**：M0.2 派发 worker；仓库本地 git 身份 `peiligo-rebuild <peiligo-rebuild@localhost>`（仅本仓库 config，未改动全局）。
- **路径基准**：本仓库根 `<LOCAL_PROJECT_PATH>_restart`，下表路径均为仓库根相对路径。
- **远程**：本仓库不配置任何 remote；旧仓 `<LOCAL_PROJECT_PATH>` 为永久只读禁区（OR-2），本步骤未对其执行任何命令。

## 1. 入库清单（共 14 行 = 实际入库文件数：11 基线 + 3 新增）

SHA256 为入库前工作区实测值（`shasum -a 256`）；字节数为 `wc -c` 实测值。

| # | 路径 | 类型 | 字节数 | SHA256 |
| --- | --- | --- | --- | --- |
| 1 | `docs/PRODUCT_REQUIREMENTS.md` | 基线 | 21945 | 623393cc1378a8d47f52e53d68957f43187e94169737509fe4f13754c11cd5f6 |
| 2 | `docs/PEILIGO_REBUILD_AUDIT.md` | 基线 | 16356 | 73bd5db63beb65346800d64ab131484916c8b5903cff8630b7b5528e8d75de54 |
| 3 | `docs/audit-report-old-peiligo.md` | 基线 | 26826 | eeaa81a0d0a21ed3b41410a0da0fbe57181a62eee7667498a5735b391c80f05b |
| 4 | `docs/audit-report-wagtail-upstream.md` | 基线 | 23498 | c3cf7ce81558eadbb5339ef93d9bac3a8eb4e24abfc213e7aa6f1611c5912d7e |
| 5 | `docs/plans/00_MASTER_PLAN.md` | 基线 | 156343 | 999773299b66bac197e7a35812f0f6f499e312d55da7d8133f66cd59ee199ffb |
| 6 | `docs/plans/01_PRODUCT_GOVERNANCE_PLAN.md` | 基线 | 44622 | 9cd64e38a6d3a70fa70c74e60e132c67af48629e1bdafbafb2ab447f26960e38 |
| 7 | `docs/plans/02_ARCHITECTURE_DOMAIN_PLAN.md` | 基线 | 92620 | ca4884a0700ef6fa7d01f3aadfcfe9ec7427a8208f21cbab439ccee9f7afe16b |
| 8 | `docs/plans/03_DELIVERY_OPERATIONS_PLAN.md` | 基线 | 75992 | 5fbb3e67f2888f94fb7c06e323e6a11231c83b6dd0e77fdc70e2c5acfcc90381 |
| 9 | `docs/decisions/D0_BASELINE_CONFIRMATION.md` | 基线 | 11465 | a95213e568597f42daed63bf0d77fc850989baf4de771d35f90d48b05c3a662f |
| 10 | `docs/reviews/M00.review.md` | 基线 | 19149 | c25800240792321f06b36775fd855a5875f24b17a9ec05462482ac878edfab32 |
| 11 | `docs/reviews/M0.1.review.md` | 基线 | 11885 | ab9cf7c9c5794a4d6ee4ff04dd338821bc8333707ece4a804c6f7c612519980a |
| 12 | `.gitignore` | 新增 | 257 | 7557b12afead75b91ad80c4729b7659469b9f5de8ff533bc94ee2f2258d67555 |
| 13 | `docs/README.md` | 新增 | 2599 | 63d2e981287d9e67df972f9c36e480a3d941ad55757957c373fe0ea991ccafdb |
| 14 | `docs/decisions/M0-2-BASELINE-MANIFEST.md` | 新增 | （自引用） | （自引用例外：以 `git show HEAD:docs/decisions/M0-2-BASELINE-MANIFEST.md \| shasum -a 256` 实测为准） |

**计数口径说明**：派发契约测试注文的"12 个基线文件"= 上表 11 个在库基线文件 + 1 个 waiver 缺席文件（`docs/reviews/M00.gpt-review.md`，见 §4，不入库、不占入库行）。实际入库文件数 = 11 基线 + 3 新增 = **14**，与本清单行数一致（满足主计划 §7 M0.2 测试要求"清单行数 = 实际入库文件数"）。`D0_BASELINE_CONFIRMATION.md` L112 亦明确"入库集合以 M0.2 派发契约为准"。

## 2. 保真核对记录（字节级保真断言）

- **方法**：对每个基线文件断言「工作区 SHA256（§1 表，入库前实测）== `git show HEAD:<路径>` SHA256（提交后实测）」，并以 `git diff --stat`（工作区 vs HEAD）为空作等效佐证；逐项结果在提交后回填于附录 A 表 A-2。
- **约束**：本步骤未改动任何既有文件内容（仅 `git add` 入库 + 新增三文件）；`.DS_Store` 与 `.local_backups/` 未入库（`.gitignore` 操作性排除）。

## 3. 分支结构记录

- **建立顺序**：`main` 承载基线提交 B1（全部入库集合 + 新增三文件）→ 自 B1 创建 `rebuild/v1` → 回填提交 B2（仅更新本 manifest 附录 A）→ `rebuild/v1` 快进至 B2，最终与 `main` 同点。
- **B2 存在理由（自引用规避）**：本 manifest 须记录基线提交哈希与提交后保真核对结果，而提交哈希无法内嵌于其自身所在的提交（内容变则哈希变，无不动点），故基线信息由紧随其后的 B2 回填；B1 才是"全部入库集合 + 新增三文件"的基线提交。
- 具体哈希与最终指向：见附录 A 表 A-1（提交后回填）。
- 分支命名符合主计划修订 12（基线分支 `rebuild/v1`；本步骤不创建 `gov/`、`arch/`、`build/` 前缀分支）。

## 4. M00.gpt-review.md 缺席说明（R3_GPT_WAIVER 豁免）

M00（G0 门）按 R3 风险级本应含 GPT 压缩 Risk/Architecture Review 记录 `docs/reviews/M00.gpt-review.md`；该文件**不存在**——G0 条件②已按一次性 `R3_GPT_WAIVER` 豁免（四要素 TASK/REASON/HUMAN_APPROVAL/DATE 原文记录于 `docs/decisions/D0_BASELINE_CONFIRMATION.md` §条件②，L17 起；waiver 一次性、不可复用、不可泛化）。故该文件不入库、不占 §1 入库行，仅在此说明。

## 5. .gitignore 口径

- **含**：`poc/`、`.env`、`.env.*`（覆盖 `.env` 与 `.env*` 模式）、`__pycache__/`、`*.sqlite3`、`media/`，另加操作性排除 `.DS_Store`、`.local_backups/`（非基线内容）。
- **不含**：`docs/ai/` 忽略行——FIX-03/v1.4：D8（M0.3）尚未裁决，M0.2 不得预先写死；该行由 M0.3 依 D8 裁决结果调整。

## 6. 秘密扫描记录（00_MASTER_PLAN §4.5 v1.2 正则，双分支）

- 提交前对 `docs/` 全量扫描：**零命中**（grep 退出码 1，无输出；实测 2026-08-18）。
- 对将入库新增内容扫描（`docs/README.md`、本 manifest 随 `docs/` 扫描；根目录 `.gitignore` 单独扫描）：**零命中**。
- 提交后对入库全历史的扫描结果：见附录 A（提交后回填）。
- 本 manifest 不复写 §4.5 正则原文（按"路径 + 字段名"口径引用主计划 §4.5）。

## 附录 A：提交后回填记录（由回填提交 B2 写入；实测于 2026-08-18）

### 表 A-1 分支与提交结构

| 项 | 值 |
| --- | --- |
| 基线提交 B1（`main`） | `e82c32aa698ce3afbf800c58b8ec97dc6b17d688`（"Baseline: intake governance docs (M0.2)"，root-commit，14 文件、4966 行插入，含全部入库集合 + 新增三文件） |
| 回填提交 B2（`main`，本提交） | 仅更新本 manifest 附录 A（自引用规避理由见 §3；不触碰其余 13 个文件） |
| `rebuild/v1` | 自 B1 建立（`git branch rebuild/v1 B1`），B2 后快进至与 `main` 同点（`git branch -f rebuild/v1 main`，快进、无历史改写） |
| remote | 无（`git remote -v` 为空；OR-2——旧仓为永久只读禁区且不配置任何指向它的 remote） |
| git 身份 | 仓库本地 `user.name=peiligo-rebuild`、`user.email=peiligo-rebuild@localhost`（`git config --local`，全局配置未改动） |

### 表 A-2 保真核对（11/11 全等）

方法见 §2：`git show B1:<路径>` 的 SHA256 与字节数逐项对照 §1 表的入库前工作区实测值，全部相等；工作区 vs HEAD 的 `git diff --stat` 为空；`git status --porcelain` 为空。

| 路径 | SHA256（HEAD 版 = 入库前工作区版，全等） | 字节数 | 核对 |
| --- | --- | --- | --- |
| `docs/PRODUCT_REQUIREMENTS.md` | 623393cc1378a8d47f52e53d68957f43187e94169737509fe4f13754c11cd5f6 | 21945 | 全等 |
| `docs/PEILIGO_REBUILD_AUDIT.md` | 73bd5db63beb65346800d64ab131484916c8b5903cff8630b7b5528e8d75de54 | 16356 | 全等 |
| `docs/audit-report-old-peiligo.md` | eeaa81a0d0a21ed3b41410a0da0fbe57181a62eee7667498a5735b391c80f05b | 26826 | 全等 |
| `docs/audit-report-wagtail-upstream.md` | c3cf7ce81558eadbb5339ef93d9bac3a8eb4e24abfc213e7aa6f1611c5912d7e | 23498 | 全等 |
| `docs/plans/00_MASTER_PLAN.md` | 999773299b66bac197e7a35812f0f6f499e312d55da7d8133f66cd59ee199ffb | 156343 | 全等 |
| `docs/plans/01_PRODUCT_GOVERNANCE_PLAN.md` | 9cd64e38a6d3a70fa70c74e60e132c67af48629e1bdafbafb2ab447f26960e38 | 44622 | 全等 |
| `docs/plans/02_ARCHITECTURE_DOMAIN_PLAN.md` | ca4884a0700ef6fa7d01f3aadfcfe9ec7427a8208f21cbab439ccee9f7afe16b | 92620 | 全等 |
| `docs/plans/03_DELIVERY_OPERATIONS_PLAN.md` | 5fbb3e67f2888f94fb7c06e323e6a11231c83b6dd0e77fdc70e2c5acfcc90381 | 75992 | 全等 |
| `docs/decisions/D0_BASELINE_CONFIRMATION.md` | a95213e568597f42daed63bf0d77fc850989baf4de771d35f90d48b05c3a662f | 11465 | 全等 |
| `docs/reviews/M00.review.md` | c25800240792321f06b36775fd855a5875f24b17a9ec05462482ac878edfab32 | 19149 | 全等 |
| `docs/reviews/M0.1.review.md` | ab9cf7c9c5794a4d6ee4ff04dd338821bc8333707ece4a804c6f7c612519980a | 11885 | 全等 |

结论：**保真断言 11/11 通过**，既有文件零改动（仅 `git add` 入库）。

### 全历史秘密扫描

- 对基线提交 B1 全树（= 全部入库内容，含新增三文件）执行 §4.5 v1.2 正则扫描（`git grep` 于 B1）：**零命中**（退出码 1，无输出）。
- 含 B2 自身在内的完整历史（`git rev-list --all`）复扫无法把"含本提交的时点结果"内嵌于本提交——按主计划 M0.2「独立实现·测试·安全审查」由独立审查亲自复跑核定；B2 仅改动本 manifest 且本文件已单独通过同一正则扫描。

### 最终验收状态（B2 后口径）

| 验收命令 | 期望 | 说明 |
| --- | --- | --- |
| `git rev-parse --is-inside-work-tree` | `true` | ✓ |
| `git status --porcelain` | 空 | 工作区干净（`.DS_Store`/`.local_backups/` 由 `.gitignore` 排除） |
| `git branch --list main rebuild/v1` | 恰好两行 | 两分支同点（B2） |
| `git log --oneline -1` | 有提交 | `log -1` 显示 B2（回填提交），基线提交 B1 为其直接父提交（全历史共两提交） |
| 基线文件 `git diff --stat` | 空 | 表 A-2 逐项 SHA256 全等佐证 |
| `grep -E "poc/\|\.env" .gitignore` | 有命中；`grep -q "docs/ai" .gitignore` 无命中 | §5 口径 |
| §4.5 扫描 `docs/` | 零命中 | 本节上文记录 |

（注：本附录写于 B2 提交前；表中"B2 后"各项由 B2 提交与 `rebuild/v1` 快进两个动作即时成立，独立审查复跑核定。）
