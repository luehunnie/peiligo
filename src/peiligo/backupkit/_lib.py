"""F-12 共享工具：备份集布局、校验和、pg_dump/pg_restore 子进程封装。

安全纪律：
- 口令只经子进程环境（PGPASSWORD）传递，不落 argv、不进任何输出；
- 目录删除只针对 ``is_backup_set`` 双重特征（目录名＝严格时间戳格式
  ∧ 含 manifest.json）的项，绝不通配。
"""

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.db import connections

BACKUP_DIRNAME_RE = re.compile(r"^\d{8}T\d{6}Z$")

DB_DUMP_NAME = "db.dump"
MEDIA_ARCHIVE_NAME = "media.tar.gz"
MANIFEST_NAME = "manifest.json"
CHECKSUMS_NAME = "sha256sums.txt"


def backup_root() -> Path:
    root = os.environ.get("BACKUP_ROOT")
    return Path(root) if root else settings.BASE_DIR / "backups"


def current_db_settings() -> dict:
    """当前活动连接参数（pytest 下＝测试库；生产＝DATABASE_URL 所指）。"""
    return connections["default"].settings_dict


def secondary_root():
    """独立存储副本目录（vendor-neutral：任何可挂载路径皆可）；未配置＝None。"""
    root = os.environ.get("SECONDARY_BACKUP_DIR")
    return Path(root) if root else None


def is_backup_set(path) -> bool:
    """Peiligo 备份集判据：严格时间戳目录名 ∧ 含 manifest.json。"""
    return (
        path.is_dir()
        and BACKUP_DIRNAME_RE.fullmatch(path.name) is not None
        and (path / MANIFEST_NAME).is_file()
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _db_conn_settings():
    db = current_db_settings()
    return {
        "host": db.get("HOST") or "",
        "port": str(db.get("PORT") or ""),
        "user": db.get("USER") or "",
        "password": db.get("PASSWORD") or "",
        "dbname": db.get("NAME"),
    }


def _pg_env() -> dict:
    conn = _db_conn_settings()
    env = dict(os.environ)
    if conn["password"]:
        env["PGPASSWORD"] = conn["password"]  # 只进子进程环境，不进 argv/输出
    return env


def dump_db(dest: Path) -> None:
    """pg_dump 自定义格式落盘（当前默认库 → dest）。失败抛 RuntimeError。"""
    conn = _db_conn_settings()
    cmd = ["pg_dump", "--format=custom", "--no-password", "--file", str(dest)]
    if conn["host"]:
        cmd += ["--host", conn["host"]]
    if conn["port"]:
        cmd += ["--port", conn["port"]]
    if conn["user"]:
        cmd += ["--username", conn["user"]]
    cmd += ["--dbname", str(conn["dbname"])]
    result = subprocess.run(cmd, env=_pg_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump 失败（exit={result.returncode}）：{result.stderr.strip()}")


def restore_db(dump: Path, target_dbname: str) -> None:
    """pg_restore 到隔离目标库（须已由 createdb 建好；本函数不建库不删库）。"""
    conn = _db_conn_settings()
    cmd = ["pg_restore", "--no-owner", "--exit-on-error", "--dbname", target_dbname]
    if conn["host"]:
        cmd += ["--host", conn["host"]]
    if conn["port"]:
        cmd += ["--port", conn["port"]]
    if conn["user"]:
        cmd += ["--username", conn["user"]]
    cmd.append(str(dump))
    result = subprocess.run(cmd, env=_pg_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pg_restore 失败（exit={result.returncode}）：{result.stderr.strip()}")


def dump_table_of_contents(dump: Path) -> str:
    """pg_restore --list：校验 dump 可读性（不落任何库）。"""
    conn = _db_conn_settings()
    cmd = ["pg_restore", "--list"]
    if conn["host"]:
        cmd += ["--host", conn["host"]]
    if conn["port"]:
        cmd += ["--port", conn["port"]]
    if conn["user"]:
        cmd += ["--username", conn["user"]]
    cmd.append(str(dump))
    result = subprocess.run(cmd, env=_pg_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pg_restore --list 失败：{result.stderr.strip()}")
    return result.stdout


def make_media_archive(dest: Path) -> int:
    """MEDIA_ROOT → tar.gz（归档内统一挂 media/ 相对根）。返回归档内文件数。"""
    import tarfile

    media_root = Path(settings.MEDIA_ROOT)
    count = 0
    with tarfile.open(dest, "w:gz") as archive:
        if media_root.is_dir():
            for item in sorted(media_root.rglob("*")):
                archive.add(item, arcname=str(Path("media") / item.relative_to(media_root)))
                if item.is_file():
                    count += 1
    return count


def extract_media_archive(archive: Path, target_dir: Path) -> None:
    import tarfile

    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(target_dir, filter="data")  # data 过滤器防路径穿越


def write_checksums(set_dir: Path) -> None:
    lines = [
        f"{sha256_file(set_dir / name)}  {name}" for name in (DB_DUMP_NAME, MEDIA_ARCHIVE_NAME)
    ]
    (set_dir / CHECKSUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_checksums(set_dir: Path) -> list:
    """逐项核对 sha256sums.txt；返回 (name, expected, actual) 不一致列表。"""
    expected = (set_dir / MANIFEST_NAME).is_file() and (set_dir / CHECKSUMS_NAME).is_file()
    if not expected:
        raise RuntimeError("备份集缺少 manifest.json 或 sha256sums.txt")
    mismatches = []
    for line in (set_dir / CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(maxsplit=1)
        actual = sha256_file(set_dir / name.strip())
        if checksum != actual:
            mismatches.append((name.strip(), checksum, actual))
    return mismatches


def copy_to_secondary(set_dir: Path, secondary: Path) -> Path:
    """整集复制到独立存储（目录存在性由调用方保证）。"""
    dest = secondary / set_dir.name
    shutil.copytree(set_dir, dest)
    return dest
