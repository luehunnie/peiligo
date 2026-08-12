"""公开内容只读 API 路由。

GET /api/contents      — 已发布内容列表（按 published_at DESC）
GET /api/contents/{id} — 已发布内容详情（不存在/draft/offline 统一 404）
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import Content
from app.schemas.content import ContentItemResponse

router = APIRouter(prefix="/api/contents", tags=["contents"])

# 请求级数据库会话依赖（使用 Annotated 避免 B008）
DBSession = Annotated[Session, Depends(get_db)]

# 以一个或多个连续空行（含纯空白行）作为段落分隔符
_BODY_SPLIT = re.compile(r"\n\s*\n")


def _split_body(body: str) -> list[str]:
    """TEXT body 按空行切段：去首尾空白、忽略空段。"""
    segments = _BODY_SPLIT.split(body.strip())
    return [seg.strip() for seg in segments if seg.strip()]


def _to_response(content: Content) -> ContentItemResponse:
    """ORM 行 → 响应模型：id 转 string、body 切段、published_at 转 ISO 字符串。"""
    return ContentItemResponse(
        id=str(content.id),
        content_type=content.content_type,
        title=content.title,
        summary=content.summary,
        body=_split_body(content.body),
        source_name=content.source_name,
        source_url=content.source_url,
        published_at=content.published_at.isoformat() if content.published_at else "",
        status=content.status,
        # 保留空对象语义：extra_data 为空 dict 时输出 {}，不转 null（对齐 ContentExtraData 契约）
        extra_data=content.extra_data or {},
    )


@router.get("", response_model=list[ContentItemResponse])
def list_contents(db: DBSession) -> list[ContentItemResponse]:
    """已发布内容列表，默认按 published_at DESC（NULLS LAST）排序。"""
    stmt = (
        select(Content)
        .where(Content.status == "published")
        .order_by(Content.published_at.desc().nullslast())
    )
    rows = db.execute(stmt).scalars().all()
    return [_to_response(row) for row in rows]


@router.get("/{content_id}", response_model=ContentItemResponse)
def get_content(content_id: str, db: DBSession) -> ContentItemResponse:
    """已发布内容详情；不存在 / draft / offline 统一返回 404。"""
    try:
        numeric_id = int(content_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        ) from None
    stmt = select(Content).where(
        Content.id == numeric_id, Content.status == "published"
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        )
    return _to_response(row)
