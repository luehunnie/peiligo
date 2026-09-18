"""API v1 只读投影层：既有模型/服务数据的 JSON 形状（docs/api/openapi.json）。

可见性谓词、过滤层、排序、分页、外链确认链、搜索短路全部复用既有权威
实现（notices/lifecycle.py、search/services.py、home/models.py、
home/views.py）；本模块零业务逻辑，仅做取数结果的形状投影。站内引用
一律路径形态（§2.1）；时间 ISO 8601（USE_TZ 感知 datetime.isoformat）。
"""

from urllib.parse import quote

from home.models import (
    CAMPUS_NEWS_MAX_ITEMS,
    _campus_news_entry,
    _content_summary,
)
from notices.models import EventFieldsMixin
from search.services import LIST_PAGE_SIZE, type_identifier

# ImageRef 仅四处现有 rendition 规格，零新规格（openapi ImageRef.description）。
RENDITION_COVER = "width-1400"  # 详情封面（article_detail 壳现状）
RENDITION_CAROUSEL = "width-1600"  # 轮播（home_page 现状，装饰 alt=""）
RENDITION_NEWS = "fill-800x520"  # 快讯卡（home_page 现状，装饰 alt=""）
RENDITION_INLINE = "width-1120"  # 正文插图（blocks/image.html 现状）

# event_status 纯计算属性（§7.1 中文三态）的机器化映射（EventStatusEnum）。
EVENT_STATUS_CODES = {
    EventFieldsMixin.STATUS_UPCOMING: "upcoming",
    EventFieldsMixin.STATUS_ONGOING: "ongoing",
    EventFieldsMixin.STATUS_ENDED: "ended",
}


def iso(value):
    return value.isoformat() if value else None


def event_status_code(page):
    """仅填了活动字段的页面存在状态；其余静默 None（现状同构）。"""
    return EVENT_STATUS_CODES.get(getattr(page, "event_status", None))


def image_ref(image, spec, alt=None):
    """ImageRef：src 路径形态；alt 缺省＝rendition.alt（default_alt_text
    同源，blocks/image.html 与详情封面现状），装饰用途调用方传空串。"""
    rendition = image.get_rendition(spec)
    return {
        "src": rendition.url,
        "width": rendition.width,
        "height": rendition.height,
        "alt": rendition.alt if alt is None else alt,
    }


def cover_ref(page, spec=RENDITION_COVER, alt=None):
    image = getattr(page, "cover_image", None)
    return image_ref(image, spec, alt) if image else None


def confirm_href(url, page_pk):
    """确认链构造（唯一出处语义，与 external_link_jump.html 的 urlencode
    过滤器同口径：quote(value, safe="/")）。"""
    return f"/link-confirm/?url={quote(url, safe='/')}&from={page_pk}"


def external_ref(url, page_pk):
    return {"url": url, "confirm_href": confirm_href(url, page_pk)} if url else None


def list_entry(page):
    """ListEntry（列表/搜索/归档共享行数据；list_summary 不截断——90 字
    截断归前端表示层）。"""
    department = getattr(page, "department", None)
    return {
        "type": type_identifier(type(page)),
        "id": page.pk,
        "title": page.title,
        "url": page.url,
        "expired": bool(page.expired),
        "section_slug": getattr(page, "section_slug", None),
        "section_title": getattr(page, "section_title", None),
        "department_name": str(department) if department else None,
        "published_at": iso(page.first_published_at),
        "event_status": event_status_code(page),
        "list_summary": _content_summary(page),
    }


def pagination(page_obj):
    return {
        "total": page_obj.paginator.count,
        "page": page_obj.number,
        "page_count": page_obj.paginator.num_pages,
        "per_page": LIST_PAGE_SIZE,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }


def filters_echo(filters):
    """FiltersEcho：解析后筛选态（非法值回退后的有效维度）。路径锚定板块
    （E3，section_from_path）不入回显（契约：仅 /search/ 返回解析命中的
    板块）；active/conditions 消费既有 filter_active/active_conditions。"""
    return {
        "q": filters.q,
        "section": filters.section.slug
        if filters.section and not filters.section_from_path
        else None,
        "dept": filters.department.slug if filters.department else None,
        "type": filters.type_identifier,
        "tag": filters.tag,
        "active": filters.filter_active,
        "conditions": [
            {"label": label, "value": value} for label, value in filters.active_conditions()
        ],
    }


def body_blocks(page):
    """正文块投影（§11.1 六块只读投影）。paragraph 的 html＝服务端渲染的
    安全片段（RichText.__str__ 即 expand_db_html 渲染结果，与 Django 模板
    消费同一管线）；转义责任在消费方渲染层（§2.3 高亮条款同语义）。"""
    blocks = []
    for block in page.body:
        value = block.value
        if block.block_type == "heading":
            data = {"text": value["text"], "level": value["level"]}
        elif block.block_type == "paragraph":
            data = {"html": str(value)}
        elif block.block_type == "image":
            data = image_ref(value, RENDITION_INLINE)
        elif block.block_type == "attachment":
            data = {
                "title": value.title,
                "url": value.url,
                "file_size": value.file_size,
            }
        elif block.block_type == "table":
            data = {
                "data": value["data"],
                "first_row_is_table_header": value.get("first_row_is_table_header", False),
            }
        else:  # external_link
            data = {
                "text": value["link_text"],
                "url": value["url"],
                "confirm_href": confirm_href(value["url"], page.pk),
            }
        blocks.append({"type": block.block_type, "value": data})
    return blocks


def attachments_ref(page):
    return [
        {"title": doc.title, "url": doc.url, "file_size": doc.file_size}
        for doc in page.attachments.all()
    ]


def event_info(page):
    """EventInfo（EventFieldsMixin）：start_at 为空即整体 null。"""
    if page.event_start_at is None:
        return None
    return {
        "status": event_status_code(page),
        "start_at": iso(page.event_start_at),
        "end_at": iso(page.event_end_at),
        "is_online": page.event_is_online,
        "location": page.event_location,
        "registration": external_ref(page.event_registration_url, page.pk),
    }


def breadcrumb(page):
    """面包屑（IA §10 家族）：首页 → 板块 → 当前页（纯文本 url=null）；
    容器段永不出现。"""
    items = [{"title": "首页", "url": "/"}]
    section_slug = getattr(page, "section_slug", None)
    if section_slug:
        items.append({"title": page.section_title, "url": f"/{section_slug}/"})
    items.append({"title": page.title, "url": None})
    return items


def carousel_entry(entry):
    """CarouselEntry（消费 home.models._carousel_entries 的既有字典）。"""
    cover = entry["cover"]
    data = dict(entry)
    data["cover"] = image_ref(cover, RENDITION_CAROUSEL, alt="") if cover else None
    return data


def campus_news_entry(page):
    """CampusNewsEntry（单条构造复用 home.models._campus_news_entry，
    追加 type/id 两契约键；cover 归 fill-800x520）。"""
    base = _campus_news_entry(page)
    cover = base["cover"]
    return {
        "type": type_identifier(type(page)),
        "id": page.pk,
        "title": base["title"],
        "href": base["href"],
        "cover": image_ref(cover, RENDITION_NEWS, alt="") if cover else None,
        "summary": base["summary"],
        "section_slug": base["section_slug"],
        "department": base["department"],
        "published_at": iso(base["date"]),
        "event_status": EVENT_STATUS_CODES.get(base["event_status"]),
    }


def campus_news_pages(featured_entries, latest_notices, upcoming_events):
    """快讯组稿选择（镜像 home.models._campus_news_entries 的确定性规则：
    已结束活动不入轨 → pk 去重先到先得 → 上限 CAMPUS_NEWS_MAX_ITEMS）。

    ponytail: 与 _campus_news_entries 的选择循环字面同构——该函数返回展示
    字典不含页面引用，API 侧需 type/id；规则为冻结常量，漂移由契约测试
    把守（v1 若改组稿规则需同步此处）。
    """
    pages = []
    seen = set()
    for page in (*featured_entries, *latest_notices, *upcoming_events):
        if getattr(page, "event_status", None) == EventFieldsMixin.STATUS_ENDED:
            continue
        if page.pk in seen:
            continue
        seen.add(page.pk)
        pages.append(page)
        if len(pages) == CAMPUS_NEWS_MAX_ITEMS:
            break
    return pages


def page_detail_data(page, preview=False):
    """E6/E9 详情判别联合（PageDetailBase＋逐型差异）；preview=True 加
    顶层 preview:true（PreviewMarker，正式页响应无此字段）。expired 按页
    面数据如实填充（E6 经路由判定放行，E9 可见性谓词不适用）。"""
    department = getattr(page, "department", None)
    section_slug = getattr(page, "section_slug", None)
    data = {
        "type": type_identifier(type(page)),
        "id": page.pk,
        "title": page.title,
        "slug": page.slug,
        "url": page.url,
        "section": {"slug": section_slug, "title": page.section_title} if section_slug else None,
        "department": {"name": department.name, "slug": department.slug} if department else None,
        "first_published_at": iso(page.first_published_at),
        "last_published_at": iso(page.last_published_at),
        "expire_at": iso(page.expire_at),
        "noindex": bool(page.noindex),
        "expired": bool(page.expired),
        "cover": cover_ref(page),
        "breadcrumb": breadcrumb(page),
    }
    kind = data["type"]
    if kind in ("notice", "article"):
        data.update(
            summary=page.summary,
            event=event_info(page),
            body=body_blocks(page),
            attachments=attachments_ref(page),
            external=external_ref(page.external_url, page.pk),
            tags=[tag.name for tag in page.tags.all()],
        )
    elif kind == "material":
        data.update(
            summary=page.summary,
            discipline=page.discipline.name,
            material_type=page.material_type.name,
            body=body_blocks(page),
            attachments=attachments_ref(page),
            external=external_ref(page.external_url, page.pk),
            tags=[tag.name for tag in page.tags.all()],
        )
    elif kind == "software":
        data.update(
            platforms=[platform.name for platform in page.platforms.all()],
            source=external_ref(page.source_url, page.pk),
            license_note=page.license_note,
            body=body_blocks(page),
        )
    elif kind == "guide":
        data.update(
            category=page.category.name,
            location=page.location,
            opening_hours=page.opening_hours,
            contact=page.contact,
            extra_notes=page.extra_notes,
            responsible_party=page.responsible_party,
            maintenance_mode=page.maintenance_mode,
            maintenance_mode_label=page.get_maintenance_mode_display(),
            last_confirmed_on=iso(page.last_confirmed_on),
        )
    if preview:
        data["preview"] = True
    return data


def sitemap_entry(location, lastmod):
    return {"loc": location, "lastmod": iso(lastmod)}
