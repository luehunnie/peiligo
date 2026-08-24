"""A3.1/A3.2 内容模型测试公共脚手架（仅测试数据构造，pytest 外不收集）。

按任务批令：测试数据只在 pytest 中产生，禁批量假业务数据入库。
"""

import datetime as dt
import json
from io import StringIO

from departments.models import Department, DepartmentContainerPage
from django.core.management import call_command
from django.utils import timezone
from home.models import SectionPage


def build_sections():
    """五板块就位（bootstrap 幂等），返回 slug → SectionPage 映射。"""
    call_command("bootstrap_sections", stdout=StringIO())
    return {s.slug: s for s in SectionPage.objects.all()}


def make_department(name, slug):
    return Department.objects.create(name=name, slug=slug)


def make_container(section, department):
    """在板块下挂一个绑定部门的已发布容器（clean 合法路径）。"""
    container = DepartmentContainerPage(
        title=f"{department.name}·{section.title}", slug=department.slug, department=department
    )
    section.add_child(instance=container)
    container.save_revision().publish()
    return container


def body_json(paragraphs=1):
    """最小合法正文 StreamField JSON（模型直建/StreamValue 路径，min_num=1）。"""
    return json.dumps(
        [{"type": "paragraph", "value": "<p>测试正文段落。</p>"} for _ in range(paragraphs)]
    )


def _contentstate_json(text):
    """Draftail 编辑器提交的 contentstate JSON（RichTextBlock 表单值格式）。"""
    return json.dumps(
        {
            "entityMap": {},
            "blocks": [
                {
                    "key": "test01",
                    "text": text,
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                }
            ],
        }
    )


def body_form_data(prefix="body", paragraphs=1):
    """最小合法正文的后台表单分片格式（StreamBlock.value_from_datadict 口径：
    count＋逐块 order/deleted/type/value 分片键，value 为 contentstate JSON）。"""
    data = {f"{prefix}-count": str(paragraphs)}
    for i in range(paragraphs):
        data[f"{prefix}-{i}-deleted"] = ""
        data[f"{prefix}-{i}-order"] = str(i)
        data[f"{prefix}-{i}-type"] = "paragraph"
        data[f"{prefix}-{i}-value"] = _contentstate_json("测试正文段落。")
    return data


def notice_data(container, **overrides):
    """NoticePage 后台编辑表单最小合法 data（chronicle 板块口径）。"""
    data = {
        "title": "测试通知",
        "slug": "test-notice",
        "summary": "测试摘要",
        "department": str(container.department_id),
        "expire_at": "2026-12-31 23:59:59",
        **body_form_data(),
    }
    data.update(overrides)
    return data


def article_data(container, **overrides):
    data = {
        "title": "测试文章",
        "slug": "test-article",
        "summary": "测试摘要",
        "department": str(container.department_id),
        **body_form_data(),
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# A3.2（M3.3）：五类内容页 ORM 级构造器——状态机/发布窗口/删除政策测试用。
# 直接构造＋add_child＋可选 save_revision/publish，绕开编辑表单细节；
# 时间值一律相对 timezone.now() 构造（避免固定日期随真实时间失效）。
# ---------------------------------------------------------------------------


def future(days=30):
    return timezone.now() + dt.timedelta(days=days)


def past(days=1):
    return timezone.now() - dt.timedelta(days=days)


def _save(page, container, publish=False, schedule_at=None):
    """入树＋按需发布/预约（E1/E2 的 ORM 等价路径）。

    live 初值显式置 False（对齐后台"存草稿"语义——admin CreateView 同样
    显式置 False，create.py；ORM 默认 True 不适用于草稿态 S0）。
    """
    page.live = False
    container.add_child(instance=page)
    if schedule_at is not None:
        page.go_live_at = schedule_at
    revision = page.save_revision()
    if publish or schedule_at is not None:
        revision.publish()
    page.refresh_from_db()
    return page


def make_notice(container, *, slug="notice-t", title="测试通知", expire_at=None, **kwargs):
    from notices.models import NoticePage

    return _save(
        NoticePage(
            title=title,
            slug=slug,
            summary="测试摘要",
            department=container.department,
            expire_at=expire_at if expire_at is not None else future(),
            body=json.loads(body_json()),
        ),
        container,
        **kwargs,
    )


def make_article(container, *, slug="article-t", title="测试文章", expire_at=None, **kwargs):
    from notices.models import ArticlePage

    return _save(
        ArticlePage(
            title=title,
            slug=slug,
            summary="测试摘要",
            department=container.department,
            expire_at=expire_at,
            body=json.loads(body_json()),
        ),
        container,
        **kwargs,
    )


def make_material(container, *, slug="material-t", title="测试资料", **kwargs):
    from resources.models import Discipline, MaterialPage, MaterialType

    return _save(
        MaterialPage(
            title=title,
            slug=slug,
            summary="测试摘要",
            department=container.department,
            discipline=Discipline.objects.get_or_create(name="计算机科学")[0],
            material_type=MaterialType.objects.get_or_create(name="课件")[0],
            body=json.loads(body_json()),
        ),
        container,
        **kwargs,
    )


def make_software(container, *, slug="software-t", title="测试工具", **kwargs):
    from resources.models import Platform, SoftwareToolPage

    return _save(
        SoftwareToolPage(
            title=title,
            slug=slug,
            department=container.department,
            platforms=[Platform.objects.get_or_create(name="Windows")[0]],
            source_url="https://example.com/tool",
            license_note="校园授权，免费使用",
            body=json.loads(body_json()),
        ),
        container,
        **kwargs,
    )


def make_guide(container, *, slug="guide-t", title="测试指南", **kwargs):
    from guides.models import GuideCategory, GuidePage

    return _save(
        GuidePage(
            title=title,
            slug=slug,
            department=container.department,
            category=GuideCategory.objects.get_or_create(name="服务地点")[0],
            location="第一教学楼一层",
            opening_hours="工作日 8:00–17:00",
            contact="0000-0000000",
            responsible_party="教务处",
            maintenance_mode="self",
            last_confirmed_on=timezone.now().date(),
        ),
        container,
        **kwargs,
    )
