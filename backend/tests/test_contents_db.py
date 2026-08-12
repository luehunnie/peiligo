"""contents: real PostgreSQL behavior tests against peiligo_test.

Each test runs inside a rolled-back transaction (see conftest.pg_conn) so no
rows are ever committed. Defaults and timestamptz values come from the DB
server defaults: inserts use Core and deliberately omit those columns, so the
values can only have been produced by PostgreSQL, not by ORM Python defaults.
"""

from datetime import datetime

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.models.content import Content

_CONTENTS = Content.__table__


def _values(**overrides) -> dict:
    """Minimal valid contents row; overridable per test."""
    base = {
        "content_type": "campus-story",
        "title": "title",
        "summary": "summary",
        "body": "body",
        "status": "draft",
    }
    base.update(overrides)
    return base


def test_valid_content_type_inserts(pg_conn) -> None:
    pg_conn.execute(insert(_CONTENTS).values(_values(content_type="campus-story")))
    rows = pg_conn.execute(select(_CONTENTS.c.content_type)).scalars().all()
    assert rows == ["campus-story"]


def test_invalid_content_type_rejected(pg_conn) -> None:
    with pytest.raises(IntegrityError) as ei:
        pg_conn.execute(insert(_CONTENTS).values(_values(content_type="bogus")))
    assert ei.value.orig.diag.constraint_name == "ck_contents_content_type"


def test_invalid_status_rejected(pg_conn) -> None:
    with pytest.raises(IntegrityError) as ei:
        pg_conn.execute(insert(_CONTENTS).values(_values(status="archived")))
    assert ei.value.orig.diag.constraint_name == "ck_contents_status"


def test_extra_data_nested_jsonb_roundtrip(pg_conn) -> None:
    nested = {"meta": {"tags": ["a", "b"], "counts": {"x": 1, "y": 2}}, "ok": True}
    pg_conn.execute(insert(_CONTENTS).values(_values(extra_data=nested)))
    got = pg_conn.execute(select(_CONTENTS.c.extra_data)).scalar()
    assert got == nested


def test_extra_data_server_default_empty_object(pg_conn) -> None:
    # extra_data omitted on purpose -> must come from DB default '{}'::jsonb.
    pg_conn.execute(insert(_CONTENTS).values(_values()))
    got = pg_conn.execute(select(_CONTENTS.c.extra_data)).scalar()
    assert got == {}


def test_created_at_is_timezone_aware(pg_conn) -> None:
    # created_at omitted -> DB server default now() must supply a tz-aware value.
    pg_conn.execute(insert(_CONTENTS).values(_values()))
    created = pg_conn.execute(select(_CONTENTS.c.created_at)).scalar()
    assert isinstance(created, datetime)
    assert created.tzinfo is not None
    assert created.utcoffset() is not None


def test_updated_at_is_timezone_aware(pg_conn) -> None:
    pg_conn.execute(insert(_CONTENTS).values(_values()))
    updated = pg_conn.execute(select(_CONTENTS.c.updated_at)).scalar()
    assert isinstance(updated, datetime)
    assert updated.tzinfo is not None
    assert updated.utcoffset() is not None


def test_published_at_can_be_null(pg_conn) -> None:
    pg_conn.execute(insert(_CONTENTS).values(_values()))
    assert pg_conn.execute(select(_CONTENTS.c.published_at)).scalar() is None


def test_body_text_multiline_roundtrip(pg_conn) -> None:
    body = "第一段。\n\n第二段。\n第三段。"
    pg_conn.execute(insert(_CONTENTS).values(_values(body=body)))
    got = pg_conn.execute(select(_CONTENTS.c.body)).scalar()
    assert got == body
    assert "\n\n" in got
