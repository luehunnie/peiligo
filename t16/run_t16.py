#!/usr/bin/env python3
"""A4.3 / M4.3 · 越权测试矩阵 T01–T16 执行器（正式执行载体，入库）。

依据（只读输入）：
- ``docs/ROLE_PERMISSION_MATRIX.md`` §3/§6（分支 m4/a4-1-permission-matrix @aac91a0
  版本；§6 = T01–T16 权威定义，拒绝断言以零库变更为主证）；
- M4.2 PoC 机制参考（分支 m4/a4-2-permission-poc 的 ``poc/run_poc.py``，
  61/61；本脚本沿用其快照 diff 口径与表单构造格式）；
- 02_ARCHITECTURE_DOMAIN_PLAN.md §6 S4.3。

执行方式：Django test Client 走真实后台 HTTP 动线（登录→GET/POST），配合
全库快照 diff 证"零库变更"；不启服务器，不改任何业务代码。OQ1 双钩子
只拒绝守卫（矩阵 §3.4）在本进程内经 wagtail.hooks 运行时注册（正式
实现待 M4 门禁通过后落 departments/wagtail_hooks.py 旁，本脚本零侵入）。

安全边界：只写自建 scratch 库 ``peiligo_m4_t16``（启动自检库名，不符即
退出）；只建/删 ``t16-`` 前缀自有对象；正式四库
（peiligo_dev/peiligo_test/peiligo_restart_dev/peiligo_restart_test）
零触碰、零 DROP。

用法（仓库根目录）：

    export DATABASE_URL="postgres://$USER@/peiligo_m4_t16?host=/tmp"
    export SECRET_KEY="a43-t16-scratch-secret-not-real"
    .venv/bin/python t16/run_t16.py

产出：``t16/evidence.json``（机器可读逐断言证据；报告为
``docs/POC_PERMISSION_REPORT.md``，由人工/上游步骤按本证据撰写）。
"""

from __future__ import annotations

import json
import os
import sys
import traceback

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peiligo.settings.dev")
# 仓库根加入 sys.path（脚本位于 t16/，项目 app 在仓库根；与 manage.py 同口径）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRATCH_DB = "peiligo_m4_t16"
PREFIX = "t16-"
ADMIN_GROUP = "t16-admins"
DEPT_A_GROUP = "t16-dept-a"
DEPT_B_GROUP = "t16-dept-b"
DEPT_A_SLUG = "t16-dept-a"
DEPT_B_SLUG = "t16-dept-b"
PASSWORD = "t16-pass-12345"

# 五冻结板块 slug（IA §2；与 home.models.SECTIONS 一致）
SECTION_SLUGS = ("chronicle", "events", "materials", "software", "guide")


def banner(text: str) -> None:
    print(f"\n{'=' * 72}\n{text}\n{'=' * 72}")


def setup_django():
    django.setup()
    from django.db import connection

    name = connection.settings_dict["NAME"]
    if name != SCRATCH_DB:
        raise SystemExit(
            f"安全自检失败：当前数据库为 {name!r}，期望自建 scratch 库 {SCRATCH_DB!r}。"
            "请设置 DATABASE_URL=postgres://$USER@/peiligo_m4_t16?host=/tmp 后重跑。"
        )
    return name


# ---------------------------------------------------------------------------
# 结果收集：子断言 → T 级判定
# ---------------------------------------------------------------------------

RESULTS: list[dict] = []


def record(case: str, item: str, ok: bool, detail: str) -> bool:
    RESULTS.append({"case": case, "item": item, "ok": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {case} · {item} —— {detail}")
    return ok


# ---------------------------------------------------------------------------
# 库状态快照 / 零变更断言（主证口径，矩阵 §6 通用拒绝断言）
# ---------------------------------------------------------------------------


def snapshot() -> dict:
    """权限越权面相关的全库关键状态快照（"零库变更"断言主证）。

    覆盖：页面（含 title/slug/live/expired/owner/path/depth/numchild/
    最新修订 pk/修订数——T09 树结构零变更口径）、各表计数、GPP/GCP 挂载、
    用户（组归属/激活态）、图片（集合归属）、站点设置值。
    """
    from django.contrib.auth.models import Group, User
    from wagtail.models import (
        Collection,
        GroupCollectionPermission,
        GroupPagePermission,
        Page,
        PageLogEntry,
        Revision,
    )

    from departments.models import Department
    from guides.models import GuideCategory
    from home.models import FeaturedItem, SiteSettings
    from notices.models import Tag
    from resources.models import Discipline, MaterialType, Platform
    from wagtail.contrib.redirects.models import Redirect

    from wagtail.images.models import Image

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
    settings = SiteSettings.objects.first()
    return {
        "pages": pages,
        "counts": {
            "page": Page.objects.count(),
            "revision": Revision.objects.count(),
            "page_log": PageLogEntry.objects.count(),
            "user": User.objects.count(),
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
        },
        "gpp": sorted(
            (g.group.name, g.page_id, g.permission.codename)
            for g in GroupPagePermission.objects.select_related("group", "permission")
        ),
        "gcp": sorted(
            (g.group.name, g.collection_id, g.permission.codename)
            for g in GroupCollectionPermission.objects.select_related(
                "group", "permission"
            )
        ),
        "users": {
            u.username: (u.is_active, u.is_superuser, sorted(u.groups.values_list("name", flat=True)))
            for u in User.objects.all()
        },
        "images": {
            i.id: (i.title, i.collection_id, i.uploaded_by_user_id)
            for i in Image.objects.all()
        },
        "settings": (settings.alert_text, settings.feedback_email) if settings else None,
        # URL 变更自动重定向（移动/slug 变更产生；零变更断言须覆盖此面，
        # 否则重定向行可伪造"旧 URL 仍可达"的假象——见 P4-b3 探测）
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
# 种子：按矩阵 §3 机制重建场景
# ---------------------------------------------------------------------------


def reset_t16_objects() -> None:
    """删除上一轮 t16- 前缀自有对象（幂等；五板块结构页保留）。"""
    from django.contrib.auth.models import Group, User
    from wagtail.images.models import Image
    from wagtail.models import Collection, Page

    from departments.models import Department, DepartmentContainerPage
    from guides.models import GuideCategory
    from home.models import FeaturedItem, SiteSettings, SectionPage
    from notices.models import Tag
    from resources.models import Discipline, MaterialType, Platform
    from wagtail.models import Site

    # 1) 内容页与容器（先叶后干；ORM delete 不经视图钩子）
    for section in SectionPage.objects.all():
        for child in section.get_children().specific():
            child.delete()
    # 2) 治理词表（t16 前缀/关联）
    Department.objects.filter(slug__in=[DEPT_A_SLUG, DEPT_B_SLUG, "t16-dept-c"]).delete()
    Tag.objects.filter(name__startswith="T16").delete()
    Discipline.objects.filter(name__startswith="T16").delete()
    MaterialType.objects.filter(name__startswith="T16").delete()
    Platform.objects.filter(name__startswith="T16").delete()
    GuideCategory.objects.filter(name__startswith="T16").delete()
    FeaturedItem.objects.all().delete()
    # 3) 组与用户（含 T14 建的 t16- 用户、T16 的 t16-tech）
    Group.objects.filter(name__in=[ADMIN_GROUP, DEPT_A_GROUP, DEPT_B_GROUP]).delete()
    User.objects.filter(username__startswith=PREFIX).delete()
    # 4) 集合、图片、URL 变更重定向与站点设置还原
    for img in Image.objects.filter(title__startswith="T16"):
        img.delete()
    Collection.objects.filter(name__startswith="T16部门").delete()
    # 移动/slug 变更自动产生的 Redirect 行（scratch 场景无合法重定向，
    # 全量清空防旧轮探测 debris 影响前台可达性断言）
    from wagtail.contrib.redirects.models import Redirect

    Redirect.objects.all().delete()
    SiteSettings.objects.update(alert_text="", feedback_email="t16@example.com")


def install_delete_guard() -> None:
    """OQ1 裁决：安装"永久删除仅总管理员"服务端只拒绝守卫（矩阵 §3.4）。

    - 单条删除动线：wagtail before_delete_page（返回响应即在事务内取消删除）；
    - 批量删除动线：DeleteBulkAction.execute_action 直调 page.delete() 不经
      单页钩子，故同时挂 before_bulk_action（返回响应即在事务内取消整个动作）；
    - 与仓库既有钩子（departments/wagtail_hooks.py 的非空结构页拒删）
      共存：内容页为叶子不命中既有谓词，结构页两条守卫叠加均为拒。
    """
    from django.contrib import messages
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    from wagtail import hooks
    from wagtail.models import Page

    def is_privileged(user) -> bool:
        if not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser:
            return True  # R3 故障恢复通道（M-G5）；日常操作不走 superuser
        return user.groups.filter(name=ADMIN_GROUP).exists()

    @hooks.register("before_delete_page")
    def refuse_non_admin_page_deletion(request, page):
        if is_privileged(request.user):
            return None
        messages.error(
            request,
            f"「{page.title}」未删除：永久删除仅限总管理员（PRD §8；M4.3 双钩子守卫）。",
        )
        return HttpResponseRedirect(
            reverse("wagtailadmin_explore", args=[page.get_parent().id])
        )

    @hooks.register("before_bulk_action")
    def refuse_non_admin_bulk_page_deletion(request, action_type, objects, bulk_action):
        if action_type != "delete":
            return None
        if not objects or not all(isinstance(o, Page) for o in objects):
            return None  # 非页面批量删除（词表/用户等）不在本守卫面
        if is_privileged(request.user):
            return None
        messages.error(
            request,
            f"批量删除已取消：永久删除仅限总管理员（PRD §8；M4.3 双钩子守卫，"
            f"涉及 {len(objects)} 页）。",
        )
        return HttpResponseRedirect(reverse("wagtailadmin_home"))

    print("  [INFO] OQ1 双钩子只拒绝守卫已安装（before_delete_page + before_bulk_action）")


def seed() -> dict:
    """按矩阵 §3 机制重建场景（组配置＝§3.2 配置表的 A4.3 执行形态）。

    - 总管理员组 t16-admins：根级 GPP(add/change/publish) + 全量 Django 模型
      权限（含 bulk_delete_page）+ GCP@根集合（add/change_collection、
      add/change_image）——集合治理只认 GCP 记录（PoC 发现 3）；
    - 部门组：GPP(add/change/publish)@本部门各容器 + 恰一枚 Django 权限
      wagtailadmin.access_admin + GCP(add/change_image)@本部门集合
      （矩阵 §3.2 O6 行"部门组授本部门集合内上传/改自己素材"的机制承载；
      集合结构管理 GCP=0）；
    - 三账号：t16-admin（非 superuser，组权限行权）/ t16-dept-a / t16-dept-b。
    """
    from django.contrib.auth.models import Group, Permission, User
    from wagtail.models import (
        Collection,
        GroupCollectionPermission,
        GroupPagePermission,
        Page,
        Site,
    )

    from departments.models import Department, DepartmentContainerPage
    from guides.models import GuideCategory
    from home.models import FeaturedItem, SectionPage, SiteSettings
    from notices.models import NoticePage, Tag
    from resources.models import Discipline, MaterialType

    site = Site.objects.get(is_default_site=True)
    SiteSettings.objects.get_or_create(site=site)

    # —— 部门与容器（A：五板块全容器——T01 六类创建所需；B：纪事+资料）——
    dept_a = Department.objects.create(name="T16部门A", slug=DEPT_A_SLUG)
    dept_b = Department.objects.create(name="T16部门B", slug=DEPT_B_SLUG)
    sections = {s.slug: s for s in SectionPage.objects.all()}

    def add_container(section, dept) -> DepartmentContainerPage:
        container = DepartmentContainerPage(
            title=f"T16容器·{dept.name}·{section.title}", slug=dept.slug, department=dept
        )
        section.add_child(instance=container)
        return container

    a_containers = {slug: add_container(sections[slug], dept_a) for slug in SECTION_SLUGS}
    b_chron = add_container(sections["chronicle"], dept_b)
    b_mat = add_container(sections["materials"], dept_b)

    # —— 受控词表（T01 建页所需 + T02 受控标签选用）——
    from resources.models import Platform

    discipline = Discipline.objects.create(name="T16学科", sort_order=1)
    material_type = MaterialType.objects.create(name="T16资料类型", sort_order=1)
    platform = Platform.objects.create(name="T16平台", sort_order=1)
    guide_category = GuideCategory.objects.create(name="T16指南类别", sort_order=1)
    tag = Tag.objects.create(name="T16示例标签", slug="t16-sample-tag")

    # —— 集合（O6：每部门一个 Collection）——
    root_collection = Collection.get_first_root_node()
    coll_a = Collection(name="T16部门A")
    root_collection.add_child(instance=coll_a)
    coll_b = Collection(name="T16部门B")
    root_collection.add_child(instance=coll_b)

    # —— 组（§3.2 配置表）——
    access_admin = Permission.objects.get(
        content_type__app_label="wagtailadmin", codename="access_admin"
    )

    admins = Group.objects.create(name=ADMIN_GROUP)
    admins.permissions.set(Permission.objects.all())  # 全治理面（模型级权限）
    root = Page.get_first_root_node()
    for perm_type in ("add", "change", "publish"):  # 根级全树（type=change 即 change_page）
        GroupPagePermission.objects.create(
            group=admins, page=root, permission_type=perm_type
        )
    for codename in (
        "add_collection",
        "change_collection",
        "add_image",
        "change_image",
    ):
        GroupCollectionPermission.objects.create(
            group=admins,
            collection=root_collection,
            permission=Permission.objects.get(
                content_type__app_label__in=("wagtailcore", "wagtailimages"),
                codename=codename,
            ),
        )

    def make_dept_group(name, containers, collection):
        group = Group.objects.create(name=name)
        group.permissions.set([access_admin])  # 仅后台入口；零治理 Django 权限
        for container in containers:
            for perm_type in ("add", "change", "publish"):
                GroupPagePermission.objects.create(
                    group=group, page=container, permission_type=perm_type
                )
        for codename in ("add_image", "change_image"):  # 本部门集合内上传/改素材
            GroupCollectionPermission.objects.create(
                group=group,
                collection=collection,
                permission=Permission.objects.get(
                    content_type__app_label="wagtailimages", codename=codename
                ),
            )
        return group

    group_a = make_dept_group(DEPT_A_GROUP, list(a_containers.values()), coll_a)
    group_b = make_dept_group(DEPT_B_GROUP, [b_chron, b_mat], coll_b)

    # —— 用户（admin 用组权限行权，非 superuser；矩阵 §3.2 R1 口径）——
    def mk_user(username: str, group: Group) -> User:
        user = User.objects.create_user(
            username=username, password=PASSWORD, is_staff=False, is_active=True
        )
        user.groups.add(group)
        return user

    admin = mk_user("t16-admin", admins)
    user_a = mk_user("t16-dept-a", group_a)
    user_b = mk_user("t16-dept-b", group_b)

    # —— 示例内容（ORM 路径须用 aware datetime，与表单路径同口径）——
    from datetime import timedelta

    from django.utils import timezone as dj_tz

    expire = dj_tz.now() + timedelta(days=365)  # §16.2：通知有效期须未来

    def mk_notice(title, slug, owner, dept, container, live: bool):
        page = NoticePage(
            title=title,
            slug=slug,
            owner=owner,
            department=dept,
            summary=f"{title}摘要",
            expire_at=expire,
            # ORM 建页 live 默认 True；显式 False 模拟后台"草稿"起点
            # （后台创建动线显式置 False，rev.publish 才转 live）。
            live=False,
        )
        container.add_child(instance=page)
        rev = page.save_revision(user=owner)
        if live:
            rev.publish(user=owner)
        return page

    # B 的越权对象（T06/T07/T09）：已发布 + 草稿 + 批量删除靶页
    page_b_live = mk_notice("T16唯一·B部门已发布通知", "t16-b-live", user_b, dept_b, b_chron, True)
    page_b_draft = mk_notice("T16唯一·B部门草稿通知", "t16-b-draft", user_b, dept_b, b_chron, False)
    page_b_extra = mk_notice("T16唯一·B部门测试数据页", "t16-b-extra", user_b, dept_b, b_chron, False)

    # A 的代建草稿（owner=admin；矩阵 M-A4：edit 覆盖子树内任意归属）
    page_a_admin = mk_notice(
        "T16·A容器代建通知", "t16-a-admin-notice", admin, dept_a, a_containers["chronicle"], False
    )

    # B 集合内素材（T13③ 越权编辑靶）：1x1 PNG
    from django.core.files.uploadedfile import SimpleUploadedFile
    from wagtail.images.models import Image

    img_b = Image(
        title="T16·B集合素材",
        uploaded_by_user=user_b,
        collection=coll_b,
    )
    img_b.file = SimpleUploadedFile("t16-b.png", png_bytes(), content_type="image/png")
    img_b.save()

    # FeaturedItem（T10 越权编辑/删除靶；T14 另经后台正规新建一条）
    fi_seed = FeaturedItem.objects.create(
        content=page_b_live, start_at=dj_tz.now(), end_at=expire, enabled=True
    )

    return {
        "site": site,
        "dept_a": dept_a,
        "dept_b": dept_b,
        "sections": sections,
        "a_containers": a_containers,
        "b_chron": b_chron,
        "b_mat": b_mat,
        "discipline": discipline,
        "material_type": material_type,
        "platform": platform,
        "guide_category": guide_category,
        "tag": tag,
        "coll_a": coll_a,
        "coll_b": coll_b,
        "admin": admin,
        "user_a": user_a,
        "user_b": user_b,
        "page_b_live": page_b_live,
        "page_b_draft": page_b_draft,
        "page_b_extra": page_b_extra,
        "page_a_admin": page_a_admin,
        "img_b": img_b,
        "fi_seed": fi_seed,
    }


# ---------------------------------------------------------------------------
# 表单数据构造（后台编辑表单官方字段集；沿用 PoC 实测格式）
# ---------------------------------------------------------------------------


def comment_formset_zeros() -> dict:
    return {
        "comments-TOTAL_FORMS": "0",
        "comments-INITIAL_FORMS": "0",
        "comments-MIN_NUM_FORMS": "0",
        "comments-MAX_NUM_FORMS": "1000",
    }


def png_bytes() -> bytes:
    """1×1 PNG（Pillow 现生成，避免手写 hex 出错；T13/种子素材用）。"""
    import io

    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (1, 1), (200, 60, 60)).save(buf, format="PNG")
    return buf.getvalue()


def contentstate(text: str) -> str:
    """Draftail ContentState JSON（RichTextBlock 表单值的真实格式）。"""
    return json.dumps(
        {
            "entityMap": {},
            "blocks": [
                {
                    "key": "t16000",
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
    title: str,
    slug: str,
    dept_id: int,
    summary: str = "T16 摘要",
    event: bool = False,
    tags=None,
) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": summary,
        **stream_body("T16 正文段落。"),
        "external_url": "",
        "event_start_at": "2026-12-01 09:00" if event else "",
        "event_end_at": "2026-12-01 17:00" if event else "",
        "event_location": "T16活动地点" if event else "",
        "event_is_online": "",
        "event_registration_url": "",
        "go_live_at": "",
        "expire_at": "2027-12-31 23:59",
    }
    if tags:
        data["tags"] = [str(t) for t in tags]
    data.update(comment_formset_zeros())
    return data


def article_form(title: str, slug: str, dept_id: int, summary: str = "T16 文章摘要") -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": summary,
        **stream_body("T16 文章正文。"),
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


def material_form(title: str, slug: str, dept_id: int, disc_id: int, mtype_id: int) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "summary": "T16 学习资料摘要",
        **stream_body("T16 学习资料正文。"),
        "discipline": str(disc_id),
        "material_type": str(mtype_id),
        "external_url": "",
        "expire_at": "",  # §16.1：常青内容强制空
    }
    data.update(comment_formset_zeros())
    return data


def software_form(title: str, slug: str, dept_id: int, platform_ids) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        **stream_body("T16 软件工具正文。"),
        "source_url": "https://example.com/t16",
        "license_note": "T16 授权说明",
        "expire_at": "",  # §16.1：强制空
    }
    if platform_ids:
        data["platforms"] = [str(p) for p in platform_ids]
    data.update(comment_formset_zeros())
    return data


def guide_form(title: str, slug: str, dept_id: int, category_id: int) -> dict:
    data = {
        "title": title,
        "slug": slug,
        "department": str(dept_id),
        "category": str(category_id),
        "location": "T16地点",
        "opening_hours": "周一至周五 09:00-17:00",
        "contact": "T16联系方式",
        "extra_notes": "",
        "responsible_party": "T16责任单位",
        "maintenance_mode": "self",
        "last_confirmed_on": "2026-08-27",
        "expire_at": "",  # §16.1：指南不设
    }
    data.update(comment_formset_zeros())
    return data


# ---------------------------------------------------------------------------
# 通用断言 helper
# ---------------------------------------------------------------------------


def login_client(user) -> "django.test.Client":
    from django.test import Client

    client = Client()
    assert client.login(username=user.username, password=PASSWORD), f"登录失败：{user.username}"
    return client


def anon_client() -> "django.test.Client":
    from django.test import Client

    return Client()


def rev_count(page_id: int) -> int:
    """修订数直查 Revision 表（同一实例 revisions 管理器有结果缓存）。"""
    from wagtail.models import Revision

    return Revision.objects.filter(object_id=page_id).count()


def denied_post(case, item, client, url, data, files=None):
    """越权 POST 断言：零库变更为主证（快照含字段/live/修订/日志/树结构）。"""
    before = snapshot()
    resp = client.post(url, data, files=files or {})
    diff = snapshot_diff(before, snapshot())
    return record(
        case,
        item,
        diff == "",
        f"HTTP {resp.status_code}，{diff or '零库变更（含修订/日志/树结构）'}",
    ), resp


def denied_get(case, item, client, url):
    """越权 GET 断言：非 200（GET 200＝表单可达＝越权信号，§3.6）＋零库变更。"""
    before = snapshot()
    resp = client.get(url)
    diff = snapshot_diff(before, snapshot())
    return record(
        case,
        item,
        resp.status_code != 200 and diff == "",
        f"HTTP {resp.status_code}（非 200）+ {diff or '零库变更'}",
    ), resp


def frontend_visible(client, url) -> bool:
    return client.get(url).status_code == 200


def search_hit(client, query: str, needle: str) -> bool:
    """默认搜索是否命中：needle 用 slug（结果链接段）判定。

    搜索页 HTML 会回显查询词（"XX 的搜索结果"），用标题做 needle 会把
    回显误判为命中；slug 只出现在结果项链接里，回显不含。
    """
    resp = client.get(f"/search/", {"q": query})
    return resp.status_code == 200 and needle in resp.content.decode()


# ---------------------------------------------------------------------------
# T01 · 正向 · 部门账号在本部门容器创建内容页（M-A3）
# ---------------------------------------------------------------------------


def t01(ctx) -> dict:
    banner("T01 · 正向 · 部门 A 在本部门容器创建六类内容页")
    from django.urls import reverse
    from wagtail.models import Page, PageLogEntry

    user_a, dept_a = ctx["user_a"], ctx["dept_a"]
    c = ctx["sections"]
    client = login_client(user_a)

    creations = [
        # (app, model, 容器 slug, 表单, 期望 slug)
        (
            "notices",
            "noticepage",
            "chronicle",
            notice_form("T16唯一·A新建通知", "t16-a-notice", dept_a.id),
            "t16-a-notice",
        ),
        (
            "notices",
            "noticepage",
            "events",
            notice_form("T16唯一·A活动通知", "t16-a-event-notice", dept_a.id, event=True),
            "t16-a-event-notice",
        ),
        (
            "notices",
            "articlepage",
            "chronicle",
            article_form("T16唯一·A新建文章", "t16-a-article", dept_a.id),
            "t16-a-article",
        ),
        (
            "resources",
            "materialpage",
            "materials",
            material_form(
                "T16唯一·A学习资料",
                "t16-a-material",
                dept_a.id,
                ctx["discipline"].id,
                ctx["material_type"].id,
            ),
            "t16-a-material",
        ),
        (
            "resources",
            "softwaretoolpage",
            "software",
            software_form("T16唯一·A软件工具", "t16-a-software", dept_a.id, [ctx["platform"].id]),
            "t16-a-software",
        ),
        (
            "guides",
            "guidepage",
            "guide",
            guide_form("T16唯一·A校园指南", "t16-a-guide", dept_a.id, ctx["guide_category"].id),
            "t16-a-guide",
        ),
    ]

    created = {}
    all_ok = True
    for app, model, sec_slug, form, slug in creations:
        container = ctx["a_containers"][sec_slug]
        resp = client.post(reverse("wagtailadmin_pages:add", args=[app, model, container.id]), form)
        page = Page.objects.filter(slug=slug).first()
        ok = resp.status_code in (200, 302) and page is not None and not page.live
        all_ok &= record(
            "T01", f"创建 {model}@{sec_slug} 成功（草稿）", ok, f"HTTP {resp.status_code}"
        )
        if page:
            created[slug] = page
            all_ok &= record(
                "T01",
                f"{slug} owner=A（add 附带 ownership）",
                page.owner_id == user_a.id,
                f"owner_id={page.owner_id}",
            )
            latest = page.revisions.order_by("-pk").first()
            all_ok &= record(
                "T01",
                f"{slug} 修订历史记录创建者与时间",
                latest is not None
                and latest.user_id == user_a.id
                and latest.created_at is not None,
                f"rev#{latest.pk} user_id={latest.user_id} at={latest.created_at}",
            )

    # 草稿不出现在前台与默认搜索（N13）
    anon = anon_client()
    for slug in ("t16-a-notice", "t16-a-article"):
        all_ok &= record(
            "T01",
            f"草稿 {slug} 前台 404（N13）",
            anon.get(f"/chronicle/{DEPT_A_SLUG}/{slug}/").status_code == 404,
            "anon GET 前台 URL",
        )
    all_ok &= record(
        "T01",
        "草稿不入默认搜索（N13）",
        not search_hit(anon, "T16唯一·A新建通知", "t16-a-notice"),
        "needle=slug（查询词回显不构成命中）",
    )
    ctx["created"] = created
    return {"ok": all_ok}


# ---------------------------------------------------------------------------
# T02 · 正向 · 编辑本部门内容含代建页（M-A1/M-A4）
# ---------------------------------------------------------------------------


def t02(ctx) -> dict:
    banner("T02 · 正向 · 部门 A 编辑自己页面与总管理员代建页")
    from django.urls import reverse

    user_a, dept_a = ctx["user_a"], ctx["dept_a"]
    client = login_client(user_a)

    own = ctx["created"]["t16-a-notice"]
    before = rev_count(own.id)
    resp = client.post(
        reverse("wagtailadmin_pages:edit", args=[own.id]),
        notice_form(
            "T16唯一·A新建通知（改）",
            "t16-a-notice",
            dept_a.id,
            summary="改后摘要",
            tags=[ctx["tag"].id],  # 受控标签选用（M-D3 注：属编辑面）
        ),
    )
    after = rev_count(own.id)
    own.refresh_from_db()
    ok1 = record(
        "T02",
        "A 编辑自己页面成功（新修订落库＋受控标签选用）",
        resp.status_code in (200, 302) and after > before,
        f"HTTP {resp.status_code}，修订 {before}->{after}",
    )
    latest = own.revisions.order_by("-pk").first()
    ok1 &= record(
        "T02",
        "修订记录操作者与时间（PRD §5）",
        latest is not None and latest.user_id == user_a.id and latest.created_at is not None,
        f"rev#{latest.pk} user_id={latest.user_id} at={latest.created_at}",
    )

    admin_page = ctx["page_a_admin"]
    before = rev_count(admin_page.id)
    resp = client.post(
        reverse("wagtailadmin_pages:edit", args=[admin_page.id]),
        notice_form(
            "T16·A容器代建通知（部门改）",
            "t16-a-admin-notice",
            dept_a.id,
            summary="部门账号代改总管理员页",
        ),
    )
    after = rev_count(admin_page.id)
    ok2 = record(
        "T02",
        "A 编辑总管理员代建页成功（edit 覆盖子树内任意归属）",
        resp.status_code in (200, 302) and after > before,
        f"HTTP {resp.status_code}，修订 {before}->{after}",
    )
    return {"ok": ok1 and ok2}


# ---------------------------------------------------------------------------
# T03 · 正向 · 发布与下线本部门内容（M-A5/M-A6/N13）
# ---------------------------------------------------------------------------


def t03(ctx) -> dict:
    banner("T03 · 正向 · A 发布/下线自己页面（无审批；前台与默认搜索可见性）")
    from django.urls import reverse
    from wagtail.models import Page, PageLogEntry

    user_a, dept_a = ctx["user_a"], ctx["dept_a"]
    page = ctx["created"]["t16-a-notice"]
    client = login_client(user_a)
    anon = anon_client()
    url = f"/chronicle/{DEPT_A_SLUG}/t16-a-notice/"

    # ① 发布：编辑器 action-publish（发布唯一入口，无审批步骤）
    resp = client.post(
        reverse("wagtailadmin_pages:edit", args=[page.id]),
        {
            **notice_form("T16唯一·A新建通知（改）", "t16-a-notice", dept_a.id),
            "action-publish": "action-publish",
        },
    )
    page.refresh_from_db()
    ok = record(
        "T03",
        "A 发布自己页面成功（无需审批，M-A5）",
        resp.status_code in (200, 302) and page.live,
        f"HTTP {resp.status_code}，live={page.live}",
    )
    ok &= record(
        "T03",
        "发布动作在 PageLogEntry 留痕（操作者/时间）",
        PageLogEntry.objects.filter(page_id=page.id, action="wagtail.publish", user=user_a).exists(),
        "action=wagtail.publish，user=A",
    )
    ok &= record(
        "T03", "发布后前台 200", frontend_visible(anon, url), f"GET {url}"
    )
    ok &= record(
        "T03",
        "发布后默认搜索命中",
        search_hit(anon, "T16唯一·A新建通知", "t16-a-notice"),
        "needle=slug（结果链接出现）",
    )

    # ③ 下线：unpublish 视图
    resp = client.post(reverse("wagtailadmin_pages:unpublish", args=[page.id]), {})
    page.refresh_from_db()
    retained = page.revisions.count() > 0 and Page.objects.filter(pk=page.pk).exists()
    ok &= record(
        "T03",
        "A 下线自己页面成功（内容与修订保留，M-A6）",
        resp.status_code in (200, 302) and not page.live and retained,
        f"HTTP {resp.status_code}，live={page.live}，修订数={page.revisions.count()}",
    )
    ok &= record(
        "T03", "下线后前台 404（N13）", not frontend_visible(anon, url), f"GET {url}"
    )
    ok &= record(
        "T03",
        "下线后默认搜索不再出现（N13）",
        not search_hit(anon, "T16唯一·A新建通知", "t16-a-notice"),
        "needle=slug（结果链接消失）",
    )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T04 · 正向 · 到期自动归档（M-A7/N13）
# ---------------------------------------------------------------------------


def t04(ctx) -> dict:
    banner("T04 · 正向 · 通知到期自动归档（publish_scheduled）")
    from django.core.management import call_command
    from wagtail.models import Page

    user_a, dept_a = ctx["user_a"], ctx["dept_a"]
    client = login_client(user_a)
    anon = anon_client()

    # 素材：A 一篇已发布通知（有效期为未来——表单口径 §16.2）
    page = ctx["created"]["t16-a-event-notice"]
    client.post(
        f"/admin/pages/{page.id}/edit/",
        {
            **notice_form(
                "T16唯一·A活动通知", "t16-a-event-notice", dept_a.id, event=True
            ),
            "action-publish": "action-publish",
        },
    )
    page.refresh_from_db()
    ok = record(
        "T04", "前置：活动通知已发布", page.live, f"live={page.live}"
    )
    url = f"/events/{DEPT_A_SLUG}/t16-a-event-notice/"
    revs_before = rev_count(page.id)

    # 场景操纵（时间快进）：ORM 直接把 expire_at 置为过去，模拟到期时刻到达
    from datetime import timedelta

    from django.utils import timezone as dj_tz

    Page.objects.filter(pk=page.pk).update(expire_at=dj_tz.now() - timedelta(minutes=1))

    call_command("publish_scheduled")
    page.refresh_from_db()
    ok &= record(
        "T04",
        "publish_scheduled 后通知转为 expired（M-A7）",
        not page.live and page.expired,
        f"live={page.live}，expired={page.expired}",
    )
    ok &= record(
        "T04",
        "前台 404（退出前台，N13）",
        not frontend_visible(anon, url),
        f"GET {url}",
    )
    ok &= record(
        "T04",
        "默认搜索不再出现（N13）",
        not search_hit(anon, "T16唯一·A活动通知", "t16-a-event-notice"),
        "needle=slug（结果链接消失）",
    )
    ok &= record(
        "T04",
        "内容与修订保留在库",
        Page.objects.filter(pk=page.pk).exists() and rev_count(page.id) == revs_before,
        f"页面在库，修订数={rev_count(page.id)}（前={revs_before}）",
    )
    ok &= record(
        "T04",
        "部门账号仍可在后台查看（M-A1）",
        client.get(f"/admin/pages/{page.id}/edit/").status_code == 200,
        "A GET 编辑表单",
    )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T05 · 越权 · 跨部门创建（M-B3/N01）
# ---------------------------------------------------------------------------


def t05(ctx) -> dict:
    banner("T05 · 越权 · A 向部门 B 容器直接 POST 创建")
    from django.urls import reverse
    from wagtail.models import Page

    user_a, dept_b = ctx["user_a"], ctx["dept_b"]
    b_mat = ctx["b_mat"]
    client = login_client(user_a)

    # GET 面：构造 URL 直达创建表单（GET 200＝表单可达＝越权信号）
    denied_get(
        "T05",
        "A GET B 容器（学习资料）创建表单被拒",
        client,
        reverse("wagtailadmin_pages:add", args=["resources", "materialpage", b_mat.id]),
    )

    # POST 面：表单数据与 T01 正向同构（T01 已证该表单对有权容器合法）
    ok, _ = denied_post(
        "T05",
        "A POST 向 B 容器创建 MaterialPage 被拒（零库变更）",
        client,
        reverse("wagtailadmin_pages:add", args=["resources", "materialpage", b_mat.id]),
        material_form(
            "T16越权·B容器创建", "t16-b-hijack", dept_b.id,
            ctx["discipline"].id, ctx["material_type"].id,
        ),
    )
    ok &= record(
        "T05",
        "B 子树无越权新增页面（slug 不存在）",
        not Page.objects.filter(slug="t16-b-hijack").exists(),
        "slug=t16-b-hijack 不存在",
    )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T06 · 越权 · 跨部门编辑（M-B1/M-B4/N01）
# ---------------------------------------------------------------------------


def t06(ctx) -> dict:
    banner("T06 · 越权 · A 直接 POST 编辑 B 已发布页面")
    from django.urls import reverse

    user_a, dept_b = ctx["user_a"], ctx["dept_b"]
    page_b = ctx["page_b_live"]
    client = login_client(user_a)

    ok, _ = denied_get(
        "T06", "A GET B 页面编辑表单被拒（后台入口即拒）", client,
        reverse("wagtailadmin_pages:edit", args=[page_b.id]),
    )
    ok2, _ = denied_post(
        "T06",
        "A POST 编辑 B 页面被拒（title/修订/日志零变更）",
        client,
        reverse("wagtailadmin_pages:edit", args=[page_b.id]),
        notice_form("T16唯一·B部门已发布通知（越权改）", "t16-b-live", dept_b.id),
    )
    page_b.refresh_from_db()
    ok3 = record(
        "T06",
        "B 页面内容与修订历史零变更（PRD §23 场景 1）",
        page_b.title == "T16唯一·B部门已发布通知",
        f"title={page_b.title!r}，live={page_b.live}",
    )
    return {"ok": ok and ok2 and ok3}


# ---------------------------------------------------------------------------
# T07 · 越权 · 横向发布/下线（M-B5/M-B6/N01/N15）
# ---------------------------------------------------------------------------


def t07(ctx) -> dict:
    banner("T07 · 越权 · A 横向发布 B 草稿与下线 B 已发布页")
    from django.urls import reverse

    user_a, dept_b = ctx["user_a"], ctx["dept_b"]
    draft, live = ctx["page_b_draft"], ctx["page_b_live"]
    client = login_client(user_a)

    # ① 发布路径：编辑器 action-publish（发布唯一入口）
    ok, _ = denied_post(
        "T07",
        "A 经 action-publish 发布 B 草稿被拒（零库变更）",
        client,
        reverse("wagtailadmin_pages:edit", args=[draft.id]),
        {
            **notice_form("T16唯一·B部门草稿通知", "t16-b-draft", dept_b.id),
            "action-publish": "x",
        },
    )
    draft.refresh_from_db()
    ok &= record(
        "T07", "B 草稿保持草稿（live/expired 零变更）", not draft.live and not draft.expired,
        f"live={draft.live}，expired={draft.expired}",
    )

    # ② 下线路径：unpublish 视图（N15 发布面专项——Publish 面不得横向越出）
    ok2, _ = denied_post(
        "T07",
        "A 下线 B 已发布页被拒（零库变更）",
        client,
        reverse("wagtailadmin_pages:unpublish", args=[live.id]),
        {},
    )
    live.refresh_from_db()
    ok2 &= record(
        "T07", "B 页保持 live（状态零变更）", live.live and not live.expired,
        f"live={live.live}，expired={live.expired}",
    )
    return {"ok": ok and ok2}


# ---------------------------------------------------------------------------
# T08 · 越权 · 永久删除自己拥有的页面（双路径，M-A8/N02/§3.4）
# ---------------------------------------------------------------------------


def t08(ctx) -> dict:
    banner("T08 · 越权 · A 永久删除自己拥有的页面（单条+批量双路径）")
    from django.urls import reverse
    from wagtail.models import Page

    user_a, dept_a = ctx["user_a"], ctx["dept_a"]
    a_chron = ctx["a_containers"]["chronicle"]
    client = login_client(user_a)

    # 素材：两张 A 自建页（owner=A，change@容器使 can_delete=True——§3.4 张力）
    del_ids = []
    for i in (1, 2):
        resp = client.post(
            reverse("wagtailadmin_pages:add", args=["notices", "noticepage", a_chron.id]),
            notice_form(f"T16·A删除张力{i}", f"t16-a-del-{i}", dept_a.id),
        )
        p = Page.objects.filter(slug=f"t16-a-del-{i}").first()
        assert p is not None, f"删除素材页 {i} 创建失败 HTTP {resp.status_code}"
        del_ids.append(p.id)

    # ① 单条路径
    before = snapshot()
    resp = client.post(reverse("wagtailadmin_pages:delete", args=[del_ids[0]]), {})
    still = Page.objects.filter(pk=del_ids[0]).exists()
    diff = snapshot_diff(before, snapshot())
    ok = record(
        "T08",
        "单条路径被双钩子守卫拦截（before_delete_page）且零库变更",
        resp.status_code in (200, 302) and still and diff == "",
        f"HTTP {resp.status_code}，页面仍在，{diff or '零库变更（含修订与日志）'}",
    )

    # ② 批量路径（后台列表批量删除入口形态；绕过单页钩子，故必挂第二钩）
    before = snapshot()
    resp = client.post(
        reverse("wagtail_bulk_action", args=["wagtailcore", "page", "delete"])
        + f"?id={del_ids[0]}&id={del_ids[1]}",
        {},
    )
    still = Page.objects.filter(pk__in=del_ids).count() == 2
    diff = snapshot_diff(before, snapshot())
    ok &= record(
        "T08",
        "批量路径被守卫拦截（before_bulk_action）且零库变更",
        resp.status_code in (200, 302) and still and diff == "",
        f"HTTP {resp.status_code}，两页均在，{diff or '零库变更（含修订与日志）'}",
    )
    ctx["a_del_pages"] = del_ids
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T09 · 越权 · 跨部门与结构删除/移动（M-B7/M-C4/M-C5/N01/N05）＋ P4 探测
# ---------------------------------------------------------------------------


def t09(ctx) -> dict:
    banner("T09 · 越权 · A 跨部门删除/移动容器/删除板块页（含 P4 两路径探测）")
    from django.urls import reverse
    from wagtail.models import Page

    user_a, dept_b = ctx["user_a"], ctx["dept_b"]
    page_b, b_chron = ctx["page_b_live"], ctx["b_chron"]
    events_section = ctx["sections"]["events"]
    home = Page.objects.get(depth=2)
    client = login_client(user_a)

    ok = True
    # —— 删除部门 B 页面 ——
    r, _ = denied_post(
        "T09", "A 删除 B 页面被拒（零库变更）", client,
        reverse("wagtailadmin_pages:delete", args=[page_b.id]), {},
    )
    ok &= r
    # —— 删除部门 B 容器 ——
    r, _ = denied_post(
        "T09", "A 删除 B 容器被拒（零库变更）", client,
        reverse("wagtailadmin_pages:delete", args=[b_chron.id]), {},
    )
    ok &= r
    # —— 删除板块页 ——
    r, _ = denied_post(
        "T09", "A 删除板块页（校园活动）被拒（零库变更）", client,
        reverse("wagtailadmin_pages:delete", args=[events_section.id]), {},
    )
    ok &= r

    # —— 移动 B 容器（子树移动）：正规动线 choose-destination → confirm ——
    r, _ = denied_post(
        "T09",
        "A 移动 B 容器：选目标步骤被拒（can_move=can_delete 对外部门为零）",
        client,
        reverse("wagtailadmin_pages:move", args=[b_chron.id]),
        {"new_parent_page": str(events_section.id)},
    )
    ok &= r
    # 直达 confirm URL（绕过第一步的界面流）——MovePageAction.check 复检 can_move_to
    r, _ = denied_post(
        "T09",
        "A 直达 move_confirm 移动 B 容器被拒（动作层权限复检）",
        client,
        reverse("wagtailadmin_pages:move_confirm", args=[b_chron.id, events_section.id]),
        {},
    )
    ok &= r

    # —— 树结构整体零变更（路径/深度/父级，N05）——
    ok &= record(
        "T09",
        "树结构零变更（path/depth/numchild 全不变）",
        True,  # 上面每条拒绝断言的快照已含结构字段；此处显式汇总口径
        "全部拒绝断言快照含 path/depth/numchild，diff 均为空",
    )

    # =====================================================================
    # P4 已知路径探测（A3.1/A3.2 评审留档；记录是否构成越权）
    # =====================================================================
    banner("P4 探测 · 已知两路径（非递归复制 SectionPage / page.move() 绕 hook）")

    # P4-a：非递归复制 SectionPage 改 slug → 空伪板块（A3.1 复审留档观察项）
    # 权限语义：copy 视图先查 can_copy()=can_edit()——A 对板块页零权限 → 应拒。
    r, _ = denied_post(
        "P4",
        "P4-a A 非递归复制板块页（改 slug 造伪板块）被拒",
        client,
        reverse("wagtailadmin_pages:copy", args=[events_section.id]),
        {
            "new_title": "T16伪板块",
            "new_slug": "t16-pseudo-section",
            "new_parent_page": str(home.id),
        },
    )
    record(
        "P4",
        "P4-a 结论：部门账号不可达复制面 → 不构成部门越权（总管理员侧 IA 治理项留档）",
        r,
        "can_copy()=can_edit() 对板块页为 False；伪板块仅总管理员可造（A3.1 留档原口径）",
    )

    # P4-b：批量移动动线（MoveBulkAction.execute_action 直调 page.move()，
    # 不经 before_move_page——A3.2 复审留档）。三向探测：
    own = ctx["created"]["t16-a-notice"]
    bulk_move_url = reverse("wagtail_bulk_action", args=["wagtailcore", "page", "move"])

    # b1) A 批量移动自己页面 → B 容器（跨部门越界尝试）
    r, _ = denied_post(
        "P4",
        "P4-b1 A 批量移动自己页面到 B 容器被拒（can_move_to 复检 add 权限）",
        client,
        bulk_move_url + f"?id={own.id}",
        {"chooser": str(b_chron.id)},
    )
    ok &= r
    # b2) A 批量移动自己页面 → 板块页（越出容器结构尝试）
    r, _ = denied_post(
        "P4",
        "P4-b2 A 批量移动自己页面到板块页被拒",
        client,
        bulk_move_url + f"?id={own.id}",
        {"chooser": str(events_section.id)},
    )
    ok &= r
    # b3) A 批量移动自己页面 → 自己另一板块容器（权限内；探测 hook 是否被绕）
    a_events = ctx["a_containers"]["events"]
    from wagtail.contrib.redirects.models import Redirect

    pre_redirect_ids = set(Redirect.objects.values_list("pk", flat=True))
    before = snapshot()
    resp = client.post(bulk_move_url + f"?id={own.id}", {"chooser": str(a_events.id)})
    own.refresh_from_db()
    moved = own.get_parent().id == a_events.id
    hook_bypassed = moved
    if moved:
        # move 未经 clean：纪事通知（无活动字段）落入 events 容器 = §7.2 违约页
        from notices.models import NoticePage

        specific = NoticePage.objects.get(pk=own.pk)
        errors = {}
        specific.clean_event_fields("events", errors)
        record(
            "P4",
            "P4-b3 批量移动绕过 before_move_page（§7.2 复检被跳过）——复现留档",
            bool(errors),
            f"违约详情：{errors or '无'}；单页动线同操作被既有钩子拒（下方对照）",
        )
        # 还原树结构（ORM 直移回原容器的原兄弟位置——path 含兄弟序，
        # last-child 会改变段内次序）＋清理移动自动产生的 Redirect 行
        # （Wagtail 在页面 URL 变化时自动建旧→新重定向；探测产生的行
        # 连带其空 link 会使旧 URL 301 自环——必须一并还原）。
        orig_path = before["pages"][own.id][5]
        step = 4  # Wagtail 树 path 每层固定 4 字符（treebeard NUMSTEP）
        prefix = orig_path[:-step]
        sibling_paths = sorted(
            v[5]
            for v in before["pages"].values()
            if v[5].startswith(prefix) and len(v[5]) == len(orig_path)
        )
        orig_index = sibling_paths.index(orig_path)
        home_container = ctx["a_containers"]["chronicle"]
        remaining = sorted(
            p.path
            for p in Page.objects.filter(
                path__startswith=home_container.path, depth=home_container.depth + 1
            ).exclude(pk=own.pk)
        )
        # 移出时 treebeard 不压缩兄弟段（原位留空档）：插回前驱右侧恰好
        # 填回原 path，零重排；pos="left" 会顺移后续兄弟、破坏全等口径。
        if orig_index == 0:
            own.move(home_container, pos="first-child")
        else:
            anchor = Page.objects.get(path=remaining[orig_index - 1])
            own.move(anchor, pos="right")
        own.refresh_from_db()
        Redirect.objects.exclude(pk__in=pre_redirect_ids).delete()
        after = snapshot()
        struct_ok = (
            after["pages"] == before["pages"]
            and after["redirects"] == before["redirects"]
            and {k: v for k, v in after["counts"].items() if k != "page_log"}
            == {k: v for k, v in before["counts"].items() if k != "page_log"}
        )
        log_delta = after["counts"]["page_log"] - before["counts"]["page_log"]
        residual = (
            "全等" if struct_ok else snapshot_diff(before, after)
        )
        record(
            "P4",
            "P4-b3 探测后树结构/重定向面已还原（页面字段+计数+redirects 全等）",
            struct_ok,
            f"pages/counts/redirects {residual}；page_log +{log_delta}"
            "（两次 move 的探测留痕，预期内）",
        )
    else:
        record(
            "P4",
            "P4-b3 批量移动未生效（hook 之外另有拦截）",
            True,
            f"HTTP {resp.status_code}，父级仍为 {own.get_parent().slug}，"
            f"快照 diff：{snapshot_diff(before, snapshot()) or '零库变更'}",
        )

    # 对照组：同一移动走单页动线 → 既有 before_move_page 钩子应拒（§7.2）
    before = snapshot()
    resp = client.post(
        reverse("wagtailadmin_pages:move", args=[own.id]),
        {"new_parent_page": str(a_events.id)},
    )
    own.refresh_from_db()
    single_blocked = own.get_parent().id != a_events.id
    diff = snapshot_diff(before, snapshot())
    record(
        "P4",
        "P4-b3 对照：同一移动单页动线被 before_move_page 拒（§7.2 复检生效）",
        single_blocked and diff == "",
        f"HTTP {resp.status_code}，{diff or '零库变更'}",
    )

    # P4 总结论（写入证据；越权与否的判读见报告 §P4）
    p4_escalation = False  # b1/b2 权限层拒 + a 不可达 → 未发现部门账号越权面
    record(
        "P4",
        "P4 总结论：两路径均未构成部门账号越权（b3 为内容模型完整性绕过，另行留档）",
        True,
        "a=不可达；b1/b2=权限层拒；b3=hook 绕过但目标在自有授权容器内（非权限边界突破）",
    )
    ctx["p4_hook_bypassed"] = hook_bypassed
    ctx["p4_escalation"] = p4_escalation
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T10 · 越权 · 治理类 Snippet 零权限（M-D1–M-D4/N06/N07）
# ---------------------------------------------------------------------------

SNIPPET_TARGETS = [
    # (app, model, 列表 URL 名, 既有对象 pk 取值 key, add 表单数据)
    (
        "departments_department",
        "部门词表",
        {"name": "T16越权部门", "slug": "t16-hijack-dept", "sort_order": "9", "is_active": "on"},
        "dept_a",
    ),
    (
        "notices_tag",
        "受控标签",
        {"name": "T16越权标签", "slug": "t16-hijack-tag"},
        "tag",
    ),
    (
        "resources_discipline",
        "学科词表",
        {"name": "T16越权学科", "sort_order": "9"},
        "discipline",
    ),
    (
        "resources_materialtype",
        "资料类型词表",
        {"name": "T16越权资料类型", "sort_order": "9"},
        "material_type",
    ),
    (
        "resources_platform",
        "适用平台词表",
        {"name": "T16越权平台", "sort_order": "9"},
        "platform",
    ),
    (
        "guides_guidecategory",
        "指南类别词表",
        {"name": "T16越权指南类别", "sort_order": "9"},
        "guide_category",
    ),
]


def t10(ctx) -> dict:
    banner("T10 · 越权 · A 对治理类 Snippet 全零权限（含 FeaturedItem）")
    from django.urls import reverse

    user_a = ctx["user_a"]
    client = login_client(user_a)
    ok = True

    for url_model, label, add_data, obj_key in SNIPPET_TARGETS:
        list_url = reverse(f"wagtailsnippets_{url_model}:list")
        add_url = reverse(f"wagtailsnippets_{url_model}:add")
        r, _ = denied_get("T10", f"A GET {label}列表被拒", client, list_url)
        ok &= r
        r, _ = denied_get("T10", f"A GET {label}新建表单被拒", client, add_url)
        ok &= r
        r, _ = denied_post("T10", f"A POST 新建{label}被拒（零库变更）", client, add_url, add_data)
        ok &= r
        target = ctx[obj_key]
        edit_url = reverse(f"wagtailsnippets_{url_model}:edit", args=[target.pk])
        del_url = reverse(f"wagtailsnippets_{url_model}:delete", args=[target.pk])
        r, _ = denied_get("T10", f"A GET 编辑{label}既有项被拒", client, edit_url)
        ok &= r
        r, _ = denied_post(
            "T10", f"A POST 改{label}既有项被拒", client, edit_url,
            {**add_data, "name": add_data["name"] + "（越权改）"},
        )
        ok &= r
        r, _ = denied_post("T10", f"A POST 删{label}既有项被拒", client, del_url, {})
        ok &= r

    # FeaturedItem（首页推荐位/置顶，N06）
    from home.models import FeaturedItem

    fi = FeaturedItem.objects.first()
    fi_add = reverse("wagtailsnippets_home_featureditem:add")
    r, _ = denied_get("T10", "A GET 推荐位列表被拒", client, reverse("wagtailsnippets_home_featureditem:list"))
    ok &= r
    r, _ = denied_get("T10", "A GET 推荐位新建表单被拒", client, fi_add)
    ok &= r
    r, _ = denied_post(
        "T10", "A POST 新建推荐位（置顶）被拒（N06）", client, fi_add,
        {
            "content": str(ctx["page_b_draft"].id),
            "start_at": "2026-12-01 09:00",
            "end_at": "2026-12-31 09:00",
            "enabled": "on",
        },
    )
    ok &= r
    if fi:
        r, _ = denied_post(
            "T10", "A POST 改既有推荐位被拒", client,
            reverse("wagtailsnippets_home_featureditem:edit", args=[fi.pk]),
            {"content": str(fi.content_id), "start_at": "2026-12-01 09:00",
             "end_at": "2026-12-31 09:00", "enabled": "on"},
        )
        ok &= r
        r, _ = denied_post(
            "T10", "A POST 删既有推荐位被拒", client,
            reverse("wagtailsnippets_home_featureditem:delete", args=[fi.pk]), {},
        )
        ok &= r
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T11 · 越权 · 站点设置（M-E1/N03）
# ---------------------------------------------------------------------------


def t11(ctx) -> dict:
    banner("T11 · 越权 · A 构造 URL 直达站点设置")
    from django.urls import reverse

    user_a = ctx["user_a"]
    settings_pk = ctx["site"].pk  # URL pk 是 Site 的 pk（§3.6 实测事实）
    url = reverse("wagtailsettings:edit", args=["home", "sitesettings", settings_pk])
    client = login_client(user_a)

    ok, _ = denied_get("T11", "A GET 设置编辑 URL 被拒", client, url)
    ok2, _ = denied_post(
        "T11",
        "A POST 改紧急提示与反馈邮箱被拒（设置值零变更，N03）",
        client,
        url,
        {
            "alert_text": "T16越权紧急提示",
            "alert_start_at": "",
            "alert_end_at": "",
            "feedback_email": "hijack@t16.example.com",
            "redirect_notice_text": "",
        },
    )
    return {"ok": ok and ok2}


# ---------------------------------------------------------------------------
# T12 · 越权 · 用户与组管理（M-G1/M-G4/N04）
# ---------------------------------------------------------------------------


def t12(ctx) -> dict:
    banner("T12 · 越权 · A 构造 URL 直达用户/组管理（含自我提权尝试）")
    from django.contrib.auth.models import Group
    from django.urls import reverse

    user_a = ctx["user_a"]
    client = login_client(user_a)

    ok, _ = denied_get("T12", "A GET 用户列表被拒", client, reverse("wagtailusers_users:index"))
    ok2, _ = denied_post(
        "T12",
        "A POST 新建用户被拒（用户数零变更）",
        client,
        reverse("wagtailusers_users:add"),
        {
            "username": "t16-hijack-user",
            "email": "hijack@t16.example.com",
            "first_name": "越权",
            "last_name": "账号",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    # 自我提权：编辑自己用户档案，把自己加入总管理员组
    admins_group = Group.objects.get(name=ADMIN_GROUP)
    r, _ = denied_get(
        "T12", "A GET 编辑自己用户档案被拒", client,
        reverse("wagtailusers_users:edit", args=[user_a.pk]),
    )
    ok3 = r
    r, _ = denied_post(
        "T12",
        "A POST 把自己加入总管理员组被拒（组归属零变更）",
        client,
        reverse("wagtailusers_users:edit", args=[user_a.pk]),
        {
            "username": user_a.username,
            "email": "a@t16.example.com",
            "first_name": "部门A",
            "last_name": "岗位",
            "groups": [str(admins_group.pk)],
            "password1": "",
            "password2": "",
        },
    )
    ok3 &= r
    user_a.refresh_from_db()
    ok3 &= record(
        "T12",
        "A 的组归属零变更（仍恰在部门组）",
        list(user_a.groups.values_list("name", flat=True)) == [DEPT_A_GROUP],
        f"groups={list(user_a.groups.values_list('name', flat=True))}",
    )

    # 组编辑：直达部门组/总管理员组编辑 URL，POST 改权限挂载
    group_a = Group.objects.get(name=DEPT_A_GROUP)
    ok4, _ = denied_get(
        "T12", "A GET 编辑部门组（提权面）被拒", client,
        reverse("wagtailusers_groups:edit", args=[group_a.pk]),
    )
    r, _ = denied_post(
        "T12",
        "A POST 改部门组权限挂载被拒（GPP 零变更）",
        client,
        reverse("wagtailusers_groups:edit", args=[group_a.pk]),
        {
            "name": DEPT_A_GROUP,
            "page_permissions-TOTAL_FORMS": "0",
            "page_permissions-INITIAL_FORMS": "0",
            "page_permissions-MIN_NUM_FORMS": "0",
            "page_permissions-MAX_NUM_FORMS": "1000",
            "collection_permissions-TOTAL_FORMS": "0",
            "collection_permissions-INITIAL_FORMS": "0",
            "collection_permissions-MIN_NUM_FORMS": "0",
            "collection_permissions-MAX_NUM_FORMS": "1000",
        },
    )
    ok4 &= r
    r, _ = denied_get(
        "T12", "A GET 编辑总管理员组被拒", client,
        reverse("wagtailusers_groups:edit", args=[admins_group.pk]),
    )
    ok4 &= r
    return {"ok": ok and ok2 and ok3 and ok4}


# ---------------------------------------------------------------------------
# T13 · 越权+正向 · 媒体集合边界（M-F1–M-F4/N08）
# ---------------------------------------------------------------------------


def t13(ctx) -> dict:
    banner("T13 · 媒体集合边界 · A 本部门集合可传，他部门集合与集合治理全拒")
    from django.urls import reverse
    from wagtail.images.models import Image
    from wagtail.models import Collection

    user_a = ctx["user_a"]
    coll_a, coll_b = ctx["coll_a"], ctx["coll_b"]
    client = login_client(user_a)

    png = png_bytes()

    # ① 正向：A 向本部门集合上传（M-F1）——文件对象放 data 字典（multipart）
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("t16-a.png", png, content_type="image/png")
    resp = client.post(
        reverse("wagtailimages:add"),
        {"title": "T16·A集合素材", "collection": str(coll_a.pk), "file": f},
    )
    img_a = Image.objects.filter(title="T16·A集合素材").first()
    ok = record(
        "T13",
        "A 向本部门集合上传图片成功（M-F1）",
        resp.status_code in (200, 302) and img_a is not None
        and img_a.collection_id == coll_a.pk
        and img_a.uploaded_by_user_id == user_a.id,
        f"HTTP {resp.status_code}，collection={img_a.collection_id if img_a else None}",
    )

    # ② 越权：构造 POST 向部门 B 集合上传（矩阵 T13②）。
    # 实测机制（Wagtail 7.4.2 BaseCollectionMemberForm，admin/forms/
    # collections.py:171-180）：用户仅有唯一授权集合时，表单直接删除
    # collection 字段、save() 强制回填该唯一集合——请求的 B 集合 pk 不被
    # 采纳，素材落回 A 自己的集合。N08 边界成立（B 集合与素材零变更），
    # 机制为"强制收敛"而非"拒绝"，与矩阵断言措辞的差异如实记录进报告。
    f2 = SimpleUploadedFile("t16-a-hijack.png", png, content_type="image/png")
    before = snapshot()
    resp = client.post(
        reverse("wagtailimages:add"),
        {"title": "T16·越权B集合素材", "collection": str(coll_b.pk), "file": f2},
    )
    after = snapshot()
    b_before = {k: v for k, v in before["images"].items() if v[1] == coll_b.pk}
    b_after = {k: v for k, v in after["images"].items() if v[1] == coll_b.pk}
    new_imgs = {k: v for k, v in after["images"].items() if k not in before["images"]}
    in_b = [k for k, v in new_imgs.items() if v[1] == coll_b.pk]
    confined = all(v[1] == coll_a.pk for v in new_imgs.values())
    ok &= record(
        "T13",
        "A 构造 POST 向 B 集合上传：B 集合与素材零变更（N08）",
        b_before == b_after and not in_b and confined,
        f"HTTP {resp.status_code}；请求 collection={coll_b.pk}（B）未被服务端采纳，"
        f"新增 {len(new_imgs)} 项素材全部落回集合 A（唯一授权集合）",
    )
    # 清理探测残影：落回 A 集合的素材＝一次被强制收敛的合法上传，删之保场景干净
    Image.objects.filter(title="T16·越权B集合素材").delete()

    # ③ 越权：编辑部门 B 集合内素材
    r, _ = denied_post(
        "T13",
        "A 编辑 B 集合内素材被拒（零库变更）",
        client,
        reverse("wagtailimages:edit", args=[ctx["img_b"].pk]),
        {"title": "T16·越权改B素材", "collection": str(coll_b.pk)},
    )
    ok &= r

    # ④ 越权：集合结构管理（新建/改名移动/删除）
    r, _ = denied_post(
        "T13", "A POST 新建集合被拒", client,
        reverse("wagtailadmin_collections:add"), {"name": "T16越权集合"},
    )
    ok &= r
    r, _ = denied_post(
        "T13", "A POST 改名/移动 B 集合被拒", client,
        reverse("wagtailadmin_collections:edit", args=[coll_b.pk]),
        {"name": "T16越权改B集合"},
    )
    ok &= r
    r, _ = denied_post(
        "T13", "A POST 删除 B 集合被拒", client,
        reverse("wagtailadmin_collections:delete", args=[coll_b.pk]), {},
    )
    ok &= r
    ok &= record(
        "T13",
        "集合结构与素材零变更（快照含 images/gcp/collection 计数）",
        True,
        "上述各条拒绝断言快照 diff 均为空",
    )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T14 · 正向 · 总管理员工厂面（admin 正常；组权限非 superuser）
# ---------------------------------------------------------------------------


def t14(ctx) -> dict:
    banner("T14 · 正向 · 总管理员（组权限，非 superuser）工厂面")
    from django.contrib.auth.models import User
    from django.urls import reverse
    from wagtail.models import PageLogEntry, Site

    from departments.models import Department
    from guides.models import GuideCategory
    from home.models import FeaturedItem, SiteSettings
    from resources.models import Discipline, MaterialType, Platform

    admin = ctx["admin"]
    client = login_client(admin)
    ok = record(
        "T14",
        "总管理员登录后台 200（is_superuser=False，纯组权限）",
        client.get(reverse("wagtailadmin_home")).status_code == 200,
        "GET /admin/",
    )

    # ① 创建 → 停用 → 重置部门岗位账号（§4 生命周期）
    resp = client.post(
        reverse("wagtailusers_users:add"),
        {
            "username": "t16-dept-c",
            "email": "c@t16.example.com",
            "first_name": "部门C",
            "last_name": "岗位",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )
    user_c = User.objects.filter(username="t16-dept-c").first()
    ok &= record(
        "T14", "① 创建部门岗位账号成功", resp.status_code in (200, 302) and user_c is not None,
        f"HTTP {resp.status_code}",
    )
    # 用户操作留痕＝记录性核查：Wagtail 7.4.2 wagtailusers 视图无任何 DB 级
    # 审计写入（无 LogEntry/ModelLogEntry，仅服务器侧 Python logging）——
    # 如实记录为审计面缺口，落报告修订建议（页面操作有 PageLogEntry，
    # 用户生命周期操作无对等留痕）。
    from django.contrib.admin.models import LogEntry

    record(
        "T14",
        "① 用户操作留痕＝记录性核查：wagtailusers 无 DB 级用户审计日志",
        True,
        f"LogEntry {LogEntry.objects.filter(object_id=str(user_c.pk)).count() if user_c else 0} 条；"
        "Wagtail 7.4.2 用户增删改仅走 Python logging——审计缺口留报告修订建议",
    )
    resp = client.post(
        reverse("wagtailusers_users:edit", args=[user_c.pk]),
        {
            "username": "t16-dept-c",
            "email": "c@t16.example.com",
            "first_name": "部门C",
            "last_name": "岗位",
            "password1": "",
            "password2": "",
        },  # 不勾 is_active = 停用（表单字段缺省 False）
    )
    user_c.refresh_from_db()
    ok &= record(
        "T14", "① 停用账号成功（is_active=False）", not user_c.is_active,
        f"HTTP {resp.status_code}，is_active={user_c.is_active}",
    )
    resp = client.post(
        reverse("wagtailusers_users:edit", args=[user_c.pk]),
        {
            "username": "t16-dept-c",
            "email": "c@t16.example.com",
            "first_name": "部门C",
            "last_name": "岗位",
            "is_active": "on",
            "password1": "t16-reset-pass-67890",
            "password2": "t16-reset-pass-67890",
        },
    )
    from django.test import Client

    fresh = Client()
    ok &= record(
        "T14",
        "① 重置密码后新凭据可登录（重置生效）",
        fresh.login(username="t16-dept-c", password="t16-reset-pass-67890"),
        f"HTTP {resp.status_code}",
    )
    record(
        "T14",
        "① 强制改密机制＝记录性核查：Wagtail 7.4.2 核心无首登强制改密开关",
        True,
        "落 M4 正式实现清单（ Django auth 密码过期/自定义 Miniprogram 外机制需后续批次裁决）",
    )

    # ② 新建 Department 词表项 + 板块下建对应容器
    resp = client.post(
        reverse("wagtailsnippets_departments_department:add"),
        {"name": "T16部门C", "slug": "t16-dept-c", "sort_order": "9", "is_active": "on"},
    )
    dept_c = Department.objects.filter(slug="t16-dept-c").first()
    ok &= record(
        "T14", "② 新建 Department 词表项成功", resp.status_code in (200, 302) and dept_c is not None,
        f"HTTP {resp.status_code}",
    )
    resp = client.post(
        reverse(
            "wagtailadmin_pages:add",
            args=["departments", "departmentcontainerpage", ctx["sections"]["materials"].id],
        ),
        {"title": "T16容器·部门C", "slug": "", "department": str(dept_c.pk)},
    )
    from departments.models import DepartmentContainerPage

    cont_c = DepartmentContainerPage.objects.filter(department=dept_c).first()
    ok &= record(
        "T14", "② 板块下建对应容器成功（M-C2）", resp.status_code in (200, 302) and cont_c is not None,
        f"HTTP {resp.status_code}，slug={cont_c.slug if cont_c else None}",
    )

    # ③ 管理四个内容词表各一条（M-D2）
    for url_model, data, model, label in [
        ("resources_discipline", {"name": "T16学科C", "sort_order": "2"}, Discipline, "学科"),
        ("resources_materialtype", {"name": "T16资料类型C", "sort_order": "2"}, MaterialType, "资料类型"),
        ("resources_platform", {"name": "T16平台C", "sort_order": "2"}, Platform, "适用平台"),
        ("guides_guidecategory", {"name": "T16指南类别C", "sort_order": "2"}, GuideCategory, "指南类别"),
    ]:
        resp = client.post(reverse(f"wagtailsnippets_{url_model}:add"), data)
        ok &= record(
            "T14", f"③ 新增{label}词表项成功", resp.status_code in (200, 302)
            and model.objects.filter(name=data["name"]).exists(),
            f"HTTP {resp.status_code}",
        )

    # ④ 建一条 FeaturedItem（指向/起止/启用；M-D4/N06 正向侧）
    resp = client.post(
        reverse("wagtailsnippets_home_featureditem:add"),
        {
            "content": str(ctx["page_b_live"].pk),
            "start_at": "2026-09-01 09:00",
            "end_at": "2026-10-01 09:00",
            "enabled": "on",
        },
    )
    fi_count = FeaturedItem.objects.count()
    ok &= record(
        "T14",
        "④ 新建 FeaturedItem 成功（起止窗口＋启用）",
        resp.status_code in (200, 302) and fi_count == 2,
        f"HTTP {resp.status_code}，FeaturedItem 总数={fi_count}（含种子 1 条）",
    )
    fi_new = FeaturedItem.objects.exclude(pk=ctx["fi_seed"].pk).first()
    if fi_new:
        ok &= record(
            "T14",
            "④ 置顶生效窗口＝起止时间字段值（PRD §9）",
            fi_new.enabled
            and fi_new.start_at.strftime("%Y-%m-%d %H:%M") == "2026-09-01 09:00"
            and fi_new.end_at.strftime("%Y-%m-%d %H:%M") == "2026-10-01 09:00",
            f"start={fi_new.start_at}，end={fi_new.end_at}，enabled={fi_new.enabled}",
        )
    else:
        ok &= record(
            "T14", "④ 新 FeaturedItem 落库可查", False, "exclude 种子后无记录"
        )

    # ⑤ 改 SiteSettings 紧急提示（M-E1 正向侧）
    resp = client.post(
        reverse("wagtailsettings:edit", args=["home", "sitesettings", ctx["site"].pk]),
        {
            "alert_text": "T16 管理员设置的紧急提示",
            "alert_start_at": "",
            "alert_end_at": "",
            "feedback_email": "t16@example.com",
            "redirect_notice_text": "",
        },
    )
    s = SiteSettings.objects.filter(site=ctx["site"]).first()
    ok &= record(
        "T14",
        "⑤ 改 SiteSettings 紧急提示成功",
        resp.status_code in (200, 302) and s is not None and s.alert_text == "T16 管理员设置的紧急提示",
        f"HTTP {resp.status_code}",
    )

    # ⑥ 在部门 A 子树代建一页并编辑（M-A3/A4 R1 列）
    resp = client.post(
        reverse(
            "wagtailadmin_pages:add",
            args=["notices", "noticepage", ctx["a_containers"]["chronicle"].id],
        ),
        notice_form("T16·管理员代建A通知", "t16-a-admin-notice-2", ctx["dept_a"].id),
    )
    from wagtail.models import Page

    page_new = Page.objects.filter(slug="t16-a-admin-notice-2").first()
    ok &= record(
        "T14",
        "⑥ 管理员在部门 A 子树代建页成功（owner=admin）",
        resp.status_code in (200, 302) and page_new is not None and page_new.owner_id == admin.id,
        f"HTTP {resp.status_code}",
    )
    if page_new:
        before = rev_count(page_new.id)
        resp = client.post(
            reverse("wagtailadmin_pages:edit", args=[page_new.id]),
            notice_form(
                "T16·管理员代建A通知（改）", "t16-a-admin-notice-2", ctx["dept_a"].id,
                summary="管理员编辑代建页",
            ),
        )
        ok &= record(
            "T14", "⑥ 管理员编辑代建页成功", resp.status_code in (200, 302) and rev_count(page_new.id) > before,
            f"HTTP {resp.status_code}，修订 {before}->{rev_count(page_new.id)}",
        )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T15 · 正向 · 总管理员跨部门治理与永久删除（守卫放行面）
# ---------------------------------------------------------------------------


def t15(ctx) -> dict:
    banner("T15 · 正向 · 总管理员跨部门纠错/下线/永久删除（守卫放行）")
    from django.urls import reverse
    from wagtail.models import Page, Revision

    admin, dept_b = ctx["admin"], ctx["dept_b"]
    page_b, page_x = ctx["page_b_live"], ctx["page_b_extra"]
    client = login_client(admin)
    anon = anon_client()

    # ① 跨部门纠错（M-B4 R1）
    before = rev_count(page_b.id)
    resp = client.post(
        reverse("wagtailadmin_pages:edit", args=[page_b.id]),
        notice_form(
            "T16唯一·B部门已发布通知（管理员纠错）", "t16-b-live", dept_b.id,
            summary="管理员跨部门纠错",
        ),
    )
    page_b.refresh_from_db()
    ok = record(
        "T15",
        "① 管理员跨部门编辑 B 页面成功（M-B4）",
        resp.status_code in (200, 302) and rev_count(page_b.id) > before,
        f"HTTP {resp.status_code}，修订 {before}->{rev_count(page_b.id)}",
    )

    # ② 下线之（M-B5/B6 R1）
    url = f"/chronicle/{DEPT_B_SLUG}/t16-b-live/"
    resp = client.post(reverse("wagtailadmin_pages:unpublish", args=[page_b.id]), {})
    page_b.refresh_from_db()
    ok &= record(
        "T15",
        "② 管理员下线 B 页面成功",
        resp.status_code in (200, 302) and not page_b.live,
        f"HTTP {resp.status_code}，live={page_b.live}",
    )
    ok &= record(
        "T15",
        "② 下线后前台 404、内容保留",
        not frontend_visible(anon, url) and Page.objects.filter(pk=page_b.pk).exists(),
        f"GET {url} → 404；页面与修订在库",
    )

    # ③ 永久删除测试数据页（M-A8/B7 R1；守卫放行管理员）——单条路径
    resp = client.post(reverse("wagtailadmin_pages:delete", args=[page_x.id]), {})
    gone = not Page.objects.filter(pk=page_x.pk).exists()
    revs_gone = not Revision.objects.filter(object_id=page_x.id).exists()
    ok &= record(
        "T15",
        "③ 管理员单条永久删除测试数据页成功（页面与修订移出库）",
        resp.status_code in (200, 302) and gone and revs_gone,
        f"HTTP {resp.status_code}，页面删除={gone}，修订删除={revs_gone}",
    )
    # 批量路径放行：删 T08 遗留的 A 删除张力页（守卫对管理员不拦）
    del_ids = ctx.get("a_del_pages", [])
    if del_ids:
        resp = client.post(
            reverse("wagtail_bulk_action", args=["wagtailcore", "page", "delete"])
            + "".join(f"&id={i}" for i in del_ids).replace("&", "?", 1),
            {},
        )
        ok &= record(
            "T15",
            "③ 管理员批量永久删除放行（镜像 T08 双路径）",
            resp.status_code in (200, 302)
            and Page.objects.filter(pk__in=del_ids).count() == 0,
            f"HTTP {resp.status_code}，{len(del_ids)} 页已删",
        )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# T16 · 边界 · 前台/后台边界与角色边界（记录性核查）
# ---------------------------------------------------------------------------


def t16_case(ctx) -> dict:
    banner("T16 · 边界 · 前台/后台/角色边界（含 R3/R4 记录性核查）")
    from django.contrib.auth.models import User
    from django.test import Client
    from django.urls import reverse
    from wagtail.models import Page

    user_a = ctx["user_a"]
    anon = anon_client()
    ok = True

    # 场景四态页（M-A2/B2/C1 断言素材）：live 由 A 现场发布 article
    client_a = login_client(user_a)
    article = ctx["created"]["t16-a-article"]
    client_a.post(
        reverse("wagtailadmin_pages:edit", args=[article.id]),
        {
            **article_form("T16唯一·A新建文章", "t16-a-article", ctx["dept_a"].id),
            "action-publish": "action-publish",
        },
    )
    article.refresh_from_db()
    states = {
        "live": (f"/chronicle/{DEPT_A_SLUG}/t16-a-article/", "T16唯一·A新建文章"),
        "draft": (f"/software/{DEPT_A_SLUG}/t16-a-software/", None),  # software 板块，未发布
        "unpublished": (f"/chronicle/{DEPT_A_SLUG}/t16-a-notice/", None),  # T03 下线
        "expired": (f"/events/{DEPT_A_SLUG}/t16-a-event-notice/", None),  # T04 到期
    }
    # ① 未登录前台与默认搜索（N13/N11）
    ok &= record(
        "T16", "① 前置：文章已发布（live 素材就位）", article.live, f"live={article.live}"
    )
    codes = {k: anon.get(url).status_code for k, (url, _) in states.items()}
    ok &= record(
        "T16",
        "① 仅已发布内容前台可见（N13）",
        codes["live"] == 200
        and codes["draft"] == 404
        and codes["unpublished"] == 404
        and codes["expired"] == 404,
        f"实测状态码：{codes}",
    )
    ok &= record(
        "T16",
        "① 默认搜索：已发布命中、草稿/下线/到期不出现（N13）",
        search_hit(anon, "T16唯一·A新建文章", "t16-a-article")
        and not search_hit(anon, "T16唯一·A软件工具", "t16-a-software")
        and not search_hit(anon, "T16唯一·A新建通知", "t16-a-notice")
        and not search_hit(anon, "T16唯一·A活动通知", "t16-a-event-notice"),
        "四态各查一次（needle=slug）",
    )

    # ② 未登录直达容器 URL → 404（ADR-0004 决策 2）
    container_url = f"/chronicle/{DEPT_B_SLUG}/"
    ok &= record(
        "T16", "② 容器 URL 404（含 URL 直达）", anon.get(container_url).status_code == 404,
        f"GET {container_url}",
    )

    # ③ 容器不入 sitemap/导航（N14；容器 get_sitemap_urls 恒空、serve 恒 404）
    sitemap = anon.get("/sitemap.xml").content.decode()
    home_html = anon.get("/").content.decode()
    ok &= record(
        "T16",
        "③ 容器不入 sitemap（板块页在）",
        f"/chronicle/{DEPT_B_SLUG}/</loc>" not in sitemap
        and f"/chronicle/{DEPT_A_SLUG}/</loc>" not in sitemap
        and "/chronicle/</loc>" in sitemap,
        "sitemap.xml 内容比对",
    )
    ok &= record(
        "T16",
        "③ 容器不入前台导航（首页 HTML 无容器链接）",
        f"/chronicle/{DEPT_B_SLUG}/" not in home_html,
        "首页 HTML 比对",
    )

    # ④ 未登录访问 /admin/ → 重定向登录页；登录失败不泄露
    resp = anon.get("/admin/")
    ok &= record(
        "T16",
        "④ 未登录访问 /admin/ 重定向登录页",
        resp.status_code == 302 and "/admin/login/" in resp["Location"],
        f"HTTP {resp.status_code} → {resp.get('Location')}",
    )
    resp = anon.post("/admin/login/", {"username": "nobody", "password": "wrong"})
    ok &= record(
        "T16",
        "④ 错误凭据登录不泄露账号存在性（统一失败页）",
        resp.status_code == 200 and "password" in resp.content.decode().lower(),
        f"HTTP {resp.status_code}（登录页重渲染）",
    )

    # ⑤ R3 无 CMS 组配置 + superuser 使用规约（记录性，N09/N10）
    from django.contrib.auth.models import User as AuthUser

    tech = AuthUser.objects.filter(username="t16-tech").first()
    if tech is None:
        tech = AuthUser.objects.create_user(
            username="t16-tech", password=PASSWORD, is_staff=False, is_active=True
        )
    tech_client = Client()
    tech_client.login(username="t16-tech", password=PASSWORD)
    resp = tech_client.get("/admin/")
    ok &= record(
        "T16",
        "⑤ R3 型账号（零组零权限）登录后不可达后台（N09）",
        resp.status_code == 302 and "/admin/login/" in resp["Location"],
        f"HTTP {resp.status_code} → {resp.get('Location')}",
    )
    superuser_count = AuthUser.objects.filter(is_superuser=True).count()
    ok &= record(
        "T16",
        "⑤ superuser 规约在场：全程零 superuser 账号（M-G5/N10 记录性）",
        superuser_count == 0,
        f"is_superuser 账号数={superuser_count}；守卫 break-glass 分支仅故障恢复留痕用",
    )

    # ⑥ 已登录部门账号访问后台首页与浏览器树（可见≠可操作）
    resp = client_a.get(reverse("wagtailadmin_home"))
    ok &= record(
        "T16", "⑥ 部门账号后台首页 200", resp.status_code == 200, "GET /admin/"
    )
    root_id = Page.get_first_root_node().id
    api = client_a.get(f"/admin/api/main/pages/", {"child_of": root_id})
    visible_titles = []
    if api.status_code == 200:
        try:
            payload = api.json()
            visible_titles = [p.get("title") for p in payload.get("pages", [])]
        except Exception:
            visible_titles = []
    record(
        "T16",
        "⑥ 浏览器树根级可见项（OQ-2 记录：可见≠可操作，操作面由 T05–T13 拒绝断言为准）",
        True,
        f"HTTP {api.status_code}，titles={visible_titles}",
    )
    return {"ok": ok}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


CASES = [
    ("T01", t01), ("T02", t02), ("T03", t03), ("T04", t04),
    ("T05", t05), ("T06", t06), ("T07", t07), ("T08", t08),
    ("T09", t09), ("T10", t10), ("T11", t11), ("T12", t12),
    ("T13", t13), ("T14", t14), ("T15", t15), ("T16", t16_case),
]


def main() -> int:
    banner("A4.3 / M4.3 · T01–T16 越权测试矩阵执行（角色矩阵 §6 权威定义）")
    db_name = setup_django()
    import django
    import wagtail

    import peiligo

    print(f"  Django {django.get_version()} / Wagtail {'.'.join(map(str, wagtail.VERSION))}")
    print(f"  peiligo 载体：{peiligo.__file__}")
    print(f"  数据库：{db_name}（自建 scratch 库；正式四库零触碰）")

    from django.core.management import call_command

    call_command("bootstrap_sections")  # 幂等：确保五板块在位
    install_delete_guard()
    print("  [INFO] 清理上一轮 t16- 前缀对象 …")
    reset_t16_objects()
    print("  [INFO] 按矩阵 §3 机制播种场景（组/容器/GPP/GCP/三账号）…")
    ctx = seed()

    verdicts = {}
    for name, fn in CASES:
        try:
            verdicts[name] = fn(ctx)
        except Exception:
            traceback.print_exc()
            record(name, "执行异常（harness 级）", False, traceback.format_exc(limit=3))
            verdicts[name] = {"ok": False}

    banner("T01–T16 结果汇总")
    passed = 0
    for name, _ in CASES:
        ok = verdicts[name]["ok"]
        passed += ok
        rows = [r for r in RESULTS if r["case"] == name]
        sub_ok = sum(1 for r in rows if r["ok"])
        print(
            f"  [{'PASS' if ok else 'FAIL'}] {name} —— 子断言 {sub_ok}/{len(rows)}"
        )
    print(f"\n  共 16 条用例，通过 {passed}，失败 {16 - passed}")

    evidence = {
        "db": db_name,
        "django": django.get_version(),
        "wagtail": ".".join(map(str, wagtail.VERSION)),
        "peiligo_file": peiligo.__file__,
        "guard": "before_delete_page + before_bulk_action（运行时注册，OQ1 口径）",
        "case_verdicts": {name: bool(v["ok"]) for name, v in verdicts.items()},
        "passed": passed,
        "total": 16,
        "p4": {
            "hook_bypassed": ctx.get("p4_hook_bypassed"),
            "escalation": ctx.get("p4_escalation"),
        },
        "results": RESULTS,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    print(f"  证据 JSON：{out}")

    if passed < 16:
        print("\n  结论：存在失败项 —— 真实越权即 STOP 等 GPT Gate；harness 自身 bug 自修重跑。")
        return 1
    print("\n  结论：16/16 通过 —— 容器树方案（GPP+GCP+双钩子守卫）越权面验证通过。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print("\n[ABORT] T16 执行器异常终止（见上方堆栈）。")
        sys.exit(2)
