# Peiligo 生产运行手册（F-09～F-13 收口）

适用架构＝冻结口径：Linux/PVE + Docker Compose + PostgreSQL + Caddy(HTTPS)。
不含 Redis/Celery/Elasticsearch/SPA/K8s。样例配置见 `deploy/.env.example`。

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

## 4. 备份（F-12：RPO ≤ 24h）

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
