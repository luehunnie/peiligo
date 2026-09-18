# Peiligo 生产运行手册（F-09～F-13 收口）

适用架构＝冻结口径：Linux/PVE + Docker Compose + PostgreSQL + Caddy(HTTPS)。
不含 Redis/Celery/Elasticsearch/SPA/K8s。样例配置见 `deploy/.env.example`。

> **状态（2026-09-12 复核）**：本文是**未来公网部署的工程预案**——截至当前阶段
> 尚未在任何真实服务器上执行过（Peiligo 尚未对公网部署，亦未做 DNS / 域名 /
> 真实 TLS 配置）。本地 Production-like Docker 验证已 PASS（2026-09-02）；
> 执行本文操作属于未来部署阶段的工作。

---

## 1. 首次部署

1. 服务器上取得代码（main 分支对应发布提交）。
2. `cd deploy && cp .env.example .env`，逐项填入真实值：
   - `POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD`：数据库三元组；
   - `SECRET_KEY`：≥50 位随机串（`python -c "import secrets;print(secrets.token_urlsafe(64))"`）；
   - `ALLOWED_HOSTS`：对外域名（逗号分隔）；
   - `DOMAIN`：Caddy 站点域名（同 ALLOWED_HOSTS 首项）；DNS A 记录指向本机；
   - `CSRF_TRUSTED_ORIGINS`：同源部署可留空；如另有跨源管理入口再补；
   - `SECONDARY_BACKUP_DIR`：独立副本目录——强烈建议指向另一块独立存储
     （NFS/外接盘）；不设＝无独立副本（ops_report 将显式 WARN）；
   - `BACKUP_ROOT`：**可选**——缺省落在 compose 具名卷 `backups`
     （容器内 `/data/backups`，重建容器不丢）；仅当要落到宿主目录/独立盘时
     才设置（bind mount 自理），并确认盘容量（见 §4 disk 信号）。
     以上变量均经 compose `environment` 显式透传进容器，`.env` 即生效。
3. 启动（首次自动构建镜像）：
   ```
   docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build
   ```
   web 容器 entrypoint 串行完成：等 DB 可达 → `migrate` → 铺 static → 起 gunicorn；
   scheduler 等 web 健康后才启动。Caddy 首次启动自动申请并续期证书（无需人工干预）。
4. 验证：`curl -f https://<域名>/healthz/` 返回 `{"status":"ok"}`；
   `/readyz/` 返回 ok 表示 DB 可达。后台 `https://<域名>/admin/` 正常登录。

## 2. 日常健康检查

- `/healthz/`：进程活着即 ok（不查 DB，供探针/负载均衡高频使用）。
- `/readyz/`：DB `SELECT 1` 可达才 ok，否则 503（不泄漏异常细节）。
- compose 内置：db 用 `pg_isready`，web 用容器内 `healthz` 探测（10s×12 次）。

## 3. 监控信号与告警接线（F-13）

无平台、无常驻守护：cron/定时器每 ≥5 分钟跑一次快照命令：

```
# /etc/cron.d/peiligo-ops（示例，宿主机或容器内均可）
*/5 * * * * docker compose --env-file deploy/.env -f deploy/docker-compose.yml \
    exec -T web python manage.py ops_report >> /var/log/peiligo-ops.json 2>&1
```

- stdout＝单份 JSON（`overall` + 各信号 `ok/warn/crit`）；
- 存在任一 CRIT → 命令非零退出。告警即接「退出码非零」（或对 JSON 做 `overall!=ok` 判断）。

信号与阈值：

| 信号 | 含义 | WARN | CRIT |
|---|---|---|---|
| database | SELECT 1 | — | 连不上 |
| disk | MEDIA_ROOT/BACKUP_ROOT/STATIC_ROOT 所在盘剩余 | <20% | <10% |
| backup_freshness | 最新备份集距今 | >12h | >24h；无备份集 |
| backup_freshness.secondary | 独立副本 | 未配置 SECONDARY_BACKUP_DIR | 已配置但为空/过期同上 |
| backup_heartbeat | 最近一次 backup_run 结果 | — | ok=false |
| publish_scheduled | 最近一次定时发布心跳 | >15 分钟未跑 | >2 小时未跑；从未跑；ok=false |
| login_anomalies | 近 24h 登录失败/锁定（axes） | 有锁定 | —（业务信号，不判停服） |
| app_errors | 可选 OPS_LOG_FILE 中近 24h ERROR 行 | >0 | —；未配置＝如实报 unknown |

## 4. 备份（F-12；现行口径 RPO ≤ 12h）

> RPO 口径：**≤ 12 小时**——由 12 小时备份频率直接派生（NFR §5.1/NF-13，
> Human 确认 2026-08-31）。PRD §15 的「每日备份 / 24 小时损失上限」是立项
> 原上限，已被更严的 12 小时口径取代；下方 backup_freshness 告警阈值
> （>12h WARN / >24h CRIT）与此对齐。

一份完整备份集＝`$BACKUP_ROOT/<YYYYmmddTHHMMSSZ>/`：`db.dump`（pg_dump
自定义格式）+ `media.tar.gz` + `manifest.json` + `sha256sums.txt`。
备份根缺省＝compose 具名卷 `backups`（容器内 `/data/backups`）。
配置了 `SECONDARY_BACKUP_DIR` 时整集另存独立副本；未配置会在输出与
ops_report 中显式标注（不静默）。任何失败：清残集、非零退出、结构化日志
`backup.run status=failed`；全程不回显数据库口令（PGPASSWORD 只进子进程环境）。

定时（≥12 小时一备）：

```
# /etc/cron.d/peiligo-backup（示例）
17 */12 * * * docker compose --env-file deploy/.env -f deploy/docker-compose.yml \
    exec -T web python manage.py backup_run >> /var/log/peiligo-backup.log 2>&1
```

手工备份：`docker compose ... exec web python manage.py backup_run`。
校验：每集 `sha256sums.txt` 可 `sha256sum -c` 复核。

## 5. 保留期清理（≥30 天）

`backup_prune` 默认 dry-run 只列不删；`--apply` 才删。删除对象＝**双重判据**
（目录名为严格 `YYYYmmddTHHMMSSZ` 且含 manifest.json）的 Peiligo 备份集，
绝不 `rm` 通配符；保留天数下限硬编码 30（`--days` 低于 30 直接报错）：

```
docker compose ... exec web python manage.py backup_prune --apply        # 默认 35 天
docker compose ... exec web python manage.py backup_prune --days 30 --apply
```

## 6. 恢复演练（RTO ≤ 4h，季度一练）

恢复**永不默认覆盖现库**：目标库名＝当前库名、媒体目录＝当前 MEDIA_ROOT
都会被拒绝。演练流程（隔离目标）：

1. 找一套备份集：`ls $BACKUP_ROOT`（取最新且 `sha256sum -c` 通过的）。
2. 先演练：`python manage.py backup_restore --source <集> --dry-run`
   （校验 manifest、校验和、pg_restore 目录、tar 可读，写任何东西＝失败）。
3. 建隔离库与空媒体目录（演练机或本机空闲盘）：
   `createdb peiligo_restore_drill`
4. 实恢复：
   ```
   python manage.py backup_restore --source <集> \
       --target-database peiligo_restore_drill --media-target-dir /tmp/drill-media
   ```
5. 起临时实例指向隔离库抽查数据；记录全程耗时，实测 RTO ≤ 4h。
   真实灾难切换由人工决定目标，同一命令换 `--target-database/--media-target-dir` 完成。

## 7. 强制改密治理（F-05R）

- 触发规则（对后台账号一律生效）：管理员在后台「新建用户」「设置/重置密码」
  后，该账号下次登录被服务端中间件强制定向到改密页，改密成功才放行；
  密码未变的管理员编辑（改姓名/邮箱/组）不触发。
- 旁路口径：ORM/CLI（`createsuperuser`/`changepassword`/`create_user`）不触发，
  种子账号不受影响。
- 会话安全：管理员重置他人密码后，该用户既有会话按 Django 规则失效。
- 应急通道（账号被锁在改密页外时）：`python manage.py clear_password_must_change
  --username <账号>` 即视为已改密放行（事后仍应人工复核该账号）。

## 8. 治理审计（F-08B，R-05 方案 B）

后台菜单「治理审计」→ `/admin/gov-audit/`：用户/组治理全量 DB 级变更
（创建/改组/改权/删组等）有据可查；审计代码位于 `src/peiligo/govaudit/`。

## 9. 日志与错误可见性

- 全部服务日志＝单行 JSON 入 stdout，由 `docker compose logs` / 宿主采集器
  接管（保留期工程默认 ≥30 天，与备份保留对齐）。运行事件码全集：
  - F-05 认证：`auth.login` / `auth.login_failed` / `auth.locked_out` /
    `auth.logout` / `password.forced_change_completed`（强制改密完成）；
  - F-07/09/10 内容：`content.published` / `content.unpublished`；
  - F-07/09 调度：`publish_scheduled.run` / `publish_scheduled.scheduler_error`；
  - F-12 备份：`backup.run` / `backup.prune`；
  - F-13 监控：`ops.report` / `ops.heartbeat_error`；
  - 其余未标注事件的日志行以 `app.log`/`app.error` 兜底事件码输出。
  （F-08B 治理审计走 DB 审计行（§8 的 /admin/gov-audit/），不经日志事件。）
- 请求异常经 `django.request` 独立成行（含堆栈，仅入日志管道）。
- ops_report 的 `app_errors` 信号需要文件源时，把 stdout JSON 落文件并在
  环境变量 `OPS_LOG_FILE` 指向它（未配置则如实报 unknown，不装作没事）。

## 10. 定时发布

`scheduler` 服务常驻跑 `publish_scheduler`（默认 60s 一轮；`--once` 供 cron
模式/测试）。结果双落：结构化日志 `publish_scheduled.run` + F-13 心跳
（ops_report 据此判新鲜度）。重启安全：待发布状态在 DB，重启后自动续跑。

## 11. 升级发布与回滚

```
# 升级
git pull（或换 tag）→ docker compose ... up -d --build   # entrypoint 自动 migrate
# 回滚：重新 up 上一发布提交构建的镜像；数据库回滚仅随恢复演练流程执行
```

禁止事项沿用批次冻结口径：不做 force push / reset --hard / 真实生产库
直接 restore；一切恢复走 §6 的显式目标参数。

## 12. 前端切换 / 回滚（SPEC-001；唯一开关）

> 形状沿用 ADR-0009 路由表 + B03 演练定稿（原 `compose.staging.yaml` /
> `STAGING_DEFAULT_UPSTREAM` 的生产对应物）。**唯一开关＝默认上游**
> `PEILIGO_DEFAULT_UPSTREAM`（deploy/.env；缺省 `web:8000`＝v1 整站回根）。
> 以下命令以 `cd deploy && docker compose --env-file .env -f docker-compose.yml`
> 为前提，简写为 `compose`。

| 态 | `PEILIGO_DEFAULT_UPSTREAM` | `/` 由谁服务 | 说明 |
| --- | --- | --- | --- |
| v1（缺省） | `web:8000` | Wagtail（v1 整站） | 部署后公开面零变化 |
| v2（cutover） | `frontend:4321` | 新 Astro 前端 | `/admin/`、`/documents/`、`/link-confirm/go/`、`/static/`、`/media/`、`/healthz*` 恒指 web，不随开关翻转 |

路由表恒定：`/api/v1/*` 在两个态下都 404（ADR-0008 §S1，API 仅内网）。

**cutover（v1 → v2；中断上限 <60s，B03 实测 ~3s）**

```sh
# 0) 前置核验：全体 healthy，且当前 v1 在根
compose ps
curl -fsS http://127.0.0.1/ -H 'Host: <域名>' | grep -q '/static/'
# 1) 切换＝翻转开关（deploy/.env 置 PEILIGO_DEFAULT_UPSTREAM=frontend:4321），仅重建 caddy
compose up -d --force-recreate caddy
# 2) 就绪判定（中断窗口终点）：新前端 200 且 Astro 资产上根
for i in $(seq 1 60); do curl -fsS http://127.0.0.1/ -H 'Host: <域名>' 2>/dev/null \
  | grep -q '/_astro/' && break; sleep 1; done
# 3) 切换后核验：SSR 真实渲染 + API 仍不公开 + 管理面可达
curl -fsS http://127.0.0.1/ -H 'Host: <域名>' | grep -q Peiligo
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/v1/chrome -H 'Host: <域名>')" = 404
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/django-admin/login/ -H 'Host: <域名>')" = 200
```

**回滚 A：全量回退 v1（上限 <5 分钟；B03 实测 ~3s）**——v2 出现阻断性问题
时的兜底。deploy/.env 把开关改回 `web:8000`，同一条
`compose up -d --force-recreate caddy`；就绪判定＝`/` 重新含 `/static/`。
只动 caddy 容器——DB、Wagtail、frontend 全不接触，可无限次重演。
Wagtail 发布两个态下都照常（定时发布不经过前端容器）。

**回滚 B：v2 内换前端镜像（秒级）**——仅前端自身回归时用：
`docker compose ... up -d --build frontend`（或指回上一镜像 tag），caddy/web 不动。

**发布时效契约**：Wagtail 发布内容 ≤30s 内对新前端可见（scheduler 60s 一轮
＋ Astro 每请求直连取数），**不触发** Astro 重建/部署。

## 13. 与 Peilige / Peilike 的边界

Peiligo、Peilige、Peilike 是三个相互独立的同级项目（见仓库根 README）：
独立仓库、独立 Compose 项目、独立数据卷与网络。运维本项目时只使用
`deploy/docker-compose.yml`（项目名缺省取目录名），**禁止** `docker system
prune -a --volumes` 等全机清理——会殃及同机其他项目的镜像与卷（详见
[guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md](guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md)
Troubleshooting 节）。
