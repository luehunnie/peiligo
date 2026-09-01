# FINAL FIX · Admin API Guard 收口审查记录

批次：终审 Reviewer A 范围外 HIGH——`/admin/api/main/pages/<id>/action/*`
绕过 HTML 守卫钩子的收口（本批唯一事项）。H-1/L-9/M-1/L-11/M-2/L-1/L-2/
L-4/L-6/L-7/L-8/L-10 已在前批完成（5cc93b7..33a5260）并经 Reviewer A/B
APPROVE。基线 33a5260；本批代码与 V-11 登记同支提交。

## ROOT_CAUSE（Wagtail 7.4.2 安装源码亲证）

- `/admin/api/main/pages/<id>/action/<name>/` 由
  `PagesAdminAPIViewSet.action_view` 承接（wagtail/admin/api/views.py:134-146）：
  无 permission_classes（项目未配置 REST_FRAMEWORK＝DRF 缺省 AllowAny）、
  无页面级权限检查，径直执行核心 `wagtail.actions.*`；
- 核心 actions 零 `before_*_page` 钩子（wagtail/actions/*.py 全无 hooks
  调用）；四条守卫钩子仅挂 HTML 动线（admin/views/pages/*.py 与
  admin/views/bulk_action/base_bulk_action.py:84）；
- 唯一屏障是 `PagePermissionTester` 树权限，而 change@容器 GPP 附带
  can_delete/can_publish（departments/wagtail_hooks.py M4.4 注）→ 修复前
  实证（行为级 RED，见下）：R2 经 API 永久删除自己内容、发布/回滚容器
  修订、移动内容跨容器（tree path 变更＋redirect 生成）；R1 经 API 删除
  页面。§17.4 非空结构拒删、L-9 移动复检与递归复制复检对 API 无钩子
  可用。
- ADMIN_API_ROLE：action 面＝**OPTIONAL_INTERFACE**——全部编译 bundle 无
  action/ 引用，仅 sidebar.js 消费 GET listing（wagtailadmin_tags.py:929
  仅 reverse `:listing`）；chooser/explorer/editor 走 HTML 动线。

## SOLUTION（方案 A：整体禁用）

`construct_admin_api` 官方扩展点按名覆盖 pages 端点 viewset：
`_ReadOnlyPagesAdminAPIViewSet`（`actions = {}` ＋ `get_urlpatterns` 跳过
action 路由，MRO 落 BaseAPIViewSet 只读 listing/detail/find，路由名不变）。
守卫语义单一来源仍是 departments/wagtail_hooks.py HTML 守卫钩子——零新增
授权逻辑，无第二套权限判断。计时安全性：`hooks.get_hooks` 先行 import
全部 app wagtail_hooks 再快照钩子表（wagtail/hooks.py:103-115），
`router.urls` 惰性求值晚于钩子环（api/v2/router.py:86-95）。R1 亦失去
API action 面＝有意（API 非产品动线，治理动线收敛回受钩子保护的 HTML
Admin）。

## HUMAN_DECISION_RECORD

- **R2_RECURSIVE_UNPUBLISH = ACCEPTED_V1_PERMISSION_BEHAVIOR**（Human
  裁决 2026-09-01）：R2 为本部门正式内容管理员、持本部门 publish 权限，
  允许批量下线自己部门内容属现有授权语义；非跨部门权限、非系统结构
  权限。V1 不新增角色层级。承载动线＝HTML Admin（Wagtail 权限门与矩阵
  语义不变）；Admin API action 面已整体禁用，与本裁决无涉。
- **ALIAS_MOVE_LOW**：别名页作为 move destination 的守卫复检口径，登记
  FINAL_FULL_PROJECT_REVIEW.md INFO_VALIDATION_ITEMS **V-11**
  （VALIDATION / FUTURE_HARDENING），本批不处理。

## ADVERSARIAL_EVIDENCE

tests/test_admin_api_actions_disabled.py（8 用例；矩阵 §3.6 零库变更快照
为主证，HTTP 状态仅辅证）：

- RED（修复前实证旁路）：R2 删除自己内容＝页面消失（page 16→15）；R2
  发布容器（wagtail.publish 日志+1）；R2 移动内容跨容器（position
  last-child，path/redirect 变更）；R1 经 API 删除；匿名 POST 302
  （端点在）。
- GREEN（修复后）：九个 action 名对 R2 一律 404＋零库变更；R1 同禁；
  匿名/R3 落 admin 兜底 302 零库变更；GET listing/detail 200 不回退
  （sidebar 依赖，test_browser_tree_api_reachable 钉住）。

## FULL_TESTS

`check`（15 项上游/已文档化警告，exit 0）· `makemigrations --check
--dry-run` 无漂移 · pytest **604 passed + 269 subtests**（基线 596+269 ＋
本批 8）· `ruff check` / `ruff format --check` 全绿 · production
`check --deploy`（哑值非密 env）仅余冻结决策内 security.W021（V-7 HSTS
无 preload）＋上游警告，exit 0。

## INDEPENDENT_REVIEW

fresh-context 审查 **final-admin-permission-consistency-review**
（2026-09-01）：独立读取 Wagtail 7.4.2 安装源码（admin/api/*、
api/actions/*、actions/* 六核心 action、admin/urls、utils/urlpatterns、
hooks.py、models/pages.py PagePermissionTester），独立复跑新增对抗测试
与全量回归（604+269 复现）、指定守卫测试组与 sidebar 可达性对照，并
进程内实测路由替换/幂等/reverse 面。七项检查——HTML/API 一致性、九
action 无绕过、R2 正常管理不误伤、无第二套 policy、无同类漏网面
（images/documents/snippets/其它 wagtail.actions 调用点全查）、机制
健壮性（钩子计时/按名覆盖/幂等/reverse 面）、匿名与 CSRF 语义——全部
CONFIRMED。**VERDICT = APPROVE**（零阻断发现）。

### 登记的非阻断注记（INFO ×3）

1. 幂等守卫为身份判定（`is PagesAdminAPIViewSet`）：若未来其它 app 先行
   以异类 viewset 覆盖 pages 端点，本守卫将静默失效——当前
   INSTALLED_APPS 序下不可能（departments 先于全部 wagtail.* app，且
   images/documents 钩子仅注册新名字）。登记知悉即可。
2. 既有读可见面（先于本批存在、与本批无关，性质与 V-9 相邻）：持
   access_admin 的账号可经 `/admin/api/main/pages/` GET 列出全部页面
   （含他部门标题/slug/草稿；`for_explorer` 为逐请求可选参数），并可经
   images/documents admin API 列取/下载全部附件（无
   CollectionViewRestriction 行）。只读；如需收口属未来 hardening
   （V-9 同族），不属本批。
3. 守卫面整体依赖 departments/wagtail_hooks.py 可导入（导入失败＝守卫
   全体失效）——既有架构属性，非本批引入。

---

*Closeout record · feat/v1-final-fixes · 2026-09-01 · 基线 33a5260*
