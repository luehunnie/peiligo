"""F-12：备份/恢复工程微 app（三个管理命令，零模型零迁移）。

- backup_run    生成一份备份集（DB dump＋media 归档＋manifest＋校验和，
                可选独立存储副本）；
- backup_prune  保留策略清理（只认 Peiligo 备份集双重特征，缺省 dry-run）；
- backup_restore校验后恢复到隔离目标（绝不默认指向当前库/当前媒体根）。

周期（≥每 12h，RPO ≤24h）与保留（≥30 天）由运维载体（cron/systemd
timer）按 runbook 调用 backup_run／backup_prune 承载。
"""

from django.apps import AppConfig


class BackupKitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "peiligo.backupkit"
    label = "backupkit"
    verbose_name = "备份恢复（F-12）"
