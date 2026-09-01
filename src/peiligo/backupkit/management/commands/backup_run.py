"""F-12：backup_run——生成一份完整备份集。

布局：$BACKUP_ROOT/<YYYYmmddTHHMMSSZ>/
  db.dump（pg_dump 自定义格式）＋ media.tar.gz＋manifest.json＋
  sha256sums.txt；SECONDARY_BACKUP_DIR 已配置时整集复制一份独立副本，
  未配置则显式报告「未配置独立副本」（不静默）。
任何一步失败：记结构化日志（backup.run status=failed）→ 清理残集 →
非零退出（CommandError）；输出永不包含数据库口令。
"""

import json
import logging
import shutil
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from peiligo.backupkit import _lib

logger = logging.getLogger("peiligo.events")


class Command(BaseCommand):
    help = "生成备份集（DB＋media＋manifest＋校验和，可选独立存储副本）。"

    def handle(self, *args, **options):
        started = time.monotonic()
        stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
        root = _lib.backup_root()
        set_dir = root / stamp
        try:
            set_dir.mkdir(parents=True)
            _lib.dump_db(set_dir / _lib.DB_DUMP_NAME)
            media_count = _lib.make_media_archive(set_dir / _lib.MEDIA_ARCHIVE_NAME)
            _lib.write_checksums(set_dir)
            manifest = {
                "created_at": timezone.now().isoformat(),
                "database_dump": _lib.DB_DUMP_NAME,
                "media_archive": _lib.MEDIA_ARCHIVE_NAME,
                "media_files": media_count,
                "database_name": str(_lib.current_db_settings()["NAME"]),
                "settings_module": settings.SETTINGS_MODULE,
            }
            (set_dir / _lib.MANIFEST_NAME).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            secondary = _lib.secondary_root()
            if secondary is not None:
                secondary.mkdir(parents=True, exist_ok=True)
                _lib.copy_to_secondary(set_dir, secondary)
                secondary_status = f"ok（{secondary / set_dir.name}）"
            else:
                secondary_status = "skipped（未配置独立副本：SECONDARY_BACKUP_DIR 未设置）"

            logger.info(
                "备份完成",
                extra={
                    "event": "backup.run",
                    "status": "ok",
                    "backup_set": set_dir.name,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "media_files": media_count,
                    "secondary": "ok" if secondary is not None else "skipped",
                },
            )
            # F-13：心跳供 ops_report 判定备份新鲜度（>12 小时 WARN / >24 小时 CRIT）。
            from peiligo.opsignal.models import OpsHeartbeat

            OpsHeartbeat.record(
                "backup",
                ok=True,
                backup_set=set_dir.name,
                secondary="ok" if secondary is not None else "skipped",
            )
            self.stdout.write(f"backup_set={set_dir}")
            self.stdout.write(f"secondary_copy={secondary_status}")
        except Exception as error:
            logger.exception(
                "备份失败",
                extra={"event": "backup.run", "status": "failed", "backup_set": stamp},
            )
            # F-13：失败心跳让 ops_report 即刻可见（新鲜度之外再有最近态）。
            from peiligo.opsignal.models import OpsHeartbeat

            OpsHeartbeat.record("backup", ok=False, error=str(error))
            shutil.rmtree(set_dir, ignore_errors=True)  # 清残集：绝不留半套备份
            raise CommandError(f"备份失败：{error}") from error
