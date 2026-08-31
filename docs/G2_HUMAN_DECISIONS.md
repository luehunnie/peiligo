# G2 Human 决策台账（G2_HUMAN_DECISIONS）

> 本台账只记 ID / Decision / Status / Confirmed Date / Source Document；详细口径见各 Source Document，不在本文件复制正文。确认人＝项目负责人；全部确认日期＝2026-08-31。部署阶段细节（CPU/RAM/IP/具体磁盘路径/具体 PVE VM·CT/具体 NAS/对象存储厂商）不在本表——见 NFR §12 `DEFERRED_DEPLOYMENT_DETAIL` 分类。

| ID | Decision | Status | Confirmed Date | Source Document |
| --- | --- | --- | --- | --- |
| Q1 | 单个附件最大 20 MiB | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §4.1/§13#1；NFR §12 PP-01 |
| Q2 | 后台账号最低密码长度 12 字符；继续使用 Django/Wagtail 原生账号机制 | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §2.2/§13#3；NFR §12 PP-03 |
| Q3 | 登录失败处理：15 分钟内连续失败 10 次→临时限制 15 分钟；成功登录后失败计数清零 | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §2.3/§13#2；NFR §12 PP-02/PP-13、§6.1 行 5 |
| Q4 | 后台访问允许公网访问；V1 不要求校园网或 IP 白名单 | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §1.1/§1.2/§13#4；NFR §12 PP-04 |
| Q5 | HSTS 最终生产目标 1 年；初次上线先使用较短周期，HTTPS/证书/反向代理稳定后提升到 1 年 | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §3.2/§13#5；NFR §12 PP-05 |
| Q6 | 后台 Session 24 小时；主动退出立即结束；修改密码等重要账号变更后相关 Session 应结束 | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §3.2/§13#6；NFR §12 PP-06 |
| Q7 | 部门容量设计基线 ≤30 个部门（仅容量与性能规划，不是业务硬上限） | HUMAN_CONFIRMED | 2026-08-31 | NFR §8/§12 PP-16 |
| Q8 | 内容容量设计基线 ≤10,000 条正式内容（不是业务硬上限） | HUMAN_CONFIRMED | 2026-08-31 | NFR §8/§12 PP-17 |
| Q9 | 备份位置：本地快速恢复副本＋至少一份独立存储副本；具体介质（NAS/另一台服务器/对象存储）留部署阶段确定 | HUMAN_CONFIRMED | 2026-08-31 | NFR §5.6/§12 PP-15 |
| Q10 | 生产架构基线：Linux/PVE＋Docker Compose＋PostgreSQL＋Caddy/HTTPS＋持久化 Database＋持久化 Media＋正式后台调度机制；CPU/RAM/IP/磁盘路径等属部署阶段细节 | HUMAN_CONFIRMED | 2026-08-31 | NFR §1.1/§12 PP-08/PP-19；SECURITY_BASELINE §13#8 |
| Q11 | Database＋Media 至少每 12 小时形成一次配套备份 | HUMAN_CONFIRMED | 2026-08-31 | NFR §5.1/NF-13 |
| Q12 | 完整恢复演练每季度至少一次；重大版本发布前额外确认最近一次可恢复备份 | HUMAN_CONFIRMED | 2026-08-31 | NFR §5.4/§12 PP-14 |
| Q13 | 典型公开页面项目自有 JavaScript 目标 ≤200 KiB（未压缩）——Review/性能预算，不是运行时硬限制 | HUMAN_CONFIRMED | 2026-08-31 | NFR §1.5/§12 PP-09 |
| Q14 | 首页人工推荐内容最多同时生效 3 条；0 条时推荐区可隐藏；不足 3 条按实际数量展示 | HUMAN_CONFIRMED | 2026-08-31 | INFORMATION_ARCHITECTURE §7.2 |
| Q15 | 推荐内容默认有效期 30 天；管理员可提前撤下或延长 | HUMAN_CONFIRMED | 2026-08-31 | INFORMATION_ARCHITECTURE §7.2 |
| Q16 | Session Cookie SameSite=Lax；正式生产同时要求 Secure=True、HttpOnly=True、HTTPS only | HUMAN_CONFIRMED | 2026-08-31 | SECURITY_BASELINE §3.2（★注） |
| Q17 | 1000 条数据规模下搜索 server-side：p50 < 1s、p95 < 2s | HUMAN_CONFIRMED | 2026-08-31 | NFR §1.3/NF-02/NF-08/§12 PP-23 |
| Q18 | 首页及主要公开页面在预发布同级环境中核心内容目标 ≤2s 可见；不要求所有资源 2 秒内全部完成 | HUMAN_CONFIRMED | 2026-08-31 | NFR §1.3/NF-01 |
| Q19 | 核心服务健康检查每 5 分钟一次；其它低变化项目可采用更低频率 | HUMAN_CONFIRMED | 2026-08-31 | NFR §6.1 行 1/§12 PP-11 |
| Q20 | 磁盘剩余 <20%：Warning；剩余 <10%：Critical | HUMAN_CONFIRMED | 2026-08-31 | NFR §6.1 行 3/§12 PP-12 |
| Q21 | 常规备份至少保留 30 天；重大版本发布前备份可单独延长保存 | HUMAN_CONFIRMED | 2026-08-31 | NFR §5.6/§12 PP-15 |
| Q22 | V1 性能设计与验收基线＝100 个并发活跃用户（不是业务硬上限） | HUMAN_CONFIRMED | 2026-08-31 | NFR §1.3/NF-08/§12 PP-10 |
| Q23 | 严重故障恢复目标 RTO ≤4 小时（前提＝可用备份存在且基础设施正常） | HUMAN_CONFIRMED | 2026-08-31 | NFR §5.4/NF-05 |

**计数**：`HUMAN_CONFIRMED` 23/23；`G2_PENDING_PARAMETERS = 0`（NFR §12 集中表：`HUMAN_CONFIRMED` 17 项＋`DEFERRED_DEPLOYMENT_DETAIL` 6 项，后者为部署阶段细节/工程默认，不计入 G2 待确认参数）。
