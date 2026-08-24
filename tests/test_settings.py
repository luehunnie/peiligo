"""settings 可导入性与配置外置冒烟测试（M1 工程基座 + A1.1 S1 环境依赖补齐）。

计划 03 S1/MB1：三套 settings 均可导入；本地与测试统一 PostgreSQL；
数据库与测试库 URL 均经环境变量外置（DATABASE_URL/TEST_DATABASE_URL），
无硬编码回环地址字面量（防旧审计 R5 硬编码模式复发）；
.env.example 覆盖必需键且全部为哑值（无真实秘密）。
"""

import importlib
import os
from pathlib import Path

import dj_database_url
import pytest
from django.conf import settings

REPO_ROOT = Path(__file__).resolve().parents[1]

SETTINGS_MODULES = [
    "peiligo.settings.base",
    "peiligo.settings.dev",
    "peiligo.settings.production",
]

# 数据库/主机配置可能出现的位置：settings 包、测试装配、pytest 配置。
HARDCODE_SCAN_TARGETS = [
    path
    for path in [
        *sorted((REPO_ROOT / "src" / "peiligo" / "settings").glob("*.py")),
        REPO_ROOT / "tests" / "conftest.py",
        REPO_ROOT / "pyproject.toml",
    ]
    if path.exists()
]

# A1.1（03 计划 S1）：.env.example 必需键与哑值标记
ENV_EXAMPLE_REQUIRED_KEYS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "ALLOWED_HOSTS",
    "MEDIA_ROOT",
]
ENV_EXAMPLE_DUMMY_MARKERS = ("CHANGE_ME", "django-insecure", "localhost", "example.com", "/tmp/")


@pytest.mark.parametrize("module", SETTINGS_MODULES)
def test_settings_module_importable(module):
    assert importlib.import_module(module) is not None


def test_no_hardcoded_loopback_in_db_related_sources():
    for path in HARDCODE_SCAN_TARGETS:
        content = path.read_text()
        assert "127.0.0.1" not in content, f"{path.relative_to(REPO_ROOT)} 含硬编码 127.0.0.1"


def test_dev_database_is_postgresql_via_env():
    """S1：本地（dev settings）数据库统一 PostgreSQL，连接来自环境变量（SQLite 不再是基线）。"""
    url = os.environ["DATABASE_URL"]
    assert url.startswith(("postgres://", "postgresql://")), "DATABASE_URL 非 PostgreSQL 连接串"
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL 未设置")
def test_test_database_name_from_env_variable():
    """S1：独立测试库名取自 TEST_DATABASE_URL 环境变量（防 R5 复发）。"""
    expected = dj_database_url.parse(os.environ["TEST_DATABASE_URL"])["NAME"]
    assert settings.DATABASES["default"]["TEST"]["NAME"] == expected


def _env_example_assignments():
    content = (REPO_ROOT / ".env.example").read_text()
    assignments = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        assignments[key.strip()] = value.strip()
    return assignments


def test_env_example_covers_required_keys():
    assignments = _env_example_assignments()
    for key in ENV_EXAMPLE_REQUIRED_KEYS:
        assert key in assignments, f".env.example 缺少必需键 {key}"
        assert assignments[key], f".env.example 键 {key} 值为空"


def test_env_example_values_are_dummy():
    """.env.example 无真实秘密：每个赋值行都含哑值标记。"""
    for key, value in _env_example_assignments().items():
        assert any(marker in value for marker in ENV_EXAMPLE_DUMMY_MARKERS), (
            f".env.example 键 {key} 的值未见哑值标记"
        )
