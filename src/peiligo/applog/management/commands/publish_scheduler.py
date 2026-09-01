"""F-09：publish_scheduled 正式周期调度器（长驻循环命令）。

冻结架构不引入 Redis/Celery：调度＝独立容器进程运行本命令，周期调用
F-07 包装命令 ``run_publish_scheduled``（其自身输出 event=
``publish_scheduled.run`` 结构化日志），异常吞入结构化日志后继续下一
周期——单次失败不终结调度进程；容器由 compose restart 策略保障进程级
存活，调度状态完全来自 DB（approved_go_live_at），重启即续跑。

间隔经 --interval 或环境 SCHED_INTERVAL_SECONDS 配置（缺省 60 秒）；
--once 模式只跑一个周期即退出（手工补跑与测试载体）。
"""

import logging
import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger("peiligo.events")


class Command(BaseCommand):
    help = "周期运行 publish_scheduled（F-09 正式调度器；--once 只跑一个周期）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=int(os.environ.get("SCHED_INTERVAL_SECONDS", "60")),
            help="两个运行周期之间的间隔秒数（缺省 60，或 SCHED_INTERVAL_SECONDS）。",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="只执行一个周期后退出（手工补跑与测试）。",
        )

    def _cycle(self):
        """单周期：失败记结构化日志但不抛出（周期循环不因单次失败终止）。"""
        try:
            call_command("run_publish_scheduled", stdout=self.stdout)
        except Exception:
            logger.exception(
                "publish_scheduled 调度周期失败",
                extra={"event": "publish_scheduled.scheduler_error"},
            )
            self.stderr.write("publish_scheduled 周期失败（详见结构化日志），将在下周期重试")

    def handle(self, *args, **options):
        interval = max(int(options["interval"]), 1)
        self._cycle()
        if options["once"]:
            return
        while True:
            time.sleep(interval)
            self._cycle()
