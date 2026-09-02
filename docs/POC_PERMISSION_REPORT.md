# M4.3 · 越权测试矩阵执行报告（T01–T16）

| 项目 | 内容 |
| --- | --- |
| 步骤 | M4.3 / S4.3（00_MASTER_PLAN §8 M4.3；02_ARCHITECTURE_DOMAIN_PLAN §6 S4.3） |
| 执行日期 | 2026-08-27 |
| 执行载体 | `t16/run_t16.py`（本分支入库；Django test Client 真实 HTTP 动线 + 全库快照 diff） |
| 权威定义 | `docs/ROLE_PERMISSION_MATRIX.md` §6（分支 m4/a4-1-permission-matrix @aac91a0；§3 机制重建） |
| 机制参考 | M4.2 PoC `poc/run_poc.py`（分支 m4/a4-2-permission-poc，61/61；快照 diff 口径与表单构造沿用） |
| 分支 | `m4/a4-3-permission-tests`（禁放 poc/） |
| 结果 | **16/16 全绿**（155/155 子断言；退出码 0） |
| 证据 | `t16/evidence.json`（机器可读逐断言）、`t16/evidence_run.log`（全量输出；下表行号指向该文件） |

---

## ① 环境记录

| 项 | 实测值 |
| --- | --- |
| Python | 3.13.11（自建 `.venv`，未污染系统环境） |
| Django | 5.2.17 |
| Wagtail | 7.4.2.final.1 |
| `peiligo.__file__` | `<USER_HOME>/orca/workspaces/peiligo/a4-3-permission-tests/src/peiligo/__init__.py`（本 worktree 载体确认） |
| 数据库 | PostgreSQL，自建 scratch 库 `peiligo_m4_t16`（socket 连接 `postgres://<用户>@/peiligo_m4_t16?host=/tmp`）。执行器启动自检库名，不符即退出。**正式四库（peiligo_dev / peiligo_test / peiligo_restart_dev / peiligo_restart_test）零触碰、零 DROP** |
| 场景重建 | 按矩阵 §3：五冻结板块（chronicle/events/materials/software/guide）+ 两部门容器树（A 五板块全建、B 建 chronicle/events）+ 三账号三组：`t16-admins`（总管理员，纯组权限，is_superuser=False：根节点 GPP add/change/publish + 全量 Django Permission + 根集合 GCP add/change_collection、add/change_image）、`t16-dept-a` / `t16-dept-b`（各仅 access_admin + 自有容器 GPP add/change/publish + 自有集合 GCP add/change_image） |
| OQ1 删除守卫 | `before_delete_page` + `before_bulk_action` 双钩子只拒绝守卫，进程内经 `wagtail.hooks` 运行时注册（特权判定 = superuser 或 `t16-admins` 成员；零侵入，正式实现待 M4 门禁后落 `departments/wagtail_hooks.py`） |
| 执行方式 | 全部服务端构造 URL/POST（Django test Client 登录后走真实后台视图）；拒绝断言以**零库变更为主证**（全库快照 diff：pages/revision/page_log/users/groups/GPP/GCP/collections/departments/词表/images/settings/redirects 全量比对），HTTP 302 为辅证；按钮 hiding 不作为安全证据 |
| 环境注记 | Wagtail 迁移自动创建默认 Editors / Moderators 组（带 GPP/GCP 行与 access_admin），**零成员、惰性存在**，不影响任何断言；正式实现建议初始化时清理（见 ④-6） |
| 幂等性 | 执行器每轮自清理 `t16-` 前缀对象后重播种；可重复复跑 |

## ② T01–T16 结果汇总表（ID | 结果 | 证据摘录）

| ID | 用例 | 子断言 | 结果 | 证据摘录（`t16/evidence_run.log` 行号） |
| --- | --- | --- | --- | --- |
| T01 | 正向 · A 本部门容器创建六类内容页 | 21/21 | **PASS** | L25–45：六类创建 302、owner=A、修订留痕、草稿前台 404/不入默认搜索 |
| T02 | 正向 · A 编辑自己页面与总管理员代建页 | 3/3 | **PASS** | L50–52：修订 1→2、rev#150 user=A、edit 覆盖子树内任意归属 |
| T03 | 正向 · A 发布/下线自己页面 | 7/7 | **PASS** | L57–63：publish 302 live=True、PageLogEntry 留痕、前台/搜索四态联动 |
| T04 | 正向 · 通知到期自动归档 | 6/6 | **PASS** | L68–73：publish_scheduled 后 expired=True、前台 404、修订保留 |
| T05 | 越权 · A 向 B 容器 POST 创建 | 3/3 | **PASS** | L78–80：GET/POST 均 302 + 零库变更、`t16-b-hijack` 不存在 |
| T06 | 越权 · A POST 编辑 B 已发布页 | 3/3 | **PASS** | L85–87：302 + 零库变更、B 页 title/live/修订零变更 |
| T07 | 越权 · A 横向发布 B 草稿/下线 B 页 | 4/4 | **PASS** | L92–95：action-publish/action-unpublish 均 302 + 零库变更 |
| T08 | 越权 · A 永久删除自己页面（单条+批量） | 2/2 | **PASS** | L100–101：双钩子守卫拦截，页面仍在 + 零库变更 |
| T09 | 越权 · A 跨部门删/移容器、删板块页 | 6/6 | **PASS** | L106–111：五路全拒 302 + 零库变更、树结构 path/depth/numchild 全不变 |
| T10 | 越权 · A 对治理类 Snippet 全零权限 | 41/41 | **PASS** | L128–168：六词表 + FeaturedItem 的 GET/POST 增删改查全拒（302 + 零库变更） |
| T11 | 越权 · A 直达站点设置 | 2/2 | **PASS** | L173–174：GET/POST 均 302 + 设置值零变更 |
| T12 | 越权 · A 直达用户/组管理（含自我提权） | 8/8 | **PASS** | L179–192：建用户/改自己档案/入 admins 组/改组权限挂载全拒、组归属仍恰为 `['t16-dept-a']` |
| T13 | 媒体集合边界 · 本部门可传他部门全拒 | 7/7 | **PASS** | L197–203：本集合上传成功；B 集合零变更（请求 collection=19 未被采纳，归位集合 A）；集合增删改全拒 |
| T14 | 正向 · 总管理员（纯组权限）工厂面 | 17/17 | **PASS** | L208–224：建账号/停用/重置密码、建部门+容器、五词表、FeaturedItem、改设置、代建页全通；两条记录性核查见 ④-3/④-4 |
| T15 | 正向 · 总管理员跨部门纠错/下线/删除 | 5/5 | **PASS** | L229–233：跨部门编辑/下线/单条删/批量删全通（守卫放行特权组） |
| T16 | 边界 · 前台/后台/角色边界 | 12/12 | **PASS** | L238–249：四态可见性 `{live:200, 其余:404}`、容器 URL 404、不入 sitemap/导航、未登录重定向、R3 型账号不可达后台、全程零 superuser |

**P4 已知两路径专项探测**（矩阵外附加探测，8/8 记录项）：详见下节。

### P4 专项 · 已知两路径是否构成越权（必测留档）

| 路径 | 探测操作 | 实际结果 | 是否越权 |
| --- | --- | --- | --- |
| P4-a 非递归复制 SectionPage 改 slug 造伪板块 | A 经 copy 动线构造（L116–117） | 302 + 零库变更；`can_copy()=can_edit()` 对板块页为 False → **部门账号不可达复制面** | **否**（伪板块仅总管理员可造，A3.1 已留档的 IA 治理项） |
| P4-b1 批量移动自己页面 → B 容器 | 构造 bulk move POST（L118） | 选目标步即拒（`can_move_to` 复检 add 权限），200 + 零库变更 | **否**（权限层拒） |
| P4-b2 批量移动自己页面 → 板块页 | 构造 bulk move POST（L119） | 同上，200 + 零库变更 | **否**（权限层拒） |
| P4-b3 批量移动自己页面 → 自有另一板块容器 | 构造 bulk move POST（L120–122） | **移动成功且绕过 `before_move_page`**（`MoveBulkAction.execute_action` 直调 `page.move()`）：造出 §7.2 违规页（`event_start_at`/`event_location` 双缺失）。对照：同一移动走单页动线被既有钩子拒（302 + 零库变更）。探测后树结构/重定向面已精确还原（pages/counts/redirects 全等，page_log +2 为预期留痕） | **否——hook 绕过但目标在自有授权容器内，属内容模型完整性绕过（§7.2 复检被跳过），非权限边界突破**；正式实现需补守卫（见 ④-2） |

### 逐条记录（前置 / 操作 / 实际结果 / 期望 / 结论）

> 每条的完整子断言与快照 diff 细节见 `t16/evidence.json`（`results[]` 按 case 分组）；下文仅录关键证据。账号约定：A=`t16-dept-a`（部门 A 编辑），B=`t16-dept-b`，管理员=`t16-admin`（纯组权限）。

**T01 正向 · A 在本部门容器创建六类内容页**
前置：五板块 + A 容器（五板块全建）就位，A 持自有容器 add。操作：A 依次 POST 创建 NoticePage（chronicle/events 两形态）、ArticlePage、MaterialPage、SoftwareToolPage、GuidePage。实际结果：六次创建全 302，owner=A，每页落一条修订（创建者/时间留痕）；草稿前台 404、不入默认搜索。期望：全成功且留痕，草稿不可见（N13）。**结论：PASS。**

**T02 正向 · A 编辑自己页面与总管理员代建页**
前置：T01 页面在库 + 管理员在 A 子树代建页一页。操作：A POST 编辑自己页面（含受控标签选用）与代建页。实际结果：均 302，修订 1→2，rev#150 user=A。期望：edit 权限覆盖子树内任意归属（GPP 挂容器）。**结论：PASS。**

**T03 正向 · A 发布/下线自己页面**
前置：A 草稿一页。操作：A action-publish → 验证前台/搜索 → action-unpublish。实际结果：发布 302 live=True，PageLogEntry（action=wagtail.publish, user=A），前台 200、搜索命中；下线 302 live=False，修订保留，前台 404、搜索消失。期望：无审批直发（M-A5）、下线留内容（M-A6）、四态可见性（N13）。**结论：PASS。**

**T04 正向 · 通知到期自动归档**
前置：A 已发布活动通知（含 expire_at）。操作：跑 `publish_scheduled` 管理命令。实际结果：live=False expired=True，前台 404、搜索消失，内容与修订保留，A 后台仍可见。期望：M-A7 自动归档 + N13 退出前台 + M-A1 后台可见。**结论：PASS。**

**T05 越权 · A 向 B 容器直接 POST 创建**
前置：B 容器（学习资料）在树。操作：A GET 创建表单 + 构造 POST 直达（不依赖表单页）。实际结果：GET 302（非 200）、POST 302，**零库变更**（含修订/日志/树结构），`t16-b-hijack` slug 不存在。期望：容器级 add 缺失 → 全拒（矩阵 M-A2）。**结论：PASS。**

**T06 越权 · A 直接 POST 编辑 B 已发布页**
前置：B 已发布通知一页。操作：A GET 编辑表单 + 构造 POST（改 title）。实际结果：均 302 + 零库变更，B 页 title/live/修订历史零变更。期望：PRD §23 场景 1 拒绝。**结论：PASS。**

**T07 越权 · A 横向发布 B 草稿与下线 B 已发布页**
前置：B 草稿一页 + B 已发布一页。操作：A 构造 action-publish（对 B 草稿）与 action-unpublish（对 B 已发布页）。实际结果：均 302 + 零库变更；B 草稿 live=False、B 页 live=True 保持。期望：Publish 权限面（方案 b 否决理由）在方案 a 下天然封闭。**结论：PASS。**

**T08 越权 · A 永久删除自己拥有的页面（双路径）**
前置：A 自有页一页 + 两页。操作：单条 delete-confirm 与批量 bulk-delete 各构造 POST。实际结果：单条被 `before_delete_page` 拦、批量被 `before_bulk_action` 拦（302 + 零库变更，页面仍在）。期望：OQ1——删除权集中总管理员，单条与批量两路径都要拦。**结论：PASS。**

**T09 越权 · A 跨部门删除/移动容器/删除板块页**
前置：B 页/B 容器/板块页在树。操作：五路构造——删 B 页、删 B 容器、删板块页、移动 B 容器（选目标步 + 直达 move_confirm 两动线）。实际结果：全 302 + 零库变更；树结构 path/depth/numchild 全不变。期望：`can_delete`/`can_move` 对外部门与板块层为零。**结论：PASS。**

**T10 越权 · A 对治理类 Snippet 全零权限**
前置：六类词表（Department/Tag/学科/资料类型/适用平台/指南类别）各有既有项 + 种子 FeaturedItem。操作：每类 GET 列表、GET 新建表单、POST 新建、GET 编辑、POST 改、POST 删（6 类 × 6 面 + FeaturedItem 5 面 = 41 断言）。实际结果：全 302 + 零库变更。期望：ADR-0004 决策 3（V1 部门零 Snippet 权限）与矩阵 N04/N06。**结论：PASS。**

**T11 越权 · A 构造 URL 直达站点设置**
前置：SiteSettings 有种子值。操作：A GET 设置编辑 URL + POST 改紧急提示/反馈邮箱。实际结果：均 302 + 设置值零变更。期望：N03 全拒。**结论：PASS。**

**T12 越权 · A 构造 URL 直达用户/组管理（含自我提权）**
前置：三账号三组在库。操作：A GET 用户列表、POST 新建用户、GET/POST 编辑自己档案（把 groups 指向 `t16-admins`）、GET/POST 编辑部门组与总管理员组（改 GPP 挂载）。实际结果：全 302 + 零库变更；A 组归属仍恰为 `['t16-dept-a']`。期望：N09/N10 全拒，无自我提权通道。**结论：PASS。**

**T13 媒体集合边界 · A 本部门可传，他部门与集合治理全拒**
前置：集合 A/B 各一，B 集合有素材一页。操作：① A 向本集合上传（PIL 生成 PNG）；② 构造 POST 指定 `collection=19`（B）；③ 编辑 B 集合内素材；④ 新建集合；⑤ 改名/移动 B 集合；⑥ 删 B 集合。实际结果：① 302 成功（M-F1）；② 302，**B 集合零变更**——服务端未采纳请求的 collection 值，新增素材被 Wagtail `BaseCollectionMemberForm` 归位到唯一授权集合 A（机制注记：恰有一个授权集合的用户表单删除 collection 字段并在 `save()` 强制归位；多集合用户则是 queryset 校验拒绝。边界未破，拒绝形态为"归位"而非 403，见 ④-5）；③–⑥ 全拒（302/404 + 零库变更，快照含 images/GCP/collection 计数）。期望：M-F1 正向 + N08 边界。**结论：PASS。**

**T14 正向 · 总管理员（纯组权限，非 superuser）工厂面**
前置：`t16-admin` 仅在 `t16-admins` 组（is_superuser=False）。操作：① 建部门岗位账号 → 停用 → 重置密码 → 新凭据登录；② 建 Department 词表项 + 板块下建容器；③ 五词表各增一项；④ 建 FeaturedItem（起止窗口+启用）；⑤ 改 SiteSettings 紧急提示；⑥ 在 A 子树代建页并编辑。实际结果：17 项全通（302 + 库变更符合预期）。两条记录性核查：**wagtailusers 无 DB 级用户审计日志**（LogEntry 0 条，仅 Python logging，见 ④-3）；**Wagtail 7.4.2 核心无首登强制改密开关**（见 ④-4）。期望：M-C/M-G 系工厂面全通。**结论：PASS。**

**T15 正向 · 总管理员跨部门纠错/下线/永久删除**
前置：B 已发布页一页 + 测试数据页两页。操作：管理员跨部门编辑 B 页 → 下线 → 单条永久删除一页 → 批量永久删除两页。实际结果：全 302；下线后前台 404 内容保留；删除后页面与修订移出库（守卫对特权组放行）。期望：M-B4 + OQ1 守卫仅拦部门账号。**结论：PASS。**

**T16 边界 · 前台/后台/角色边界（含 R3/R4 记录性核查）**
前置：live/草稿/下线/到期四态页面各一。操作：① 匿名 GET 四态 URL + 默认搜索四查；② 匿名 GET 容器 URL；③ 比对 sitemap.xml 与首页导航 HTML；④ 未登录访问 `/admin/` + 错误凭据登录；⑤ R3 型账号（零组零权限）访问 `/admin/`；⑥ A 后台首页 + 浏览器树根级可见项。实际结果：① `{live: 200, draft/unpublished/expired: 404}`，搜索仅 live 命中；② 容器 URL 404；③ sitemap 仅首页+板块、导航无容器链接；④ 302 → 登录页 / 统一失败页 200；⑤ 302 不可达；⑥ A 后台 200（根级可见 titles=[]，OQ-2 记录：可见≠可操作，操作面以 T05–T13 拒绝断言为准）；全程零 superuser 账号（M-G5/N10）。期望：N13/N14/N09 全满足。**结论：PASS。**

## ③ 结论

**16/16 全部通过（155/155 子断言，0 失败，退出码 0）。**

容器树方案（板块下按部门建容器 + GPP 挂容器节点树形传播 + GCP 挂部门集合 + OQ1 双钩子删除守卫 + 部门零 Snippet 权限）的越权面验证通过：

1. **横向越权全拒**（T05–T09、T13②③–⑥）：部门账号对其他部门容器/页面/集合的全部构造动线（GET/POST、单条/批量、直达确认步）均被权限层拒绝，且**以零库变更为主证**——无"HTTP 拒了但库动了"的假阴性。
2. **纵向提权全拒**（T10–T12）：词表/推荐位/站点设置/用户与组管理（含自我提权）全部不可达，组归属零变更。
3. **Publish 权限面专项封闭**（T07）：方案 b 否决理由（板块级 Publish 横向越权）在方案 a 下反向验证成立。
4. **正向面全通**（T01–T04、T13①、T14–T15）：部门账号完整自助动线与总管理员（纯组权限）工厂/纠错/删除动线无一处被守卫误伤。
5. **前台/后台边界**（T16 + 各用例内嵌断言）：容器 URL 404、不入 sitemap/导航/默认搜索；四态可见性正确；未登录与 R3 型账号不可达后台；全程零 superuser。
6. **P4 已知两路径均不构成部门账号越权**：P4-a 部门账号不可达复制面（总管理员侧 IA 治理项，A3.1 已留档）；P4-b1/b2 权限层拒；P4-b3 批量移动绕过 `before_move_page` 钩子（§7.2 内容复检被跳过），但移动目标始终限自有授权容器内、不跨权限边界——**定性为内容模型完整性绕过而非越权**，正式实现需补 move 批量路径守卫（④-2）。
7. **未发现任何真实越权**——无触发"该条 FAIL + 最小复现 + STOP 等 GPT Gate"判废条款的情形。

对 ADR-0004 的最终影响：**生效条件（S4.3 越权矩阵全绿）满足 → 维持 Accepted**；验证证据已回写 ADR-0004"验证证据"节（本分支同提交；状态字段未动——ADR 状态变更决策权在项目负责人，代理不代决）。最终以独立审查复跑 + G2 门为准。

## ④ 修订建议（对 ADR-0004 与 ROLE_PERMISSION_MATRIX；均为建议，不擅自实施）

1. **ADR-0004 验证证据回写**：本步骤已完成（16/16 + 执行日期 + 报告路径），闭环决策 4 的生效条件主张。
2. **M4 正式实现必补：bulk move 路径守卫**。P4-b3 证实 `MoveBulkAction.execute_action` 直调 `page.move()` 绕过 `before_move_page`（上游 Wagtail 7.4.2 行为），单页动线守卫不覆盖批量动线。建议正式实现将 OQ1 守卫从"delete 双钩子"扩为"delete + move 双钩子"（`before_bulk_action` 内拦 `action=move` 或注册 `before_move_page` 等效批量复检），并在矩阵 §6 T09 或新增行加入"批量移动绕 hook"必测项。
3. **矩阵 §6 T14① 断言口径补注（用户审计）**：Wagtail 7.4.2 wagtailusers 无 DB 级用户审计（增删改仅 Python logging，LogEntry 0 条），与页面操作的 PageLogEntry 不对称。建议矩阵/M-G 系标注此缺口，正式实现若 PRD §5 要求用户操作留痕，需自定义审计（信号挂 LogEntry 或日志导出方案，另行裁决）。
4. **矩阵 §6 T14① 断言口径补注（强制改密）**：Wagtail 核心无首登/重置后强制改密开关，M-G3 若要求该机制需自定义（密码过期标记或第三方包），建议列入 M4 正式实现清单裁决。
5. **矩阵 §6 T13② 断言口径补注（单集合归位机制）**：恰有一个授权集合的用户，Wagtail `BaseCollectionMemberForm` 删除 collection 字段并在 `save()` 强制归位——服务端不采纳构造的越权集合值，边界成立但拒绝形态是"归位"而非显式拒绝（多集合用户才是 queryset 拒绝）。建议矩阵补注，避免后续复跑按"必须 403"误判。
6. **默认 Editors/Moderators 组**：迁移自动创建、零成员、惰性。建议正式实现初始化步骤清理或明确留档，矩阵环境节可补一行注记。
7. **P4-a 伪板块**：部门账号不可达（本报告证实）；总管理员侧治理（非递归复制确认提示或禁用）维持 A3.1 留档口径，无需改矩阵。

## ⑤ 附录：复现命令

```bash
# 0) 仓库根目录（worktree a4-3-permission-tests，分支 m4/a4-3-permission-tests）
#    首次环境（已建则跳过）：
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt && .venv/bin/pip install -e .

# 1) 自建 scratch 库（正式四库零触碰；库名不符时执行器自检退出）
createdb peiligo_m4_t16

# 2) 环境变量（scratch 哑值；连接走本机 PG socket）
export DATABASE_URL="postgres://$USER@/peiligo_m4_t16?host=/tmp"
export SECRET_KEY="a43-t16-scratch-secret-not-real"

# 3) 建表 + 五板块（幂等）
.venv/bin/python manage.py migrate
.venv/bin/python manage.py bootstrap_sections

# 4) 全量执行 T01–T16 + P4 探测（幂等：每轮自清理 t16- 前缀对象后重播种）
.venv/bin/python t16/run_t16.py
#    退出码 0 ⇔ 16/16；产物 t16/evidence.json（逐断言机器可读证据）

# 5) 采证复跑（生成与本报告同口径的全量日志）
.venv/bin/python t16/run_t16.py > t16/evidence_run.log 2>&1; echo "exit=$?"

# 测试账号（scratch 库内一次性对象，随每轮重播种）：t16-admin / t16-dept-a / t16-dept-b，口令 t16-pass-12345
```

复核入口：`t16/evidence.json`（`results[]` 逐断言含 case/ok/detail；`p4` 节记录 hook_bypassed/escalation 结论）、`t16/evidence_run.log`（汇总表行号索引见 ②）。
