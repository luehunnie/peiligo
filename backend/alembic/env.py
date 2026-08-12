"""Alembic 迁移环境。

连接串从应用配置 DATABASE_URL 注入（不在 alembic.ini 内留存真实凭据），
target_metadata 指向 Base.metadata。显式导入两个业务模型，确保 metadata
实际包含 contents / admin_users。本模块不调用 create_all，也不引入第二套
数据库配置体系。
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import DATABASE_URL
from app.database import Base
from app.models.admin_user import AdminUser  # noqa: F401  注册到 Base.metadata
from app.models.content import Content  # noqa: F401  注册到 Base.metadata

# alembic.context（运行时注入）
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 由应用配置注入连接串
# set_main_option 经 ConfigParser 插值，原始 % 必须写成 %%（不修改真实 URL，也不二次 URL-encode）
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：按 SQL 文本生成迁移，不建立数据库连接。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：通过 Engine 连接数据库并运行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
