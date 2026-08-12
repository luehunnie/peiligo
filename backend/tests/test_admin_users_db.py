"""admin_users: real PostgreSQL behavior tests against peiligo_test.

password_hash uses an obvious fixed test string only; no hashing or auth
logic is implemented here. Each test runs inside a rolled-back transaction
(see conftest.pg_conn) so no rows are ever committed.
"""

from datetime import datetime

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.models.admin_user import AdminUser

_ADMIN = AdminUser.__table__
_HASH = "test-password-hash"


def test_admin_user_inserts(pg_conn) -> None:
    pg_conn.execute(insert(_ADMIN).values(username="alice", password_hash=_HASH))
    names = pg_conn.execute(select(_ADMIN.c.username)).scalars().all()
    assert names == ["alice"]


def test_duplicate_username_rejected(pg_conn) -> None:
    pg_conn.execute(insert(_ADMIN).values(username="bob", password_hash=_HASH))
    with pytest.raises(IntegrityError) as ei:
        pg_conn.execute(insert(_ADMIN).values(username="bob", password_hash=_HASH))
    assert ei.value.orig.diag.constraint_name == "admin_users_username_key"


def test_is_active_server_default_true(pg_conn) -> None:
    # is_active omitted -> must come from DB default, not an ORM default.
    pg_conn.execute(insert(_ADMIN).values(username="carol", password_hash=_HASH))
    assert pg_conn.execute(select(_ADMIN.c.is_active)).scalar() is True


def test_created_at_is_timezone_aware(pg_conn) -> None:
    pg_conn.execute(insert(_ADMIN).values(username="dave", password_hash=_HASH))
    created = pg_conn.execute(select(_ADMIN.c.created_at)).scalar()
    assert isinstance(created, datetime)
    assert created.tzinfo is not None
    assert created.utcoffset() is not None


def test_last_login_at_can_be_null(pg_conn) -> None:
    pg_conn.execute(insert(_ADMIN).values(username="erin", password_hash=_HASH))
    assert pg_conn.execute(select(_ADMIN.c.last_login_at)).scalar() is None
