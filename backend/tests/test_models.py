"""contents / admin_users 的 metadata 级测试，不连接真实数据库。"""

from sqlalchemy import CheckConstraint, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Base
from app.models.admin_user import AdminUser
from app.models.content import Content


def test_metadata_contains_exactly_two_tables() -> None:
    assert set(Base.metadata.tables.keys()) == {"contents", "admin_users"}


def test_contents_columns_present() -> None:
    cols = set(Content.__table__.columns.keys())
    expected = {
        "id",
        "content_type",
        "title",
        "summary",
        "body",
        "source_name",
        "source_url",
        "extra_data",
        "status",
        "created_at",
        "updated_at",
        "published_at",
    }
    assert expected <= cols


def test_contents_nullable() -> None:
    c = Content.__table__.c
    non_null = (
        "id",
        "content_type",
        "title",
        "summary",
        "body",
        "extra_data",
        "status",
        "created_at",
        "updated_at",
    )
    for name in non_null:
        assert c[name].nullable is False, name
    for name in ("source_name", "source_url", "published_at"):
        assert c[name].nullable is True, name


def test_contents_types() -> None:
    c = Content.__table__.c
    assert isinstance(c["id"].type, Integer)
    assert isinstance(c["body"].type, Text)
    assert isinstance(c["extra_data"].type, JSONB)
    for name in ("created_at", "updated_at", "published_at"):
        assert isinstance(c[name].type, DateTime), name
        assert c[name].type.timezone is True, name


def test_contents_checks_and_indexes() -> None:
    t = Content.__table__
    checks = [con for con in t.constraints if isinstance(con, CheckConstraint)]
    texts = {str(con.sqltext) for con in checks}
    # content_type 与 status 各一条 CHECK，且覆盖冻结枚举
    assert any("campus-story" in s for s in texts)
    assert any("software-resource" in s for s in texts)
    status_vals = {"draft", "published", "offline"}
    assert any(status_vals <= set(s.split("'")[1::2]) for s in texts)
    assert len(checks) == 2
    # 恰好三个二级索引
    idx_cols = {tuple(col.name for col in idx.columns) for idx in t.indexes}
    assert ("content_type",) in idx_cols
    assert ("status",) in idx_cols
    assert ("published_at",) in idx_cols
    assert len(t.indexes) == 3


def test_admin_users_columns_and_constraints() -> None:
    t = AdminUser.__table__
    assert set(t.columns.keys()) == {
        "id",
        "username",
        "password_hash",
        "is_active",
        "created_at",
        "last_login_at",
    }
    assert t.c.username.nullable is False
    assert t.c.username.unique is True
    assert t.c.password_hash.nullable is False
    assert t.c.is_active.nullable is False
    assert t.c.last_login_at.nullable is True
    assert isinstance(t.c.created_at.type, DateTime)
    assert t.c.created_at.type.timezone is True
    # admin_users 不引入 CHECK 约束
    assert not [con for con in t.constraints if isinstance(con, CheckConstraint)]
