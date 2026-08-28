# 预约发布与排程语义（Publish / Archive / Scheduling）

## 文档信息

| 字段 | 值 |
| --- | --- |
| 文档 | `docs/PUBLISH_ARCHIVE_SCHEDULING.md` |
| 日期 | 2026-08-28（首落盘，M5.1 批次＝§1–§5） |
| 本步范围 | §1–§5：`go_live_at` 预约发布语义、`expire_at` 到期下线边界语义、`publish_scheduled` 任务行为与小时级运行口径、时区（Asia/Shanghai）全链路口径、Featured/推荐位排程交互、分级 A 边界用例表＋断言附录（PA-xx）。§6–§10（到期归档与历史搜索语义）归 M5.2，本文不写 |
| 引源 | 00_MASTER_PLAN §12 M5.1（验收命令＋分级 A）；02_ARCHITECTURE_DOMAIN_PLAN §2.4/§7 S5.1；PRD §7.1/§7.2（预约发布/有效期）、§8（发布归档纠错）、§9（首页推荐位）、§16（环境与部署）；CONTENT_MODEL §14–§19（M3.3 状态机，只读承接，零冲突义务）；上游审计 §3.3（`docs/audit-report-wagtail-upstream.md` L93/L94/L123/L205）；INFORMATION_ARCHITECTURE §7.1/§7.2（推荐位数量固定原则与空缺不渲染口径）；Wagtail 7.4.2 官方源码亲证（位点随文标注，基准路径 `.venv/lib/python3.13/site-packages/wagtail/`，下文 `wagtail/` 前缀均指此）；现有代码与测试（`notices/lifecycle.py`、`home/models.py`、`src/peiligo/settings/base.py`、`tests/test_publish_window.py`、`tests/test_lifecycle_state.py`、`tests/test_lifecycle_transitions.py`，只读事实）；M5.1 设计契约（Human 指令，最高优先级） |
| 分支 | `arch/m5.1-scheduling`（基于 `main` @ 7b622db） |
| 步骤约束 | 只产出本文档；不写代码/迁移/测试/部署；不改其他文档；不进入 M5.2（§6–§10）、M6/M7/G2 |

## 阅读约定

- **DEFERRED_TO_M5_2**：到期归档视图、历史搜索、下线/归档/删除三态对比表、可见性规则总表——属 M5.2（本文 §6–§10 预留位），本文只登记指针，不设计。
- **实现留 B 阶段**：production 周期调度部署（B6 容器落地）、`clean` 校验扩展、settings 时区修改、首页推荐位前台消费（MB8）——本文只冻结语义与验收口径，不落实现。
- **承接声明**：CONTENT_MODEL §14–§19（M3.3）已冻结五状态推导（§14.2）、转换表 E1–E11（§14.3）、字段映射与未来性校验（§16.1/§16.2）、三口径术语（§16.4）。本文是其**验收口径与运维安排**的下游消费者，逐条零冲突；凡 M3.3 已冻结处本文引 § 号不重述。
- **断言编号裁决（处理 CONTENT_MODEL §19.3 登记项）**：本文断言系列为 **PA-xx**（00 §12 M5.1 v1.x 指定；M5.1 设计契约确认）。02 S5.1 草案曾以 PS-01–PS-05 编号预留本文，与 CONTENT_MODEL §18 的 PS-10–PS-29 系列数值无重叠但同名——按 CONTENT_MODEL §19.3 建议"以文档前缀消歧"处理：PS-01–PS-05 逐条映射为本文 PA-01/PA-03/PA-15/PA-18/PA-08（别名映射表见附录 C，内容一字不丢），本文正文不再使用 PS 编号。
- 源码引证格式：`wagtail/<相对路径>:<行号>`（7.4.2 官方包，VERSION=(7,4,2,"final",1)，`wagtail/__init__.py:9` 亲证）；本项目代码引证格式：`<路径>:<行号>`。

## 1. `go_live_at` 预约发布语义

### 1.1 业务状态归属（承接 M3.3 §14.2，零新增）

携带未来 `go_live_at` 的页面在到点前属 **S1 `scheduled`（预约发布中）**。判定谓词＝**修订级** `Revision.approved_go_live_at` 非空（存在待执行预约修订），而非对象级 `Page.go_live_at` 列——依据与残留语义见 CONTENT_MODEL §14.2 注记（E3/E7/E8 均不清对象级 `go_live_at`，对象级残留不参与判定）。本节承接该裁决，不重开。

S1 页面的前台可见性：**前台 404、不出现在任何列表**（CURRENT_DEFAULT＝{S2}，CONTENT_MODEL §16.4；路由内建 404＋列表/搜索均消费 `current_default_pages()`，`notices/lifecycle.py:90-99`）。预约期间后台可编辑、可预览（登录态，§15.2 承接）。

### 1.2 到点机制：官方命令是唯一生效通道

到点正式公开由官方管理命令 **`publish_scheduled`** 执行（E3，系统触发、无人工），项目不自建第二套调度。工作集与动作（源码亲证，详见 §3）：

- 预约登记：保存携带未来 `go_live_at` 的修订并执行 publish → `wagtail/actions/publish_revision.py:113`（`go_live_at > now` 判定，严格大于）进入预约分支：修订级 `approved_go_live_at` 置位并保存（L116-117），同对象其他修订的 `approved_go_live_at` 清空（L119，**单一待执行修订不变式**）；非 live 对象保持 `live=False`（L128）。
- 到点执行：命令取 `approved_go_live_at < now` 的修订（`wagtail/management/commands/publish_scheduled.py:90-93`，严格小于）逐条 `rp.publish(log_action="wagtail.publish.scheduled")`（L114-117）→ `Revision.publish` 委托对象 `publish()`（`wagtail/models/revisions.py:204-217`）→ 转入立即发布分支：`live=True`、清全部 `approved_go_live_at`（`publish_revision.py:130-134`）、`expired=False`（L135）、`last_published_at`/`live_revision` 落定（L140-148）。
- **与项目 helper 的配合**：`notices/lifecycle.py:32-55` `lifecycle_state` 的 S1 谓词 `scheduled_revision` 与官方同源（`wagtail/models/draft_state.py:176-177`，`revisions.filter(approved_go_live_at__isnull=False).first()`；官方状态串 `status_string` 同一谓词，L78-92）。E3 执行后对象级 `go_live_at` 残留不清除（官方行为，§14.2 注），推导仍正确判 S2——已有测试 `tests/test_lifecycle_state.py:101-133`（ResidualGoLiveAtTests）覆盖。

### 1.3 修改预约时间

预约期内重新保存修订＋publish（携带新 `go_live_at`，无论更晚或更早）＝旧待执行修订被清（`publish_revision.py:119` 排他清空）、新修订登记新时刻——**单一待执行修订被整体替换，旧时间作废，以新时间为准**。修改期间对象保持 S1（从未发布页）或 S2b（live 页，见 1.5）。项目侧无额外状态要维护；§16.2 未来性校验链对 NoticePage 同步要求 `expire_at` 仍未来（E11 口径，CONTENT_MODEL §14.3）。

### 1.4 取消预约

取消＝**官方内建 unschedule 动作**（后台修订历史视图，URL 名 `wagtailadmin_pages:revisions_unschedule`，`wagtail/admin/urls/pages.py:135`；实现 `wagtail/admin/views/generic/models.py:1728-1731`：仅置 `revision.approved_go_live_at = None` 并保存，**不动对象级 `go_live_at`**）。取消后回落预约前原态（E4：draft/unpublished/expired 按 §14.2 推导），对象级残留无害（S1 判定不读该列）。既有实测留痕：`tests/test_lifecycle_transitions.py:125-138`（内建视图实测）与 L104-123（三序列回落）。项目不自建取消接口。

### 1.5 live 页的预约修订（"live + scheduled"）

已 live 页面编辑后携带未来 `go_live_at` publish：官方保持 `live=True` 不中断（`publish_revision.py:121-127` 提前 return），状态串为 "live + scheduled"（`draft_state.py:86-88`）——本项目按 CONTENT_MODEL §14.2 判 S2b（有未发布修订），到点后修订内容生效转 S2a。**不产生新状态、不另设校验**（§14.3 已冻结 live→scheduled 无转换边）。

### 1.6 到点可见窗口（验收口径冻结）

官方建议命令**每小时**运行（上游审计 §3.3 引证 `docs/reference/management_commands.md:19-24`；审计 L93）。因此"到达 `go_live_at` 时刻"到"前台可见"之间存在**最长 1 小时任务窗口**（外加单次运行时长）。冻结验收口径：**到点后 ≤1 小时内可见**；该窗口是 B 阶段测试的时间容差依据（02 S5.1 测试要求行），也是产品向运营方沟通的承诺口径。停机错过到点的补偿语义见 §3.4。

## 2. `expire_at` 到期下线语义

### 2.1 边界时刻语义（三段冻结）

设 `expire_at` 时刻为 T，命令运行时刻为 N（均为 timezone-aware 绝对时刻，§4）：

| 时段 | 判定 | 行为 |
| --- | --- | --- |
| 到期前（N < T，含"前一分钟"） | 不属过期集 | 页面保持 S2 live，前台正常展示；带未来 `expire_at` 是 S2 的属性，**不单设状态**（§14.2 注承接） |
| 精确到达边界（N == T） | **仍不属过期集** | 源码严格小于：过期集过滤 `expire_at__lt=now`（`publish_scheduled.py:46`）——`expire_at` 恰等于当前时刻的运行**不执行**下线，留待下一次 N > T 的运行 |
| 到期后（N > T 的首次运行） | 属过期集 | 执行 E7（见 2.2） |

同理预约侧：`approved_go_live_at__lt=now`（`publish_scheduled.py:91-93`）——N == `go_live_at` 的运行不发布，首次 N > `go_live_at` 的运行发布（§1.2）。**边界语义统一口径：所有调度比较为严格不等（`<`），"精确到点"留待下一周期。**

### 2.2 到期动作（E7，承接 M3.3 §14.3/§16.3）

对 `live=True ∧ expire_at < N` 的页执行 `unpublish(set_expired=True, log_action="wagtail.unpublish.scheduled")`（`publish_scheduled.py:85-88`）。`UnpublishAction` 逐行语义（`wagtail/actions/unpublish.py`）：`live=False`（L56-57，仅 live 页生效）、`expired=True`（L61-62）、`live_revision=None`（L59）、清全部修订级 `approved_go_live_at`（L78）。**内容、全部修订、slug/URL 零删除**（数据保留层，§17.5/PS-24 承接）。到期后退出首页与默认列表＝落入 S3、离开 CURRENT_DEFAULT（§16.4）；**到期内容在归档视图/搜索中的可见性归 M5.2 §6–§10（DEFERRED_TO_M5_2），V1 现状＝到期即前台不可见**（PS-25/PS-26 承接，本文不关闭该缺口）。

**仅 live 页生效**：过期集过滤自带 `live=True`（L46），且 `unpublish` 对非 live 对象无操作（L52-57）——draft/scheduled 页的 `expire_at` 永不触发转换（§14.3 非法表；既有测试 `tests/test_lifecycle_transitions.py:181-207`）。

### 2.3 修改 `expire_at`

- **live 页修改**：编辑表单保存新值＋发布修订后，新 `expire_at` 写入对象行（修订内容→对象字段），**旧到期时刻作废，以新值为准**（下一周期按新值比较）。新值须经 §16.2 未来性校验（NoticePage 必填且未来；ArticlePage 填写时须未来）——修改为过去值在 clean 层被拒（`notices/lifecycle.py:70-88`，既有测试 `tests/test_publish_window.py:33-38`）。仅保存修订不发布则不影响 live 页当前值（对象级生效语义）。
- **改晚/改早均合法**：无最小间隔约束；改早可在下一周期提前到期，改晚则旧时刻自然作废。

### 2.4 取消 `expire_at`

按模型政策（CONTENT_MODEL §16.1 冻结表）：**ArticlePage 可空**（取消＝清空字段，clean 放行）；**NoticePage 必填不可取消**（CM-01）；**Material/SoftwareTool/Guide 强制空**（PS-23，无"取消"语义可言）。取消 ArticlePage 的 `expire_at` 后页面转为常青 live，退场方式回落 E8 手动下线（PRD §8）。

### 2.5 已到期内容的重新发布/重新设期

E9（expired → live 立即重发布）/E11（离线 → scheduled 重新预约）：publish 动作原子置 `expired=False`（`publish_revision.py:135`，"发布即非 expired"），NoticePage 须经 §16.2 给出新未来 `expire_at`（`clean_publish_window` 在 E9/E10/E11 三路径同一闸口强制，CONTENT_MODEL §16.2 落实层说明）。重新设期＝E9/E11 后按 2.3 修改口径生效。既有测试：`tests/test_lifecycle_transitions.py:154-177`（E9/E10/E11）。

### 2.6 不建第二套 expiry 状态

`expired` 是 Wagtail 内建列（`wagtail/models/draft_state.py:35-38` 字段族），S3 由内建列纯推导（§14.2），项目零新增状态字段——**禁止也不需要任何与 M3.3 等义的 expiry 状态字段**（M5.1 设计契约；`tests/test_lifecycle_state.py:160-171` 机器形状测试已固化"mixin 零模型字段"）。

## 3. `publish_scheduled` 任务与运行口径（7.4.2 真实行为，源码为证）

### 3.1 命令职责（单一命令，两相动作）

`wagtail/management/commands/publish_scheduled.py`（全文亲证，版本 7.4.2）：

1. **过期相（先执行）**：工作集＝各模型 `live=True ∧ expire_at__lt=now`，按 `expire_at` 升序（L44-49）；逐对象 `unpublish(set_expired=True, log_action="wagtail.unpublish.scheduled")`（L85-88）。查询集先 `list()` 取尽再逐个处理（L83-84 注释明示：防处理过程中游标失效）。
2. **预约相（后执行）**：工作集＝`Revision` 全表中 `approved_go_live_at__lt=now`，按 `approved_go_live_at` 升序（L90-93）；逐修订 `rp.publish(log_action="wagtail.publish.scheduled")`（L114-117）。

**是否同时处理 `go_live_at` 与 `expire_at`：是**——同一命令一次运行先做过期下线、后做预约发布，两相共用一次进程。

- **作用域**：`Page` ＋ 全部非 Page 的 `DraftStateMixin` 模型（L35-40）。本项目 FeaturedItem/SiteSettings 均不混入 `DraftStateMixin`（CONTENT_MODEL §15.4 终判；`home/models.py:86-146/149-188` 亲证为普通 Model）——**结构性不在命令工作集**，其展示窗口是请求时计算的展示语义，非任务驱动（§5.2）。
- **修订内容过期判定为死代码**：`revision_date_expired()`（L8-16）在 7.4.2 中定义但**无任何调用点**（全文件检索亲证）——过期判定以**对象级 `expire_at` 列**为准，不读修订内容中的 `expire_at`。调查结论登记，防止下游误引用。
- **`--dryrun`**：命令支持干跑（L21-33 与两相 dryrun 分支），运维核查可用，不改变库。

### 3.2 幂等性（重跑安全，源码三重保证）

连续重复执行同一命令**不产生额外状态变更**：

1. 过期相过滤自带 `live=True`——已 E7 的对象（`live=False`）不再入选；
2. `unpublish` 对非 live 对象整体短路（`unpublish.py:52-57`，"Does nothing if live is already False"）；
3. 预约相的修订在发布时已清 `approved_go_live_at`（`publish_revision.py:134`）——已发布的修订不再入选。

推论：**错过周期后的补执行天然安全**（§3.4），重复调度（cron 抖动/人工补跑）无副作用。

### 3.3 单次运行失败的处理

- 命令**无整体事务包裹、无逐项 try/except**：某一对象处理抛异常即中断本次运行（Django 命令以非零退出码结束），**已处理对象保持已处理状态，未处理对象原样留待下次**。
- **补偿语义**：工作集每次运行从数据库现态重新推导（`__lt=now` 不设下限，取**全部**历史积压项而非仅近一小时）——停机/失败错过的项在恢复后的下一次运行**自动补执行**，无需人工补偿动作。
- 数据安全：E7/E3 均不删数据（§2.2/§17.5），失败不产生中间丢失态；单项已 `save()` 落库的进度不回滚。
- 运维口径（设计层登记，部署归 B6）：命令非零退出应触发告警（衔接 M7.2 非功能基线监控项）；每小时周期内的单次失败由下一周期自动重试收敛。

### 3.4 小时级运行口径与 production 调度安排（仅设计层记录）

- **频率**：**每小时一次**（官方建议，上游审计 L93 引证 `docs/reference/management_commands.md:19-24`）。冻结为 production 口径；到点→生效的验收容差＝**≤1 小时＋单次运行时长**（§1.6/§2.1）。
- **production 周期调用机制（本轮不做 Docker/PVE/systemd 部署）**：容器环境以**独立 cron/任务容器**（或宿主 crontab）周期执行 `python manage.py publish_scheduled`（上游审计 L123；02 S5.1"容器环境安排：独立 cron/任务容器，B6 落地"）。候选形态二选一，B6 落地时留痕：①独立 cron 容器（部署编排内常驻）；②宿主 crontab 直调容器内命令。约束：与应用容器共享同一数据库与配置；执行身份与告警接入按 M7.2 基线。**本节仅为设计层记录，不在 M5.1 实现任何部署。**

## 4. 时区口径（Asia/Shanghai）

### 4.1 现状核验（settings 亲证）

`src/peiligo/settings/base.py:161-167`：`LANGUAGE_CODE = "en-us"`、`TIME_ZONE = "UTC"`、`USE_TZ = True`；`dev.py`/`production.py` 无覆盖项。**当前配置非 Asia/Shanghai**（`TIME_ZONE="UTC"`），触发设计契约的修复登记分支（4.4）。

### 4.2 全链路时区口径（`USE_TZ=True` 下的 Django 语义，冻结）

| 环节 | 口径 | 依据 |
| --- | --- | --- |
| 存储 | 数据库一律存 **aware UTC**（`USE_TZ=True` 时 Django 自动转换落库） | Django 5.2 `USE_TZ` 官方语义 |
| 后台管理员输入 | Admin 表单 `DateTimeField` 按**当前时区**（由 `TIME_ZONE` 决定）把输入的钟面时间解析为 aware 时刻；当前＝UTC（管理员被迫以 UTC 输入），修复后＝Asia/Shanghai 钟面 | Django 当前时区机制（`TIME_ZONE` 为缺省当前时区） |
| Wagtail 调度 | `publish_scheduled` 两相比较均为 `timezone.now()`（aware UTC 绝对时刻）对 DB aware UTC 列——**`TIME_ZONE` 取值不影响任何调度判定结果**（绝对时刻等价） | `publish_scheduled.py:46/92` 亲证：比较对象是 aware 绝对时刻 |
| 前台显示 | 模板 `date`/`time` 过滤器按当前时区渲染 aware 时刻；修复后访客见 Asia/Shanghai 钟面 | Django 模板时区过滤器语义 |

**边界不变式：所有时间边界（`go_live_at`/`expire_at`/`approved_go_live_at`/FeaturedItem `start_at`/`end_at`）一律 timezone-aware，禁止 naive datetime。** 现状核验：`clean_publish_window` 用 `timezone.now()`（`notices/lifecycle.py:86`）、测试 helpers `future()` 基于 `timezone.now()`（`tests/helpers.py:108-109`）、既有调度测试全部 aware＋mock 推进（`tests/test_lifecycle_transitions.py:33-36`）——全链路无 naive 使用点。

### 4.3 业务时区＝Asia/Shanghai 的含义

业务时区作用于**输入与显示两个钟面层**（管理员以北京时间填表、访客以北京时间看到时刻），不作用于**调度判定层**（绝对时刻比较，§4.2 第三行）。故切换业务时区是纯表示层变更，生命周期语义零变化。

### 4.4 最小正式修复方案（实现留 B 阶段/下一阶段）

- **修改**：`src/peiligo/settings/base.py` 单行 `TIME_ZONE = "UTC"` → `"Asia/Shanghai"`；`USE_TZ = True` **不动**（aware 不变式的前提）。非 DB schema 项，**零迁移**。`LANGUAGE_CODE` 的 i18n 决策不属本文范围，不扩围。
- **不破坏现有生命周期的测试证明思路（2026-08-28 评审修正前提）**：①既有测试**除一处外**全量使用 aware 时刻（`timezone.now()`/`future()`）与 `mock.patch("django.utils.timezone.now")` 推进，调度类断言与钟面表示解耦；**例外＝墙钟钟面断言一处**：`tests/test_permissions_admin_boundary.py:163-164`（`test_create_featured_item`）对 FeaturedItem `start_at`/`end_at` 做 `strftime("%Y-%m-%d %H:%M")` 钟面等值比较——表单 `DateTimeField.to_python` 逐支经 `from_current_timezone` 按当前时区把提交的 naive 钟面转为 aware（`django/forms/fields.py:543-561`＋`django/forms/utils.py:215-227`），落库 aware UTC，ORM 读回 aware UTC，裸 `strftime` 渲染 UTC 钟面：`TIME_ZONE="UTC"` 下两钟面恰好相等所以现绿；切 Asia/Shanghai 后提交钟面按 +08:00 解析、读回 UTC 钟面为 "01:00"，两行断言**必红**；②该测试的同步调整步骤（随时区修复一并执行，实现阶段动作，本文不改测试代码）：两行读回断言改为 `timezone.localtime(fi.start_at).strftime("%Y-%m-%d %H:%M")`（`end_at` 同法），或等价改为与 `datetime(2026, 9, 1, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))` 的 aware 绝对时刻等值比较——断言语义不变（仍验证表单→DB→读回钟面往返一致），仅消除对 `TIME_ZONE` 取值的隐式依赖；③调整后在 `TIME_ZONE="Asia/Shanghai"` 下复跑全量测试套件，期望全绿（调度比较与钟面表示解耦的推论，前提＝②已执行）；④补一条表示层等价断言（PA-19）：同一绝对时刻（如 `2026-01-01T16:00:00+00:00` ＝北京时间 `2026-01-02 00:00`）在两种 `TIME_ZONE` 配置下 E3/E7 判定与 `CURRENT_DEFAULT` 成员关系完全一致；⑤表单输入回归：Admin 保存 `expire_at` 后 DB 值的绝对时刻与表单钟面＋Asia/Shanghai 偏移一致。
- 该修复的执行时点与批次归属实现阶段排期（本文只登记方案与证明思路，不改 settings——M5.1 禁改代码）。

## 5. Featured/推荐位交互与边界用例表

### 5.1 调查结论（正式存在性核验，非计划假定）

**FeaturedItem 已正式存在于本仓库**（模型与判定层）：

- 模型：`home/models.py:86-146`（`content` FK CASCADE→Page、`start_at`/`end_at`/`enabled`，clean 成对校验 `end ≥ start`），migration `home/migrations/0005_featureditem_sitesettings.py`；
- 展示有效性判定：`is_on_display()`（`home/models.py:136-146`）＝**四条件合取**：`enabled` ∧ `start_at ≤ now ≤ end_at` ∧ 所指页 `lifecycle_state == live`（∈ CURRENT_DEFAULT）——即 CONTENT_MODEL §15.4 语义冻结的落地实现；
- 管理与测试：仅总管理员管理（M4 权限，`tests/test_permissions_admin_boundary.py:148-161` N06）；字段/窗口/级联测试在案（`tests/test_taxonomy_snippets.py:67-95`、`tests/test_deletion_policy.py:149-192`）；
- **前台消费尚未实装**：`home/templates/home/home_page.html:10-12` 仅占位注释（"推荐位/置顶位……MB8"），`HomePage.get_context` 不查询 FeaturedItem（`home/models.py:40-54`）——首页渲染属 B 阶段（MB8）。

据此走设计契约"**已存在 → 冻结交互规则**"分支：以下 5.2 冻结项对现存模型成立、对 MB8 前台消费构成实现契约。

### 5.2 交互规则冻结（不新增平行 publication 状态）

1. **未到 `go_live_at` 的内容不得因推荐位提前公开**：`is_on_display` 第四条件（所指 ∈ CURRENT_DEFAULT）已结构性排除 S1——推荐位不是绕过预约的旁路。MB8 前台消费必须以该谓词（或等价 queryset `live ∧ ¬expired`）过滤，**禁止**仅按 `enabled`＋起止窗口渲染后交由页面路由兜底。
2. **expired/offline 内容不得因推荐位继续出现在默认前台**：同第四条件排除 S3/S4（及 S0）。到期/下线后推荐项在首页即时失效——**无需等待任何任务**（请求时计算，非 `publish_scheduled` 驱动）。
3. **推荐项引用不可见内容时前台安全降级**：逐项过滤跳过——不渲染占位、不抛错、**不泄漏不可见内容的标题/摘要**；有效项可少于槽位数；全部无效或无推荐时**区块整体不渲染**（IA §7.1 冻结口径："空缺时区块整体不渲染"）。被引内容被永久删除时 FeaturedItem CASCADE 同删、零悬挂（CONTENT_MODEL §17.3/PS-13，`tests/test_deletion_policy.py:172-174` 在案）。
4. **不新增平行 publication 状态**：FeaturedItem 不混入 `DraftStateMixin`（§15.4 终判），`start_at`/`end_at`＋`enabled` 是**展示窗口**语义，不是生命周期状态，不与 `go_live_at`/`expire_at` 构成双源。结构性不在 `publish_scheduled` 工作集（§3.1）。
5. **数量固定**：槽位总数为固定常量（IA §7.2"数量固定原则"），V1 默认槽位数**建议 6**（02 S5.1，**标记：项目负责人确认**），实现阶段在站点级配置给定并留痕，不写入模型字段。超出槽位的申请一律不展示。
6. **管理权与申请通道**：仅总管理员管理 FeaturedItem（PRD §8/§9；M4 已落实）；部门置顶申请走统一工作邮箱，不建模自助通道（PRD §8、IA §7.2）。
7. **时区口径**：`start_at`/`end_at` 全链路同 §4（aware 存储、Asia/Shanghai 钟面输入显示、比较为绝对时刻）；窗口边界 `start_at ≤ now ≤ end_at` 为**闭区间**（含两端，`home/models.py:144` 亲证），与 §2.1 生命周期的严格 `<` 不同——两者是不同对象的边界口径，各自冻结，不得混用。

### 5.3 边界用例表（测试要求分级 A）

实现阶段约束（写入断言附录，PA-30）：**测试不得 sleep**；用可控时间（`mock.patch("django.utils.timezone.now")` ＋ `call_command("publish_scheduled")`，既有模式 `tests/test_lifecycle_transitions.py:33-36`）或直接设置模型/DB 时间后运行正式命令（`queryset.update(expire_at=...)` 绕过 clean 模拟时间流逝，既有模式 L40-42）。

| # | 用例 | 期望（断言摘要） | 断言 |
| --- | --- | --- | --- |
| B01 | 未来 `go_live_at`（S1，未到点） | 前台 404、不入任何列表；状态 S1（修订级判定） | PA-01 |
| B02 | 精确 `go_live_at` 边界（N == T 运行） | 严格 `<`：本次不发布，仍 S1；N > T 首次运行发布 | PA-02 |
| B03 | 过去 `go_live_at`（到点后命令运行） | E3 转 live、入 CURRENT_DEFAULT；到点→可见 ≤1 小时窗口 | PA-03 |
| B04 | 修改 `go_live_at` 到更晚（或更早） | 旧待执行修订作废、单一新时刻生效；不早于/晚于新时刻泄漏 | PA-04 |
| B05 | 取消预约（内建 unschedule） | 回落预约前原态（E4）；对象级残留不误判 S1 | PA-05 |
| B06 | live 页＋未来 `expire_at` | 保持 S2、前台正常展示（未来到期是属性非状态） | PA-06 |
| B07 | 精确 `expire_at` 边界（N == T 运行） | 严格 `<`：本次不下线，仍 live；N > T 首次运行下线 | PA-07 |
| B08 | 过去 `expire_at`（到点后命令运行） | E7 转 S3、退出首页与默认列表；数据/修订/URL 零删除 | PA-08 |
| B09 | 修改 `expire_at`（live 页，改晚/改早/改过去） | 新值经 clean 未来性强制；发布修订后旧时刻作废以新值为准；改过去被拒 | PA-09 |
| B10 | 取消 `expire_at` | Article 清空合法转常青；Notice 必填被拒；三类常青强制空不变 | PA-10 |
| B11 | 已到期内容重新发布/重新设期（E9/E11） | `expired` 复位、Notice 新未来有效期强制；重设期按新值生效 | PA-11 |
| B12 | `go_live_at ≥ expire_at` 组合 | 官方 admin 表单拒 `>`（相等放行，仅覆盖表单路径，§5.4）；项目语义更严判非法（含相等），校验归属＝clean 层扩展（补脚本/API 路径） | PA-12 |
| B13 | 已发布内容设置未来 `expire_at`（首发即带） | 同 B06：S2 属性、到点前可见 | PA-06 |
| B14 | `publish_scheduled` 重跑（同刻连续两次） | 第二次零状态变更（幂等三重保证） | PA-13 |
| B15 | 单次运行中项失败后下一周期 | 已处理项保持、失败/积压项自动补执行（工作集重推导） | PA-14 |
| B16 | FeaturedItem 指向 S1/S3/S4/S0 页 | `is_on_display` 为 False（四条件合取）；首页不出现 | PA-16 |
| B17 | FeaturedItem 窗口边界（start/end 当刻） | 闭区间：`start_at ≤ N ≤ end_at` 当刻有效；窗外 False | PA-15 |
| B18 | 推荐位数量与降级 | 有效项 ≤ 槽位常量；无效项跳过不占位不泄漏；全无效区块不渲染 | PA-17/PA-18 |

### 5.4 `go_live_at ≥ expire_at` 非法组合的校验归属（裁决）

- **官方语义（2026-08-28 评审修正，源码亲证）**：Wagtail 7.4.2 admin 表单**存在**该校验——`WagtailAdminDraftStateFormMixin.clean`（`wagtail/admin/forms/models.py:234-258`）在表单提交时校验两条：①`go_live_at`/`expire_at` 同时非空且 `go_live_at > expire_at` 时对两字段 `add_error`（"Go live date/time must be before expiry date/time"）——**严格大于才拒，相等放行**；②`expire_at < timezone.now()` 时报错（"Expiry date/time must be in the future."）——严格过去才拒（等于当下放行），对 `go_live_at` 本身无未来性要求。该 mixin 由 `wagtail/admin/panels/base.py:47-48` 注入**全部 `DraftStateMixin` 模型**的 admin 表单（页面编辑表单即含）；错误时机＝admin 表单提交（`clean()` 内），模型层与命令层（`publish_scheduled`）不复检。官方口径的残留缺口：相等组合可经 admin 提交——到点发布时 `expire_at` 已成过去，下一次运行即 E7 下线（"上线即已过期"窗口经相等路径可达，最长约 1 小时）；脚本/API 等非表单路径完全绕过该校验。
- **产品语义**：该组合对 NoticePage 无意义（发布即为立即过期），属无效配置。
- **校验归属裁决（修正后）**：归**项目 clean 层**（`notices/lifecycle.py` `clean_publish_window` 扩展：`go_live_at` 与 `expire_at` 同时非空时须 `go_live_at < expire_at`），与 §16.2 未来性同一闸口（发布动作经同一校验链）；**实现留 B 阶段**，本文冻结语义与断言（PA-12）。保留理由（修正后）：官方校验仅覆盖 admin 表单路径——脚本（shell/数据脚本）、API、未来后台定制路径不经过该表单，项目 clean 层是唯一全路径闸口。**口径差异**：PA-12 严于官方（官方相等放行，本项目须严格 `<`），以更严口径同时封死经 admin 相等路径触达的"上线即已过期"窗口。不归属 admin 表单定制、不归属任务层兜底。

## 6. 到期归档区语义（历史归档视图）

> 本节起为 M5.2 批次增补（2026-08-28，分支 `arch/m5.2-archive-search`，基于 main@bd4b822）。§1–§5 与附录 A/B/C 既有内容（M5.1 冻结）零改动；§2.2 与阅读约定登记的 DEFERRED_TO_M5_2 指针自本节起兑现。CONTENT_MODEL §16.4 预冻结的三口径术语（CURRENT_DEFAULT / HISTORICAL / ARCHIVE-SEARCH）与状态谓词是本节地基，凡该文已冻结处本文引 § 号不重述。

### 6.1 每板块设「历史归档」视图（语义冻结，URL 留 B 阶段）

- **视图设置**：五个一级板块（`chronicle`/`events`/`materials`/`software`/`guide`，§1.4 板块推导规则单一事实源）各设一个「历史归档」视图。URL 形态（如 `/chronicle/archive/` 之类）与入口呈现（导航位/页内入口）留 B 阶段裁定（02 S5.2 记为 B4；实施挂接＝归档查询 MB8、前台模板 MB9、搜索谓词 MB10，00 §16 步骤表），本文只冻结语义。
- **queryset 口径**：归档视图消费 **HISTORICAL 集**（§16.4）＝CURRENT_DEFAULT ∪ {S3 expired}＝S2 ∪ S3；实现谓词＝`Q(live=True) | Q(expired=True)`（`live ∧ expired` 经 E7 原子置位不可达，§14.2 注，故合取互斥等价）。expired 条目必须带「已过期」标注——标注语义＝可见的「已过期」文字徽标（视觉样式细节 B 阶段），不得仅以排序靠后/灰化等隐式方式表达。
- **对象域**：五类内容页（§14.1 适用对象）；结构页/容器/Snippet/设置不入（与 §21.1 搜索对象域同口径）；板块内对象域＝该板块推导规则（§1.4）约束下的内容页子集。
- **expired 子集的类型构成**：S3 仅由 E7 产生，而 Material/SoftwareTool/Guide 的 `expire_at` 强制空（PS-23/PA-10）结构性不入过期集——**expired 子集＝过期通知＋过期文章**（ArticlePage `expire_at` 可选，§2.4）。资料/软件/指南三板块的归档视图仍按统一语义设置（live 全集即其内容面），expired 子集结构性为空：不特判、不省略视图、不因空而跳板。
- **默认排序**：发布时间倒序（`-first_published_at`，§21.6 全站口径；PRD §7.1「默认按发布时间倒序展示」对归档视图同样成立），expired 条目与 live 条目同序混排，V1 无降权规则（如需降权/分区段→走变更流程）。
- **成员资格＝状态基础（非时刻基础）**：入归档集以 E7 已执行（状态 S3）为准，非 `expire_at` 时刻到达——到期时刻与入列之间存在 ≤1 小时任务窗口（§1.6/§2.1 同口径），窗口内页面仍属 S2、仍在默认列表，不提前入归档。反之 E9 重发布即时回 CURRENT_DEFAULT、撤出 expired 子集（前台可见性请求时判定，无任务依赖）。

### 6.2 R4 张力处置（显式裁决）

上游审计 §3.3「注意张力」（审计 L95）/风险 R4（审计 L165）：Wagtail 默认前台/搜索只出 live 内容 vs PRD §7.1「到期后自动退出首页和默认列表，但保留在历史归档及站内搜索中」。裁决：

1. **张力不构成冲突，构成分层**：PRD 该句自身已给出拆分——「退出首页和默认列表」＝CURRENT_DEFAULT 消费位（live-only 不动）；「保留在历史归档及站内搜索中」＝HISTORICAL/ARCHIVE-SEARCH 消费位（视图层放宽谓词）。两层并行、各守各的谓词，互不修改。
2. **实现归属＝项目前台 queryset 过滤层**：复用 §1–§5 冻结的谓词体系同源扩展——现状 `current_default_pages()`（`notices/lifecycle.py:98-107`）与 `_current_default_search_queryset()`（`search/services.py:197-202`，V1 现状＝到期即前台/搜索不可见，PA-24 所记）之上派生 HISTORICAL/ARCHIVE-SEARCH 谓词，仅在归档视图与搜索入口消费。**不 patch Wagtail core、不新增平行状态字段**（PA-23 承接）：归档可见性是查询口径，不是状态——`live`/`expired` 内建列经 §14.2 推导已完备承载。
3. **术语口径**：本项目无独立「归档」动作、无 `archived` 状态列——「归档」（PRD §8「通知到期自动归档」）＝到期（E7）的结果态 S3 经 HISTORICAL/ARCHIVE-SEARCH 口径可见的合称。任何实现不得引入 archived 布尔列或第二套归档状态机（PA-23）。

### 6.3 expired 条目的正文可达性（裁决）

- **语义不变式**：经归档视图或搜索结果到达的 expired 条目，其内容正文对匿名访客必须可读，且呈现带「已过期」标注——这是 PRD §7.1「保留在历史归档及站内搜索中」的可读性兑现；条目可查出但链接 404 的「保留」名存实亡，不满足该条款。
- **对比语义**：S4 手动下线与 S0/S1 无此不变式——具名 URL 404、搜索不可见（02 S5.2 草案 PA-04/PA-06 断言，本文 PA-34/PA-36）。expired 可达与下线 404 的差异是三种退场方式（§8）的刻意区分，非实现巧合。
- **实现载体留 B 阶段**：满足不变式的两种候选形态——①expired 页原 slug URL 放行渲染（路由对 S3 消费 HISTORICAL 谓词，页首加「已过期」横幅）；②归档视图/搜索结果内嵌呈现（原 URL 保持 404）。形态选择随 URL 形态归 B4/MB8–MB9 裁定并留痕；**无论何种形态，本节不变式与 S0/S1/S4 的 404 口径不变**。
- **载体①差异登记义务（2026-08-28 收口评审冻结）**：载体①「expired 页原 slug URL 放行渲染」与 CONTENT_MODEL §16.4 CURRENT_DEFAULT 行「前台路由（非本集具名 URL＝404）」存在字面差异（S3 ∉ CURRENT_DEFAULT 而其具名 URL 渲染，超出 HISTORICAL 行消费位置「各板块『历史归档』视图」的字面覆盖）——**B 阶段若选载体①，须在 CONTENT_MODEL §16.4 补差异登记行（HISTORICAL 消费位的具名 URL 放行），随 MB8–MB9 一并留痕**；该义务在设计层即冻结，不留待实现期才发现。载体②（原 URL 保持 404）与两行零字面差异，无此义务。
- **与 §16.4 零冲突**：CONTENT_MODEL §16.4 CURRENT_DEFAULT 行「前台路由（非本集具名 URL＝404）」冻结的是 CURRENT_DEFAULT 消费位语义，本节不动它；S3 的正文可达性属 §16.4 **HISTORICAL 行**（消费位置＝归档视图，落地批次＝M5.2）授权范围内的 M5.2 细化——HISTORICAL 消费位覆盖「归档视图内的条目呈现（含其正文）」，是对该行的兑现而非修改。

### 6.4 PA-24 缺口闭环登记

M5.1 PA-24 登记「V1 现状＝到期即前台不可见，任何实现不得声称已提供历史归档查询」。闭环路径显式登记：

- **语义层（本文闭合）**：§6–§10 落地即闭合——HISTORICAL/ARCHIVE-SEARCH 的语义、消费位与断言（PA-31–PA-36）自本文起存在。
- **实现层（B 阶段回填）**：代码缺口（归档视图未实装、搜索谓词仍 live-only）由 B 阶段回填——归档视图与 URL/载体形态归 MB8–MB9、搜索谓词放宽归 MB10；回填前 PA-24 断言持续有效（守门：任何实现/文档不得虚假声称已提供），回填后验收口径移交 PA-31–PA-36，PA-24 保留为附录 A 历史登记（可增不可减，效力窗口＝M5.2 设计落地至 B 阶段回填之间）。

## 7. 前台可见性规则总表（逐位置）

对齐锚点＝PRD §7.1 原文：「到期后自动退出首页和默认列表，但保留在历史归档及站内搜索中。」

| 前台位置 | 消费口径（谓词） | S2 live | S3 expired | S0/S1/S4 | 标注义务 |
| --- | --- | --- | --- | --- | --- |
| 首页列表区 | CURRENT_DEFAULT（live ∧ ¬expired） | 可见 | 不可见（自动退出） | 不可见 | — |
| 首页推荐位 | `is_on_display` 四条件合取（§5.2 冻结） | 窗口内可见 | 不可见（请求时即时失效） | 不可见 | — |
| 板块默认列表 | CURRENT_DEFAULT（＝CURRENT_DEFAULT_SEARCH 同谓词，§21.5/PS-33；现状 `search/services.py:197-202`） | 可见 | 不可见 | 不可见 | — |
| 板块历史归档视图 | HISTORICAL（§6.1） | 可见 | 可见 | 不可见 | expired 条目「已过期」徽标 |
| 站内搜索（`/search/` 与各搜索入口） | ARCHIVE-SEARCH（§7.1） | 可见 | **默认命中** | 不可见（恒不入任何搜索口径，PS-25/PS-34） | expired 结果「已过期」标注 |
| 具名 URL 直达（路由） | §6.3 裁决 | 渲染 | 正文可达＋「已过期」标注（载体 B 阶段裁定） | 404 | expired 页「已过期」标注 |

补充口径：

- **未发布/已下线（S0 草稿/S1 预约未到点/S4 已下线）＝任何前台位置与搜索均不可见**（§16.4/PS-25；PRD §23 必测项「未发布或已下线内容不会公开展示」）。
- **推荐位不随归档放宽**：§5.2 四条件冻结不变——expired 内容不因 HISTORICAL 口径回流推荐位；归档语义只作用于归档视图与搜索两个消费位。
- **后台/预览不在本表**：登录态编辑与内建预览沿 §15.2 承接，不受三口径约束。
- **入口绑定义务**：板块默认列表入口与搜索入口各自消费对应口径（默认列表＝CURRENT_DEFAULT、搜索＝ARCHIVE-SEARCH），两入口共用字段契约与筛选参数（§21），仅可见性谓词不同——实现须将谓词按入口绑定，不得因共用代码层把 expired 泄入默认列表（PA-31 守门）。

### 7.1 ARCHIVE-SEARCH 细则（搜索含 expired）

- **谓词**：搜索对象域默认放宽至 ARCHIVE-SEARCH＝S2 ∪ S3（M3.4 §21.5 预告兑现）：在 §21.1 对象域（五内容页）上把 `live ∧ ¬expired` 放宽为 `Q(live=True) | Q(expired=True)`（同 §6.1 口径）。实现形态＝`_current_default_search_queryset()` 的归档变体（同源扩展，§6.2-2），归 MB10。`FilterField("expired")` 已声明（§20.1 表 A）——谓词放宽**零结构变更、零新增 FilterField/索引字段**（§21.5 预期「同一字段契约＋放宽谓词」的兑现）。
- **类型口径（裁决）**：§16.4/§21.5/PRD §7.1 原文均为「expired **通知**」——本文冻结：**下限承诺＝过期通知必入（PA-33 验收锚点，PRD 驱动）；实际口径＝S3 状态中性（过期文章同入）**。理由：三口径定义于状态而非类型（§16.4）；HISTORICAL（归档视图）已类型中性，搜索若仅收通知将造成同一 S3 状态在归档可见而搜索不可见的口径分裂；常青三类型结构性无 S3（§6.1），状态中性零扩围副作用。
- **标注**：expired 结果条目带「已过期」标注（与归档视图徽标同语义同文案；样式细节 B 阶段）。
- **组合执行不变**：filter-first＋保序旋钮（§21.6）对 ARCHIVE-SEARCH 同样成立——先放宽可见性谓词，再施加 §21.1–§21.2 筛选维度与 `.search(q, order_by_relevance=False)`；排序默认发布时间倒序（§6.1 同口径，expired 无降权）。
- **「默认」的含义**：含 expired 是搜索的缺省口径，不设用户开关（V1 不新增公开参数，§21.4；未来如需时间/状态筛选参数→走变更流程）。

### 7.2 与 M3.3/M3.4 契约零冲突对照（独立审查锚点）

| 冻结项 | 本文消费方式 | 冲突判定 |
| --- | --- | --- |
| CONTENT_MODEL §14.2 五状态推导 | 归档/搜索可见性全部挂 S2/S3 状态，零新状态、零新列 | 零冲突（PA-23 承接） |
| CONTENT_MODEL §16.4 三口径定义 | HISTORICAL/ARCHIVE-SEARCH 按定义兑现（消费位/标注义务照抄），CURRENT_DEFAULT 行不动 | 零冲突（§6.3-4 读法登记） |
| CONTENT_MODEL §16.4 三口径定义——ARCHIVE-SEARCH 对 PRD §7.1 字面（行 2 补记） | §16.4 三口径按定义兑现零冲突（行 2 判定不变）；ARCHIVE-SEARCH 口径状态中性（S2∪S3）超出 PRD §7.1「expired 通知」字面 | 显式登记差异（非冲突）——差异读法见表下补记行 |
| CONTENT_MODEL §17.5 恢复边界表 | §8 三态表在其上扩列可见性/搜索/留痕维度，恢复边界逐行一致 | 零冲突（该表注明的 M5.2 §8 兑现） |
| CONTENT_MODEL §21.5/PS-34 差异登记 | 「落地前不得声称已提供」口径照抄（§6.4）；谓词放宽零结构变更（§7.1） | 零冲突（其预告的 M5.2 细则即本文） |
| CONTENT_MODEL §24.1 PS-33 | PS-33 冻结的是 V1 现状谓词（live ∧ ¬expired 不含 expired）——M5.2 后搜索口径升级为 ARCHIVE-SEARCH，PS-33 的守门对象（draft/scheduled/unpublished/容器/结构页不入）全部保持，唯一差异＝expired 由排除改纳入（其 §21.5 行预告授权） | 显式登记差异（非冲突） |

**表下读法（行 2 补记，2026-08-28 收口评审）**：差异内容＝ARCHIVE-SEARCH 类型口径由 PRD §7.1「expired 通知」字面放宽为状态中性（S2∪S3）——下限承诺＝过期通知必入（§7.1 类型口径裁决，PA-33 验收锚点），依据＝§16.4 三口径定义于状态而非类型。同款差异于 HISTORICAL（归档视图）侧同样成立（过期文章同入归档视图，§6.1 expired 子集＝过期通知＋过期文章），下限承诺同为过期通知必入——两处均按行 5（PS-33）同款「显式登记差异（非冲突）」登记，非冲突。

## 8. 下线 / 归档 / 永久删除三态对比表

CONTENT_MODEL §17.5 冻结恢复边界表并注明「完整三态对比表归 M5.2 §8」——本节兑现。三态＝同一内容页的三种互斥退场处置：

| 维度 | 到期归档（E7 → S3） | 手动下线（E8 → S4） | 永久删除（§17.2） |
| --- | --- | --- | --- |
| 触发与执行者 | 系统自动（`publish_scheduled` 过期相，无人工） | 部门账号（仅本部门内容）／总管理员，手动即时 | 仅总管理员，手动 |
| 适用对象 | 携 `expire_at` 的 live 页（仅 live 页可被到期，PA-26） | 任何 live 内容页（通知可先于到期下线，§14.3 E8） | 测试数据/违法内容/明确无保留价值记录（PRD §8 三情形，不得扩围） |
| 结果 | S3 expired | S4 unpublished | Page 行＋全部修订硬删，对象不复存在 |
| 内容/修订/slug-URL 数据 | 全保留（§2.2） | 全保留 | 硬删，产品内不可恢复（仅运维备份恢复，PRD §15） |
| 首页/默认列表/推荐位 | 不可见（退出 CURRENT_DEFAULT，推荐位即时失效） | 不可见 | 不可见 |
| 历史归档视图 | 可见＋「已过期」标注 | 不可见 | 不可见 |
| 站内搜索 | 默认命中＋标注 | 不可见 | 不可见 |
| 具名 URL 直达 | 正文可达＋标注（载体 B 阶段，§6.3） | 404 | 404 |
| 产品内恢复 | E9 重新发布（通知须新未来有效期，§2.5） | E10 重新发布 | 无恢复路径（运维事件非产品能力） |
| 操作留痕 | 内建日志（`wagtail.unpublish.scheduled`） | 内建日志（`wagtail.unpublish`）＋修订史 | 内建页面日志（`wagtail.delete`；审计载体口径＝§9.2/PA-35） |
| 连带影响 | 无 | 无 | FeaturedItem 级联同删（§17.3 CASCADE，零悬挂）；部门/词表 PROTECT 拦截按 §17.3 |

读法要点：

- 「归档」与「下线」的**前台差异仅在历史归档视图与站内搜索两处**（§7 总表）；首页/默认列表两者同不可见——PRD §7.1「退出首页和默认列表」同时覆盖两种退场。
- 到期 vs 下线的先后：E8 先于到期执行则页面已非 live，过期集 `live=True` 过滤不再入选（§2.2）——手动下线优先，到期动作幂等跳过，不产生 S4→S3 二次转换（§14.3 无该边）。
- 默认退场路径＝E7/E8（§17.1「内容默认下线或归档，不直接永久删除」）；永久删除是仅总管理员的例外通道，非运营常规动线。

## 9. 纠错与下架快速通道

### 9.1 常规纠错反馈通道（PRD §8 末两条）

- 每个内容页提供统一工作邮箱反馈入口（mailto 链接），**邮件自动带上内容标题与页面地址**（PRD §8 原文）；邮箱单值＝`SiteSettings.feedback_email`（`home/models.py:173-175` 亲证，help_text 已冻结同款语义，与指南投稿邮箱同源）。
- V1 不建站内工单/表单/投诉状态流（PRD 无此要求）；反馈处理为线下流程，处理动线＝编辑修正后发布修订（E5/E6）或按需 E8 下线。
- 呈现细节（链接位置、标题/地址注入格式）＝B 阶段模板实现，语义在此冻结。

### 9.2 版权/安全投诉下架快速通道（PRD §11 末段；CONTENT_MODEL §17.2 承接）

收到版权或安全投诉时（总管理员动线）：

1. **立即隐藏＝立即 unpublish（E8）**：转 S4——任何前台位置与搜索**即时**不可见（§7 总表；可见性请求时判定，无任务窗口——E8 是手动即时动作，与 E7 的 ≤1 小时任务窗口性质不同）。「立即隐藏」用下线实现而非删除（与 §17.1 默认路径一致）。
2. **内部记录＝天然留痕**：E8 的修订史＋内建操作日志（`wagtail.unpublish`，操作者＋时间）即内部处理记录；**V1 不新建投诉/下架审计模型**（PRD 无此要求；PA-23——投诉处理状态不入模型，线下台账承载）。
3. **核实后二择**：恢复＝E10 重新发布（即时回 CURRENT_DEFAULT）；确属违法/无保留价值＝§17.2 永久删除（仅总管理员，适用范围照 PRD §8 三情形）。核实期间内容对公众不可见、对后台登录态可见可编辑（§14.3 编辑正交声明）。
4. 本节即 M7.1 独立审查所引「纠错下架通道〔引用 S5.2 §9〕」的落点；同口径断言＝PA-34（下线即全前台不可见）。

## 10. 测试断言（PA-31–PA-36；02 S5.2 草案六条全量落档）

断言续号自 PA-31 起（附录 A「可增不可减」）。02 S5.2 草案自带的 PA-01–PA-06 与本文 M5.1 既有 PA-01–PA-06 同名不同义，按附录 C 同款续号方式映射消歧（别名映射表见附录 D，草案原文编号在表内保留）。六条断言是 PRD §23 两条必测项——「通知到期后自动归档」「未发布或已下线内容不会公开展示」——的设计源（02 S5.2 测试要求行）：

| 断言 | 用例 | 期望（断言摘要） | PRD § |
| --- | --- | --- | --- |
| PA-31 | 通知到期（E7 执行后） | 退出首页与全部板块默认列表（CURRENT_DEFAULT 不含）；推荐位即时失效——与 PA-32/PA-33 成对断言的「不可见」侧 | §7.1/§23 |
| PA-32 | 同一到期页在板块历史归档视图 | 可见且带「已过期」标注；HISTORICAL 谓词（live ∪ expired）成立 | §7.1/§8/§23 |
| PA-33 | 同一过期通知经站内搜索 | 默认命中且结果带「已过期」标注（ARCHIVE-SEARCH，无用户开关） | §7.1/§10/§23 |
| PA-34 | 手动下线（E8）内容 | 具名 URL 404 且搜索/归档视图均不可见（S4 与 S3 的刻意对比，§6.3） | §8/§11/§23 |
| PA-35 | 永久删除 | 仅总管理员可执行（部门账号被拒）；产生审计记录＝内建页面日志（`wagtail.delete`，操作者＋时间，§17.2/§9.2 载体口径）；FeaturedItem 级联零悬挂（§17.3） | §8 |
| PA-36 | 未发布草稿（S0）与预约未到点（S1） | 任何匿名路径（具名 URL/首页/默认列表/归档视图/搜索）均不可达、不可见 | §8/§23 |

- **成对断言要求（00 §12 M5.2 测试要求）**：「到期后默认列表不可见＋归档/搜索可见」双断言必须成对出现——PA-31 与 PA-32/PA-33 在同一测试用例组内对**同一页面对象**先后断言（同一 E7 后对象：先断默认列表/首页不含，再断归档视图含＋搜索命中），禁止只在单一位置断言。
- **测试实现约束（PA-30 承接）**：不得 sleep；用 `mock.patch("django.utils.timezone.now")`＋`call_command("publish_scheduled")` 或 `queryset.update(expire_at=...)` 直设时间后跑正式命令（既有模式 `tests/test_lifecycle_transitions.py:33-42`；PA-01–PA-30 落档先例＝`tests/test_publish_scheduled_boundaries.py`，本批断言同款扩展）。

## 11. 可追溯性补行（M5.2）

| 条目 | PRD § |
| --- | --- |
| §6 历史归档视图语义（HISTORICAL 消费、R4 处置、正文可达性、PA-24 闭环） | §7.1（保留在历史归档）、§8（通知到期自动归档） |
| §7 可见性规则总表＋ARCHIVE-SEARCH 细则 | §7.1（原文逐句）、§10（搜索覆盖与筛选）、§8（已下线不可见）、§23 |
| §8 三态对比表 | §8（默认下线/归档不删除；永久删除仅总管理员三情形） |
| §9 纠错与下架快速通道 | §8（邮箱反馈自动带标题地址）、§11（投诉立即隐藏＋内部记录） |
| §10 断言 PA-31–PA-36 | §7.1/§8/§10/§11、§23（两条必测项设计源） |
| 附录 D 别名映射 | 02 S5.2 草案断言消歧（附录 C 末行登记的 M5.2 输入兑现） |

## 附录 A：断言清单（PA-xx，B 阶段测试预写；可增不可减）

| 断言 ID | 对象 | 断言 | PRD § |
| --- | --- | --- | --- |
| PA-01 | 预约未到点（S1） | 前台 404 且不入任何列表；S1 判定基于修订级 `approved_go_live_at`，对象级残留不参与（＝02 S5.1 PS-01 别名） | §7.1/§7.2 |
| PA-02 | 精确 `go_live_at` 边界 | `approved_go_live_at` 严格 `<` 比较：N == T 的运行不发布；首次 N > T 运行发布 | §7.1 |
| PA-03 | 到点发布（E3） | `publish_scheduled` 执行后转 live、入 CURRENT_DEFAULT；到点→可见 ≤1 小时任务窗口（＝PS-02 别名） | §7.1/§7.2 |
| PA-04 | 修改预约时间 | 旧待执行修订清空、新时刻登记（单一待执行修订）；生效时刻以新值为准，无旧时刻泄漏 | §7.1 |
| PA-05 | 取消预约（E4） | 内建 unschedule 仅清修订级；回落预约前原态；不产生其他状态变更（＝CONTENT_MODEL PS-17 语义复用） | §7.1 |
| PA-06 | live＋未来 `expire_at` | 保持 S2 可见；未来到期是 S2 属性不单设状态；到点前不因该字段离集 | §7.1 |
| PA-07 | 精确 `expire_at` 边界 | `expire_at__lt` 严格比较：N == T 的运行不下线；首次 N > T 运行执行 E7 | §7.1 |
| PA-08 | 到期下线（E7） | 过期集＝`live ∧ expire_at < N`；执行后退出首页与默认列表；内容/修订/URL 零删除（＝PS-05 别名） | §7.1 |
| PA-09 | 修改 `expire_at` | 新值须过 clean 未来性；发布修订后旧时刻作废；live 页对象级生效（未发布修订不影响现值） | §7.1/§7.2 |
| PA-10 | 取消 `expire_at` | Article 可清空转常青；Notice 必填不可取消；Material/SoftwareTool/Guide 强制空 | §7.1/§7.2/§7.4–§7.6 |
| PA-11 | 到期重发布/重设期（E9/E11） | publish 原子置 `expired=False`；Notice 新未来有效期经 clean 强制；重设期按新值生效 | §7.1/§8 |
| PA-12 | `go_live_at ≥ expire_at` | 判非法并经 clean 层拒绝（`go_live_at < expire_at`，严于官方"仅拒 `>`、相等放行"）；官方校验仅 admin 表单路径，全路径闸口归项目 clean（§5.4） | §7.1 |
| PA-13 | 命令幂等 | 同刻重跑第二次零状态变更：live=F 不入过期集、unpublish 短路、已发布修订 `approved_go_live_at` 已清 | §7.1 |
| PA-14 | 失败补偿 | 单项失败中断本次运行但不回滚已处理项；下期工作集重推导自动补执行全部积压（无下限过滤） | §7.1 |
| PA-15 | 推荐位窗口 | `is_on_display` ＝四条件合取；起止闭区间（含两端）；窗口外不展示（＝PS-03 别名） | §9 |
| PA-16 | 推荐位不泄漏不可见内容 | 所指页 ∉ CURRENT_DEFAULT（S0/S1/S3/S4）即不展示：未到 `go_live_at` 不得提前公开、expired/offline 不得残留默认前台 | §9/§8 |
| PA-17 | 推荐位安全降级 | 引用不可见内容的推荐项被跳过：不占位、不报错、不泄漏标题摘要；全无效时区块整体不渲染（IA §7.1） | §9 |
| PA-18 | 推荐位数量 | 展示有效项 ≤ 槽位固定常量（V1 默认建议 6，项目负责人确认；站点级配置留痕）（＝PS-04 别名） | §9/§8 |
| PA-19 | 时区不变式 | 全部时间边界 timezone-aware，禁 naive；`TIME_ZONE` 取值不影响 E3/E7 判定与 CURRENT_DEFAULT 成员（绝对时刻等价）；Asia/Shanghai 修复后全量既有测试全绿（前提＝`test_permissions_admin_boundary.py:163-164` 墙钟断言同步调整，§4.4） | §16 |
| PA-20 | 调度比较语义 | `publish_scheduled` 两相均为严格 `<`（`publish_scheduled.py:46/92`）；比较对象为 aware 绝对时刻 | §7.1 |
| PA-21 | 作用域封闭 | FeaturedItem/SiteSettings 不在命令工作集（非 `DraftStateMixin`）；展示窗口为请求时计算，无任务依赖 | §9 |
| PA-22 | 到点窗口验收口径 | 到点→生效 ≤1 小时＋单次运行时长；production 每小时周期调用（独立 cron/任务容器，B6 落地留痕） | §7.1 |
| PA-23 | 状态字段零新增 | 不建第二套 scheduled_status/expiry 状态字段；状态由内建列纯推导（§14.1/§2.6 承接） | §8 |
| PA-24 | 归档缺口不关闭 | 到期后归档/搜索可见性仍归 M5.2；V1 现状＝到期即前台不可见，任何实现不得声称已提供历史归档查询（PS-26 承接） | §7.1 |
| PA-25 | live 页预约修订 | live 页携未来 `go_live_at` publish 保持 live 不中断（S2b），到点后修订生效（无新状态） | §7.2 |
| PA-26 | 仅 live 页可被到期 | draft/scheduled 页的 `expire_at` 永不触发转换（过期集 `live=True` 过滤＋unpublish 短路；＝CONTENT_MODEL PS-18 语义复用） | §7.1 |
| PA-27 | 死代码防误用 | 7.4.2 `revision_date_expired` 无调用点；过期判定以对象级列为准，下游不得引用修订内容过期判定 | §7.1 |
| PA-28 | 修改预约的单修订不变式 | 同一对象任一时刻至多一条 `approved_go_live_at` 非空修订（登记即排他清空） | §7.1 |
| PA-29 | 管理权封闭 | FeaturedItem 仅总管理员可管理；部门无自助通道（邮箱申请不建模） | §8/§9 |
| PA-30 | 测试实现约束 | 测试不得 sleep；用 mock `timezone.now`＋`call_command` 或 DB 直设时间后跑正式命令 | §23 |
| PA-31 | 到期退出默认位（E7 后） | 退出首页与全部板块默认列表；推荐位即时失效；与 PA-32/PA-33 成对断言（＝02 S5.2 PA-01 别名，附录 D） | §7.1/§23 |
| PA-32 | 归档列表可见 | 板块历史归档视图＝HISTORICAL（live ∪ expired）；expired 条目带「已过期」标注（＝02 S5.2 PA-02 别名） | §7.1/§8/§23 |
| PA-33 | 搜索默认含过期通知 | ARCHIVE-SEARCH：站内搜索默认命中 expired 通知（状态中性，过期文章同入）且带标注；不设用户开关（＝02 S5.2 PA-03 别名） | §7.1/§10/§23 |
| PA-34 | 手动下线不可见 | S4：具名 URL 404 且搜索/归档视图均不可见（与 S3 可达的刻意对比，§6.3）（＝02 S5.2 PA-04 别名） | §8/§11/§23 |
| PA-35 | 永久删除封闭＋审计 | 仅总管理员（部门账号被拒）；审计载体＝内建页面日志 `wagtail.delete`；FeaturedItem 级联零悬挂（＝02 S5.2 PA-05 别名） | §8 |
| PA-36 | 草稿/预约匿名不可达 | S0/S1 任何匿名路径（URL/列表/归档/搜索）不可见（＝02 S5.2 PA-06 别名） | §8/§23 |

## 附录 B：可追溯性表

| 条目 | PRD § |
| --- | --- |
| §1 预约发布语义（S1 归属、官方机制、修改/取消、窗口） | §7.1/§7.2（支持预约发布） |
| §2 到期边界三段、E7、修改/取消/重设期 | §7.1（有效期与到期退出）、§7.2（不默认下线时间）、§8（到期自动归档） |
| §2.6 零新增状态字段 | §8（默认下线/归档不删除） |
| §3 命令行为/幂等/失败/运行口径 | §7.1（到期自动）、§16（容器化部署环境）；00 §12 M5.1、02 §7 S5.1 |
| §4 时区全链路与修复方案 | §16（环境与部署）；M5.1 设计契约（Human 指令） |
| §5.1–5.2 Featured 交互冻结 | §9（推荐位/置顶条款）、§8（仅总管理员/邮箱申请） |
| §5.2 数量固定 | §9；IA §7.2；02 §7 S5.1（默认 6 建议值） |
| §5.3 边界用例表 | §7.1/§7.2/§8/§9、§23（自动化测试口径） |
| §5.4 非法组合校验归属 | §7.1（有效期语义推论）；官方 admin 表单校验亲证（§5.4 修正） |
| 附录 A 断言 PA-01–PA-30 | 逐行标注（PRD 无对应条款者为计划/契约引源） |
| §6 历史归档视图语义（M5.2 增补） | §7.1（保留在历史归档）、§8（通知到期自动归档） |
| §7 可见性规则总表＋ARCHIVE-SEARCH 细则（M5.2 增补） | §7.1（原文逐句）、§10（搜索覆盖与筛选）、§8（已下线不可见）、§23 |
| §8 三态对比表（M5.2 增补） | §8（默认下线/归档不删除；永久删除仅总管理员三情形） |
| §9 纠错与下架快速通道（M5.2 增补） | §8（邮箱反馈自动带标题地址）、§11（投诉立即隐藏＋内部记录） |
| §10 断言 PA-31–PA-36＋附录 D 别名映射（M5.2 增补） | §7.1/§8/§10/§11、§23（两条必测项设计源） |

## 附录 C：PS-01–PS-05 别名映射（02 S5.1 必含断言消歧）

处理 CONTENT_MODEL §19.3 编号登记：02 S5.1 草案为本文预留的 PS-01–PS-05 与 CONTENT_MODEL §18 的 PS 系列（PS-10–PS-29）同名不同文档。按其建议的"文档前缀消歧"裁决：本文正式编号＝**PA-xx**（00 §12 M5.1 指定），PS-01–PS-05 逐条映射如下（内容一字不丢，别名留痕；同名不同义风险随映射消除）：

| 02 S5.1 草案断言 | 本文正式断言 | 备注 |
| --- | --- | --- |
| PS-01 预约未到前台 404 且不入列表 | PA-01 | 语义一致 |
| PS-02 `publish_scheduled` 执行后到点内容 live | PA-03 | 含 ≤1 小时窗口口径 |
| PS-03 推荐位仅在起止窗口内于首页展示 | PA-15 | 四条件合取＋闭区间 |
| PS-04 推荐位数量不超过固定上限 | PA-18 | 槽位常量，默认建议 6 待项目负责人确认 |
| PS-05 到期执行后内容退出首页与默认列表 | PA-08 | 含数据零删除 |

（M5.2 的 §6–§10 增补时沿用 PA-xx 续号（PA-31 起），与 02 S5.2 草案的 PA-01–PA-06 由该批次自行映射消歧——本行登记为 M5.2 输入。）

## 附录 D：02 S5.2 草案 PA-01–PA-06 别名映射（M5.2 断言消歧）

附录 C 末行登记的 M5.2 输入兑现：02 S5.2 草案为本文 §6–§10 预留的断言编号 PA-01–PA-06，与本文 M5.1 既有 PA-01–PA-06（§5.3/附录 A）同名不同义。按附录 C 同款「续号消歧」裁决：M5.2 断言正式编号＝**PA-31–PA-36**（附录 A「可增不可减」续号），草案编号逐条映射如下（内容一字不丢，草案原文编号保留在表内使验收 grep 命中；同名不同义风险随映射消除）：

| 02 S5.2 草案断言 | 本文正式断言 | 备注 |
| --- | --- | --- |
| PA-01 到期后退出首页与默认列表 | PA-31 | 与 M5.1 PA-08（E7 退出）同域；本条为归档侧成对断言口径 |
| PA-02 归档列表可见且带「已过期」标注 | PA-32 | HISTORICAL 口径（§6.1） |
| PA-03 站内搜索默认命中过期通知 | PA-33 | ARCHIVE-SEARCH 口径（§7.1） |
| PA-04 手动下线内容前台 404 且搜索不可见 | PA-34 | S4 与 S3 的刻意对比（§6.3/§8） |
| PA-05 永久删除仅总管理员且产生审计记录 | PA-35 | 审计载体＝内建页面日志（§17.2 口径，§9.2） |
| PA-06 未发布草稿任何匿名路径不可达 | PA-36 | S0/S1 恒不可见（§7 总表末行） |
