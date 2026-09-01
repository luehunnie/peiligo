# Post-G2 Gap Audit 独立审查（POST_G2_GAP_AUDIT.review）

- **Review 身份**：Post-G2-gap-audit-review，fresh-context 独立子会话（不继承 Gap Audit 实现上下文）
- **日期**：2026-09-01
- **被审对象**：`docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md`（只读 Implementation Gap Audit）
- **BASELINE（实测）**：`main` @ `3dd0caa`（`git rev-parse HEAD` = 3dd0caaf0a3869d0d79da2589d44f0ddd8d08db2，branch=main）——与被审文档自称 BASELINE 一致
- **审查性质**：只读复核；本轮唯一产出为本文件，其余一切文件/目录严格只读，零 git 写操作

## 0. 抽查清单（抽样覆盖声明）

**G2 Gap 二十五项（G2_FREEZE_EVIDENCE §5）抽验 14 项＝56%（要求 ≥30%）**，且含任务指定的全部 9 项必抽：
第 1（E1 接线）、第 2（20 MiB）、第 3（MIME）、第 4（魔数）、第 5（外链确认页）、第 9（推荐位）、第 13（SEO）、第 23（日志）、第 24（CI）；
另加抽：第 6（生产 Cookie）、第 7（登录限速/强制改密）、第 8（HSTS）、第 14–17（备份族，脚本零命中一次覆盖四项）、第 25（容器/Caddy）。

**HIGH 项 2/2 逐项复核**：F-01、F-05。

**MB 映射抽验 4 行**：MB1、MB8、MB12、MB16。

每项证据均为本会话亲自读码/亲自 grep 所得（file:line），未转抄被审文档指针。

## 1. G2 Gap 逐项核验表

| # | 项 | 审计判定 | 本审查复验证据（亲自读码） | 结论 |
| --- | --- | --- | --- | --- |
| 1 | E1_PRODUCTION_WIRING | NOT_DONE | `src/peiligo/settings/base.py:234-238` 唯一后端＝通用 `wagtail.search.backends.database`；grep `SELECTED_SEARCH_BACKEND` 与 `icontains` 在项目代码（src/home/search/notices/resources/guides/departments/templates）0 命中；`docs/adr/0006-chinese-search-backend.md`「决策」节明载 PRODUCTION_IMPLEMENTATION_REQUIRED=YES（PG vendor 下默认后端走 FTS＝E2 语义）；金标集仅字段占位 `search/services.py:273-274`，30 条本体不在库 | 一致 |
| 2 | UPLOAD_SIZE_ENFORCEMENT | NOT_DONE | `base.py:262` `WAGTAILDOCS_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB` | 一致 |
| 3 | MIME_VALIDATION | NOT_DONE | 项目 app 代码 grep `content_type/mimetype`：仅命中无关处（migrations、`departments/management/commands/init_permissions.py:67`），无任何上传 MIME 校验逻辑 | 一致 |
| 4 | FILE_SIGNATURE_VALIDATION | NOT_DONE | 项目代码零 `filetype/magic` 调用；`filetype==1.2.0` 在 `requirements.txt`（在依赖树可用未用） | 一致 |
| 5 | EXTERNAL_REDIRECT_CONFIRMATION | NOT_DONE | `src/peiligo/urls.py:17-30` 全部路由无确认页；`templates/` 无确认页模板；`templates/blocks/external_link.html:1-6` 过渡形态＝「链接文字＋完整 URL 明文」无 `<a>`，注释自证确认页 DEFERRED；文案位已预留 `home/models.py:177-181`（redirect_notice_text） | 一致 |
| 6 | PRODUCTION_COOKIE_CONFIGURATION | NOT_DONE | `src/peiligo/settings/production.py:1-21` 仅 DEBUG=False（:3）、SECRET_KEY env（:7）、ALLOWED_HOSTS env（:10）、ManifestStaticFilesStorage（:16）；无 SESSION/CSRF `_COOKIE_SECURE`、无显式 SameSite/Age | 一致 |
| 7 | LOGIN_RATE_LIMIT / FORCE_PASSWORD_CHANGE | NOT_DONE | `requirements.txt` 全表逐行核对无 axes；`base.py:142-155` MinimumLengthValidator（:146-148）无 options＝默认 8 位；grep `set_password/force.*change/must_change` 在项目代码 0 命中 | 一致 |
| 8 | HSTS_FINAL_CONFIGURATION | NOT_DONE | `production.py` 全文无 `SECURE_HSTS_*` | 一致 |
| 9 | FEATURED_COUNT / EXPIRY_ALIGNMENT | PARTIAL | 模型 DONE：`home/models.py:95-156` FeaturedItem（start_at/end_at 必填无预填＝30 天默认缺：110-111；`is_on_display` 四条件：146-156）；测试在库 `tests/test_publish_scheduled_boundaries.py:491-553`（PA15–PA17：闭区间/不可见状态/无效跳过）；前台消费 NOT_DONE：`home/templates/home/home_page.html:7-15` 注释自证 ①–④ 数据区未插入，模板实渲染仅 hero＋搜索台＋五板块网格（:16-57）；首页推荐位渲染测试为 0（`tests/test_home.py` 仅 4 条树/渲染冒烟，grep FeaturedItem 0 命中） | 一致 |
| 13 | SEO_FINAL_ALIGNMENT | PARTIAL | 已实现：`templates/base.html:18-29`（query 态 noindex＋canonical）、`search/templates/search/search.html:13-18`、`home/templates/home/section_archive.html:15-20`、`src/peiligo/urls.py:29` sitemap、`departments/models.py:213-216` 容器排除；未实现：grep `noindex` 在五内容模型 0 命中（单篇字段缺）、全仓 `find -name robots.txt` 0 命中、确认页 noindex 随 #5 缺 | 一致 |
| 14–17 | BACKUP_AUTOMATION/SCHEDULE/RETENTION/INDEPENDENT_COPY | NOT_DONE ×4 | 仓库根无 `scripts/` 目录；无任何备份脚本/compose/cron 载体文件 | 一致 |
| 18 | RESTORE_DRILL | NOT_DONE（运维类） | 同上零实现零执行载体（分流判定另见 §3-b） | 一致 |
| 23 | STRUCTURED_LOGGING | NOT_DONE | `base.py`（全文 267 行）与 `production.py`（全文 21 行）均无 LOGGING dict；grep `LOGGING` in settings 0 命中 | 一致 |
| 24 | CI | NOT_DONE | `.github/` 目录不存在（ls 实证）；本地工具链在库：`pyproject.toml:16` pytest 配置、`:22` ruff 配置、`requirements-dev.txt:3` pip-audit==2.10.1 | 一致 |
| 25 | CONTAINER / CADDY FINALIZATION | NOT_DONE | `Dockerfile`、`docker-compose.yml`、`Caddyfile`、`scripts/` 全部不存在（ls 实证）；`gunicorn==26.1.0` 在 `requirements.txt` | 一致 |

## 2. HIGH 项逐项复核

### F-01（E1 搜索语义生产接线）——判定/证据/定级均核验一致
- NOT_DONE 成立：见 §1 表第 1 行（base.py:234-238、零显式后端选择、金标占位）。
- HIGH 定级理由属实：ADR-0006「背景」与「后果」节明载 PG 连接下 `wagtail.search.backends.database` 走 FTS 路径＝E2 语义、icontains fallback 不可达——接线缺失或错误＝全站搜索语义静默漂移（E1→E2），且「选型 Accepted ≠ 实现已发生」（NFR §11 状态边界）。
- 复验门引用属实：NFR §11.4（`docs/NON_FUNCTIONAL_REQUIREMENTS.md:468`）与 NF-17（`:439`）存在且内容与审计所述一致（hit@10/三档/p50/p95/并发/九项）。
- 金标集回归入 F-01 附带：合理——30 条本体不在库（services.py:270-274 仅挂接点）。

### F-05（登录治理）——判定/证据/定级均核验一致
- NOT_DONE 成立：见 §1 表第 7 行（无 axes、默认 8 位、无强制改密）。
- HIGH 定级理由属实：`docs/G2_HUMAN_DECISIONS.md:10` Q4＝后台允许公网访问（V1 无白名单），叠加无限速＋密码策略未提级，暴露面真实；Q2/Q3 参数（12 位；10 次/15 分钟→锁 15 分钟）为 Human 确认值（`G2_HUMAN_DECISIONS.md:8-9`），审计要求实现不得走样正确。

## 3. 检查清单 a–e 逐条结论

**a) 判定与证据真实性——通过。**
- DONE 有真证据：抽验 MB1（`base.py:126-136` TEST_DATABASE_URL 护栏、`tests/test_settings.py:48-91` 六条 env 外置/哑值断言、requirements 锁定 wagtail==7.4.2/Django==5.2.17/modelsearch==1.3.2、settings 三层 base/dev/production 实存）与域 A/C（`departments/models.py:153-216` 容器三重排除：serve 404 :209-211、search_fields=[] :193、get_sitemap_urls :213-216；`departments/wagtail_hooks.py` 移动/复制 :79-173、非空拒删单条＋批量 :197-231、删除仅总管理员单条＋批量 :242-280；`departments/permissions.py` is_privileged :43）。
- PARTIAL 准确、无「有函数名即完成」误判：域 E 正确切分「契约层 DONE（`search/services.py` 全 274 行亲读：五参数解析 :155-177、filter-first 保序 :225-242、双可见性 :216-222）与 E1 接线 NOT_DONE」；域 J 正确切分「模型 DONE 与前台消费 NOT_DONE」；域 F 正确指出白名单在库但为官方默认集（base.py:248-259 含 csv/txt/zip/key/odt、缺 doc/xls/ppt）。
- NOT_DONE 真的不存在实现：本审查独立 grep 复核（SELECTED_SEARCH_BACKEND/icontains/axes/LOGGING/MIME/magic/noindex 字段/robots.txt/.github/Dockerfile/compose/Caddyfile/scripts/强制改密钩子/健康端点）全部 0 命中，无审计漏搜迹象。
- OBSOLETE 有 superseding 决策：唯一登记 M0.3–M0.7，superseded_by＝G2 Human 签收第 6 项（`docs/G2_FREEZE_EVIDENCE.md:132`，2026-09-01），出处属实；「MB1–MB18 无一步 OBSOLETE」与抽验相符（MB12/16 缺文件属实、MB8 残留属实）。

**b) 测试/部署/运维分流——通过。**
- VALIDATION_ONLY（E1 复验门 NF-17、NF-01/02/07/08/09 实测、axe 扫描＋走查、check --deploy、金标集构建执行）均为「执行/测量」而非写码，分流正确；axe「工具化接入」入 F-11（写 CI 文件＝开发）与「扫描执行」入验证，切分自洽。
- DEPLOYMENT_ONLY（PVE/Docker 环境搭建、域名/TLS、DNS、.env 注入、初始化命令执行、测量环境搭建）与 F-09/F-10/F-12 的「写工程文件」边界清楚：写 Dockerfile/脚本属仓库内实现，跑部署属部署——分类一致。
- OPERATIONS_ONLY（演练、备份值守、令牌轮换、R-05 裁决本身）正确；F-08 以 Human 裁决为前置（签收第 7 项，`G2_FREEZE_EVIDENCE.md:133`），未被擅自转为纯开发项——处置正确。
- 未发现把验证/部署/运维动作计入 13 项纯开发 backlog 的情况。

**c) backlog 漏项自查（本审查独立 18 领域扫查对照）——未发现漏项。**
- A–R 逐域对照审计 §2/§7：每一真实实现缺口均有归属（E→F-01、F→F-02、G→F-03、J/首页四区→F-04、I→F-05、K→F-06、P→F-07、C/R-05→F-08、D 调度＋R→F-09、H→F-10、L 工具化＋Q→F-11、N→F-12、O→F-13）。
- 重点排查过的候选漏项均不成立：①分页——`docs/INFORMATION_ARCHITECTURE.md:313` 明文「分页等其余参数不属本步冻结项」，正确地未登记；②WAGTAILADMIN_BASE_URL 占位——NFR §12 PP-19（`:512`）＝DEFERRED_DEPLOYMENT_DETAIL，属部署细节非开发缺口；③发布调度载体——已归 F-09；④生产健康端点——已随 F-09。
- §4.1-3 三项新发现（首页搜索参数 bug、500.html lang、空 peiligo.js）均经独立复证属实（见 §5）。

**d) 零生产代码改动声明——属实。**
`git status --short` 仅 `?? docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md`（被审文档自身，未跟踪）；`git diff`（tracked 文件）零输出；无 src/templates/static/settings 任何改动；审查文件 `docs/reviews/POST_G2_GAP_AUDIT.review.md` 在被审时点尚不存在，与审计「本轮仅有的两个新增文档」声明一致。

**e) §4.1「G2 矩阵两行落后于代码」——属实。**
`git merge-base --is-ancestor 4d67473 0caece5` 通过（4d67473 是 0caece5 祖先）；`git show -s` 实证：4d67473＝2026-08-28「M5.2 归档与历史搜索实现」，触及 `home/views.py`、`src/peiligo/urls.py`、`home/templates/home/section_archive.html`；0caece5＝2026-09-01（G2-A 合并点＝G2-B 基线）。即归档视图代码在 G2-B 检查时点已在树，而 `G2_FREEZE_EVIDENCE.md:43-44`（PUBLISH/ARCHIVE 两行）仍记「历史归档视图未实现」——审计的更正方向正确。SEO 域更正亦经 §1 表第 13 行证据独立证实。

## 4. MB 映射抽验（4/18 行）

| MB | 审计判定 | 本审查复验证据 | 结论 |
| --- | --- | --- | --- |
| MB1 环境与依赖基线 | DONE | `base.py:126-136`；`tests/test_settings.py` 六条；requirements.txt 锁版三件实测在文件中；settings 仅 base/dev/production 三文件（ls 实证） | 一致 |
| MB8 发布、到期归档与置顶/推荐位 | PARTIAL | 生命周期/归档视图/expired 放行（`notices/lifecycle.py:75-88` route、`base.html:72-76` 横幅、`home/views.py:19-37`、`urls.py:22-26`）＋FeaturedItem 模型全在库；残留实证：首页消费缺（home_page.html）、30 天默认缺（start_at/end_at 必填无预填）、生产调度载体缺（`publish_scheduled` 仅测试 `call_command` 命中，全仓无 cron/compose/scripts）——残留归 F-04/F-09 正确 | 一致 |
| MB12 外链确认跳转页 | NOT_DONE | 无路由/视图/模板；过渡形态 `templates/blocks/external_link.html:1-6`；字段位（`resources/models.py:113,178`、`notices/models.py:255,320`）与文案位（`home/models.py:177-181`）已预留——「整页待实现、预留位已备」双表述均属实 | 一致 |
| MB16 容器化与本地编排 | NOT_DONE | Dockerfile/compose/Caddyfile/scripts 零文件（ls 实证） | 一致 |

## 5. 审计新发现（§4.1-3）独立复证

1. **首页搜索参数 bug——属实，且为真实用户可见缺陷**：`home/templates/home/home_page.html:28` `name="query"`，而服务端读取 `q`（`search/services.py:158,171`）；对照 `search/templates/search/search.html:31` 自身表单用 `name="q"`——证明 `query` 系笔误而非约定。归 F-04 修复恰当。
2. **`templates/500.html:2` `lang="en"`——属实**（全文站 `base.html:3` 为 zh-hans）。
3. **`static/js/peiligo.js` 0 字节仍被加载——属实**（`base.html:104` 引用；wc -c＝0）。

## 6. 发现的问题列表

**BLOCKER：无。**（抽验 14/25 Gap 项＋2/2 HIGH＋4/18 MB 行中，无一例判定错误、无一例真实缺口漏登记、无一例验证/部署/运维误计为纯开发。）

**SUGGESTION：3 项（均不动摇任何判定/批次/最终结论）。**
1. **§5 计数小误**：分类总账记 NOT_DONE「其中 4 项属纯验证、1 项属纯运维」；但审计自表 §4 标注「（验证类）」者仅 3 项（#10、#11、#12），「（运维类）」1 项（#18）。「4」应为「3」。不影响 23 项总数、批次划分与「剩 2 个开发批次」结论。
2. **域 H/F-10 表述精度**：`SECURE_CONTENT_TYPE_NOSNIFF` 与 `SECURE_REFERRER_POLICY` 记为「未接线」。Django 5.2 下二者默认即生效（nosniff=True；referrer-policy='same-origin'）——「未显式配置」字面成立，且 F-10 显式固化属合理加固，但「未接线」易被读成「当前响应头缺失」。建议 F-10 备注改为「显式固化（现由 Django 默认开启）」。
3. **证据计数未能完全对账（轻微）**：域 B 证据「测试 13+13+13+18+10+32 条覆盖」中，13（notice_article）/13（material_software）/18（event_fields）/10（guide）四数与本审查逐文件计数精确吻合，但 13/32 两数无法唯一对应到具体文件（就近候选 test_publish_window=13、test_lifecycle_state=14、test_current_default=7 均不等于 32）。覆盖面方向经全仓 399 条 def test 实证无疑，仅建议改为逐文件列名。另：500.html lang 与空 js 两小疵挂 F-04（首页数据区）名下略牵强——它们已登记有主，仅归属建议（更贴近 F-11 a11y/静态卫生），非缺陷。

## 7. 最终 VERDICT

**PASS**

理由：抽查范围内（56% Gap 覆盖＋全部 HIGH＋4 行 MB＋五项指定必抽）审计判定与当前代码逐项相符；NOT_DONE 均经本审查独立 grep/读码证实为零实现；PARTIAL 切分准确；OBSOLETE 有 Human 签收 superseding 决策；分流正确无混计；18 领域独立扫查未发现漏项；「零生产代码改动」与「§4.1 矩阵偏差更正」两项关键声明均经 git 层面实证成立。SUGGESTION 三项均不影响判定方向、backlog 完整性与「剩余 2 个开发批次」结论，留待审计文档下次修订时顺带采纳（本审查按边界不代改）。

## 8. 生产代码改动核验结果

- `git rev-parse HEAD`＝`3dd0caaf0a3869d0d79da2589d44f0ddd8d08db2`（＝自称 BASELINE，branch=main）
- `git status --short`＝仅 `?? docs/POST_G2_IMPLEMENTATION_GAP_AUDIT.md`（未跟踪新增文档）
- `git diff`（tracked 文件）＝空；src/、templates/、static/、settings/ 零改动
- **核验结论：审计「生产代码改动＝零」声明属实。**
