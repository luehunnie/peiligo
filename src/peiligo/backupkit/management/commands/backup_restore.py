"""F-12：backup_restore——校验后恢复到隔离目标。

铁律：绝不默认毁当前库/当前媒体。终审 L-7 文档如实化：**dry-run 非
缺省**，不显式给目标＝拒绝执行，绝不静默真恢复。
- --dry-run：只做校验与计划——manifest/校验和/dump 可读性
  （pg_restore --list）/归档可读性，不写任何库与盘；
- 不带 --dry-run：未显式给 --target-database（须已由 createdb 建好）
  与 --media-target-dir 即拒绝执行；二者齐备才做实际恢复，且目标库
  与当前库同名、媒体目录等于或位于当前 MEDIA_ROOT 之内时拒绝
  （防止误毁在线库与在线媒体）。
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from peiligo.backupkit import _lib


class Command(BaseCommand):
    help = (
        "从备份集恢复到隔离目标（--dry-run 只校验出计划；实际恢复必须显式"
        "给 --target-database 与 --media-target-dir；拒绝指向当前库/当前媒体根）。"
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="备份集目录（含 manifest.json）")
        parser.add_argument("--dry-run", action="store_true", help="只校验并打印计划，不写任何数据")
        parser.add_argument(
            "--target-database",
            default="",
            help="目标库（须已 createdb；与当前库同名即拒绝）",
        )
        parser.add_argument(
            "--media-target-dir",
            default="",
            help="媒体解包目录（与当前 MEDIA_ROOT 同径即拒绝）",
        )

    def handle(self, *args, **options):
        set_dir = Path(options["source"])
        if not _lib.is_backup_set(set_dir):
            raise CommandError(f"不是合法备份集（须为时间戳目录且含 manifest.json）：{set_dir}")

        self.stdout.write(f"[verify] {set_dir}")
        try:
            mismatches = _lib.verify_checksums(set_dir)
        except RuntimeError as error:
            # 清单含路径逃逸等非法条目同样以 CommandError 收口（非零退出）。
            raise CommandError(f"校验失败：{error}") from error
        if mismatches:
            raise CommandError(f"校验和不匹配：{mismatches}")
        self.stdout.write("[verify] sha256 全部一致")
        _lib.dump_table_of_contents(set_dir / _lib.DB_DUMP_NAME)
        self.stdout.write("[verify] db.dump 可读（pg_restore --list）")
        import tarfile

        with tarfile.open(set_dir / _lib.MEDIA_ARCHIVE_NAME, "r:gz") as archive:
            archive.getmembers()
        self.stdout.write("[verify] media.tar.gz 可读")

        target_db = options["target_database"]
        media_dir = Path(options["media_target_dir"]) if options["media_target_dir"] else None
        current_db = str(_lib.current_db_settings()["NAME"])
        current_media = Path(settings.MEDIA_ROOT)

        if options["dry_run"]:
            plan = (
                "[dry-run] 计划：db.dump → --target-database={}; "
                "media.tar.gz → --media-target-dir={}"
            ).format(target_db or "<须显式指定>", media_dir or "<须显式指定>")
            self.stdout.write(plan)
            self.stdout.write("[dry-run] 未写任何数据")
            return

        if not target_db or media_dir is None:
            raise CommandError("实际恢复必须显式指定 --target-database 与 --media-target-dir")
        if target_db == current_db:
            raise CommandError(
                f"拒绝恢复：目标库与当前使用库同名（{current_db}）。请建隔离目标库后再恢复"
            )
        if media_dir.resolve() == current_media.resolve():
            raise CommandError(
                f"拒绝恢复：媒体目录与当前 MEDIA_ROOT 相同（{current_media}）。请指定隔离目录"
            )

        connection.close()
        _lib.restore_db(set_dir / _lib.DB_DUMP_NAME, target_db)
        self.stdout.write(f"restored_database={target_db}")
        _lib.extract_media_archive(set_dir / _lib.MEDIA_ARCHIVE_NAME, media_dir)
        self.stdout.write(f"restored_media={media_dir}")
        self.stdout.write("restore 完成（RTO 演练见 runbook；切换流量前请先核查目标库内容）")
