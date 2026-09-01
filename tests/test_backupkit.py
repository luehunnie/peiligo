"""F-12：备份/恢复工程行为测试（隔离临时目录；真实 pg_dump/pg_restore 往返）。

冻结口径逐项核对：
- 备份集＝时间戳目录＋db.dump＋media.tar.gz＋manifest.json＋校验和；
- 独立副本未配置须显式报告（不静默）；
- 失败→非零退出＋残集清理＋不泄露口令；
- 保留策略只删 Peiligo 备份集双重特征项，其余目录绝不触碰；
- 恢复缺省 dry-run 零写入；实际恢复须显式隔离目标，与当前库/当前
  媒体根同名同径即拒绝。
"""

import os
import shutil
import tarfile
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock, skipUnless

import psycopg
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from peiligo.backupkit import _lib

PG_TOOLS = bool(shutil.which("pg_dump") and shutil.which("pg_restore"))


def scratch_db_name():
    """隔离恢复目标：当前活动测试库名＋后缀（非 settings.DATABASES——
    pytest 下后者仍指 dev 库名，活动连接名才真实）。"""
    return str(connection.settings_dict["NAME"]) + "_restore_chk"


def parse_backup_set(buf: StringIO) -> Path:
    return Path(buf.getvalue().split("backup_set=")[1].strip().splitlines()[0])


def make_backup_set(root: Path) -> Path:
    """真实跑一份 backup_run，返回备份集目录。"""
    buf = StringIO()
    with mock.patch.dict(os.environ, {"BACKUP_ROOT": str(root)}):
        call_command("backup_run", stdout=buf)
    return parse_backup_set(buf)


@skipUnless(PG_TOOLS, "需要 pg_dump/pg_restore 客户端")
class BackupRunTests(TestCase):
    def test_backup_set_layout_and_checksums(self):
        with (
            tempfile.TemporaryDirectory(prefix="f12-backup-") as tmp,
            tempfile.TemporaryDirectory(prefix="f12-media-") as media,
        ):
            (Path(media) / "f12.txt").write_text("备份样例", encoding="utf-8")
            with (
                mock.patch.dict(os.environ, {"BACKUP_ROOT": tmp}),
                override_settings(MEDIA_ROOT=media),
            ):
                buf = StringIO()
                call_command("backup_run", stdout=buf)
                set_dir = parse_backup_set(buf)
                self.assertTrue(_lib.is_backup_set(set_dir))
                self.assertTrue((set_dir / _lib.DB_DUMP_NAME).stat().st_size > 0)
                with tarfile.open(set_dir / _lib.MEDIA_ARCHIVE_NAME) as archive:
                    names = archive.getnames()
                self.assertIn("media/f12.txt", names)
                self.assertEqual(_lib.verify_checksums(set_dir), [], "校验和自洽")
                self.assertIn("未配置独立副本", buf.getvalue(), "独立副本未配置须显式报告")
                # 口令纪律：输出不得包含当前库口令（口令为空＝socket 信任认证）
                password = connection.settings_dict.get("PASSWORD") or ""
                if password:
                    self.assertNotIn(password, buf.getvalue())

    def test_secondary_copy_when_configured(self):
        with (
            tempfile.TemporaryDirectory(prefix="f12-backup-") as tmp,
            tempfile.TemporaryDirectory(prefix="f12-second-") as second,
            tempfile.TemporaryDirectory(prefix="f12-media-") as media,
        ):
            with (
                mock.patch.dict(
                    os.environ,
                    {"BACKUP_ROOT": tmp, "SECONDARY_BACKUP_DIR": second},
                ),
                override_settings(MEDIA_ROOT=media),
            ):
                buf = StringIO()
                call_command("backup_run", stdout=buf)
                set_dir = parse_backup_set(buf)
                mirror = Path(second) / set_dir.name
                self.assertTrue(_lib.is_backup_set(mirror), "独立副本整集落位")
                self.assertIn("secondary_copy=ok", buf.getvalue())

    def test_failure_exits_nonzero_and_cleans_partial_set(self):
        with (
            tempfile.TemporaryDirectory(prefix="f12-backup-") as tmp,
            mock.patch.dict(os.environ, {"BACKUP_ROOT": tmp}),
        ):
            with mock.patch.object(_lib, "dump_db", side_effect=RuntimeError("pg 爆了")):
                with self.assertRaises(CommandError):
                    call_command("backup_run", stdout=StringIO(), stderr=StringIO())
            self.assertEqual(list(Path(tmp).iterdir()), [], "失败不留残集（防半套备份被误用）")


@skipUnless(PG_TOOLS, "需要 pg_dump/pg_restore 客户端")
class BackupPruneTests(TestCase):
    def _aged(self, root, name, with_manifest=True):
        path = Path(root) / name
        path.mkdir()
        if with_manifest:
            (path / _lib.MANIFEST_NAME).write_text("{}", encoding="utf-8")
        old = os.path.getmtime(path) - 40 * 24 * 3600  # 40 天前
        os.utime(path, (old, old))
        return path

    def test_prune_only_touches_peiligo_sets(self):
        with (
            tempfile.TemporaryDirectory(prefix="f12-prune-") as tmp,
            mock.patch.dict(os.environ, {"BACKUP_ROOT": tmp}),
        ):
            old_set = self._aged(tmp, "20250101T000000Z", with_manifest=True)
            decoy_noname = self._aged(tmp, "someone-elses-dir", with_manifest=False)
            decoy_nomanifest = self._aged(tmp, "20250102T000000Z", with_manifest=False)

            # 缺省 dry-run：只打印计划，不删
            buf = StringIO()
            call_command("backup_prune", stdout=buf)
            self.assertTrue(old_set.exists(), "dry-run 不删除")

            call_command("backup_prune", "--apply", stdout=StringIO())
            self.assertFalse(old_set.exists(), "过期备份集被清理")
            self.assertTrue(decoy_noname.exists(), "非备份集目录绝不触碰")
            self.assertTrue(decoy_nomanifest.exists(), "同名无 manifest 目录绝不触碰")

    def test_prune_refuses_below_frozen_floor(self):
        with self.assertRaises(ValueError):
            call_command("backup_prune", "--days", "7", stdout=StringIO())


@skipUnless(PG_TOOLS, "需要 pg_dump/pg_restore 客户端")
class BackupRestoreTests(TestCase):
    def _drop_scratch(self):
        # DDL 须在事务块外：走独立 autocommit 连接（不动 Django 测试连接）
        scratch = scratch_db_name()
        conn = psycopg.connect(dbname="postgres", user=connection.settings_dict["USER"])
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{scratch}"')
        conn.close()

    def setUp(self):
        self._drop_scratch()

    def tearDown(self):
        self._drop_scratch()

    def test_dry_run_writes_nothing(self):
        scratch = scratch_db_name()
        with (
            tempfile.TemporaryDirectory(prefix="f12-restore-") as tmp,
            tempfile.TemporaryDirectory(prefix="f12-backup-") as backup_tmp,
        ):
            set_dir = make_backup_set(Path(backup_tmp))
            buf = StringIO()
            call_command(
                "backup_restore",
                "--source",
                str(set_dir),
                "--dry-run",
                "--target-database",
                scratch,
                "--media-target-dir",
                tmp,
                stdout=buf,
            )
            self.assertIn("dry-run", buf.getvalue())
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (scratch,))
                self.assertIsNone(cursor.fetchone(), "dry-run 不建库不写库")

    def test_restore_to_isolated_target(self):
        scratch = scratch_db_name()
        with (
            tempfile.TemporaryDirectory(prefix="f12-restore-") as target,
            tempfile.TemporaryDirectory(prefix="f12-media-") as media,
            tempfile.TemporaryDirectory(prefix="f12-backup-") as backup_tmp,
        ):
            (Path(media) / "keep.txt").write_text("媒体样例", encoding="utf-8")
            with override_settings(MEDIA_ROOT=media):
                set_dir = make_backup_set(Path(backup_tmp))

            # 隔离目标库由调用方 createdb（runbook 口径）
            db_user = connection.settings_dict["USER"]
            conn = psycopg.connect(dbname="postgres", user=db_user)
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE "{scratch}"')
            conn.close()

            buf = StringIO()
            call_command(
                "backup_restore",
                "--source",
                str(set_dir),
                "--target-database",
                scratch,
                "--media-target-dir",
                target,
                stdout=buf,
            )
            self.assertIn("restored_database=", buf.getvalue())
            self.assertTrue((Path(target) / "media" / "keep.txt").exists(), "媒体解包落隔离目录")
            conn = psycopg.connect(dbname=scratch)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='django_migrations'"
                )
                self.assertEqual(cursor.fetchone()[0], 1, "目标库恢复出 Django 表")
            conn.close()

    def test_refuses_current_database_and_current_media_root(self):
        current_db = str(connection.settings_dict["NAME"])
        with tempfile.TemporaryDirectory(prefix="f12-backup-") as backup_tmp:
            set_dir = make_backup_set(Path(backup_tmp))
            with self.assertRaises(CommandError):
                call_command(
                    "backup_restore",
                    "--source",
                    str(set_dir),
                    "--target-database",
                    current_db,
                    "--media-target-dir",
                    tempfile.mkdtemp(prefix="f12-anywhere-"),
                    stdout=StringIO(),
                )
            with self.assertRaises(CommandError):
                call_command(
                    "backup_restore",
                    "--source",
                    str(set_dir),
                    "--target-database",
                    scratch_db_name(),
                    "--media-target-dir",
                    str(settings.MEDIA_ROOT),
                    stdout=StringIO(),
                )
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (scratch_db_name(),),
                )
                self.assertIsNone(cursor.fetchone(), "拒绝路径不产生任何库")


class VerifyChecksumsTraversalTests(TestCase):
    """独立审查 P2 加固：sha256sums.txt 条目只允许集内平文件名，
    含路径成分（../、绝对路径、分隔符）即整体拒绝，绝不拼接执行。"""

    def test_malformed_entries_are_rejected(self):
        for bad in ("0" * 64 + "  ../../etc/passwd", "0" * 64 + "  /etc/passwd"):
            with self.subTest(entry=bad.split(maxsplit=1)[1]):
                with tempfile.TemporaryDirectory(prefix="f12-chksum-") as tmp:
                    set_dir = Path(tmp) / "20260901T010000Z"
                    set_dir.mkdir()
                    (set_dir / _lib.MANIFEST_NAME).write_text("{}", encoding="utf-8")
                    (set_dir / _lib.CHECKSUMS_NAME).write_text(bad + "\n", encoding="utf-8")
                    with self.assertRaisesMessage(RuntimeError, "非法路径条目"):
                        _lib.verify_checksums(set_dir)

    def test_valid_entry_passes_through(self):
        import hashlib

        with tempfile.TemporaryDirectory(prefix="f12-chksum-") as tmp:
            set_dir = Path(tmp) / "20260901T010000Z"
            set_dir.mkdir()
            (set_dir / _lib.MANIFEST_NAME).write_text("{}", encoding="utf-8")
            (set_dir / _lib.DB_DUMP_NAME).write_bytes(b"PGDMP")
            digest = hashlib.sha256(b"PGDMP").hexdigest()
            (set_dir / _lib.CHECKSUMS_NAME).write_text(
                f"{digest}  {_lib.DB_DUMP_NAME}\n", encoding="utf-8"
            )
            self.assertEqual(_lib.verify_checksums(set_dir), [])
