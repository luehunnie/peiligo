"""F-07：publish_scheduled 运行结果结构化日志包装（正式调度载体随 F-09）。

Wagtail 官方 ``publish_scheduled`` 命令静默运行、不报运行结果；本包装
命令不改其语义，仅以「到期修订数前后差值」导出可观测结果并记结构化
日志（event=``publish_scheduled.run``）。到期判定与官方命令同源
（approved_go_live_at 已批且已到点），差值即本次实际发布条数。
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.models import Revision


def _due_revisions_count(now):
    return Revision.page_revisions.filter(
        approved_go_live_at__isnull=False, approved_go_live_at__lte=now
    ).count()


class Command(BaseCommand):
    help = "运行 Wagtail publish_scheduled 并以结构化日志输出运行结果（F-07）。"

    def handle(self, *args, **options):
        now = timezone.now()
        due_before = _due_revisions_count(now)
        try:
            call_command("publish_scheduled")
        except Exception as exc:
            # F-13：失败也落心跳，ops_report 才能区分「没跑」与「跑了但失败」。
            from peiligo.opsignal.models import OpsHeartbeat

            OpsHeartbeat.record("publish_scheduled", ok=False, error=str(exc))
            raise
        due_after = _due_revisions_count(timezone.now())

        published = max(due_before - due_after, 0)
        self.stdout.write(f"due_before={due_before} published={published} due_after={due_after}")

        # F-13：心跳供 ops_report 判定定时发布新鲜度（>15 分钟 WARN / >2 小时 CRIT）。
        from peiligo.opsignal.models import OpsHeartbeat

        OpsHeartbeat.record(
            "publish_scheduled", ok=True, published=published, due_before=due_before
        )

        logging.getLogger("peiligo.events").info(
            "publish_scheduled 运行完成",
            extra={
                "event": "publish_scheduled.run",
                "due_before": due_before,
                "published": published,
                "due_after": due_after,
            },
        )
