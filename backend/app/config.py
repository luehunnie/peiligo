"""配置读取模块。

仅负责从环境变量与本地 .env 加载并校验数据库连接配置。
本模块不创建数据库 Engine / Session，也不建立任何连接。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 仓库根目录（本文件位于 backend/app/config.py，向上两级）
_REPO_ROOT = Path(__file__).resolve().parents[2]

# 加载本地 .env；文件缺失或变量已在真实环境中设置时安全跳过
load_dotenv(dotenv_path=_REPO_ROOT / ".env", override=False)


def _require_env(name: str) -> str:
    """读取必需环境变量，缺失或为空时抛出清晰错误，不附带任何默认值。"""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"缺少必需配置 {name}：请在仓库根目录 .env 中设置（参考 .env.example）。"
        )
    return value


# 数据库连接配置（仅保留字符串，不在此建立连接）
DATABASE_URL: str = _require_env("DATABASE_URL")
TEST_DATABASE_URL: str = _require_env("TEST_DATABASE_URL")
