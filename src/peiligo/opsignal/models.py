"""F-13：心跳表——各后台作业的最近一次运行结果（DB 可查，不依赖日志留存）。

记录方：backup_run / publish_scheduler（及其 --once）在完成或失败时调用
:meth:`OpsHeartbeat.record`；记录失败只打日志，绝不影响作业本身。
读取方：ops_report 快照命令。
"""

from django.db import models
from django.utils import timezone


class OpsHeartbeat(models.Model):
    kind = models.CharField(max_length=64, primary_key=True, verbose_name="作业种类")
    ok = models.BooleanField(default=False, verbose_name="最近一次是否成功")
    detail = models.JSONField(default=dict, blank=True, verbose_name="结果细节")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时刻")

    class Meta:
        verbose_name = "作业心跳"
        verbose_name_plural = "作业心跳"

    def __str__(self):
        return f"OpsHeartbeat({self.kind}, ok={self.ok}, at={self.updated_at.isoformat()})"

    @classmethod
    def record(cls, kind: str, ok: bool, **detail) -> None:
        """记一条心跳；任何异常吞为日志（监控记录不得拖垮被监控作业）。"""
        import logging

        try:
            cls.objects.update_or_create(
                kind=kind, defaults={"ok": ok, "detail": detail, "updated_at": timezone.now()}
            )
        except Exception:
            logging.getLogger("peiligo.events").exception(
                "心跳记录失败", extra={"event": "ops.heartbeat_error", "kind": kind}
            )
