"""公开内容只读 API 集成测试：基于 peiligo_test 事务回滚隔离。

覆盖列表过滤、排序、详情 404、body 切段、camelCase、extraData、source 可空等契约。
每个测试通过 contents_api fixture 覆盖 get_db，使 API 端点共享 pg_conn 回滚事务。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.content import Content

_CONTENTS = Content.__table__
_CST = timezone(timedelta(hours=8))


def _values(**overrides) -> dict:
    """最小有效 contents 行，按测试需要覆盖字段。"""
    base = {
        "content_type": "campus-story",
        "title": "title",
        "summary": "summary",
        "body": "body",
        "status": "draft",
    }
    base.update(overrides)
    return base


def _insert(pg_conn, **overrides) -> int:
    """插入一行 contents 并返回自增 id。"""
    result = pg_conn.execute(
        insert(_CONTENTS).values(_values(**overrides)).returning(_CONTENTS.c.id)
    )
    return result.scalar()


def _request(method: str, path: str) -> httpx.Response:
    """以 ASGI transport 发送同步 HTTP 请求。"""
    transport = httpx.ASGITransport(app=app)

    async def _call() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.request(method, path)

    return asyncio.run(_call())


@pytest.fixture()
def contents_api(pg_conn):
    """覆盖 get_db，使 API 端点共享 pg_conn 回滚事务。"""
    session = Session(bind=pg_conn, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    session.close()


def test_list_returns_only_published(pg_conn, contents_api) -> None:
    _insert(pg_conn, title="pub", status="published")
    _insert(pg_conn, title="draft", status="draft")
    _insert(pg_conn, title="off", status="offline")

    resp = _request("GET", "/api/contents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "pub"


def test_list_sorted_by_published_at_desc(pg_conn, contents_api) -> None:
    _insert(
        pg_conn,
        title="older",
        status="published",
        published_at=datetime(2025, 1, 1, tzinfo=_CST),
    )
    _insert(
        pg_conn,
        title="newer",
        status="published",
        published_at=datetime(2025, 6, 1, tzinfo=_CST),
    )

    resp = _request("GET", "/api/contents")
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "newer"
    assert data[1]["title"] == "older"


def test_list_empty_when_no_published(pg_conn, contents_api) -> None:
    _insert(pg_conn, status="draft")
    resp = _request("GET", "/api/contents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_null_published_at_no_crash(pg_conn, contents_api) -> None:
    """published 但 published_at 为空时不应导致列表 500。"""
    _insert(pg_conn, title="no-date", status="published")
    resp = _request("GET", "/api/contents")
    assert resp.status_code == 200
    assert resp.json()[0]["publishedAt"] == ""


def test_detail_published_returns_200(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, title="detail", status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "detail"


def test_detail_not_found_returns_404(contents_api) -> None:
    resp = _request("GET", "/api/contents/99999")
    assert resp.status_code == 404


def test_detail_non_integer_id_returns_404(contents_api) -> None:
    resp = _request("GET", "/api/contents/abc")
    assert resp.status_code == 404


def test_detail_draft_returns_404(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, status="draft")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.status_code == 404


def test_detail_offline_returns_404(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, status="offline")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.status_code == 404


def test_body_split_into_paragraphs(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, body="第一段。\n\n第二段。\n第三段。", status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.json()["body"] == ["第一段。", "第二段。\n第三段。"]


def test_body_strips_whitespace_and_ignores_empty(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, body="  A  \n\n\n  B  ", status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.json()["body"] == ["A", "B"]


def test_json_keys_are_camel_case(pg_conn, contents_api) -> None:
    cid = _insert(
        pg_conn,
        status="published",
        source_name="src",
        source_url="http://example.com",
    )
    resp = _request("GET", f"/api/contents/{cid}")
    assert set(resp.json().keys()) == {
        "id",
        "contentType",
        "title",
        "summary",
        "body",
        "sourceName",
        "sourceUrl",
        "publishedAt",
        "status",
        "extraData",
    }


def test_id_is_string(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    assert isinstance(resp.json()["id"], str)


def test_extra_data_preserves_types(pg_conn, contents_api) -> None:
    extra = {"tag": "news", "count": 42, "featured": True, "labels": ["a", "b"]}
    cid = _insert(pg_conn, status="published", extra_data=extra)
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.json()["extraData"] == extra


def test_extra_data_empty_returns_empty_object(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    assert resp.json()["extraData"] == {}


def test_source_nullable(pg_conn, contents_api) -> None:
    cid = _insert(pg_conn, status="published")
    resp = _request("GET", f"/api/contents/{cid}")
    data = resp.json()
    assert data["sourceName"] is None
    assert data["sourceUrl"] is None
