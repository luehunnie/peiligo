# Local Docker Production-like Runtime Validation — 证据记录

- 日期:2026-09-02(UTC 时间戳以容器日志为准)
- 性质:V1 冻结架构在本机的首次真实「构建 → 启动 → 验收 → 持久化 → 备份 → 恢复」全链验证
- 结论:**LOCAL_PRODUCTION_RUNTIME_VALIDATION = PASS**
- 本文件为验证证据,不含任何密码/秘密/令牌/私人环境信息

## 环境

| 项 | 值 |
|---|---|
| 基线 | canonical `peiligo` 仓 `main` @ `3783a72` |
| 验证分支 | `fix/dockerfile-editable-install`(本地,未 push),含 5 个验证修复提交(见下) |
| 宿主 | macOS arm64,Docker Desktop(Docker 29.6.1 / Compose v5.3.0) |
| 编排 | `deploy/docker-compose.yml`:`--env-file deploy/.env -f deploy/docker-compose.yml`(项目名 deploy,四容器 db/web/scheduler/caddy) |
| 本地 .env | 未入库(ignored,chmod 600);配置变量名:POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / SECRET_KEY / ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS / WAGTAILADMIN_BASE_URL / DOMAIN / GUNICORN_WORKERS / SCHED_INTERVAL_SECONDS / HSTS_SECONDS(仅列名,值不记录) |
| 域名口径 | DOMAIN=localhost,Caddy 本地自签;HSTS_SECONDS=3600(观察值,避免本机长期 HSTS 污染) |

## 验证结果(A–L)

| 阶段 | 项 | 结果 | 关键证据 |
|---|---|---|---|
| A | git 门 / Docker 预检 | PASS | 分支 main 与 origin 同步且 clean;daemon 正常;无外部资源/端口冲突 |
| B | 指南 vs 实现核对 | PASS(以代码为准) | 读 LOCAL_RUN_AND_VALIDATION_GUIDE / SERVER_DEPLOYMENT_GUIDE / PRODUCTION_RUNBOOK;实现事实以 deploy/ 真实文件为准 |
| C | compose config | PASS | 插值校验通过 |
| D | build | PASS(修复 #1/#2 后) | 见缺陷表 |
| E | up 首启 | PASS | 四容器 running,db/web healthy |
| F | 健康/前台/静态/迁移 | PASS | healthz/readyz 200;首页+五板块 200;ManifestStaticFilesStorage 清单资源 200;entrypoint 自动 migrate;bootstrap_sections 幂等;init_permissions(--password-stdin)建总管理员组 |
| G | Human 验收门 | PASS | 人工在 `/admin/` 建部门(科技社/kejishe)、部门容器、GuidePage「peiligo开发完成」并上传图片;前台经 Caddy 可访问(200) |
| G+ | 持久化 | PASS | 全量快照 before/after 完全一致(pages/departments/images/docs/revisions/users);media 卷 4 文件俱在;优雅重启(down 无 -v → up --wait)六卷俱存 |
| H | Scheduler | PASS | RestartCount=0;日志每 60s 输出 `publish_scheduled.run`;OpsHeartbeat 表 kind=publish_scheduled ok=True 与日志同时刻;**端到端定时发布**:草稿页 `approved_go_live_at=+10s`,到期 tick `due_before=1 published=1 due_after=0`,页面转 live,到期前未被提前发布 |
| I | ops_report | PASS | JSON 快照八类信号;备份前 backup_freshness=crit 且命令非零退出(设计);备份后 crit→warn(仅剩未配 SECONDARY_BACKUP_DIR 的 warn,属非阻塞项) |
| J | backup_run + 持久化 | PASS(修复 #5 后) | 备份集 `20260902T053127Z`:db.dump / media.tar.gz(4 文件)/ manifest.json / sha256sums.txt;`sha256sum -c` 双 OK;再次优雅重启后备份集仍在卷内且校和仍 OK |
| K | restore | PASS | `--dry-run`(缺省)四项 [verify] 全过且拒绝无显式目标的真实恢复(设计);隔离演练:`createdb peiligo_restore_drill` + `--target-database ... --media-target-dir /tmp/drill-media`,恢复 EXIT=0,四表行数与 live 库逐一 MATCH(pages 9 / users 1 / images 1 / docs 0),id=10 内容与 5 个 live 板块俱在,media 4/4 对齐;演练产物已清理(drill 库 drop、drill media 删除),live 库未受任何影响 |
| L | 终态 | PASS | 栈保持运行(四容器,db/web healthy);live 库 9 页俱在;仓库工作区 clean |

## 发现的真实仓库缺陷(共 5,全部经授权在 fix 分支最小修复)

| # | 缺陷 | 实证 | 修复提交 |
|---|---|---|---|
| 1 | Dockerfile `pip install -e ./src`,而项目定义在仓库根 | build 失败:file:///app/src does not appear to be a Python project | `7bf1707`(`-e .`) |
| 2 | 多源 `COPY` 目录名不保留(内容平铺),八 app 包未落位 | build 期 collectstatic `ModuleNotFoundError: No module named 'home'`;alpine 探针实证平铺语义 | `52ad216`(逐 app COPY) |
| 3 | pgdata 挂旧路径 `/data`,与 postgres:18+ 镜像布局(/var/lib/postgresql/18/docker)冲突 | db 容器拒启并循环报错 | `793b1bb`(挂 /var/lib/postgresql) |
| 4 | web healthcheck 硬编码 Host: 127.0.0.1,被 DisallowedHost 判 400,scheduler 永远等不到 healthy | 探针日志 400;scheduler pending | `5a4a9a4`(探针 Host 取 ALLOWED_HOSTS 首项) |
| 5 | Dockerfile 未预建 /data/backups,具名卷首挂 root 属主,backup_run 必 PermissionError | `PermissionError: /data/backups/20260902T052856Z`;media/static 因预建而正常(对照) | `8524cbf`(mkdir 补项);既有卷属主一次性 chown 修复(卷为空,无数据) |

## 非阻塞项(任务书 §38 口径,不计入本地 FAIL)

- TLS 证书为 Caddy 本地自签(localhost);真实域名/DNS/公网证书未验
- SECONDARY_BACKUP_DIR 未配置(ops_report warn 来源);正式恢复演练(切换流量级)未做
- 性能/WCAG/告警接线/服务器部署均不在本轮范围
- `manage.py check` 的 treebeard.E001 / wagtailsearch.W001 WARNINGS 为上游 Wagtail 提示,非阻塞

## 交接注意事项

- 5 个修复提交在本地 `fix/dockerfile-editable-install`,**未 push**;提交者身份为 git 自动推断(陈俊贤 <USER@…local>),push 前可 `git commit --amend --reset-author` 或合并时自行确认
- main 与 fix 分支的合流(本地 merge 或远端 PR)由 Human 决定;修复合入 main 前,勿在其他机器按原 Dockerfile 部署
- 本地 .env 与管理员凭据文件均未入库;本轮凭据仅限本地验证用途
