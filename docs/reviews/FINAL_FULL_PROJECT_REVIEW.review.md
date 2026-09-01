# FINAL_FULL_PROJECT_REVIEW · Independent Review Record

对应主审报告：`docs/FINAL_FULL_PROJECT_REVIEW.md`（untracked）
基线：canonical `main` = `origin/main` = `f3bbbed74dbe68fa13f2552383d7f29f7e1862a2`
复核日期：2026-09-01
本文件 untracked/uncommitted，等 Human 阅读后决定是否落档。

两名 Reviewer 均为 fresh-context 独立会话，READ-ONLY 纪律（未改任何文件、无 git 写操作、未运行测试——测试为主审职责且已实跑）。

---

## REVIEWER A（Final-architecture-security-review）

### VERDICT
**APPROVE_WITH_NOTES**（无 BLOCKER/HIGH；主审 PASS_WITH_FIXES 方向成立，但 FINDINGS 集合需补入 N-1 等，其中 N-1 属主审漏报的冻结规格违反而非风格问题）

### CONFIRMED（独立复核后确认）
- ARCHITECTURE 零漂移：全仓 grep 无 rest_framework/APIView/ViewSet/celery/vue/react 消费点；`frontend/` 仅 `__init__.py`；单一认证（base.py:110-113 恰两后端，AxesStandaloneBackend 置首）、单一发布状态（notices/lifecycle.py:45-68 纯推导零字段）、单一搜索后端（base.py:313-317 显式钉 E1IcontainsSearchBackend）。
- axes 冻结值：10 次/15 分钟/成功清零/锁定键 `[username,ip_address]`（base.py:120-123）；AxesMiddleware 挂链尾合规；test_login_governance.py:67-107 行为级锁定。
- 密码策略/会话：12 位 MinimumLengthValidator OPTIONS（base.py:216-218）、24h+Lax+HttpOnly+Secure（base.py:228；production.py:26-30）。
- **passwordgate 无绕过面**（对抗证伪"改密旁路"候选）：/admin/password-change/ 有 access_admin 门；GATE_EXEMPT_PATHS 精确匹配，大小写/尾斜杠/双斜杠变体均不命中豁免＝被 302 进闸门；/admin/account/ 面板与 /admin/password_reset/* 均不在豁免单；/django-admin/ 改密需 is_staff=True 而 init_permissions 恒 `is_staff=False`（init_permissions.py:226-228）。
- UPLOAD 收口：WAGTAILDOCS_DOCUMENT_FORM_BASE（base.py:345）覆盖单文件/多文件/编辑替换三路径；`_post_clean` 的 changed_data 门正确；图片侧扩展收窄 + Willow/Pillow 解码；签名识别失败一律拒绝；未发现第四条上传入口。
- EXTERNAL_LINKS：校验链完备（白名单+userinfo 拒绝+URLValidator）；确认页零 JS/零 meta refresh；`from` 仅数字 pk 且 live∧¬expired 过滤；go 端点二次校验后才 302；对抗形态（`https://a\@b`、凭据段、scheme 相对、空白符）均被拒；纯 302 无 SSRF 面。
- R-05 治理审计：actor 不伪造（receivers.py:40-51 non_request 显式标注）；权限门=superuser∨change_user∨change_group（views.py:54-62）+ 菜单同条件隐藏（wagtail_hooks.py:74-82）；批量启停补钩子；删除去重兜底。
- production.py 安全值逐项、DOCKER/COMPOSE/CADDY（非 root/哑值构建/`${VAR}` 插值/healthcheck 链/Caddy admin 回环）全部属实。
- M-1、M-2、L-1、L-3、L-5、V-6 均 CONFIRM；M-1 补充证据：**compose web/scheduler env 未透传 FEEDBACK_EMAIL**——生产里连 env 路线都是哑值（已并入主审报告 L-11）。

### DISAGREEMENTS
1. 主审 PERMISSIONS 节"move/copy 递归路径…封堵"不完整：**批量移动**（Wagtail `bulk_actions/move.py` `action_type="move"`，execute_action 直调 `page.move()`）不经 `before_move_page`，项目 `before_bulk_action` 两钩子只拦 `delete`（wagtail_hooks.py:223、269）→ 已并入主审报告（L-9 + PERMISSIONS 节更正）。
2. 主审 PERMISSIONS 节未覆盖矩阵 M-C3 实现符合性 → 已并入主审报告（H-1）。

### NEW_FINDINGS
- **N-1 · MEDIUM（A 的原始定级）**：`init_permissions.py:171-176` change GPP 挂容器节点自身＋GPP 子树语义（wagtail pages.py:2190-2196）→ R2 可编辑容器 department/slug，违反冻结矩阵 M-C3（ROLE_PERMISSION_MATRIX.md:92）；含"FK 改 B 后重跑 init_permissions → B 组 GPP 挂上 A 容器子树"升级链；无测试覆盖。
- **N-2 · LOW**：批量移动绕过内容模型复检（R2 面受 can_move_to 目的地权限约束，非安全越权）。
- **N-3 · LOW**：GroupCollectionPermission 变更无逐项审计明细（与 GPP 粒度不对称）。
- **N-4 · LOW**：compose 无 FEEDBACK_EMAIL 透传。
- **N-5 · INFO**：wagtaildocs serve 视图公开（Wagtail 缺省），未认证可按自增 ID 枚举下载文档。
- **N-6 · INFO**：根集合 GCP 无 delete 项，非超管 R1 无法删除图片/集合（疑为有意，建议 Runbook 登记）。

### NO_ISSUE_SPOT_CHECKS（7 项，防主审漏报）
CONTENT_MODEL / IA（容器 404+sitemap+导航零树查询）/ HOMEPAGE / SEO / HEALTH_READINESS / REPO_HYGIENE / ARCHITECTURE+CI —— 全部 **ALIGNED**。

### 四域 HIGH 候选对抗结论
权限域跨部门直连路径全部证伪（collection 过滤、can_move_to 权限闸、删除双钩子 fail-closed）但 N-1 成立；认证域闸门旁路候选全部证伪；上传域证伪（无第四入口）；外链域证伪。**主审 BLOCKER=0/HIGH=0 判定在 A 处维持**（A 将 N-1 定级 MEDIUM）。

---

## REVIEWER B（Final-reliability-maintainability-review）

### VERDICT
**APPROVE_WITH_NOTES**（主审 PASS_WITH_FIXES / BLOCKER=0 / HIGH=0 成立；四域 HIGH 候选全部被证伪或降级为 LOW；另发现 3 处 LOW 与 3 处主审措辞不精确）

### CONFIRMED
- **M-1 CONFIRM**（context_processors.py:25 / base.html:97 / home_page.html:103 / home/models.py:286 零消费点 / base.py:347-350 注释失实）。
- **M-2 CONFIRM**（production.py:54-57；local.py 不存在；.gitignore/.dockerignore 均无该文件名）。裁决 TECH_DEBT_NON_BLOCKING 同意。
- **L-1 ~ L-5 全部 CONFIRM**（附 file:line 证据）。

### DISAGREEMENTS（主审措辞/事实不精确，均已修正入主审报告）
1. 主审 MIGRATIONS 节"无数据 migration"不准：home 0002/0004 为 RunPython 数据迁移（官方骨架模式，带 reverse，无风险）。
2. 主审 CI 节"全库唯一 skipif"不准：test_backupkit.py 3 处 `skipUnless(PG_TOOLS)` + test_search_e1_backend.py PG vendor 门控；CI 均满足，不构成降门换绿。
3. 主审 RESTORE 节"缺省 dry-run"不成立：`--dry-run` 为显式 opt-in；缺省＝无参数拒绝/带参数实恢复；安全铁律不依赖该语义，但 docstring 同病（→ L-7）。

### NEW_FINDINGS
- **N-B-1 · LOW**：ops_report.py:60-70 DB 不可达时快照 JSON 丢失（违背自身注释"快照仍如实输出"），exit code 告警锚点仍有效（→ L-6）。
- **N-B-2 · LOW**：backup_restore docstring "缺省 dry-run" 与实现差一档（→ L-7）。
- **N-B-3 · LOW**：恢复媒体目标仅拒精确相等，MEDIA_ROOT 子目录放行（→ L-8）。

### NO_ISSUE_SPOT_CHECKS（11 项，防主审漏报）
SEARCH（三消费位谓词绑定一致；Wagtail 上游源码证实 publish 置 expired=False / 到期 set_expired=True → Q(live)|Q(expired) 恰为 S2∪S3；route() 仅放行 expired；无 N+1）/ PUBLISH_LIFECYCLE（S0/S1/S4 落回内建 404 全矩阵测试）/ MIGRATIONS / CI / TESTS（抽读 7 文件断言密集，lifecycle_state 32 处、search_contract 33 处断言）/ BACKUP（构造的"心跳异常击穿清理"HIGH 候选被证伪——OpsHeartbeat.record 全吞异常 + rmtree 必达有测试锁定）/ RESTORE / RETENTION / MONITORING（心跳失败不拖垮作业双层证实）/ LOGGING / PERMISSIONS —— 全部 **ALIGNED**。

### 四域 HIGH 候选对抗结论
搜索可见性、生命周期 route()、备份/恢复、监控四域构造的 HIGH 候选两例证伪、三例降级为上述 LOW。**主审 BLOCKER=0/HIGH=0 判定在 B 处维持**。

---

# CONSOLIDATED_REVIEW_RESULT

| 项 | 结果 |
| --- | --- |
| Reviewer A | APPROVE_WITH_NOTES |
| Reviewer B | APPROVE_WITH_NOTES |
| 主审 BLOCKER=0 | **双方维持** |
| 主审 HIGH=0 | **被推翻**：A 的 N-1 经主审亲证（矩阵 M-C3 明文＋GPP 子树语义 pages.py:2195＋MoveBulkAction 只拦 delete 复核）升级为 **H-1 · HIGH**（冻结权限规格违反 + 部门账号正常 UI 即可触达 + 条件升级链） |
| 主审 MEDIUM=2 | M-1、M-2 双双 CONFIRM，维持 |
| 主审 LOW=5 | 维持 + 新增 6（B：L-6/L-7/L-8；A：L-9/L-10/L-11）＝ **11** |
| INFO | +2（A：V-9 附件公开面、V-10 图片删除 GCP 缺项）＝ **10** |
| 主审措辞修正 | B 的 3 处（数据迁移计数、skip 门控计数、restore 默认语义）＋ A 的 1 处（PERMISSIONS"封堵"表述）均已修正入主审报告 |
| **最终裁决** | **PASS_WITH_FIXES**（不变）：BLOCKER 0 / HIGH 1 / MEDIUM 2 / LOW 11 / INFO 10 |
| Final Fix Backlog | H-1（容器编辑守卫 + 批量移动收口 + 回归测试）、M-1（feedback_email 接线 + L-11 透传）、M-2（删 local import）为主，L 级 9 项顺手批——合计约一天 |
| NEXT_STEP | **B · FINAL_FIX_REQUIRED**（不变） |

两名 Reviewer 对主审 NO ISSUE 领域共抽查 18 项（A 7 + B 11），全部 ALIGNED，无新增漏报领域。

---

*Review record by 主审 Claude（汇总 A/B 输出并亲证升级项）· 2026-09-01 · 基线 f3bbbed*
