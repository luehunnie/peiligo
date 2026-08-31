# 安全基线（SECURITY_BASELINE）

## 文档信息

| 项 | 值 |
| --- | --- |
| 文档目的 | 把 PRD §5/§11/§12/§17 的安全要求与两轮审计安全风险落成可执行的安全设计基线，供 B 阶段实现与审查引用（02 §9 S7.1） |
| 步骤 | M7.1（引源：00_MASTER_PLAN §14 M7.1；02 §9 S7.1 全文） |
| 依赖 | M3.2（附件字段）、M4.1（账号与权限，含 M4.2/M4.3/M4.4 实证回写） |
| 允许修改范围 | 本文件（新建）；不改任何代码与 settings |
| 状态口径 | 本文档是**设计基线 + 现状审计**，不是实现报告——凡未实现的控制一律如实标注（见 §0.1），实现一律留 B 阶段 |
| G2-A 更新 | 2026-08-31 项目负责人 23 项参数确认落档（Q1–Q23 全表＝`docs/G2_HUMAN_DECISIONS.md`；本文 §13 逐行更新确认状态，相关小节加注）；实现状态四值标签（§0.1）不因此改变——未实现项仍如实标注 |

## 0. 状态口径与权限边界（阅读前提）

### 0.1 状态标签（四值，全文统一）

| 标签 | 含义 |
| --- | --- |
| `SATISFIED` | 已实现，且有代码/配置证据（本文标注证据位置） |
| `PARTIAL` | 部分实现，或已实现但与目标口径存在明确差距（差距写明） |
| `NOT_IMPLEMENTED` | 未实现——本轮不改 settings/代码，按 §14 Post-G2 Gap 登记随 B 阶段/部署阶段承接 |
| `NEEDS_VERIFICATION` | 机制存在但定论依赖部署环境参数或项目负责人确认（关联 §13 待确认参数表） |

**诚实性规则**：`SATISFIED` 必须给出可复核证据路径；凡把计划写成已完成的条目按文档缺陷处理。本文所有"现状"以 main=cd6eca0 代码为准。

### 0.2 权限边界（承接 M4，不重设计）

以下六条为 M4 阶段已实现并经独立安全评审的边界事实，本文**原样承接**，不在安全基线中另起炉灶：

1. **未授权默认不开放**（fail-closed）：一切权限判断以"拒绝"为缺省；Wagtail 守卫异常时 Django 默认 500——拦截面过宽不会放行（M4-SECURITY-REVIEW §6）。
2. **按钮显隐不替代服务端判断**：仅界面隐藏不算通过；越权测试以数据库零变更快照为主证，HTTP 状态码仅辅助（ROLE_PERMISSION_MATRIX §6 通用拒绝断言）。
3. **部门账号只管本部门**：部门组＝GPP(add/change/publish)@本部门容器节点，树形传播天然隔离（ADR-0004 决策 1）。
4. **跨部门操作被服务端阻止**：构造 URL/POST、单条/批量、直达确认步全部动线在权限层拒绝（T05–T09、T13，M4.3 16/16；独立评审攻击抽查 18/18）。
5. **高权限走矩阵**：账号管理、永久删除、站点设置、词表/推荐位等治理动线仅 R1（总管理员）可达（矩阵 §2/§3.2；T08/T10/T11/T12）。
6. **不建第二套用户系统**：只用 Django auth＋Wagtail 官方扩展点（hooks/权限配置），无自建 RBAC（PRD §5；矩阵 §3.1 方向锁定冻结；ADR-0004 决策 4 升级路径约束）。

### 0.3 本文档与代码的关系

- 本文按代码**如实记录**现状，不给出与现状相反的描述；差距与补齐动作进 §12 Implementation Mapping 与 §14 Post-G2 Gap。
- 本轮不改任何 settings（任务边界）；因此 §1/§3/§4 中一切"待接线"项的 `NOT_IMPLEMENTED` 标注即最终本轮结论。

---

## 1. 后台访问控制

### 1.1 需求（PRD §5）

Wagtail 管理后台仅允许从校园网或学校 VPN 访问；管理后台必须使用 HTTPS、登录限速和强密码策略。矩阵 §3.5 定性：这些是**环境配置而非组权限**，不进入权限组模型；矩阵 §6 T16 仅验证"未登录访问 /admin/ 被重定向到登录页"（已 PASS，POC_PERMISSION_REPORT ②）。

> **Human 决策（2026-08-31，Q4）**：后台访问**允许公网访问，V1 不要求校园网或 IP 白名单**——上文"仅允许从校园网或 VPN 访问"的网段限制要求在 V1 被该决策取代；SB-01/SEC-23（后台网段边界）随之关闭（见 §13#4、§12、§14）。HTTPS、登录限速、强密码策略三项要求不变。

### 1.2 两方案对比与推荐

| 方案 | 机制 | 优点 | 缺点/风险 |
| --- | --- | --- | --- |
| A. 反向代理 ACL | 在反代（Nginx 等）对 `/admin/`、`/django-admin/` 路径做 `allow/deny`（校园网网段 + VPN 网段），网段外直接 403 | 边界处拒绝，请求不进应用即被挡；零 Django 代码；不受应用层漏洞影响 | 依赖部署环境（上游审计 U5：生产服务器反代/证书条件待校方确认）；配置在代码仓之外，需部署文档固化 |
| B. Django 中间件 | 自定义中间件按 `REMOTE_ADDR` 网段白名单拦截后台路径 | 配置入仓、可测试 | 须正确处理反代场景的 `X-Forwarded-For`（见 §1.3）；应用层代码一旦有豁免路径即失效 |

**推荐**：**A 为主、B 为可选纵深**。生产部署在校园内反代之后（PRD §16 容器化部署），反代 ACL 是天然边界；若项目负责人确认反代不可控，再落 B（中间件）作为唯一防线。两方案都要求网段清单（校园网 + VPN CIDR）先经项目负责人确认（§13 待确认参数表）。

> **Human 决策（2026-08-31，Q4）后更新**：V1 允许公网访问后台、不要求校园网/IP 白名单 → 方案 A/B 的网段清单前提已消解，**V1 不实施后台网段限制**（A/B 两方案均不落地；上文推荐保留为历史设计记录，如未来决策收紧再启用）。

### 1.3 `X-Forwarded-For` 信任链注意事项（方案 B 落地前置）

- 客户端可伪造 `X-Forwarded-For` 首段；只有**从右向左跳过受信任代理数**之后的那一跳才是可信客户端地址，或直接信任反代注入的单一变量。
- 若采用方案 B 且存在反代：中间件必须只信任"最后一跳由已知反代写入"的值；禁止取首段。
- 同源信任链问题：`SECURE_PROXY_SSL_HEADER` 只有在"确有 TLS 终结反代、且应用不可直连"时才允许配置，否则等于把"是否 HTTPS"的判定权交给请求头（可伪造）。生产配置与反代形态联动确认（NEEDS_VERIFICATION，§13）。
- 现状：项目代码与 settings 中**无任何**后台网络限制实现（无 REMOTE_ADDR/IP 判断代码；settings 无相关配置）→ **`NOT_IMPLEMENTED`**（断言 SB-01/SEC-23）。

### 1.4 HTTPS 强制

- PRD §5 要求后台 HTTPS；PRD §16 生产环境在校方服务器，证书条件待确认（上游审计 U5）。
- 现状：`SECURE_SSL_REDIRECT` 未配置（Django 默认 False）、HSTS 未配置（§3.2）；生产设计＝反代层 301 跳转 HTTPS ＋ Django `SECURE_SSL_REDIRECT=True`/HSTS 双保险 → **`NOT_IMPLEMENTED`**（断言 SEC-24）。

---

## 2. 认证与账户

### 2.1 认证体系（不重设计）

- 使用 Wagtail/Django 自带认证与权限体系，不自建独立用户中心；不开放公开注册，不建学生账号；首版仅用户名＋密码，不强制多因素（PRD §5）→ 架构面 **`SATISFIED`**（证据：INSTALLED_APPS 仅 django.contrib.auth + wagtail.users；M4-SECURITY-REVIEW §6"无自定义认证代码"）。
- 后台登录/退出边界由 Wagtail admin 内建承担：`/admin/` 未登录访问重定向登录页（T16 PASS）；前台无登录入口（PRD §12 学生前台免登录）；`peiligo/urls.py` 无自定义登录/登出视图。注记：`/django-admin/`（Django admin）随官方模板默认挂载（`peiligo/urls.py:18`），其权限同样走 Django auth，但建议 B 阶段评估是否保留暴露面（非阻断注记）。

### 2.2 强密码策略（AUTH_PASSWORD_VALIDATORS）

现状已配置官方四校验器（`src/peiligo/settings/base.py:142-155`，官方模板默认值）→ **`SATISFIED`**：

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

- 校验位置：Django 表单（后台建号/改密）统一执行；被拒即 ValidationError 回显（SB-02 验证基础）。
- 注记：`MinimumLengthValidator` 未显式传 `min_length`，取默认 8——**Human 已确认（2026-08-31，Q2）：最低密码长度＝12 字符**（§13#3；B 阶段显式接线）；继续使用 Django / Wagtail 原生账号机制（Q2 同确认）；`NumericPasswordValidator` 仅禁纯数字，强度主力是前三者（框架口径）。

### 2.3 登录限速

- PRD §5 要求登录限速；02 S7.1 指定候选方案 **django-axes**。**Human 已确认（2026-08-31，Q3）**：登录失败处理＝**15 分钟内连续失败 10 次 → 临时限制 15 分钟；成功登录后失败计数清零**（原建议 5 次/15 分钟由本确认值取代；§13#2）。
- 设计要点：`AXES_FAILURE_LIMIT=5`、`AXES_COOLOFF_TIME=15 分钟`、锁定键建议 `username + ip_address` 组合（兼顾撞库与爆破）；django-axes 以 `AXES_MIDDLEWARE`＋认证后端追加方式接入，与 Wagtail admin 登录视图兼容，无需改 Wagtail 核心。注意：失败计数依赖可还原客户端 IP——与 §1.3 X-Forwarded-For 信任链结论联动（反代场景须传可信 IP，否则限速可被伪造头绕过）。
- 现状：requirements 无 axes 依赖、settings 无配置 → **`NOT_IMPLEMENTED`**（断言 SB-03/SEC-15）。

### 2.4 密码重置后强制改密

- PRD §5：部门账号密码可由总管理员重置；**重置后必须强制修改密码；不得使用长期统一默认密码**。
- 已知缺口（M4-SECURITY-REVIEW 遗留 #5）：Wagtail 7.4.2 核心无"首登/重置后强制改密"开关（M4.3 ④-4 同结论）。当前流程依赖"重置→线下告知→登录后改密"的人工纪律，技术上未强制。
- 机制设计（B 阶段实现，本文只定方向）：① 用户属性记录 `密码设定时刻`（如 profile 字段或 `password_last_set`）；② R1 重置动作将该时刻置空；③ admin 入口中间件检查"已登录且密码未设定"→ 强制重定向到改密页，改密完成前拦截其余后台路由；④ 首登改密视为同一机制（矩阵 §4 创建行）。该检查必须**服务端路由级**，不能只靠提示文案（0.2 条 2）。
- 现状 → **`NOT_IMPLEMENTED`**（断言 SB-04/SEC-16）。

### 2.5 账号生命周期（交接/停用/重置）

按 ROLE_PERMISSION_MATRIX §4 承接（不在本文重述细则）：创建（R1，每部门至多一个岗位账号）、交接（立即重置凭据、旧凭据即时失效）、停用（`is_active=False`，不删号、已发布内容保留）、密码重置（重置后强制改密，§2.4）、审计（Wagtail 修订历史记录操作者与时间，§6.1）。V1 仅一名总管理员；superuser 单独保管、日常不用（矩阵 §4 末段）。

---

## 3. 传输与响应头

> 增量要求（Human M7-C）：本节按代码**如实记录**；未接线＝`NOT_IMPLEMENTED`，本轮不改 settings。Django 默认值均经已安装 Django 5.2.17 `global_settings.py` 实证。

### 3.1 CSRF

- `django.middleware.csrf.CsrfViewMiddleware` 在 MIDDLEWARE 链（`base.py:78`）；Django 表单与 Wagtail admin 全部动线带 token → **`SATISFIED`**。
- 项目代码证据集内无 `csrf_exempt` 豁免（apps/src 全量 rg 零命中）。
- 后续验证：B 阶段加"无 token POST 被 403 拒"回归断言。

### 3.2 `SECURE_*` 与 Cookie 逐项现状表

| 项 | Django 默认（5.2 实证） | 项目 settings 是否显式配置 | 现状定性 |
| --- | --- | --- | --- |
| SESSION_COOKIE_HTTPONLY | True | 未配置（取默认） | `SATISFIED`（默认即目标值） |
| SESSION_COOKIE_SAMESITE | `"Lax"` | 未配置 | `SATISFIED` |
| SESSION_COOKIE_SECURE | False | 未配置 | **`NOT_IMPLEMENTED`**（生产须 True）★ |
| CSRF_COOKIE_HTTPONLY | False | 未配置 | `SATISFIED`（框架口径：默认 False，CSRF token 需前端可读） |
| CSRF_COOKIE_SECURE | False | 未配置 | **`NOT_IMPLEMENTED`**（生产须 True） |
| SESSION_COOKIE_AGE | 2 周 | 未配置 | `NEEDS_VERIFICATION`（后台会话时长是否缩短，§13）→ **Human 已确认（2026-08-31，Q6）：24 小时**；主动退出立即结束；修改密码等重要账号变更后，相关 Session 应结束（B 阶段接线） |
| SECURE_SSL_REDIRECT | False | 未配置 | **`NOT_IMPLEMENTED`**（§1.4） |
| SECURE_HSTS_SECONDS | 0 | 未配置 | **`NOT_IMPLEMENTED`**（**Human 已确认（2026-08-31，Q5）：最终生产目标 1 年；初次上线先用较短周期，确认 HTTPS、证书和反向代理稳定后再提升到 1 年**——先短后长） |
| SECURE_PROXY_SSL_HEADER | None | 未配置 | `NEEDS_VERIFICATION`（仅与可信反代联动配置，§1.3）→ **Human 已确认（2026-08-31，Q10）：生产反代＝Caddy（TLS 终结于反代）**；具体接线值部署阶段定 |
| SECURE_CONTENT_TYPE_NOSNIFF | True | 未配置 | `SATISFIED` |
| SECURE_REFERRER_POLICY | `"same-origin"` | 未配置 | `SATISFIED` |
| SECURE_CROSS_ORIGIN_OPENER_POLICY | `"same-origin"` | 未配置 | `SATISFIED` |
| DEBUG（production） | — | `production.py:3` `DEBUG = False` | `SATISFIED` |
| DEBUG（dev） | — | `dev.py:4` `DEBUG = True` | 开发态预期（不部署） |
| ALLOWED_HOSTS（production） | — | env 必填（`production.py:10`） | `SATISFIED`（dev 为 `["*"]`，仅开发态） |

★ production cookie 安全配置（SESSION/CSRF `_COOKIE_SECURE` 等）＝四项特别如实标注之一：当前 production.py **只设置了 DEBUG/SECRET_KEY/ALLOWED_HOSTS/静态后端**，cookie 与 `SECURE_*` 一族**全部未接线** → 生产部署清单必须补齐（§12/§14；断言 SEC-07/08 已达标项靠 Django 默认，SEC-24 未达标）。**生产 cookie 目标已由 Human 确认（2026-08-31，Q16）：Session Cookie `SameSite=Lax`（Django 默认已符）＋ `Secure=True` ＋ `HttpOnly=True`，HTTPS only**——部署接线按此四项执行。

### 3.3 CSP 基线方向

V1 不引入复杂 CSP（服务端模板＋Wagtail admin 脚本域需先行验证）；基线方向：生产仅允许同源脚本与样式、`frame-ancestors 'none'`（与 X-Frame-Options DENY 双保险）、报告模式先行。属 B 阶段/部署阶段实现项 → `NOT_IMPLEMENTED`（设计方向已定，无断言压力）。

### 3.4 X-Frame-Options（点击劫持）

`XFrameOptionsMiddleware` 在 MIDDLEWARE 链（`base.py:81`），Django 5.2 默认 `X_FRAME_OPTIONS = "DENY"`（global_settings 实证）→ **`SATISFIED`**。后台与前台全站带 `X-Frame-Options: DENY`。

### 3.5 媒体与静态文件服务边界

- `urls.py:33-39`：仅 `DEBUG=True` 时由 Django dev server 出 `/media/`、`/static/`——生产（DEBUG=False）必须由反代或独立容器承接，否则媒体 404/不可达（部署验证项，NEEDS_VERIFICATION，随 G3 部署验收）。
- 生产静态走 `ManifestStaticFilesStorage`（`production.py:16`）——防升级后旧缓存脚本（完整性正向项）。

---

## 4. 附件与上传

### 4.1 类型白名单（以 PRD 为准，不自行扩充）

- **目标白名单（02 S7.1 §4 冻结，来源 PRD §11"PDF、Office 文档和常见图片"）**：`pdf / doc / docx / xls / xlsx / ppt / pptx / png / jpg / webp`。本文不扩充、不删减。
- **现状**（`base.py:248-262`，官方模板默认值，尚未按 PRD 对齐）：
  - `WAGTAILDOCS_EXTENSIONS = csv, docx, key, odt, pdf, pptx, rtf, txt, xlsx, zip`——**超出** PRD 白名单（csv/txt/zip/key/odt），且**缺少** doc/xls/ppt；图片不走 wagtaildocs（经 wagtailimages 图片库治理，PRD §7.7/CM §11.1）。
  - `WAGTAILDOCS_MAX_UPLOAD_SIZE = 10MB`；02 S7.1 建议默认 **20MB〔标记确认〕**——两值不一致 → 入 §13 待确认参数表。**Human 已确认（2026-08-31，Q1）：单个附件最大 20 MiB**（MB 阶段 settings 对齐）。
  - 定性：**`PARTIAL`**（存在白名单机制，但集合未按 PRD 收窄；本轮不改 settings，MB 阶段对齐；断言 SEC-17）。
- 附件块（DocumentChooserBlock）与 `NoticePage.attachments`/`MaterialPage.attachments` 等字段均最终经 wagtaildocs 统一上传面——白名单是**单一收口点**（`base.py` WAGTAILDOCS 配置），无旁路上传入口（证据：blocks.py AttachmentBlock 注释"上传策略＝全站 WAGTAILDOCS 配置"）。

### 4.2 三级一致性校验（扩展名 + MIME + 魔数）

回应上游审计 R7 与综合审计 P2（"官方设置只覆盖前两级，魔数检测为项目层补充"）：

| 层级 | 机制 | 信任度 | 现状 |
| --- | --- | --- | --- |
| ① 扩展名 | `WAGTAILDOCS_EXTENSIONS` 上传拒绝 | 低（可伪造） | `SATISFIED`（机制在，集合待对齐 §4.1） |
| ② MIME/content-type | 浏览器上报值，仅作参考记录 | 低（可伪造，不单独作为放行依据） | 无显式校验（`PARTIAL`） |
| ③ 魔数（文件签名） | 读文件头字节与签名表比对，与①②交叉一致才放行 | 中（伪造成本高） | **未接入**：项目代码无魔数检测调用 → **`NOT_IMPLEMENTED`** ★ |

- ★ 四项特别如实标注之一：**MIME+魔数三级一致性校验未实现**。当前伪造扩展名文件（如 `evil.pdf` 实为可执行/脚本内容）在扩展名层可通过（SB-05 目前不可达）。
- 实现方向（B 阶段，不新增第三方扫描基础设施）：以 Wagtail Document 保存钩子/自定义 clean 挂轻量魔数比对（读文件头 N 字节比对签名表）；依赖清单中已存在 `filetype==1.2.0`（requirements.txt；B 阶段确认其归属后复用）可承担签名识别——**不引入杀毒引擎、不建独立扫描服务**。
- 图片类注记：wagtailimages 上传经 Pillow/Willow 实际解码，非图片字节会被拒——图片事实上已有深层校验；本节三级校验针对 wagtaildocs 文档面。
- 验证方式（SB-05）：构造"扩展名×内容"错位样本矩阵（伪 pdf/伪 docx/真 pdf 改名等）逐个上传，预期白名单外或魔数不符全部拒绝。

### 4.3 危险扩展名黑名单（纵深）

白名单是根本防线；黑名单作为防御性校验显式拒绝（即使未来白名单误扩也不放行）：`html / htm / svg / js / mjs / exe / bat / cmd / com / scr / sh / php / jsp / asp / aspx / jar / vbs / ps1`。理由：服务端存储后经同源域名回传给访客的文件若为 HTML/SVG 可执行脚本上下文即构成存储型 XSS；可执行格式无业务必要。

### 4.4 文件名安全规则

| 规则 | 设计 | 现状 |
| --- | --- | --- |
| 长度上限 | 存储名 ≤ 255 字节（文件系统约束）；超限截断保留扩展名；具体阈值入 §13（2026-08-31 G2-A 分类＝工程默认，随实现落地，见 §13#7） | `PARTIAL` |
| 禁路径形式 | 拒绝 `../`、绝对路径、盘符前缀（路径穿越） | Django `Storage.get_valid_name()` 对路径分隔符做基础清洗 → `PARTIAL`（框架基础在，无显式拒绝测试） |
| 控制字符 | 剥离控制字符与全空格畸形名 | 同上（`PARTIAL`） |
| 展示名与存储名分离 | Wagtail Document `title`（展示，可中文）与 `file`（存储名，由 storage 去重生成）天然分离 | `SATISFIED`（框架机制；`notices` 等页面引用 Document 经选择器而非文件名） |

后续验证方式：B 阶段以 `../../x.pdf`、超长名、含控制字符名样本上传，断言存储名被清洗且页面展示不回显原始路径。

### 4.5 禁止上传敏感数据（治理红线）

PRD §11：禁止上传密码、个人敏感信息、成绩名单等不应公开的数据。**定性为治理约束**（内容语义无法技术校验），处置：上传红线写入编辑培训与后台 help 文案；R1 拥有纠错下架通道（PRD §8/§11：投诉即隐藏、留内部处理记录）。`SATISFIED`（成文）＋人工治理验证（B 阶段纳入审查清单）。

---

## 5. 秘密与配置

> 增量要求（Human M7-F）；政策母法＝00_MASTER_PLAN §4.5 / M0.5 SECRETS_POLICY（代理/脚本禁区：任何工作流不得读取或输出凭据文件与环境变量值；报告只允许"路径＋字段名"）。

| 控制项 | 设计 | 现状（证据） | 定性 |
| --- | --- | --- | --- |
| 密钥经环境变量/批准 Secret 方式注入 | `env_required()` 缺失即快速失败（`base.py:115-123`） | SECRET_KEY dev/production 均 env 必填（`dev.py:8`、`production.py:7`），无内联默认值 | `SATISFIED` |
| SECRET_KEY 不用公开默认值 | 官方模板 `django-insecure-*` 内联值已废弃 | 同上；`.env.example` 值为哑值示例，生产禁用样例值 | `SATISFIED` |
| .env 不入 Git | `.gitignore:3-4` 排除 `.env`/`.env.*` | 已生效；`.env.example` 白名单入库（`.gitignore:22`） | `SATISFIED` |
| .env.example 仅示例值 | 键名＋哑值（CHANGE_ME/example.com 形态） | 已核（本步骤亲读，无真实值） | `SATISFIED`（G3 前复核一次） |
| DB 口令不入仓 | 连接串整体外置 `DATABASE_URL`（`base.py:128`） | settings 零硬编码主机/口令（A1.1） | `SATISFIED` |
| 日志不记真实密钥 | PRD §17：日志不得记录密码或敏感附件内容；异常/调试日志禁打 env 值 | 项目代码无打印配置值路径（M4-SECURITY-REVIEW §6：入口唯一、来源 stdin/env、无泄露路径；`DEBUG=False` 时 Django 不在错误页暴露 settings） | `SATISFIED`（成文＋现状无违规；断言 SEC-13） |
| production DEBUG=False | `production.py:3` | 已配置 | `SATISFIED` |
| 测试与生产隔离 | PRD §16：测试/生产不共享数据库、媒体目录、密钥、域名 | TEST_DATABASE_URL 独立库（`base.py:133-136`）；生产参数待部署确认 | `SATISFIED`（代码面）＋`NEEDS_VERIFICATION`（部署面） |
| CI 用平台 Secret Store | CI 不落秘密于仓库/日志，用平台 Secret Store 注入 | CI 未建（MB15 计划挂 secret 扫描与依赖检查） | `NEEDS_VERIFICATION` → MB15 承接 |
| 曾暴露令牌轮换 | 综合审计 P0（敏感字段曾入代理 transcript） | M0.5 政策已立；轮换动作属项目负责人运维事项 | 登记 §14（非代码项） |

---

## 6. 审计与日志

### 6.1 内容操作审计

- Wagtail 自带修订历史＋log_actions：记录操作者与时间（PRD §5）；页面动线有 PageLogEntry（M4 实测，矩阵 §3.6）→ `SATISFIED`。
- 保留 ≥ 1 年（PRD §15 审计日志口径）：现状无任何清理/归档任务＝自然保留 → `SATISFIED`（现状）＋备份覆盖验证留 M7.2/部署复核。
- 已知缺口（承接 M4-SECURITY-REVIEW 遗留 #4）：**用户与组管理动线无 DB 级审计**（wagtailusers 仅 Python logging，Wagtail 7.4.2 上游现状；T14 断言已固化该行为）。登记 §7 R-05，处置留项目负责人裁决（可接受/补 webhook 日志）。

### 6.2 日志脱敏规则（成文）

1. 不记录密码、密钥、env 值、Token（§5；PRD §17）。
2. 不记录敏感附件内容或其可还原摘要（文件名路径可记）。
3. 用户身份以岗位账号名记录；前台不显示操作人姓名（PRD §4.3，矩阵 §5）。
4. DEBUG 级日志不入生产日志管道（DEBUG=False 生产前提下自然收敛）。

### 6.3 异常登录监控点

- PRD §17 五项监控之一（其余四项属 M7.2 非功能基线/部署）。
- 判定口径建议（与 §2.3 限速联动）：① 单账号连续失败达阈值（与 axes 锁定同源取数）；② 单 IP 高频失败跨多账号（爆破特征）；③ 锁定解除后立即再失败（耐心攻击特征）。命中→记结构化日志并告警。
- 实现载体：B6（监控落地，工具不锁定）→ **`NOT_IMPLEMENTED`**（断言 SEC-30）。

---

## 7. 已知风险登记表

引用两审计安全相关行＋本基线处置状态（"关闭"＝已有实现或决策消解；"承接"＝本文已落设计，实现待 B/部署）：

| 编号 | 来源 | 风险 | 处置状态 |
| --- | --- | --- | --- |
| R-01 | 上游审计 R2 | 板块级 Publish 横向越权（扁平树方案 b） | **关闭**——ADR-0004 容器树（方案 a）结构性规避；T07 反向验证成立 |
| R-02 | 上游审计 R3 | Snippet 无 per-instance 权限 | **关闭**——V1 部门账号零 Snippet 权限（ADR-0004 决策 3；矩阵 §3.2；T10 全拒） |
| R-03 | 上游审计 R7 ＋ 综合审计 P2 | 附件伪造 MIME 校验深度 | **承接**——三级校验设计见 §4.2；现状 NOT_IMPLEMENTED（SB-05 待实现后可测） |
| R-04 | 综合审计 P0 | 凭据进入代理 transcript/Evidence Packet | **关闭（政策）＋待办（轮换）**——M0.5 秘密禁区政策固化＋MB15 CI secret 扫描；令牌轮换登记 §14 |
| R-05 | M4-SECURITY-REVIEW 遗留 #4 | 用户/组管理无 DB 级审计 | **开放（低）**——上游现状；§6.1 处置留裁决 |
| R-06 | M4-SECURITY-REVIEW 遗留 #5 | 无首登/重置后强制改密开关 | **承接**——机制设计 §2.4；NOT_IMPLEMENTED（SB-04） |
| R-07 | M4 报告 P4-b3 | 批量移动绕 `before_move_page` 钩子 | **开放（低，非越权）**——定性为内容模型完整性绕过（M4.3 ③-6）；正式实现补 move 批量守卫 |
| R-08 | 上游审计 U5 | 生产反代/证书条件未知 | **收窄（2026-08-31）**——反代形态已确认＝Caddy（Q10），§1 网段方案已随 Q4 撤销；域名/证书等部署条件仍待提供（PP-19 `DEFERRED_DEPLOYMENT_DETAIL`） |

---

## 8. 可追溯性表

| 基线主题 | PRD 要求 | 其他引源 | 本文章节 | 断言 | 现状 |
| --- | --- | --- | --- | --- | --- |
| 后台仅校园网/VPN | PRD §5 | 矩阵 §3.5；02 S7.1 §1 | §1 | SB-01/SEC-23 | NOT_IMPLEMENTED → 2026-08-31 Human 决策（Q4）V1 公网访问，本行要求随决策关闭（§1.1/§13#4） |
| 后台 HTTPS | PRD §5 | 02 S7.1 §1 | §1.4/§3.2 | SEC-24 | NOT_IMPLEMENTED |
| 登录限速 | PRD §5 | 02 S7.1 §2 | §2.3 | SB-03/SEC-15 | NOT_IMPLEMENTED |
| 强密码策略 | PRD §5 | 02 S7.1 §2 | §2.2 | SB-02/SEC-14 | SATISFIED |
| 重置后强制改密 | PRD §5 | 矩阵 §4；M4 遗留 #5 | §2.4 | SB-04/SEC-16 | NOT_IMPLEMENTED |
| 修订历史/操作者 | PRD §5 | 矩阵 §4 | §6.1 | SEC-05 附 | SATISFIED |
| 不自建用户体系 | PRD §5 | 矩阵 §3.1 | §0.2 | SEC-05 | SATISFIED |
| 附件类型/大小限制 | PRD §11 | CM §11.3；02 S7.1 §4 | §4.1 | SEC-17 | PARTIAL |
| 危险扩展名/伪造 MIME | PRD §11 | 上游 R7；综合 P2 | §4.2/§4.3 | SB-05/SEC-18 | NOT_IMPLEMENTED |
| 禁传敏感数据 | PRD §11 | CM §11.3 | §4.5 | —（治理） | SATISFIED（成文） |
| 外链确认跳转页 | PRD §7.5、§11、§23 | CM §11.4 | §10-7/§6 前置 | SB-06/SEC-21 | NOT_IMPLEMENTED |
| 前台免登录公开 | PRD §12 | 矩阵 §5 | §2.1 | SEC-29 | SATISFIED |
| 日志脱敏 | PRD §17 | 综合审计 | §6.2 | SEC-13 | SATISFIED |
| 异常登录监控 | PRD §17 | 02 S7.1 §6 | §6.3 | SEC-30 | NOT_IMPLEMENTED |
| 权限默认拒绝/部门隔离 | PRD §4.3、§23 | ADR-0004；T01–T16 | §0.2 | SEC-01–04 | SATISFIED |
| CSRF/会话 | PRD §5（框架面） | 02 S7.1 §3 | §3.1/§3.2 | SEC-06–08 | SATISFIED |
| 秘密管理 | PRD §16 | M0.5；综合 P0 | §5 | SEC-10–12 | SATISFIED |
| 测试/生产隔离 | PRD §16 | — | §5 | SEC-09 | SATISFIED（代码面） |

---

## 9. 断言清单

> 增量要求（Human M7-I）：可测试断言体系，编号 SEC-xx（即 00_MASTER_PLAN §14 M7.1 阶段目标所称 SE-xx，命名统一为 SEC-xx）；不写测试代码——每条给出验证方法，作为 B 阶段安全测试（分级 A）的设计源。02 计划 SB-01–SB-06 全部纳入并映射。

### 9.1 SEC-xx 断言（SEC-01–SEC-30）

| 编号 | 断言（可测试陈述） | 验证方法 | 状态 |
| --- | --- | --- | --- |
| SEC-01 | 未授权操作默认被拒（fail-closed）：无对应权限的已登录账号对任何写操作，数据库零变更 | 矩阵 §6 通用拒绝断言（零变更快照）；T 系列拒权格 | `SATISFIED`（M4.3 16/16） |
| SEC-02 | 部门账号仅能对本部门容器子树读写发 | T05/T06/T09/T13 构造动线全拒 | `SATISFIED` |
| SEC-03 | 跨部门写操作在服务端阻止，按钮显隐不构成防线（GET 表单可达即越权信号） | 拒权后 GET 确认页不可达 200 断言＋库零变更 | `SATISFIED` |
| SEC-04 | 高权限动线（账号、词表、推荐位、站点设置、永久删除）仅 R1 可达 | T08/T10/T11/T12 | `SATISFIED` |
| SEC-05 | 系统不含第二套用户/权限实现：无自定义认证与 RBAC 代码 | 代码审计（M4-SECURITY-REVIEW §6；G3 复审） | `SATISFIED` |
| SEC-06 | 全站表单 POST 受 CSRF 保护，无豁免入口 | 无 token POST → 403 回归断言；`csrf_exempt` 零命中扫描 | `SATISFIED` |
| SEC-07 | 会话 Cookie 带 HttpOnly | 响应头断言 `Set-Cookie: sessionid` 含 HttpOnly | `SATISFIED`（Django 默认） |
| SEC-08 | 会话 Cookie SameSite=Lax | 响应头断言 | `SATISFIED`（Django 默认） |
| SEC-09 | 生产配置 `DEBUG=False` 且 ALLOWED_HOSTS 非通配 | 部署环境 `manage.py check --deploy` 警告清零 | `SATISFIED`（配置在仓；部署环境复核） |
| SEC-10 | SECRET_KEY 无公开默认值、缺失即拒绝启动 | 无 SECRET_KEY 启动 → RuntimeError 快速失败测试 | `SATISFIED` |
| SEC-11 | `.env` 不入库；`.env.example` 仅哑值 | `git ls-files` 无 .env；example 文件复核 | `SATISFIED` |
| SEC-12 | 数据库口令仅经 DATABASE_URL 环境变量进入进程 | 仓库内无连接串硬编码（审计） | `SATISFIED` |
| SEC-13 | 日志与错误输出不含密码/密钥/env 值/附件内容 | G3 抽查＋DEBUG=False 错误页无 settings 暴露 | `SATISFIED` |
| SEC-14 | 弱密码（过短/常见/纯数字/与属性相似）被拒 | `validate_password` 样本矩阵断言 | `SATISFIED` |
| SEC-15 | 连续失败登录达阈值触发锁定 | SB-03 场景（未实现） | `NOT_IMPLEMENTED` |
| SEC-16 | 密码重置后未改密账号无法执行其他后台操作 | SB-04 场景（未实现） | `NOT_IMPLEMENTED` |
| SEC-17 | 上传白名单＝PRD §11 集合（pdf/doc/docx/xls/xlsx/ppt/pptx/png/jpg/webp），白名单外拒绝 | 白名单内外样本上传矩阵 | `PARTIAL`（机制在、集合待收窄） |
| SEC-18 | 扩展名、MIME、魔数不一致的文件被拒 | SB-05 伪装修样本矩阵（未实现） | `NOT_IMPLEMENTED` |
| SEC-19 | 存储文件名无路径形式/控制字符/超长；展示名与存储名分离 | 文件名攻击样本上传断言 | `PARTIAL`（框架基础清洗在，显式规则未落） |
| SEC-20 | 外链仅接受 http/https scheme，缺协议/userinfo/相对 URL 拒绝 | §10-7 处理规则逐条断言（收窄未实现） | `PARTIAL`（URLField 格式校验在，scheme 白名单未收窄） |
| SEC-21 | 外链前台输出经统一确认跳转页，显示域名/来源/时间/声明 | SB-06 场景（未实现） | `NOT_IMPLEMENTED` |
| SEC-22 | 站内不存在用户可控的开放重定向 | redirect 目标白名单断言（跳转页未建，随 SEC-21 落地） | `NEEDS_VERIFICATION` |
| SEC-23 | 后台路径仅校园网/VPN 网段可达 | SB-01 场景（未实现） | `NOT_IMPLEMENTED` |
| SEC-24 | 生产强制 HTTPS 并启用 HSTS | curl http→301 断言；HSTS 头断言 | `NOT_IMPLEMENTED` |
| SEC-25 | 模板输出默认转义；无 RawHTML/任意 HTML 入口 | XSS 样本回显断言；CM-07 白名单反射断言 | `SATISFIED` |
| SEC-26 | 数据库访问全部 ORM 参数化，无 SQL 字符串拼接 | 代码审计（`raw(`/`extra(` 零命中扫描） | `SATISFIED` |
| SEC-27 | 无 shell 拼接；管理命令敏感参数经 stdin/env 传入 | 代码审计（subprocess 零命中）＋M4 口令纪律复审 | `SATISFIED` |
| SEC-28 | 响应头基线：X-Frame-Options DENY、nosniff、Referrer-Policy 同源 | curl 响应头断言 | `SATISFIED`（Django 默认＋中间件实证） |
| SEC-29 | 未发布/已下线/已归档内容前台与默认搜索不可见 | PRD §23 必测项；N13/四态可见性断言 | `SATISFIED` |
| SEC-30 | 异常登录（阈值/跨账号爆破/解锁即再失败）产生结构化告警日志 | 监控点注入测试（B6） | `NOT_IMPLEMENTED` |

### 9.2 SB-01–SB-06（02 S7.1 断言，原文纳入并映射）

| 编号 | 断言原文（02 S7.1 §9） | 验证方法 | 映射 | 状态 |
| --- | --- | --- | --- | --- |
| SB-01 | 后台非校园网访问被拒 | 非 VPN 源 IP 访问 `/admin/` → 403/拒绝（部署环境执行） | SEC-23 | `NOT_IMPLEMENTED` |
| SB-02 | 弱密码被拒 | 密码校验器样本矩阵（§2.2） | SEC-14 | `SATISFIED` |
| SB-03 | 连续失败登录触发限速 | axes 锁定行为断言（§2.3，未实现） | SEC-15 | `NOT_IMPLEMENTED` |
| SB-04 | 重置后未改密不能进行其他操作 | 改密前路由拦截断言（§2.4，未实现） | SEC-16 | `NOT_IMPLEMENTED` |
| SB-05 | 伪造扩展名/魔数不符文件被拒 | 三级校验样本矩阵（§4.2，未实现） | SEC-18 | `NOT_IMPLEMENTED` |
| SB-06 | 外链经确认跳转页且显示域名/来源/时间/声明（PRD §7.5） | 跳转页四要素断言（§10-7/§6 前置，未实现；PRD §23 必测） | SEC-21 | `NOT_IMPLEMENTED` |

---

## 10. 输入边界专节

> 增量要求（Human M7-B）：逐项写来源/允许格式/校验位置/异常处理/现状/后续验证方式。总原则承接 §0.2：一切输入在服务端校验；界面约束只是体验层。

### 10-1 搜索参数（`/search/`）

- 来源：前台 GET `request.GET`（`search/views.py:15`）。
- 允许格式：五参数 `q/section/dept/type/tag`——`q` 自由文本（模板转义回显）；`section` ∈ 五冻结 slug；`type` ∈ 五值单射；`dept`/`tag` ∈ 存在的 slug。
- 校验位置：`search/services.resolve_search_filters` 服务层白名单解析（双入口共用：搜索页＋板块列表页）。
- 异常处理：非法值**视同未提供**，200 回退全量/表单态，不 404 不 5xx（CONTENT_MODEL §21.3）；无参数不查全量。
- 现状：`SATISFIED`（M3.4 契约实现＋`tests/test_search_contract.py` 等测试族）。
- 后续验证：`<script>`/SQL 元字符/超长 q 回显与查询回归；非法维度值回退断言（已有，MB 回归保持）。

### 10-2 筛选参数（板块列表页）

- 来源：前台 GET（与搜索共用过滤层，CONTENT_MODEL §21.1 双载体）。
- 允许格式/校验位置/异常处理：同 10-1（同一 `services` 过滤层＝单一事实源）。
- 现状：`SATISFIED`。
- 后续验证：与 10-1 共用回归集。

### 10-3 后台表单

- 来源：已登录后台用户提交（Wagtail admin 页面/Snippet/设置表单）。
- 允许格式：由模型字段类型＋Panel 定义决定（Django forms 机制）。
- 校验位置：字段级 form 验证＋模型 `clean()`（如 `NoticePage.clean` 组合板块/有效期/活动字段/标签四组校验，`notices/models.py:271-280`）。
- 异常处理：ValidationError 汇总回显，不落库。
- 现状：`SATISFIED`（框架＋M3/M5 实现的 clean 族）。
- 后续验证：T 系列回归＋边界值（超长、类型错位）样本。

### 10-4 StreamField

- 来源：后台页面编辑器（分片字段 `body-count/body-0-type/body-0-value`，矩阵 §3.6）。
- 允许格式：白名单六块（标题/受控富文本/图片/附件/表格/外链，`notices/blocks.py:81-88`）；RichText 限 `bold, italic, link, ol, ul` 五 features（`blocks.py:19`）；类型级收窄（SoftwareToolPage 减附件块）；**RawHTML 全族禁入**（CM-07）。
- 校验位置：StreamField 块级解析（未知块类型/缺块即 ValidationError）＋RichText features 双层过滤（编辑器工具条＋入库转换）。
- 异常处理：非法块/非法 features 拒绝保存。
- 现状：`SATISFIED`（结构与 features 已收窄；白名单"以测试反射断言"留 B 阶段——CM §11.1 落位提示）。
- 后续验证：反射断言全站 StreamField 块集 ⊆ 六块；Draftail ContentState 非法 payload 拒绝。

### 10-5 分类与标签

- 来源：后台编辑表单（受控标签多选）。
- 允许格式：仅受控词表既有 Tag（总管理员维护，Snippet 权限 R1 专属）。
- 校验位置：三道闸——表单闸（`ControlledTagField` 词表多选，`notices/models.py:64-73`）＋clean 闸（`clean_controlled_tags` 在集群自动创建**前**拦截未知名，`notices/models.py:76-88`）＋权限闸（词表 Snippet 零部门权限，T10）。
- 异常处理：未知标签 ValidationError 中文提示，不自动建签。
- 现状：`SATISFIED`（CM-08；T10 通过）。
- 后续验证：伪造 tag id/直 POST 未知标签名 → 拒绝断言（T10 回归）。

### 10-6 文件上传

- 来源：已登录后台用户（wagtaildocs 文档库/附件块；wagtailimages 图片库/图片块）。
- 允许格式：PRD §11 白名单（§4.1 目标集）；大小上限＝**20 MiB（Human 2026-08-31 确认，Q1；§13）**。
- 校验位置：wagtaildocs 扩展名白名单（①层）＋生产可加的魔数钩子（③层，§4.2）；图片面 Willow 解码校验。
- 异常处理：白名单外/超限/魔数不符→上传拒绝报错。
- 现状：`PARTIAL`（①层机制在但集合未对齐 PRD；③层未实现；上限两值冲突待确认）。
- 后续验证：SB-05 样本矩阵（§4.2）；文件名攻击样本（§4.4）。

### 10-7 外部链接（字段与跳转目标）

- 来源：后台编辑表单（`external_url` URLField ×4 处＋外链块 URLBlock，CM §11.4 清单：通知/文章 `external_url`、活动 `event_registration_url`、资料 `external_url`、软件工具 `source_url`）。
- 允许格式：**仅 http/https** 绝对 URL；展示与比对统一规则（增量 E 成文）：
  1. **前后空白**：strip 后再校验（拒绝"空格夹带"）；
  2. **大小写规范化**：scheme 与 host 小写化后比对/展示（`HTTPS://` ≡ `https://`）；
  3. **URL 格式错**：URLValidator 不过 → ValidationError 拒绝入库；
  4. **缺协议**：拒绝入库并提示显式补全（**不静默补 `https://`**——避免编辑意图被改写）；
  5. **user:pass 形式（userinfo）**：拒绝（含 `@` 凭据段的 URL 防钓鱼混淆，且禁止凭据进 URL——§5 纪律的输入面延伸）；
  6. **相对/不完整 URL**：拒绝（URLField 要求绝对 URL，天然拦截 `//host` 之类 scheme 相对形式须显式断言补测）；
  7. **scheme 白名单**：Django URLValidator 默认放行 `ftp/ftps` 等 scheme——**须显式收窄到 http/https**（当前未收窄 → SEC-20 `PARTIAL`）。
- 校验位置：字段层（URLField/URLBlock clean，收窄后）＋输出层（跳转页目标二次白名单校验，防库内历史脏数据）。
- 异常处理：全部拒绝路径给明确中文提示；跳转页对目标做同样校验后才 302。
- 现状：`PARTIAL`（URLField 格式校验在；scheme 收窄、userinfo/strip 规则未实现；确认跳转页未实现 → SB-06/SEC-21 `NOT_IMPLEMENTED`，§14 登记 Post-G2 Gap）。
- 后续验证：§10-7 规则 1–7 逐条断言＋跳转页四要素（域名/来源/时间/声明，PRD §7.5）断言。

### 10-8 登录与 Session

- 来源：后台登录表单（Wagtail admin 内建；PRD §5 仅用户名密码）。
- 允许格式：凭据 POST（CSRF 保护内）；会话经签名 cookie（sessionid）。
- 校验位置：Django `authenticate`＋SessionMiddleware；登录成功框架自动轮换 session key（会话固定防护，框架内建）；权限判定走矩阵（§0.2）。
- 异常处理：认证失败统一报错；未登录访问后台 302 登录页（T16）；限速未接入（§2.3）。
- 现状：`SATISFIED`（框架面）＋`NOT_IMPLEMENTED`（限速/强制改密增量）。
- 后续验证：SB-03/SB-04；会话 cookie 属性断言（SEC-07/08）；会话超时策略＝**24 小时（Human 2026-08-31 确认，Q6；§13）**。

### 10-9 management command

- 来源：服务器本地 shell 执行（运维/部署）；不暴露 HTTP 面。
- 允许格式：命令行参数（非敏感）＋敏感值经 stdin/env（口令纪律：入口唯一、来源受控、无泄露路径——M4-SECURITY-REVIEW §6）。
- 校验位置：Django command 参数解析＋命令内环境变量快速失败（`env_required` 同源）。
- 异常处理：缺参快速失败不建半账（M4 实测语义）。
- 现状：`SATISFIED`（M4 全套命令审计通过；幂等双跑零漂移）。
- 后续验证：G3 代码审计复审（零 subprocess/零 SQL 拼接维持——SEC-26/27）。

---

## 11. 输出编码与数据边界

> 增量要求（Human M7-G）：每项写框架保护机制＋项目约束＋现状＋后续测试方法。

| # | 边界 | 框架保护机制 | 项目约束 | 现状 | 后续测试方法 |
| --- | --- | --- | --- | --- | --- |
| 1 | HTML 输出 | Django 模板自动转义（`{{ }}` 默认 escape） | 禁 `|safe`/`mark_safe` 于用户内容（代码证据集零命中）；RawHTML 块全族禁入（CM-07） | `SATISFIED` | XSS 样本（`<script>`/事件属性）入库→前台回显断言被转义 |
| 2 | RichText | features 双层收窄（工具条＋入库转换，Wagtail 官方机制）；输出仅白名单 tag | features=`bold, italic, link, ol, ul`（`blocks.py:19`）；禁 image/文档链接/headings features | `SATISFIED` | 富文本 XSS 样本（onerror/伪协议链接）回归 |
| 3 | DB 查询 | ORM 全参数化（Django queryset） | 禁 `raw()`/`extra()`/字符串拼接查询 | `SATISFIED`（M4 审计：无 SQL 拼接新面；SEC-26） | 代码审计＋注入元字符搜索回归（q 参数） |
| 4 | URL 跳转 | Django `redirect()` 不校验目标——防护靠调用纪律 | 跳转目标仅站内路径或 §10-7 白名单 URL；跳转页未建（§14）；库内 `external_url` 不直出裸跳转（CM §11.4 冻结语义） | `NEEDS_VERIFICATION`（SEC-22；随 SEC-21 落地闭合） | open redirect 样本（`//evil`、`https:evil`）断言拒绝 |
| 5 | 文件路径 | `FileSystemStorage.get_valid_name()` 基础清洗＋去重命名 | 用户输入不拼接进文件路径；媒体路由生产不入 Django（§3.5） | `PARTIAL`（SEC-19） | 路径穿越/控制字符文件名样本上传断言 |
| 6 | Shell/管理命令 | Django command 无 shell 参与 | 禁 subprocess/os.system 拼接；敏感参数 stdin/env（§10-9） | `SATISFIED`（SEC-27） | 代码审计（零命中扫描入 G3 清单） |
| 7 | Template | 引擎自动转义＋固定模板文件渲染 | 禁把用户输入当模板源码渲染（`Template(text)` 于用户串）；模板目录不入用户写面 | `SATISFIED` | 审计（模板注入=以用户串建模板）零命中 |
| 8 | 日志内容 | DEBUG=False 生产不暴露 settings（§6.2） | §6.2 四条脱敏规则成文 | `SATISFIED`（SEC-13） | G3 日志抽查 |
| 9 | HTTP Header | SecurityMiddleware＋XFrameOptionsMiddleware（DENY/nosniff/Referrer-Policy/COOP，§3.2/§3.4） | 生产补 HSTS/CSP（§3.2/§3.3） | `SATISFIED`（基线项）＋`NOT_IMPLEMENTED`（HSTS/CSP） | curl 响应头断言（SEC-28/SEC-24） |

---

## 12. Implementation Mapping 状态表

> 增量要求（Human M7-H）：CONTROL/STATUS/EVIDENCE/FUTURE_ACTION 四列；★＝四项特别如实标注项。STATUS 口径见 §0.1。

| CONTROL | STATUS | EVIDENCE | FUTURE_ACTION |
| --- | --- | --- | --- |
| AUTH_PASSWORD_VALIDATORS 四校验器 | `SATISFIED` | `base.py:142-155` | min_length＝12 接线（Human 2026-08-31 确认，Q2；§13#3） |
| CSRF 全站覆盖 | `SATISFIED` | `base.py:78`；csrf_exempt 零命中 | 无 token POST 回归断言（B 阶段） |
| Session Cookie HttpOnly/SameSite | `SATISFIED` | Django 5.2 global_settings 默认实证（§3.2） | 部署环境响应头复测 |
| ★ production cookie 安全配置（SESSION/CSRF `_COOKIE_SECURE`、`SECURE_*` 一族） | `NOT_IMPLEMENTED` | `production.py` 仅 DEBUG/SECRET_KEY/ALLOWED_HOSTS/静态后端 | 部署阶段接线（目标值已确认：SameSite=Lax＋Secure＋HttpOnly＋HTTPS only——Q16；HSTS 目标 1 年先短后长——Q5）；`SECURE_PROXY_SSL_HEADER` 随 Caddy 反代（Q10）部署接线（§1.3/§13） |
| X-Frame-Options DENY | `SATISFIED` | `base.py:81`＋Django 默认 DENY | 无 |
| production DEBUG=False / ALLOWED_HOSTS 外置 | `SATISFIED` | `production.py:3,10` | 部署环境 `check --deploy` 复核 |
| ★ 附件 MIME＋魔数三级一致性校验 | `NOT_IMPLEMENTED` | `base.py:248-262` 仅扩展名＋大小；项目代码无魔数检测 | B 阶段钩子实现（§4.2；复用依赖内 filetype，不加扫描基础设施）；SB-05 随之可测 |
| 附件扩展名白名单（PRD 对齐） | `PARTIAL` | `base.py:248-259` 为官方模板默认集（csv/txt/zip/key/odt 超界；doc/xls/ppt 缺） | MB 阶段按 §4.1 目标集收窄 settings |
| 上传大小上限 | `PARTIAL` | `base.py:262` 10MB vs 02 计划默认 20MB | 20 MiB（Human 2026-08-31 确认，Q1）；MB 阶段统一 settings |
| 文件名规则（长度/路径/控制字符/分离） | `PARTIAL` | storage 基础清洗（§4.4） | B 阶段显式校验＋样本断言 |
| ★ 外链确认跳转页 | `NOT_IMPLEMENTED` | `urls.py` 无跳转路由；CM §11.4 设计冻结 | B 阶段实现（ADR-0005 #5 载体）＋§14 Gap 闭环；SB-06/PRD §23 必测 |
| 外链 scheme 白名单（http/https） | `PARTIAL` | URLField 存在；URLValidator 默认 scheme 集未收窄 | B 阶段字段收窄＋§10-7 规则断言 |
| 登录限速（django-axes） | `NOT_IMPLEMENTED` | requirements 无 axes | B 阶段接入；参数已确认（Q3：15 分钟内连续失败 10 次→临时限制 15 分钟；成功登录后计数清零） |
| 重置/首登强制改密 | `NOT_IMPLEMENTED` | M4-SECURITY-REVIEW 遗留 #5 | B 阶段按 §2.4 设计实现 |
| 后台网络边界（校园网/VPN） | `NOT_IMPLEMENTED` | 代码/settings 无 IP 限制（§1.2） | **2026-08-31 Human 决策（Q4）：V1 公网访问、不要求校园网/IP 白名单 → 本控制随决策关闭**（历史设计记录保留 §1.2） |
| HTTPS 强制/HSTS/CSP | `NOT_IMPLEMENTED` | §3.2 默认关闭；§3.3 方向已定 | 部署接线（HSTS 先短后长、目标 1 年——Q5）＋G3 复测 |
| 权限默认拒绝＋部门隔离＋高权限矩阵 | `SATISFIED` | ADR-0004 Accepted；POC 16/16；M4 安全评审 PASS | T 系列随 MB 回归 |
| 受控标签三道闸 | `SATISFIED` | `notices/models.py:64-88` | T10 回归 |
| StreamField/RichText 白名单 | `SATISFIED` | `notices/blocks.py` | 反射断言（B 阶段） |
| 搜索/筛选参数白名单解析 | `SATISFIED` | `search/services.py` | 契约测试随 MB 回归 |
| 模板自动转义/无 RawHTML | `SATISFIED` | Django 默认＋CM-07（§11-1/2） | XSS 回归 |
| ORM 参数化/无 shell 拼接 | `SATISFIED` | M4-SECURITY-REVIEW §6（§11-3/6） | G3 审计复审 |
| 秘密 env 外置/不入仓/日志不记密钥 | `SATISFIED` | `base.py:115-128`；`.gitignore:3-4`；M4 口令纪律 | MB15 CI secret 扫描挂接 |
| CI 平台 Secret Store＋依赖安全检查 | `NEEDS_VERIFICATION` | CI 未建（PRD §23 CI 要求） | MB15 落地 |
| ★ 日志/秘密边界（不记密码密钥附件） | `SATISFIED` | §6.2 规则＋现状无违规（M4 审计） | G3 日志抽查维持 |
| 修订历史/操作审计（内容面） | `SATISFIED` | PageLogEntry（矩阵 §3.6） | 保留策略随 M7.2/备份复核 |
| 异常登录监控 | `NOT_IMPLEMENTED` | 无实现（§6.3） | B6 落地（口径已定） |

STATUS 计数（27 行）：`SATISFIED` 14 ／ `PARTIAL` 4 ／ `NOT_IMPLEMENTED` 8 ／ `NEEDS_VERIFICATION` 1。

---

## 13. 安全待确认参数表（集中）

> 大小上限未定等参数集中于此（增量 D/F）；确认人＝项目负责人；M7.2 待确认参数表互见（本表仅安全项）。**2026-08-31 G2-A 更新**：项目负责人已对 23 项项目参数逐项确认（Human Confirmed Date＝2026-08-31；全表 Q1–Q23＝`docs/G2_HUMAN_DECISIONS.md`；NFR §12 为全文唯一集中表并集），本表新增末列状态，**`G2_PENDING_PARAMETERS = 0`**。部署阶段细节（CPU/RAM/IP/具体磁盘路径/具体 PVE VM·CT/具体 NAS/对象存储厂商）统一 `DEFERRED_DEPLOYMENT_DETAIL`，不计入 G2 待确认参数。

| # | 参数 | 建议默认 | 现状 | 关联 | G2-A 状态（2026-08-31） |
| --- | --- | --- | --- | --- | --- |
| 1 | 附件大小上限 | 20MB（02 S7.1 建议，标记确认） | 10MB（`base.py:262` 模板默认） | §4.1 | `HUMAN_CONFIRMED`＝**20 MiB**（Q1；MB 阶段 settings 对齐） |
| 2 | django-axes 限速参数 | 5 次 / 15 分钟（标记确认） | 未安装 | §2.3；SB-03 | `HUMAN_CONFIRMED`＝**15 分钟内连续失败 10 次→临时限制 15 分钟；成功登录后失败计数清零**（Q3） |
| 3 | `MinimumLengthValidator.min_length` | 8（现状）→ 建议 10–12 | 未显式配置 | §2.2 | `HUMAN_CONFIRMED`＝**12 字符**（Q2；继续 Django/Wagtail 原生账号机制） |
| 4 | 校园网＋VPN 网段清单 | 待校方提供（上游 U5） | 无 | §1.2/§1.3；SB-01 | `HUMAN_CONFIRMED`＝**允许公网访问，V1 不要求校园网/IP 白名单**——无需网段清单（Q4；SB-01/SEC-23 随决策关闭） |
| 5 | HSTS 秒数（先短后长策略） | 建议 1 年（成熟后） | 0 | §3.2；SEC-24 | `HUMAN_CONFIRMED`＝**最终生产目标 1 年；初次上线先用较短周期，HTTPS/证书/反代稳定后提升**（Q5） |
| 6 | 后台会话时长（SESSION_COOKIE_AGE） | 建议缩短至 ≤ 1 天（后台面） | 2 周（Django 默认） | §3.2 | `HUMAN_CONFIRMED`＝**24 小时**；主动退出立即结束；改密等重要账号变更后相关 Session 结束（Q6） |
| 7 | 存储文件名长度上限 | 255 字节截断保留扩展名 | 未显式 | §4.4 | `DEFERRED_DEPLOYMENT_DETAIL`＝工程默认（255 字节截断保留扩展名）随实现落地；非 Human 政策参数（Q1–Q23 未含） |
| 8 | 生产反代形态（TLS 终结位置） | 决定 `SECURE_PROXY_SSL_HEADER` 与限速 IP 口径 | 待校方环境（U5） | §1.3/§3.2 | `HUMAN_CONFIRMED`＝**Caddy（TLS 终结于反代）**（Q10）；`SECURE_PROXY_SSL_HEADER` 具体接线值部署阶段定 |

---

## 14. Post-G2 Gap 登记

> G2 门放行时明确知道、由 MB/部署阶段承接的缺口（增量 E 登记）。全部 NOT_IMPLEMENTED 控制的实现义务集中于此，不得在 G2 材料中被表述为已完成。

| Gap | 承接阶段 | 阻断断言 |
| --- | --- | --- |
| 外链确认跳转页（PRD §7.5 四要素） | B 阶段（MB） | SB-06/SEC-21；PRD §23 必测 |
| production cookie/`SECURE_*` 接线 | 部署阶段（G3 前复核） | SEC-24（部分）；目标值已确认（Q16 cookie 四项、Q5 HSTS、Q6 会话 24h、Q10 Caddy） |
| 附件三级校验＋白名单 PRD 对齐＋上限 | MB | SB-05/SEC-17/SEC-18（上限值已确认＝20 MiB，Q1） |
| 登录限速、强制改密 | MB | SB-03/SB-04（限速参数已确认，Q3） |
| ~~后台网络边界（反代 ACL/中间件）~~ | 部署阶段 | SB-01——**2026-08-31 撤销：Human Q4 确认 V1 公网访问、不要求校园网/IP 白名单，本 Gap 随决策关闭** |
| 异常登录监控、CI Secret Store | B6/MB15 | SEC-30 |
| 曾暴露令牌轮换（治理动作） | 项目负责人 | —（非代码） |
| 用户/组管理 DB 级审计裁决（R-05） | 项目负责人裁决 | — |

---

## 附：验收命令自检记录

本文完成后在分支 `arch/m7.1-security-baseline` 按源步骤执行 02 S7.1 与 00 §14 M7.1 验收命令（结果见提交说明与 worker_done）：文件存在、关键词齐全（校园网/VPN/限速/强制改密/魔数/白名单/审计/默认拒绝/外链）、`AUTH_PASSWORD_VALIDATORS`、`SB-0[1-6]`、`PRD §` ≥ 10、§4.5 秘密扫描零命中。
