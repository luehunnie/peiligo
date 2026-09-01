"""F-13：ops_report——一次性观测快照（机器可读 JSON＋结构化日志）。

冻结口径：无监控平台、无常驻守护。cron/定时器每 ≥5 分钟跑一次本命令：
- stdout 输出单份 JSON（整体级与各信号级，供接线告警或人工查看）；
- 记结构化日志 event=``ops.report``；
- 存在任一 CRIT 时以 CommandError 非零退出（告警接线的判定锚点）。

信号与阈值（冻结）：
- database           SELECT 1 可达；失败＝CRIT。
- disk               MEDIA_ROOT/BACKUP_ROOT/STATIC_ROOT 所在盘剩余
                     <20%＝WARN、<10%＝CRIT（仅项目路径，不扫全盘）。
- backup_freshness   最新备份集距今 >12h＝WARN、>24h＝CRIT、无任何
                     备份集＝CRIT；SECONDARY_BACKUP_DIR 未配置＝WARN
                     （显式不静默），已配置但为空＝CRIT，时限同上。
- publish_scheduled  最近心跳：无记录＝CRIT（从未跑过）；距今 >15 分钟
                     ＝WARN、>2 小时＝CRIT；最近一次 ok=False＝CRIT。
- login_anomalies    复用 F-05 axes 轴：近 24h 失败次数与锁定次数
                     （仅提示，不判 CRIT——业务异常而非服务故障）。
- app_errors         可选 OPS_LOG_FILE：近 24h ERROR 行数 >0＝WARN；
                     未配置则如实报告 unknown（不装作没事）。
"""

import json
import logging
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from peiligo.backupkit import _lib
from peiligo.opsignal.models import OpsHeartbeat

logger = logging.getLogger("peiligo.events")

DISK_WARN_PCT = 20
DISK_CRIT_PCT = 10
BACKUP_WARN = timedelta(hours=12)
BACKUP_CRIT = timedelta(hours=24)
PUB_WARN = timedelta(minutes=15)
PUB_CRIT = timedelta(hours=2)
LOGIN_WINDOW = timedelta(hours=24)


def _pct_free(path):
    usage = shutil.disk_usage(path)
    return round(usage.free / usage.total * 100, 1)


def _disk_check():
    targets = {
        "MEDIA_ROOT": Path(settings.MEDIA_ROOT),
        "BACKUP_ROOT": _lib.backup_root(),
        "STATIC_ROOT": Path(settings.STATIC_ROOT),
    }
    worst, items = "ok", []
    for name, path in targets.items():
        if not path.exists():
            items.append({"path": name, "level": "warn", "free_pct": None, "note": "路径不存在"})
            worst = _worse(worst, "warn")
            continue
        free = _pct_free(path)
        level = "ok"
        if free < DISK_CRIT_PCT:
            level = "crit"
        elif free < DISK_WARN_PCT:
            level = "warn"
        items.append({"path": name, "level": level, "free_pct": free})
        worst = _worse(worst, level)
    return worst, {
        "thresholds": {"warn_pct": DISK_WARN_PCT, "crit_pct": DISK_CRIT_PCT},
        "mounts": items,
    }


def _latest_set_age(root):
    """最新合法备份集距现在的时长；无集合返回 None。"""
    now = timezone.now()
    latest = None
    for entry in sorted(root.glob("*")):
        if _lib.is_backup_set(entry):
            mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=UTC)
            latest = mtime if latest is None else max(latest, mtime)
    return None if latest is None else now - latest


def _age_level(age):
    if age is None:
        return "crit"
    if age > BACKUP_CRIT:
        return "crit"
    if age > BACKUP_WARN:
        return "warn"
    return "ok"


def _backup_check():
    root = _lib.backup_root()
    age = _latest_set_age(root) if root.exists() else None
    worst = _age_level(age)
    secondary = _lib.secondary_root()
    if secondary is None:
        sec = {"level": "warn", "note": "SECONDARY_BACKUP_DIR 未配置（无独立副本）"}
        worst = _worse(worst, "warn")
    else:
        sec_age = _latest_set_age(secondary) if secondary.exists() else None
        sec = {"level": _age_level(sec_age), "age_hours": _hours(sec_age)}
        worst = _worse(worst, sec["level"])
    return worst, {
        "thresholds": {"warn": "12h", "crit": "24h"},
        "primary": {"age_hours": _hours(age)},
        "secondary": sec,
    }


def _publish_check():
    hb = OpsHeartbeat.objects.filter(kind="publish_scheduled").first()
    if hb is None:
        return "crit", {"note": "从未运行（无心跳记录）"}
    age = timezone.now() - hb.updated_at
    level = "ok"
    if age > PUB_CRIT:
        level = "crit"
    elif age > PUB_WARN:
        level = "warn"
    if not hb.ok:
        level = "crit"
    return level, {
        "ok": hb.ok,
        "age_minutes": round(age.total_seconds() / 60, 1),
        "thresholds": {"warn": "15m", "crit": "2h"},
        "detail": hb.detail,
    }


def _backup_heartbeat_check():
    hb = OpsHeartbeat.objects.filter(kind="backup").first()
    if hb is None:
        return "ok", {"note": "尚无备份心跳（freshness 由 backup_freshness 判定）"}
    if not hb.ok:
        return "crit", {"ok": False, "detail": hb.detail}
    return "ok", {"ok": True, "detail": hb.detail}


def _login_check():
    from axes.models import AccessFailureLog

    cutoff = timezone.now() - LOGIN_WINDOW
    failures = AccessFailureLog.objects.filter(attempt_time__gte=cutoff).count()
    lockouts = AccessFailureLog.objects.filter(attempt_time__gte=cutoff, locked_out=True).count()
    level = "ok" if lockouts == 0 else "warn"
    return level, {
        "window": "24h",
        "failures": failures,
        "lockouts": lockouts,
        "note": "业务异常信号，不判 CRIT",
    }


def _app_errors_check():
    log_path = os.environ.get("OPS_LOG_FILE")
    if not log_path:
        return "ok", {"status": "unknown", "note": "未配置 OPS_LOG_FILE（结构化日志仅在 stdout）"}
    path = os.fsdecode(log_path)
    if not os.path.exists(path):
        return "warn", {"status": "unknown", "note": f"OPS_LOG_FILE 不存在：{path}"}
    cutoff = timezone.now() - LOGIN_WINDOW
    errors = 0
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                # F-07 JsonFormatter 的时刻键是 "ts"（ISO-8601，UTC 带时区）。
                record = json.loads(line)
                when = datetime.fromisoformat(record["ts"])
                if when.tzinfo is None:
                    when = when.replace(tzinfo=UTC)
                if record.get("level") == "ERROR" and when >= cutoff:
                    errors += 1
            except (ValueError, KeyError, TypeError):
                continue
    return ("warn" if errors else "ok"), {"window": "24h", "error_lines": errors}


def _hours(age):
    return None if age is None else round(age.total_seconds() / 3600, 1)


def _worse(current, candidate):
    order = {"ok": 0, "warn": 1, "crit": 2}
    return candidate if order[candidate] > order[current] else current


class Command(BaseCommand):
    help = "输出监控信号快照（JSON）；存在 CRIT 信号时非零退出（F-13）。"

    def handle(self, *args, **options):
        checks = {}
        overall = "ok"

        # database：连不通则其余 DB 依赖信号一并无意义，但快照仍如实输出。
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = {"level": "ok"}
        except Exception as error:
            checks["database"] = {"level": "crit", "error": str(error)}
            overall = "crit"

        for name, check in (
            ("disk", _disk_check),
            ("backup_freshness", _backup_check),
            ("backup_heartbeat", _backup_heartbeat_check),
            ("publish_scheduled", _publish_check),
            ("login_anomalies", _login_check),
            ("app_errors", _app_errors_check),
        ):
            level, detail = check()
            checks[name] = {"level": level, **detail}
            overall = _worse(overall, level)

        report = {
            "generated_at": timezone.now().isoformat(),
            "overall": overall,
            "checks": checks,
        }
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))

        logger.log(
            logging.INFO if overall != "crit" else logging.ERROR,
            "监控快照",
            extra={"event": "ops.report", "overall": overall},
        )

        if overall == "crit":
            crits = [name for name, item in checks.items() if item["level"] == "crit"]
            raise CommandError(f"存在 CRIT 信号：{', '.join(crits)}")
