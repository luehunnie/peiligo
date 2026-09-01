"""F-12：backup_prune——保留策略清理（缺省 dry-run）。

只删同时满足两特征的目录：目录名为严格 ``YYYYmmddTHHMMSSZ`` 时间戳
格式 ∧ 含 manifest.json（is_backup_set）——其余任何目录/文件一律
不碰，绝无通配删除。缺省只打印计划；--apply 才真正删除。配置了
SECONDARY_BACKUP_DIR 时副本侧同规则同步清理。
"""

import logging
import os
import shutil
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from peiligo.backupkit import _lib

logger = logging.getLogger("peiligo.events")


class Command(BaseCommand):
    help = "按保留期清理过期备份集（只认 Peiligo 备份集特征；缺省 dry-run）。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=int(os.environ.get("BACKUP_RETENTION_DAYS", "35")),
            help="保留天数（缺省 35 或 BACKUP_RETENTION_DAYS；冻结下限 30）。",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="真正执行删除；缺省只打印计划（dry-run）。",
        )

    def handle(self, *args, **options):
        days = int(options["days"])
        if days < 30:
            raise ValueError("保留期不得短于冻结下限 30 天")
        cutoff = timezone.now() - timedelta(days=days)
        expired = [
            path
            for path in sorted(_lib.backup_root().glob("*"))
            if _lib.is_backup_set(path) and path.stat().st_mtime < cutoff.timestamp()
        ]

        secondary = _lib.secondary_root()
        expired_secondary = []
        if secondary is not None and secondary.is_dir():
            expired_secondary = [
                path
                for path in sorted(secondary.glob("*"))
                if _lib.is_backup_set(path) and path.stat().st_mtime < cutoff.timestamp()
            ]

        if not options["apply"]:
            for path in expired:
                self.stdout.write(f"[dry-run] 将删除 {path}")
            for path in expired_secondary:
                self.stdout.write(f"[dry-run] 将删除副本 {path}")
            self.stdout.write(
                f"dry-run：共 {len(expired) + len(expired_secondary)} 项到期（未删除）"
            )
            return

        for path in expired:
            shutil.rmtree(path)
            self.stdout.write(f"deleted={path}")
        for path in expired_secondary:
            shutil.rmtree(path)
            self.stdout.write(f"deleted_secondary={path}")
        logger.info(
            "备份保留清理",
            extra={
                "event": "backup.prune",
                "deleted_local": len(expired),
                "deleted_secondary": len(expired_secondary),
                "retention_days": days,
            },
        )
