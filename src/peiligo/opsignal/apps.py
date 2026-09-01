"""F-13：监控信号微 app（一个心跳表＋ops_report 快照命令）。

冻结口径：不上监控平台、无常驻守护——信号全部可观测自两处：
- DB 心跳表（备份/定时发布是否按时落行）；
- ops_report 快照命令（cron ≥5 分钟一跑；非零退出＝可接线告警）。
"""

from django.apps import AppConfig


class OpsignalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "peiligo.opsignal"
    label = "opsignal"
    verbose_name = "监控信号（F-13）"
