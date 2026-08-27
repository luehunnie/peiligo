# M4.4 权限正式实现 · 最终安全评审报告（合并门判定）

| 字段 | 值 |
| --- | --- |
| 审查对象 | `m4/a4-4-formal-implementation@3e858a2`（基线 `main@50b60fc`；评审 diff = `git diff main...HEAD`，12 文件 +2423/-1，全部落在 `departments/` 与 `tests/`） |
| 审查载体 | `m4/a4-4-security-review@3e858a2`（本分支；评审产出单 commit，不改实现、不 push） |
| 权威依据 | `docs/ROLE_PERMISSION_MATRIX.md`（取自 `m4/a4-1-permission-matrix@aac91a0`，`git show` 亲读全文 507 行）；M4.3 `docs/POC_PERMISSION_REPORT.md`（16/16）；实现者工作报告 `/tmp/a4-4-work-report.md`（已通读，零采信——全部验收由本审查独立复跑） |
| 评审日期 | 2026-08-27 |
| **结论** | **PASS（可合并）**——六项评审全绿，无阻断项；非阻断遗留 6 项登记于 §7（与实现者 OPEN_ITEMS 一致，均经本审查独立复核定性） |

## 0. 环境亲证（README 自建）

- 本 worktree 自建 `.venv`（Python 3.13.11；`python3.13 -m venv` 经 pyenv 3.13.11 显式路径）；`pip install -r requirements*.txt && pip install -e .`。
- **`peiligo.__file__` = `/Users/chenjunxian/vscode_projects/peiligo/.worktrees/a4-4-security-review/src/peiligo/__init__.py`**（亲证指本 worktree）。
- 版本钉版亲证：Wagtail 7.4.2 / Django 5.2.17 / modelsearch 1.3.2 / psycopg 3.3.4（`pip list` 与 ADR-0001 一致）；`pip check` 无破损依赖。
- 数据库纪律：`DATABASE_URL→peiligo_restart_dev`（migrate no-op；幂等探针全程 `transaction.set_rollback` 零持久变更）；`TEST_DATABASE_URL→peiligo_restart_test`（pytest-django 自建自清，输出含 Creating/Destroying test database）。`peiligo_dev`/`peiligo_test` **零触碰、零 DROP**（本审查全程唯一 psql 操作为只读 `SELECT datname`）。

## 1. T01–T16 全量复跑 — PASS（16/16）

`pytest tests/test_permissions_*.py -v` → **62 passed + 18 subtests, exit 0, 40.18s**。逐条对矩阵 §6（五要素：编号/覆盖/前置/步骤/预期）人工核对，映射完整、断言口径忠实：

| 测试 | 结果 | 矩阵核对要点（亲读测试源码 + 复跑双证） |
| --- | --- | --- |
| T01 | PASS | 六类内容页创建（M-A3）；owner=A；草稿前台 404/不入搜索（N13）；修订留痕 |
| T02 | PASS | 编辑自己页＋总管理员代建页（M-A4：edit 覆盖子树内任意归属）；修订 1→2 |
| T03 | PASS | 无审批直发（M-A5）＋下线留内容（M-A6）＋四态联动（N13） |
| T04 | PASS | `publish_scheduled` 到期归档（M-A7）：expired=True、前台 404、修订保留 |
| T05 | PASS | GET 面（200=越权信号反向用）＋POST 面（M-B3/N01）；`b-hijack` 不存在 |
| T06 | PASS | B 页 title/live/修订零变更（M-B4/N01） |
| T07 | PASS | action-publish B 草稿＋unpublish B 已发布页双拒（M-B5/B6/N01/N15——方案 b 否决理由反向验证） |
| T08 | PASS | 单条（before_delete_page）＋批量（before_bulk_action）双路径（M-A8/N02/§3.4）；零库变更＋页面仍在＋拒因送达 |
| T09 | PASS | 删 B 页/B 容器/板块页、移动两动线（M-B7/C4/C5/N01/N05）；path/depth/numchild 全不变 |
| T10 | PASS | 六词表+FeaturedItem 共 41 面（M-D1–D4/N06/N07）；列表/新建/编辑/删除全拒 |
| T11 | PASS | settings URL pk=Site pk（§3.6）；GET/POST 双拒、值零变更（M-E1/N03） |
| T12 | PASS | 用户列表/新建/自我提权/组权限挂载全拒（M-G1/G4/N04）；组归属仍恰 `['dept-jwc-a']` |
| T13 | PASS | ①本集合上传成功（M-F1）；②B 集合零变更＋归位机制（M4.3 ④-5 口径）；③④素材/集合治理全拒（N08） |
| T14 | PASS | 总管理员（is_superuser=False 纯组权限）工厂面 7 例（§4 生命周期/词表/容器/FeaturedItem/设置/代建）；含记录性核查（用户操作无 DB 级审计——OPEN_ITEM ④） |
| T15 | PASS | 跨部门纠错/下线/单条删/批量删全通（M-B4/B5/A8 R1 列——守卫放行侧直证） |
| T16 | PASS | 四态可见性、容器 404、sitemap/导航、未登录/R3 不可达后台、零 superuser（N09–N14） |
| 附加 | PASS | `GuardPrivilegeBoundaryTests`（技术维护组成员非特权——§3.2 R3 边界直证）；`InitPermissionsCommandTests`×13＋`WorldScaffoldSanityTests`×2 |

断言主证口径与矩阵 §6 一致：**拒绝以零库变更快照为主证**（`permission_snapshot` 覆盖 pages/修订/日志/树结构/GPP/GCP/用户/集合/设置/重定向全表），302 仅辅证；按钮隐藏从未作为安全证据。

## 2. 跨部门攻击抽查（评审者亲手构造，18 条）— PASS（18/18）

独立探针（临时测试文件跑于 `peiligo_restart_test` 事务回滚内，采证后删除不入提交；与迁移测试集**零重名素材**，含多条迁移测试未覆盖的新向量）：

| # | 攻击（A 部门账号为攻击者） | HTTP | 零库变更 | 判定 |
| --- | --- | --- | --- | --- |
| A1 | 批量删除他部门页面（纯 B 批：B live＋B draft） | 302 | **是** | 拒 |
| A2 | **混合批量删除**（自己页＋B 页同批） | 302 | **是**（自己页同被整批取消） | 拒 |
| A3 | **copy 自己页面到他部门容器**（new_parent_page=B 容器） | 200 | **是**（无复制件产生） | 拒 |
| A4 | **alias 别名到他部门容器** | 200 | **是** | 拒 |
| A5 | 递归复制板块页造伪板块（P4-a 部门侧） | 302 | **是** | 拒 |
| A6 | 直达 move_confirm 移动 B 容器到另一板块 | 302 | **是** | 拒 |
| A7 | **批量移动自己页面到 B 容器**（P4-b 跨部门变体——M4.3 仅测自有容器目标；选目标步 GET＋destination/new_parent_page/move_to 三字段形态 POST 共 4 探针） | 200 | **是**（A 页均未离开本部门容器） | 拒 |
| A8 | Department 词表 Snippet POST | 302 | **是** | 拒 |
| A9 | Tag 受控标签 Snippet POST | 302 | **是** | 拒 |
| A10 | FeaturedItem POST（首页置顶，N06） | 302 | **是** | 拒 |
| A11 | SiteSettings POST（Site pk URL） | 302 | **是**（feedback_email 未变） | 拒 |
| A12 | 构造 publish B 草稿（**Wagtail 7.4.2 无专用 publish URL——NoReverseMatch 亲证**，唯一入口=edit+action-publish；两形态均测） | 302 | **是**（草稿保持草稿） | 拒 |
| A13 | 构造 unpublish B 已发布页 | 302 | **是**（保持 live） | 拒 |
| A14 | **own 页面 department 字段篡改**（表单把 department 指到 B） | 200 | **是**（department 仍=A——`clean_content_page` 部门一致性校验兜底） | 拒 |
| A15 | 向 B 容器 POST MaterialPage（另一向导路径） | 302 | **是**（无新页面） | 拒 |

结论：**横向越权（跨部门 CRUD/发布/删除/移动/复制）与纵向提权（Snippet/设置/置顶）全部服务端拒绝，主证为全库快照零变更**；未发现任何"HTTP 拒了但库动了"的假阴性。A7 专项证实 P4-b3（批量移动绕 `before_move_page`）**不构成权限边界突破**——目标越出本部门容器时权限层（`can_move_to` 复检 add）始终拒绝，与 M4.3 定性一致。

## 3. 全套命令 — PASS（7/7）

| 命令 | 结果 |
| --- | --- |
| `manage.py check` | **exit 0**；15 WARNING 全部为已知无害项（10×treebeard.E001 上游弃用提示——M1 基线 3 条经 A2.1/M2/M3 新增 Page 类型后增至 10 条，同根因；5×wagtailsearch.W001 既有） |
| `makemigrations --check --dry-run` | **No changes detected**（exit 0，零漂移） |
| `migrate`（peiligo_restart_dev） | **No migrations to apply** |
| `pytest -q` 全量 | **340 passed + 152 subtests, 80.68s, exit 0** |
| `ruff check .` | **All checks passed** |
| `ruff format --check .` | **120 files already formatted** |
| §4.5 v1.2 秘密扫描（`docs/` 全量正则契约） | **零命中**（grep exit 1=通过） |

附加完整性核验：`pip check` 无破损；**Wagtail site-packages RECORD 哈希逐文件校验 4116 文件、异常 0**（wagtail core 物理未被改动）。

## 4. M1–M3 零退化 — PASS

独立基线复跑（temp worktree `main@50b60fc`，复用本 venv——`src/peiligo` 在 main↔HEAD 零 diff 亲证，等价加载）：

| 载体 | pytest 结果 |
| --- | --- |
| main@50b60fc 基线 | **278 passed + 134 subtests, 46.43s（全绿）** |
| 本分支 @3e858a2 | **340 passed + 152 subtests** |

差值精确等于新增权限套件：278+62=340、134+18=152——**纯增量、零退化**；既有 M1–M3 测试（含 `test_home.py` 缓存修复）全部原样通过。

## 5. 代码审计 — PASS（六项逐证）

1. **守卫 fail-closed 只拒绝**：`departments/permissions.py::is_privileged` 匿名/未认证→False、组不存在→False；两钩子（`refuse_non_admin_page_deletion`/`refuse_non_admin_bulk_page_deletion`）只返回拒绝响应或 None 放行，**从不新增授权**——特权放行后仍须过 Wagtail 默认 can_delete（T15 双侧直证）；批量守卫混批（Page+非 Page）经 A2 亲证整批取消。技术维护组成员不进特权判定（专测直证）。
2. **无自建 RBAC/JWT/admin_users 表/Session 部门判权**：diff 全文件 grep 零命中（唯一"class.*Permission"命中为测试类名）；部门归属判权仅凭树位置（GPP@容器传播），无任何读 Session 比对的代码路径（N12 合规）。
3. **无真实密码入库**：init 命令口令仅 `--password-stdin`/`PEILIGO_INIT_PASSWORD`，缺省拒绝创建、零默认口令、输出零明文（源码亲读＋专测 3 例）；测试口令全为合成值（`t44-*`/`stdin-pw-*`/`pw-x`，事务回滚测试库内），正式扫描零命中。
4. **未改 Wagtail core**：diff 仅 `departments/`+`tests/`（name-only 亲证）；venv wagtail 7.4.2 RECORD 哈希校验 4116 文件零异常。
5. **init_permissions 幂等（双跑零变化）**：dev 库活体双跑（事务包裹＋强制回滚，零持久变更）——组清单/GPP/GCP/每组 Django 权限集第二跑后**完全相等**；套件内另有 `test_idempotent_rerun_converges`（含权限收敛）与 `test_new_container_attached_on_rerun`（新容器重跑补挂）双证。
6. **实现形态与矩阵 §3.2 逐项对齐**：总管理员组=根级 GPP×3＋全量模型权限（含 bulk_delete_page）＋GCP@根集合四记录；部门组=容器 GPP×3＋恰一枚 access_admin（set() 收敛幂等）＋GCP@本部门集合；技术维护组=零权限占位（有挂载则收敛回零）；空 Editors/Moderators 清理（有成员告警保留）。

## 6. 威胁面小结（安全评审视角）

- **认证/授权**：无自定义认证代码；全部经 Django auth＋Wagtail 权限体系。越权面（§2 十八探针）零突破。
- **注入面**：diff 无 SQL 拼接/模板注入/反序列化新面（守卫与命令仅 ORM 调用＋固定文案 messages）。
- **口令纪律**：入口唯一（管理命令）、来源受控（stdin/env）、无泄露路径。
- **攻击面收敛**：无新增公开 URL/视图；全部变更为后台钩子（已登录面）与离线命令。
- **失败模式**：守卫异常时 Django 默认 500（fail-closed 方向——拦截面过宽不会放行）；`_read_password` 快速失败不建半账。

## 7. 非阻断遗留（登记，不构成合并门阻断）

1. **P4-b3 批量移动绕 `before_move_page`**（内容模型完整性绕过，非越权——本审查 A7 亲证跨部门目标被权限层拒）。已在实现报告登记，待矩阵修订时扩"delete+move 双钩"；矩阵 §6 T09 现口径不含批量移动必测项，故不阻断。
2. **组名为选定值**（总管理员/技术维护/`dept-<slug>`）：矩阵未钉字符串；单点定义于 `departments/permissions.py`，改名一处生效。
3. **技术维护组形态**：矩阵 §3.2 R3"不入任何 Wagtail 组" vs 任务三组要求——零权限占位调和，入组不获任何权限（专测＋守卫边界测双证）。
4. **wagtailusers 无 DB 级用户审计**（页面操作有 PageLogEntry、用户操作仅 Python logging）：Wagtail 7.4.2 上游现状，T14 断言固化；M-G2/G3 留痕缺口待 M7.1/后续裁决。
5. **无首登/重置后强制改密开关**：Wagtail 核心无该机制（M4.3 ④-4）；交接依赖重置口令流程。
6. **README treebeard.E001 条数注记滞后**（"5 条"实为 10 条——M3 五内容页类型各增一条，同根因同无害性；文档漂移，非代码问题，可随下次 README 触碰顺带更新）。

另记（观察项，无需动作）：init 命令 GPP/GCP 收敛为增量式（get_or_create 只补不删）——经旁路（如 R1 手工挂载）引入的冗余挂载重跑不剪除；属配置工具边界而非安全缺陷（权限变更面归 R1 管理职责），Django 权限集则严格收敛（set()）。

## 8. 合并门判定

**PASS** —— 判据全绿：①T01–T16 复跑 16/16（62+18 subtests）；②攻击抽查 18/18 零库变更拒绝；③七命令全过（check/migrations/migrate/pytest 340+152/ruff×2/秘密扫描零命中）；④M1–M3 零退化（278 基线全绿、纯增量 62）；⑤代码审计六项零违规（fail-closed/无自建 RBAC/无真密码/未改 core/幂等双跑零漂移/形态对齐 §3.2）。实现忠实承载 ROLE_PERMISSION_MATRIX §3（方向锁定、配置表、关闭措施），ADR-0004 生效条件维持满足。
