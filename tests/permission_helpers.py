"""M4.4 权限矩阵测试（T01–T16 迁移）公共脚手架。

场景经正式实现重建（区别于 M4.3 丢弃式执行器 t16/run_t16.py）：

- 组/GPP/GCP/集合骨架由 ``init_permissions`` 管理命令生成——被测对象
  即正式配置载体，而非测试内联 ORM 拼装；
- 删除守卫即 ``departments/wagtail_hooks.py`` 正式钩子（app 装载即生效，
  无运行时注册）；
- 断言口径沿用 M4.3：拒绝以**零库变更快照为主证**（字段/live/最新修订
  pk/修订数/日志/树结构/GPP/GCP/用户/集合等），HTTP 302 仅辅证——拒权
  与成功同为 302，凭状态码不可区分（矩阵 §3.6）。

测试数据只在 pytest 中产生（任务批令），TestCase 事务回滚自清、可重复。
"""

import io
import json
import tempfile
from collections.abc import Iterable

from departments.models import Department, DepartmentContainerPage
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from guides.models import GuideCategory
from home.models import FeaturedItem, SectionPage, SiteSettings
from notices.models import Tag
from resources.models import Discipline, MaterialType, Platform
from wagtail.images.models import Image
from wagtail.models import (
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Page,
    PageLogEntry,
    Revision,
    Site,
)

# 测试口令（仅测试数据；正式口令只经 env/stdin，见 init_permissions）
PASSWORD = "t44-pass-12345"

SECTION_SLUGS = ("chronicle", "events", "materials", "software", "guide")


# ---------------------------------------------------------------------------
# 场景播种（对齐 M4.3 t16 seed；组配置走正式 init_permissions 命令）
# ---------------------------------------------------------------------------


def build_permission_world() -> dict:
    """五板块＋两部门容器树＋正式权限骨架＋三账号＋基础词表/样例页。

    部门 A 建满五板块容器（T01 六类创建所需）；部门 B 建 chronicle/
    materials 两容器。返回测试上下文 dict（页面/组/集合/账号等句柄）。
    """
    call_command("bootstrap_sections", stdout=io.StringIO())
    sections = {s.slug: s for s in SectionPage.objects.all()}

    dept_a = Department.objects.create(name="教务处", slug="jwc-a")
    dept_b = Department.objects.create(name="学生处", slug="xsc-b")

    def add_container(section, dept):
        container = DepartmentContainerPage(
            title=f"{dept.name}·{section.title}", slug=dept.slug, department=dept
        )
        section.add_child(instance=container)
        return container

    a_containers = {slug: add_container(sections[slug], dept_a) for slug in SECTION_SLUGS}
    b_chron = add_container(sections["chronicle"], dept_b)
    b_mat = add_container(sections["materials"], dept_b)

    # 正式权限骨架（被测配置载体）：三组＋GPP@容器＋GCP@集合＋默认组清理
    call_command("init_permissions", stdout=io.StringIO())

    coll_a = Collection.objects.get(name=dept_a.name)
    coll_b = Collection.objects.get(name=dept_b.name)
    group_admins = Group.objects.get(name="总管理员")
    group_a = Group.objects.get(name=f"dept-{dept_a.slug}")
    group_b = Group.objects.get(name=f"dept-{dept_b.slug}")

    def mk_user(username, group):
        user = get_user_model().objects.create_user(
            username=username, password=PASSWORD, is_staff=False, is_active=True
        )
        user.groups.add(group)
        return user

    admin = mk_user("t44-admin", group_admins)  # 纯组权限行权（非 superuser）
    user_a = mk_user("t44-dept-a", group_a)
    user_b = mk_user("t44-dept-b", group_b)

    # 词表（建页/受控标签选用所需）
    discipline = Discipline.objects.create(name="计算机科学", sort_order=1)
    material_type = MaterialType.objects.create(name="课件", sort_order=1)
    platform = Platform.objects.create(name="Windows", sort_order=1)
    guide_category = GuideCategory.objects.create(name="服务地点", sort_order=1)
    tag = Tag.objects.create(name="注册流程", slug="t44-tag")

    site = Site.objects.get(is_default_site=True)
    settings_obj, _ = SiteSettings.objects.get_or_create(site=site)

    # B 的样例页：一草稿一已发布（T06/T07 越权对象）
    from notices.models import NoticePage

    from .helpers import future

    def mk_notice(title, slug, owner, dept, container, live):
        page = NoticePage(
            title=title,
            slug=slug,
            owner=owner,
            department=dept,
            summary="测试摘要",
            expire_at=future(days=365),
        )
        page.live = False  # 对齐后台"存草稿"语义（helpers._save 同口径）
        container.add_child(instance=page)
        revision = page.save_revision(user=owner)
        if live:
            revision.publish(user=owner)
        page.refresh_from_db()
        return page

    page_b_live = mk_notice("B部门已发布通知", "t44-b-live", user_b, dept_b, b_chron, True)
    page_b_draft = mk_notice("B部门草稿通知", "t44-b-draft", user_b, dept_b, b_chron, False)

    # B 集合既有素材（T13③ 越权编辑对象）——真实 PNG 落临时 MEDIA_ROOT
    # （Wagtail Image.save 会读文件算元数据；测试文件不入仓库 media/）
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import override_settings

    with tempfile.TemporaryDirectory(prefix="t44-media-") as media_tmp:
        with override_settings(MEDIA_ROOT=media_tmp):
            img_b = Image(title="B集合素材", uploaded_by_user=user_b, collection=coll_b)
            img_b.file = SimpleUploadedFile("t44-b.png", png_bytes(), content_type="image/png")
            img_b.save()

    return {
        "sections": sections,
        "dept_a": dept_a,
        "dept_b": dept_b,
        "a_containers": a_containers,
        "b_chron": b_chron,
        "b_mat": b_mat,
        "group_admins": group_admins,
        "group_a": group_a,
        "group_b": group_b,
        "coll_a": coll_a,
        "coll_b": coll_b,
        "admin": admin,
        "user_a": user_a,
        "user_b": user_b,
        "discipline": discipline,
        "material_type": material_type,
        "platform": platform,
        "guide_category": guide_category,
        "tag": tag,
        "site": site,
        "site_settings": settings_obj,
        "page_b_live": page_b_live,
        "page_b_draft": page_b_draft,
        "img_b": img_b,
    }


# ---------------------------------------------------------------------------
# 零库变更快照（M4.3 断言主证口径的移植）
# ---------------------------------------------------------------------------


def permission_snapshot() -> dict:
    """权限越权面相关全库关键状态快照（"零库变更"断言主证）。

    覆盖：页面（title/slug/live/expired/owner/path/depth/numchild/最新修订
    pk/修订数）、各表计数、GPP/GCP 挂载、用户组归属、图片集合归属、
    站点设置值、URL 变更重定向。
    """
    from wagtail.contrib.redirects.models import Redirect

    pages = {}
    for p in Page.objects.all():
        latest_rev = p.revisions.order_by("-pk").first()
        pages[p.id] = (
            p.title,
            p.slug,
            p.live,
            p.expired,
            p.owner_id,
            p.path,
            p.depth,
            p.numchild,
            latest_rev.pk if latest_rev else None,
            p.revisions.count(),
        )
    settings_obj = SiteSettings.objects.first()
    return {
        "pages": pages,
        "counts": {
            "page": Page.objects.count(),
            "revision": Revision.objects.count(),
            "page_log": PageLogEntry.objects.count(),
            "user": get_user_model().objects.count(),
            "group": Group.objects.count(),
            "grouppagepermission": GroupPagePermission.objects.count(),
            "groupcollectionpermission": GroupCollectionPermission.objects.count(),
            "collection": Collection.objects.count(),
            "department": Department.objects.count(),
            "tag": Tag.objects.count(),
            "discipline": Discipline.objects.count(),
            "materialtype": MaterialType.objects.count(),
            "platform": Platform.objects.count(),
            "guidecategory": GuideCategory.objects.count(),
            "featureditem": FeaturedItem.objects.count(),
            "image": Image.objects.count(),
        },
        "gpp": sorted(
            (g.group.name, g.page_id, g.permission.codename)
            for g in GroupPagePermission.objects.select_related("group", "permission")
        ),
        "gcp": sorted(
            (g.group.name, g.collection_id, g.permission.codename)
            for g in GroupCollectionPermission.objects.select_related("group", "permission")
        ),
        "users": {
            u.username: (
                u.is_active,
                u.is_superuser,
                sorted(u.groups.values_list("name", flat=True)),
            )
            for u in get_user_model().objects.all()
        },
        "images": {
            i.id: (i.title, i.collection_id, i.uploaded_by_user_id) for i in Image.objects.all()
        },
        "settings": (
            settings_obj.alert_text,
            settings_obj.feedback_email,
        )
        if settings_obj
        else None,
        "redirects": sorted(
            (r.old_path, r.site_id, r.redirect_link or "", r.is_permanent)
            for r in Redirect.objects.all()
        ),
    }


def snapshot_diff(a: dict, b: dict) -> str:
    """两份快照的差异描述（空串 = 零变更）。"""
    parts = []
    for key in ("pages", "counts", "gpp", "gcp", "users", "images", "settings", "redirects"):
        if a[key] != b[key]:
            if key == "pages":
                gone = set(a[key]) - set(b[key])
                new = set(b[key]) - set(a[key])
                changed = {k for k in set(a[key]) & set(b[key]) if a[key][k] != b[key][k]}
                parts.append(
                    f"pages: 消失={sorted(gone)} 新增={sorted(new)} 变更={sorted(changed)}"
                )
            else:
                parts.append(f"{key}: {a[key]} -> {b[key]}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# 客户端与通用断言 helper
# ---------------------------------------------------------------------------


def login_client(user) -> Client:
    client = Client()
    assert client.login(username=user.username, password=PASSWORD), f"登录失败：{user.username}"
    return client


def bulk_delete_url(*page_ids) -> str:
    """后台列表批量删除入口形态（勾选 id 经查询串，M4.2 实测口径）。"""
    url = reverse("wagtail_bulk_action", args=["wagtailcore", "page", "delete"])
    return url + "?" + "&".join(f"id={i}" for i in page_ids)


def rev_count(page_id: int) -> int:
    """修订数直查 Revision 表（实例 revisions 管理器有结果缓存）。"""
    return Revision.objects.filter(object_id=page_id).count()


def denied_post(testcase, client, url, data, msg=""):
    """越权 POST 断言：零库变更为主证（快照含字段/live/修订/日志/树结构）。"""
    before = permission_snapshot()
    resp = client.post(url, data)
    diff = snapshot_diff(before, permission_snapshot())
    testcase.assertEqual(diff, "", f"预期零库变更：{msg or url}；实际 diff：{diff}")
    return resp


def denied_get(testcase, client, url, msg=""):
    """越权 GET 断言：非 200（GET 200＝表单可达＝越权信号，矩阵 §3.6）＋零库变更。"""
    before = permission_snapshot()
    resp = client.get(url)
    diff = snapshot_diff(before, permission_snapshot())
    testcase.assertNotEqual(resp.status_code, 200, f"GET 不应可达：{msg or url}")
    testcase.assertEqual(diff, "", f"预期零库变更：{msg or url}；实际 diff：{diff}")
    return resp


def search_hit(client, query: str, needle: str) -> bool:
    """默认搜索是否命中：needle 用 slug（搜索页回显查询词，标题做 needle 会误判）。"""
    resp = client.get("/search/", {"q": query})
    return resp.status_code == 200 and needle in resp.content.decode()


def png_bytes() -> bytes:
    """1×1 PNG（Pillow 现生成；T13 上传用）。"""
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (1, 1), (200, 60, 60)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 表单数据构造（后台编辑表单官方字段集；ContentState JSON 口径见矩阵 §3.6）
# ---------------------------------------------------------------------------


def comment_formset_zeros() -> dict:
    return {
        "comments-TOTAL_FORMS": "0",
        "comments-INITIAL_FORMS": "0",
        "comments-MIN_NUM_FORMS": "0",
        "comments-MAX_NUM_FORMS": "1000",
    }


def contentstate(text: str) -> str:
    """Draftail ContentState JSON（RichTextBlock 表单值的真实格式）。"""
    return json.dumps(
        {
            "entityMap": {},
            "blocks": [
                {
                    "key": "t44000",
                    "text": text,
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                }
            ],
        },
        ensure_ascii=False,
    )


def stream_body(text: str) -> dict:
    """StreamField 表单提交格式（count/deleted/order/type/value 分片字段）。"""
    return {
        "body-count": "1",
        "body-0-deleted": "",
        "body-0-order": "0",
        "body-0-type": "paragraph",
        "body-0-value": contentstate(text),
    }


def notice_form(
    title, slug, dept_id, summary="测试摘要", event=False, tags: Iterable | None = None
) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": summary,
        **stream_body("测试正文段落。"),
        "external_url": "",
        "event_start_at": "2026-12-01 09:00" if event else "",
        "event_end_at": "2026-12-01 17:00" if event else "",
        "event_location": "测试活动地点" if event else "",
        "event_is_online": "",
        "event_registration_url": "",
        "go_live_at": "",
        "expire_at": "2027-12-31 23:59",
    }
    if tags:
        data["tags"] = [str(t) for t in tags]
    data.update(comment_formset_zeros())
    return data


def article_form(title, slug, dept_id, summary="测试文章摘要") -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": summary,
        **stream_body("测试文章正文。"),
        "external_url": "",
        "event_start_at": "",
        "event_end_at": "",
        "event_location": "",
        "event_is_online": "",
        "event_registration_url": "",
        "go_live_at": "",
        "expire_at": "",  # §16.1：文章可选
    }
    data.update(comment_formset_zeros())
    return data


def material_form(title, slug, dept_id, disc_id, mtype_id) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": "测试学习资料摘要",
        **stream_body("测试学习资料正文。"),
        "discipline": str(disc_id),
        "material_type": str(mtype_id),
        "external_url": "",
        "expire_at": "",  # §16.1：常青内容强制空
    }
    data.update(comment_formset_zeros())
    return data


def software_form(title, slug, dept_id, platform_ids) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        **stream_body("测试软件工具正文。"),
        "source_url": "https://example.com/t44",
        "license_note": "测试授权说明",
        "expire_at": "",  # §16.1：强制空
    }
    if platform_ids:
        data["platforms"] = [str(p) for p in platform_ids]
    data.update(comment_formset_zeros())
    return data


def guide_form(title, slug, dept_id, category_id) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "category": str(category_id),
        "location": "测试地点",
        "opening_hours": "周一至周五 09:00-17:00",
        "contact": "测试联系方式",
        "extra_notes": "",
        "responsible_party": "测试责任单位",
        "maintenance_mode": "self",
        "last_confirmed_on": "2026-08-27",
        "expire_at": "",  # §16.1：指南不设
    }
    data.update(comment_formset_zeros())
    return data


def add_url(app_label, model_name, parent_id) -> str:
    return reverse("wagtailadmin_pages:add", args=[app_label, model_name, parent_id])
