<!--
SPEC-001 ADR-0009 · 本仓库内新撰写（非上游恢复，与 0008 的 verbatim 恢复
载体不同）。授权链＝SPEC-001 Spec Issue（#2，G1 Human 已授权）Ticket F11
（#11，R2）——Spec「Relevant ADRs 预期产出②《部署拓扑》ADR 在此定稿」。
状态适用范围显式限于 staging；生产接线终决属 B03（R3）/Human Gate。
〔正仓集成注（2026-09-18）：下文引用的 docs/cutover-frontend.md 与
evidence/b03-integration-rehearsal 属验收版仓库，不在本仓；本仓对应物＝
deploy/Caddyfile＋deploy/docker-compose.yml 与 docs/PRODUCTION_RUNBOOK.md
§12。〕
B03 补记（2026-09-17）：切换/回滚机制已在本 ADR 路由表形状内定稿（唯一开关
＝路由表第 7 行默认上游 STAGING_DEFAULT_UPSTREAM）并本地演练实测通过
（docs/cutover-frontend.md + evidence/b03-integration-rehearsal）——零路由表
形状变更，非冲突修订；生产接线执行属 B04（R4，Human Gate G6 之后）。
-->

# ADR-0009 · 部署拓扑：compose 双应用容器＋Caddy 同源（staging 定稿）

## 状态字段头

| 字段     | 值                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 编号     | 0009                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 日期     | 2026-09-16（F11 落盘）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 状态     | Accepted（**范围限 staging**：F11 R2 自主授权内定稿，载体＝本仓库 `compose.staging.yaml` + `Caddyfile.staging` + CI `staging-topology` 门。生产接线（真实域名/TLS/PostgreSQL 复用/调度器/cutover 路由）属 B03（R3，Human Gate）——B03 落地时若与本 ADR 冲突，按修订流程改本文件，不得静默偏离）。**B03 补记（2026-09-17）**：切换/回滚机制定稿＝路由表第 7 行默认上游参数化（`STAGING_DEFAULT_UPSTREAM`，v2 缺省 `frontend:4321`；v1 回滚态 `backend:8000` 整站回根），零路由表形状变更、非冲突修订；runbook 与演练实测见 `docs/cutover-frontend.md`（阈值：切换中断 <60s、回滚 v1 <300s，均实测通过）；生产接线执行属 B04（R4，G6 之后） |
| 关联决策 | SPEC-001 Architecture Constraint 3（单台服务器、单一 Peiligo Compose 项目内新增独立双应用容器，复用既有 Caddy/PostgreSQL/调度器；浏览器同源）/ Constraint 5（与 Peilige/Peilike 严格隔离）/ Staging 1（受限·noindex·新旧并排）；ADR-0008 §S1（`/api/` 不公开路由、旧 Django 路径继续路由）                                                                                                                                                                                                                                                                                                                                               |

## 背景

- **要解决的问题**：F11a 定了 Astro 应用容器本体、B02 定了 overlay 后的真实 Django 容器，两者尚未被放进同一个**同源浏览器拓扑**——评审（G5 真机）、新旧并排对比、noindex/受限访问、与生产同构的故障语义都需要一个可本地验证、可整体搬上单台服务器的 staging 拓扑定义。
- **现状**：`compose.mock.yaml`（F11a 契约夹具冒烟）与 `compose.overlay.yaml`（B02 双容器冒烟）都是开发/验证拓扑，各自把 frontend/backend 端口直接暴露到宿主机，无入口层、无访问门、无并排对比路径——均**不是**部署模板。

## 决策

**staging＝一个 compose 项目（`peiligo-staging`）三个服务：`caddy`（唯一公开入口，单端口单 origin）＋ `frontend`（新 Astro）＋ `backend`（overlay 后真实 Django/Wagtail，sqlite 冒烟数据面）。路由表冻结如下，Caddy `route` 内按书写顺序执行：**

| #   | 匹配                                                                                   | 动作                                                                                      | 依据                                                                                                                     |
| --- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1   | 全部响应                                                                               | 加 `X-Robots-Tag: noindex, nofollow`                                                      | Staging 1 禁收录                                                                                                         |
| 2   | `/robots.txt`                                                                          | 覆盖为全站 `Disallow: /`，**免认证**                                                      | 爬虫须能读到禁抓信号（与 v1 robots 同理）；兼作 Caddy 存活探针                                                           |
| 3   | 其余全部                                                                               | `basic_auth`（凭据经 `STAGING_BASIC_AUTH` 注入，compose `:?` 门＝未设置拒绝启动）         | Staging 1 受限访问                                                                                                       |
| 4   | `/api/v1/*`                                                                            | `404`（不代理）                                                                           | **ADR-0008 §S1：Caddy 不公开路由 `/api/`**——API 仅经 Compose 内网供 Astro SSR 取数，浏览器零直接调用                     |
| 5   | `/legacy/*`                                                                            | 剥前缀 → `backend:8000`                                                                   | 新旧并排对比路径（旧＝Wagtail 渲染）                                                                                     |
| 6   | `/django-admin/`、`/admin/`、`/static/`、`/media/`、`/documents/`、`/link-confirm/go/` | → `backend:8000`                                                                          | ADR-0008 §S1 保持 Django 现状（管理面、静态/媒体/文档、外链出口 go 端点）；`/static/` 亦是 `/legacy/` 页面的资源引用前缀 |
| 7   | 其余                                                                                   | → 默认上游 `STAGING_DEFAULT_UPSTREAM`（缺省 `frontend:4321`；v1 回滚态置 `backend:8000`） | 新 Astro 站点（唯一默认上游；`/search/`、`/link-confirm/`、`/preview/` 等随之）。B03 切换/回滚唯一开关，路由表形状不变   |

配套冻结：

- **隔离（Constraint 5）**：compose 项目名 `peiligo-staging` → 网络卷等全部资源项目内自洽（默认网络 `peiligo-staging_default`），**零 `external` 网络、零共享卷、零 bind 挂载宿主数据目录**（backend sqlite 在容器内一次性）；环境变量前缀 `PEILIGO_STAGING_*`/`STAGING_*`。与 Peilige/Peilike 之间不存在任何可达路径。
- **健康语义**：frontend 用镜像内置 `/healthz` 探针（进程活着即健康，上游故障不翻转——F08 契约）；backend 探 `/api/v1/chrome`（迁移完成＋WSGI 就绪）；caddy 探免认证的 `/robots.txt`。三者均 `restart: unless-stopped`。
- **故障语义**：frontend 容器停 → caddy 对新前端路径 502（入口层如实反映下游故障），backend 不受影响——旧 Wagtail 路径与管理面照常，Wagtail 发布时效与新前端重建/部署完全解耦（Constraint 3「重建不影响 Wagtail」）。backend 停 → 新前端按 F08 契约走 ≤5min 陈旧回退→样式化错误，管理面 502。
- **已知评审限制**：`/legacy/` 页面内的站内链接是根路径绝对地址，点击会落回新前端——并排对比须手动保持 `/legacy/` 前缀。不在 overlay 内加改写中间件（改基线行为＝超范围）；生产切换（B04）后该路径整体退役，此限制仅存在于评审期。

## 后果

- **正面**：单一 origin 即完整评审面（G5 真机评审无需多端口多服务）；新旧对比、noindex、受限访问、管理面接线全部可本地验证并随 CI 门防漂移；拓扑整体可搬上单台服务器（B03 只替换数据面与 TLS/域名参数，不改路由表形状）。
- **代价与权衡**：staging 走 http（TLS 属生产接线）；backend 用容器内 sqlite（生产 PostgreSQL 复用属 B03，本拓扑不挂卷即不碰任何既有卷）；basic_auth 明文 realm 级访问门只满足「受限」，不满足多用户审计（生产评审若需账号体系，B03 升级——不静默沿用）。
- **`/api/` 不公开路由的验证面**：CI `staging-topology` 门断言同 origin 下 `/api/v1/chrome` 为 404、而首页仍渲染真实数据（证明 SSR 内网取数工作正常）——同源与 API 不公开两个命题同时成立。

## 替代方案

1. **staging 上把 `/api/v1/` 经 Caddy 公开路由** → 未选：直接违反 ADR-0008 §S1 冻结条款；浏览器零直接 API 调用的安全基线（F04 服务层契约）不需要它，公开面只会扩大攻击面。生产若需公网 API 属 public API 变更（R3+），走契约演进。
2. **把旧站整树挂在 `/legacy/` 下（Wagtail 加 URL 前缀中间件）** → 未选：须改基线 Django 行为（overlay 红线）或引入子路径部署复杂度；对比评审用前缀导航即可达成。
3. **入口用 nginx/traefik** → 未选：生产既有 Caddy（Constraint 3 复用原则）；staging 与生产同入口件可让路由表在演练（B03）时零转译。
4. **frontend/backend 继续各自直曝宿主端口（compose.overlay 式）** → 未选：无单一 origin、无访问门，不符合 Staging 1，且会把内网 API 面暴露到宿主。
