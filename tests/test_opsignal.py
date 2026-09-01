"""F-13：监控信号测试——心跳表、接线（publish/backup）、ops_report 快照判定。"""

import json
import os
import shutil
import time
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from peiligo.backupkit import _lib
from peiligo.backupkit._lib import MANIFEST_NAME
from peiligo.opsignal.models import OpsHeartbeat

REPORT = "peiligo.opsignal.management.commands.ops_report"
SCHEDULER = "peiligo.applog.management.commands.run_publish_scheduled"


def run_report():
    """ops_report 的 stdout 走 self.stdout，需显式捕获再解析 JSON。"""
    out = StringIO()
    call_command("ops_report", stdout=out)
    return json.loads(out.getvalue())


def make_backup_set(root, name="20260901T010000Z", mtime=None):
    """最小合法备份集：时间戳目录名＋manifest.json（is_backup_set 判据）。"""
    set_dir = root / name
    set_dir.mkdir(parents=True)
    (set_dir / MANIFEST_NAME).write_text("{}", encoding="utf-8")
    if mtime is not None:
        os.utime(set_dir, (mtime, mtime))
    return set_dir


@pytest.fixture()
def ops_env(monkeypatch, tmp_path):
    """隔离观测环境：备份根指 tmp；独立副本与日志文件默认未配置。"""
    root = tmp_path / "backups"
    root.mkdir()
    monkeypatch.setenv("BACKUP_ROOT", str(root))
    monkeypatch.delenv("SECONDARY_BACKUP_DIR", raising=False)
    monkeypatch.delenv("OPS_LOG_FILE", raising=False)
    return root


@pytest.fixture()
def quiet_world(ops_env, monkeypatch, tmp_path):
    """无备份集但其余信号正常：disk 钉 50% 余量，publish 心跳新鲜。"""
    media, static = tmp_path / "media", tmp_path / "static"
    media.mkdir()
    static.mkdir()
    OpsHeartbeat.record("publish_scheduled", ok=True, published=0)
    with (
        mock.patch(f"{REPORT}._pct_free", return_value=50.0),
        override_settings(MEDIA_ROOT=media, STATIC_ROOT=static),
    ):
        yield ops_env


@pytest.fixture()
def fresh_world(quiet_world, monkeypatch):
    """全绿世界：主/副备份集均新鲜，双心跳在册。"""
    make_backup_set(quiet_world, mtime=time.time())
    secondary = quiet_world.parent / "secondary"
    secondary.mkdir()
    make_backup_set(secondary, mtime=time.time())
    monkeypatch.setenv("SECONDARY_BACKUP_DIR", str(secondary))
    OpsHeartbeat.record("backup", ok=True, backup_set="20260901T010000Z")
    return quiet_world


@pytest.mark.django_db
class TestHeartbeatRecord:
    def test_record_creates_then_updates_single_row(self):
        OpsHeartbeat.record("backup", ok=True, backup_set="a")
        OpsHeartbeat.record("backup", ok=False, error="later")
        hb = OpsHeartbeat.objects.get(kind="backup")
        assert hb.ok is False
        assert hb.detail == {"error": "later"}
        assert OpsHeartbeat.objects.count() == 1

    def test_record_never_breaks_caller(self, monkeypatch):
        monkeypatch.setattr(
            OpsHeartbeat.objects, "update_or_create", mock.Mock(side_effect=RuntimeError("db gone"))
        )
        OpsHeartbeat.record("backup", ok=True)  # 不抛即通过


@pytest.mark.django_db
class TestPublishHeartbeatWiring:
    def test_success_records_ok_heartbeat(self):
        call_command("run_publish_scheduled")
        hb = OpsHeartbeat.objects.get(kind="publish_scheduled")
        assert hb.ok is True
        assert "published" in hb.detail

    def test_failure_records_not_ok_and_reraises(self, monkeypatch):
        monkeypatch.setattr(
            f"{SCHEDULER}.call_command", mock.Mock(side_effect=RuntimeError("wagtail exploded"))
        )
        with pytest.raises(RuntimeError, match="wagtail exploded"):
            call_command("run_publish_scheduled")
        hb = OpsHeartbeat.objects.get(kind="publish_scheduled")
        assert hb.ok is False


@pytest.mark.django_db
class TestBackupHeartbeatWiring:
    @pytest.fixture()
    def fast_backup_env(self, monkeypatch, tmp_path):
        """备份根指 tmp；dump/媒体/校验和打桩，只验证心跳接线本身。"""
        monkeypatch.setenv("BACKUP_ROOT", str(tmp_path / "backups"))
        monkeypatch.delenv("SECONDARY_BACKUP_DIR", raising=False)

        def fake_dump(dest):
            dest.write_bytes(b"PGDMP")

        monkeypatch.setattr(_lib, "dump_db", fake_dump)
        monkeypatch.setattr(_lib, "make_media_archive", mock.Mock(return_value=0))
        monkeypatch.setattr(_lib, "write_checksums", mock.Mock())

    def test_success_records_ok_heartbeat(self, fast_backup_env):
        call_command("backup_run")
        hb = OpsHeartbeat.objects.get(kind="backup")
        assert hb.ok is True
        assert hb.detail["secondary"] == "skipped"

    def test_failure_records_not_ok_and_cleans_set(self, fast_backup_env, monkeypatch):
        monkeypatch.setattr(_lib, "dump_db", mock.Mock(side_effect=RuntimeError("pg gone")))
        with pytest.raises(CommandError, match="备份失败"):
            call_command("backup_run")
        hb = OpsHeartbeat.objects.get(kind="backup")
        assert hb.ok is False
        root = _lib.backup_root()
        assert list(root.iterdir()) == []  # 残集已清理


class TestDiskCheck:
    @pytest.fixture()
    def three_roots(self, monkeypatch, tmp_path):
        media, static, backups = tmp_path / "media", tmp_path / "static", tmp_path / "backups"
        for path in (media, static, backups):
            path.mkdir()
        monkeypatch.setenv("BACKUP_ROOT", str(backups))
        monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(free=50, total=100))
        with override_settings(MEDIA_ROOT=media, STATIC_ROOT=static):
            yield

    def test_free_disk_maps_to_ok(self, three_roots):
        from peiligo.opsignal.management.commands import ops_report

        level, detail = ops_report._disk_check()
        assert level == "ok"
        assert all(mount["level"] == "ok" for mount in detail["mounts"])

    def test_warn_and_crit_thresholds(self, three_roots, monkeypatch):
        import peiligo.opsignal.management.commands.ops_report as module

        for free, expected in ((15.0, "warn"), (5.0, "crit")):
            monkeypatch.setattr(module, "_pct_free", lambda path, _free=free: _free)
            level, detail = module._disk_check()
            assert level == expected
            assert {mount["level"] for mount in detail["mounts"]} == {expected}

    def test_missing_path_is_warn_not_crash(self, monkeypatch, tmp_path):
        from peiligo.opsignal.management.commands import ops_report

        monkeypatch.setenv("BACKUP_ROOT", str(tmp_path / "nope-backups"))
        with override_settings(MEDIA_ROOT=tmp_path / "nope", STATIC_ROOT=tmp_path / "also-nope"):
            level, detail = ops_report._disk_check()
        assert level == "warn"
        assert all(mount["free_pct"] is None for mount in detail["mounts"])


@pytest.mark.django_db
class TestOpsReport:
    def test_stdout_is_machine_readable_json(self, fresh_world):
        report = run_report()
        assert report["overall"] == "ok"
        # 冻结口径「最近成功时刻」须绝对透出（独立审查 P2 修复）。
        assert report["checks"]["backup_heartbeat"]["last_ok_at"]
        assert set(report["checks"]) == {
            "database",
            "disk",
            "backup_freshness",
            "backup_heartbeat",
            "publish_scheduled",
            "login_anomalies",
            "app_errors",
        }

    def test_empty_backup_root_crit_exits_nonzero(self, quiet_world):
        with pytest.raises(CommandError, match="backup_freshness"):
            call_command("ops_report")

    def test_aged_primary_backup_crit(self, quiet_world):
        make_backup_set(quiet_world, mtime=time.time() - 25 * 3600)
        with pytest.raises(CommandError, match="backup_freshness"):
            call_command("ops_report")

    def test_aged_primary_backup_warn_exits_zero(self, quiet_world):
        make_backup_set(quiet_world, mtime=time.time() - 13 * 3600)
        report = run_report()
        assert report["checks"]["backup_freshness"]["level"] == "warn"
        assert report["overall"] == "warn"

    def test_secondary_unconfigured_is_explicit_warn(self, quiet_world):
        make_backup_set(quiet_world, mtime=time.time())
        report = run_report()
        sec = report["checks"]["backup_freshness"]["secondary"]
        assert sec["level"] == "warn"
        assert "SECONDARY_BACKUP_DIR" in sec["note"]

    def test_secondary_configured_but_empty_crit(self, fresh_world, monkeypatch, tmp_path):
        empty = tmp_path / "empty-secondary"
        empty.mkdir()
        monkeypatch.setenv("SECONDARY_BACKUP_DIR", str(empty))
        with pytest.raises(CommandError, match="backup_freshness"):
            call_command("ops_report")

    def test_publish_heartbeat_missing_crit(self, quiet_world):
        OpsHeartbeat.objects.filter(kind="publish_scheduled").delete()
        with pytest.raises(CommandError, match="publish_scheduled"):
            call_command("ops_report")

    def test_publish_heartbeat_stale_warn_then_crit(self, fresh_world):
        OpsHeartbeat.objects.filter(kind="publish_scheduled").update(
            updated_at=timezone.now() - timedelta(minutes=16)
        )
        report = run_report()
        assert report["checks"]["publish_scheduled"]["level"] == "warn"

        OpsHeartbeat.objects.filter(kind="publish_scheduled").update(
            updated_at=timezone.now() - timedelta(hours=3)
        )
        with pytest.raises(CommandError, match="publish_scheduled"):
            call_command("ops_report")

    def test_publish_failed_heartbeat_crit_even_if_fresh(self, fresh_world):
        OpsHeartbeat.record("publish_scheduled", ok=False, error="boom")
        with pytest.raises(CommandError, match="publish_scheduled"):
            call_command("ops_report")

    def test_login_lockout_is_warn_not_crit(self, fresh_world):
        from axes.models import AccessFailureLog

        AccessFailureLog.objects.create(
            username="t13-locked", ip_address="10.0.0.9", locked_out=True
        )
        report = run_report()
        login = report["checks"]["login_anomalies"]
        assert login["level"] == "warn"
        assert login["lockouts"] == 1
        assert report["overall"] == "warn"

    def test_app_errors_recent_error_line_counts(self, fresh_world, tmp_path, monkeypatch):
        now_iso = timezone.now().isoformat()
        old_iso = (timezone.now() - timedelta(hours=30)).isoformat()
        log_file = tmp_path / "events.log"
        log_file.write_text(
            json.dumps({"ts": now_iso, "level": "ERROR"})
            + "\n"
            + json.dumps({"ts": old_iso, "level": "ERROR"})
            + "\n"
            + json.dumps({"ts": now_iso, "level": "INFO"})
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("OPS_LOG_FILE", str(log_file))
        report = run_report()
        assert report["checks"]["app_errors"]["error_lines"] == 1
        assert report["checks"]["app_errors"]["level"] == "warn"

    def test_app_errors_unknown_when_unconfigured(self, fresh_world):
        report = run_report()
        assert report["checks"]["app_errors"]["status"] == "unknown"
