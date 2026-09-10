"""首页轮播 CarouselItem 模型测试（首页升级 Phase 3；Phase 2 冻结架构）。

- XOR（站内 XOR 外链）与外链字段配对（站内项外链侧字段全空、外链项标题必填）；
- external_url 复用 ``validate_external_url``（SB §10-7 回归，字段层 validator）；
- 站内目标白名单（仅五类内容页）与 lifecycle canonical 可展示判定
  （lifecycle_state == LIFECYCLE_LIVE，与 FeaturedItem.is_on_display 同口径）；
- 删除联动：internal_page CASCADE、external_cover_image SET_NULL；
- 排序（sort_order 升序、pk 稳定）与位容量（新建拒第 6 条、编辑既有放行）；
- snippet 权限：superuser/总管理员可管理、部门编辑不可（T10/T14 既有口径）。
"""

import datetime as dt

from django.contrib.auth import get_user_model
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from home.models import CarouselItem, HomePage, SectionPage
from wagtail.models import Page

from .helpers import (
    build_sections,
    future,
    make_article,
    make_container,
    make_department,
    make_guide,
    make_image,
    make_material,
    make_notice,
    make_software,
)
from .permission_helpers import (
    PASSWORD,
    build_permission_world,
    denied_get,
    denied_post,
    login_client,
)

HOUR = dt.timedelta(hours=1)


def carousel_add_data(page=None):
    """后台 snippet 新建表单最小 data（站内项或外链项二选一）。"""
    if page is not None:
        return {
            "internal_page": str(page.pk),
            "external_title": "",
            "external_url": "",
            "external_cover_image": "",
            "sort_order": "0",
        }
    return {
        "internal_page": "",
        "external_title": "外链标题",
        "external_url": "https://example.com/carousel",
        "external_cover_image": "",
        "sort_order": "0",
    }


class CarouselItemBase(TestCase):
    """公共基类：五板块＋同部门五容器（五类内容页各占其一）。"""

    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.containers = {
            slug: make_container(section, cls.department) for slug, section in sections.items()
        }

    @staticmethod
    def internal_item(page, **overrides):
        """站内项（未保存实例；full_clean 为主要被测面）。"""
        return CarouselItem(internal_page=page, **overrides)

    @staticmethod
    def external_item(**overrides):
        """外链项（未保存实例；URL+标题缺省合法）。"""
        defaults = {"external_url": "https://example.com/carousel", "external_title": "外链标题"}
        defaults.update(overrides)
        return CarouselItem(**defaults)

    @classmethod
    def live_notice(cls, slug):
        return make_notice(cls.containers["chronicle"], slug=slug, publish=True)


class CarouselXorTests(CarouselItemBase):
    """XOR（冻结决策 3）：站内与外链二选一。"""

    def test_internal_only_passes(self):
        item = self.internal_item(self.live_notice("xor-internal"))
        item.full_clean()
        item.save()

    def test_external_url_and_title_passes(self):
        item = self.external_item()
        item.full_clean()
        item.save()

    def test_both_set_fails(self):
        notice = self.live_notice("xor-both")
        item = self.external_item(internal_page=notice)
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)
        self.assertIn("external_url", ctx.exception.message_dict)

    def test_neither_set_fails(self):
        item = CarouselItem()
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)
        self.assertIn("external_url", ctx.exception.message_dict)


class ExternalFieldTests(CarouselItemBase):
    """外链字段配对（冻结决策 5/6）与 URL validator 复用（冻结决策 7）。"""

    def test_external_without_title_fails(self):
        item = self.external_item(external_title="")
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("external_title", ctx.exception.message_dict)

    def test_external_whitespace_only_title_fails(self):
        item = self.external_item(external_title="   ")
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("external_title", ctx.exception.message_dict)

    def test_internal_with_external_title_fails(self):
        item = self.internal_item(self.live_notice("ext-title"), external_title="多余外链标题")
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("external_title", ctx.exception.message_dict)

    def test_internal_with_external_cover_image_fails(self):
        item = self.internal_item(
            self.live_notice("ext-cover"), external_cover_image=make_image("多余外链封面")
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("external_cover_image", ctx.exception.message_dict)

    def test_invalid_external_url_rejected(self):
        """缺协议/含空格等非法 URL 由字段层 validate_external_url 拒绝（SB §10-7）。"""
        for bad in ("不是网址", "ftp://example.com/a", "https://user:pass@example.com/a"):
            with self.subTest(url=bad):
                item = self.external_item(external_url=bad)
                with self.assertRaises(ValidationError) as ctx:
                    item.full_clean()
                self.assertIn("external_url", ctx.exception.message_dict)


class InternalTargetTypeTests(CarouselItemBase):
    """站内目标白名单（冻结决策 4）：仅五类内容页。"""

    def test_five_content_types_allowed(self):
        make_notice(self.containers["chronicle"], slug="wl-notice", publish=True)
        make_article(self.containers["chronicle"], slug="wl-article", publish=True)
        make_material(self.containers["materials"], slug="wl-material", publish=True)
        make_software(self.containers["software"], slug="wl-software", publish=True)
        make_guide(self.containers["guide"], slug="wl-guide", publish=True)
        for slug in ("wl-notice", "wl-article", "wl-material", "wl-software", "wl-guide"):
            page = Page.objects.get(slug=slug).specific
            with self.subTest(model=type(page).__name__):
                self.internal_item(page).full_clean()

    def test_structure_pages_rejected(self):
        """首页/板块页/部门容器一律拒绝（CASE 5）。"""
        home = HomePage(title="轮播白名单外首页")
        Page.get_first_root_node().add_child(instance=home)
        section = SectionPage.objects.get(slug="chronicle")
        container = self.containers["chronicle"]
        for target in (home, section, container):
            with self.subTest(model=type(target.specific).__name__):
                with self.assertRaises(ValidationError) as ctx:
                    self.internal_item(target).full_clean()
                self.assertIn("internal_page", ctx.exception.message_dict)


class LifecycleTargetTests(CarouselItemBase):
    """站内目标可展示性＝canonical LIFECYCLE_LIVE 口径（GPT REFINEMENT #1；
    与 FeaturedItem.is_on_display 同一谓词，零新 lifecycle 规则）。"""

    def test_live_target_allowed(self):
        item = self.internal_item(self.live_notice("lc-live"))
        item.full_clean()
        self.assertTrue(item.is_on_display())

    def test_draft_target_rejected(self):
        draft = make_notice(self.containers["chronicle"], slug="lc-draft")
        with self.assertRaises(ValidationError) as ctx:
            self.internal_item(draft).full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)

    def test_scheduled_target_rejected(self):
        scheduled = make_notice(
            self.containers["chronicle"], slug="lc-scheduled", schedule_at=future(days=1)
        )
        with self.assertRaises(ValidationError) as ctx:
            self.internal_item(scheduled).full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)

    def test_unpublished_target_rejected(self):
        unpublished = self.live_notice("lc-unpublished")
        unpublished.unpublish()
        unpublished.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            self.internal_item(unpublished).full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)

    def test_expired_target_rejected(self):
        expired = self.live_notice("lc-expired")
        type(expired).objects.filter(pk=expired.pk).update(expire_at=timezone.now() - HOUR)
        call_command("publish_scheduled", verbosity=0)
        expired.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            self.internal_item(expired).full_clean()
        self.assertIn("internal_page", ctx.exception.message_dict)

    def test_target_state_change_recognized_after_save(self):
        """保存后目标状态变化 → is_on_display 识别为不可展示（下线）。"""
        notice = self.live_notice("lc-flip")
        item = self.internal_item(notice)
        item.full_clean()
        item.save()
        self.assertTrue(item.is_on_display())
        notice.unpublish()
        item.refresh_from_db()
        self.assertFalse(item.is_on_display())


class DeleteSemanticsTests(CarouselItemBase):
    """删除联动：internal_page CASCADE（冻结决策 8）、
    external_cover_image SET_NULL（冻结决策 9）。"""

    def test_internal_page_delete_cascades_item(self):
        notice = self.live_notice("del-cascade")
        item = self.internal_item(notice)
        item.full_clean()
        item.save()
        notice.delete()
        self.assertFalse(CarouselItem.objects.filter(pk=item.pk).exists())

    def test_external_cover_image_delete_sets_null(self):
        cover = make_image("外链封面")
        item = self.external_item(external_cover_image=cover)
        item.full_clean()
        item.save()
        cover.delete()
        item.refresh_from_db()
        self.assertIsNone(item.external_cover_image)
        self.assertTrue(CarouselItem.objects.filter(pk=item.pk).exists())


class OrderingTests(CarouselItemBase):
    """排序（冻结决策 10）：sort_order 升序、同值 pk 稳定、重复值允许。"""

    def test_ordering_sort_order_then_pk(self):
        first = self.internal_item(self.live_notice("ord-a"), sort_order=10)
        first.save()
        second = self.internal_item(
            make_article(self.containers["chronicle"], slug="ord-b", publish=True), sort_order=0
        )
        second.save()
        third = self.internal_item(
            make_guide(self.containers["guide"], slug="ord-c", publish=True), sort_order=0
        )
        third.save()
        # 乱序创建后读取：sort_order 升序；同值 0 内按 pk 稳定（second 先建）。
        self.assertEqual(
            [item.pk for item in CarouselItem.objects.all()],
            [second.pk, third.pk, first.pk],
        )


class MaxFiveTests(CarouselItemBase):
    """位容量（冻结决策 11＋GPT REFINEMENT #2）：拒第 6 条新建，编辑既有放行。"""

    def test_sixth_new_item_rejected(self):
        for i in range(5):
            self.internal_item(self.live_notice(f"max-{i}")).save()
        sixth = self.external_item()
        with self.assertRaises(ValidationError) as ctx:
            sixth.full_clean()
        self.assertIn(NON_FIELD_ERRORS, ctx.exception.message_dict)
        self.assertEqual(CarouselItem.objects.count(), 5)

    def test_editing_existing_item_allowed_when_full(self):
        items = [self.internal_item(self.live_notice(f"edit-{i}")) for i in range(5)]
        for item in items:
            item.save()
        first = CarouselItem.objects.get(pk=items[0].pk)
        first.sort_order = 42
        first.full_clean()  # 5 条时编辑既有项（exclude 自身 pk）必须放行
        first.save()
        self.assertEqual(CarouselItem.objects.get(pk=first.pk).sort_order, 42)


class CarouselPermissionTests(TestCase):
    """权限（TASK G）：现有机制自然覆盖新 snippet，零权限系统改动。

    总管理员组全量模型权限经 init_permissions 发放（矩阵 §3.2——新 snippet
    权限行随迁移生成后天然纳入，测试世界即正式配置载体）；部门组恰
    access_admin 一枚（§3.6）；superuser 走 Django 内建全权。
    """

    @classmethod
    def setUpTestData(cls):
        cls.world = build_permission_world()

    def test_superuser_can_manage(self):
        get_user_model().objects.create_superuser("t3-super", "super@example.com", PASSWORD)
        client = Client()
        self.assertTrue(client.login(username="t3-super", password=PASSWORD))
        resp = client.get(reverse("wagtailsnippets_home_carouselitem:list"))
        self.assertEqual(resp.status_code, 200)
        resp = client.post(
            reverse("wagtailsnippets_home_carouselitem:add"),
            carousel_add_data(self.world["page_b_live"]),
        )
        self.assertTrue(
            CarouselItem.objects.filter(internal_page_id=self.world["page_b_live"].pk).exists(),
            f"superuser 可管理 HTTP {resp.status_code}",
        )

    def test_global_admin_can_manage(self):
        """总管理员（纯组权限行权，非 superuser）可管理（T14 同口径正向）。"""
        client = login_client(self.world["admin"])
        resp = client.post(
            reverse("wagtailsnippets_home_carouselitem:add"),
            carousel_add_data(self.world["page_b_live"]),
        )
        item = CarouselItem.objects.filter(internal_page_id=self.world["page_b_live"].pk).first()
        self.assertIsNotNone(item, f"总管理员可管理 HTTP {resp.status_code}")
        resp = client.post(
            reverse("wagtailsnippets_home_carouselitem:edit", args=[item.pk]),
            carousel_add_data(self.world["page_b_live"]),
        )
        self.assertEqual(CarouselItem.objects.count(), 1, f"编辑既有项 HTTP {resp.status_code}")

    def test_dept_editor_denied(self):
        """部门编辑全操作面拒绝（T10 同口径：零库变更为主证）。"""
        w = self.world
        client = login_client(w["user_a"])
        item = CarouselItem(internal_page=w["page_b_live"])
        item.full_clean()
        item.save()
        denied_get(self, client, reverse("wagtailsnippets_home_carouselitem:list"), "轮播列表")
        add_url = reverse("wagtailsnippets_home_carouselitem:add")
        denied_get(self, client, add_url, "轮播新建表单")
        denied_post(self, client, add_url, carousel_add_data(w["page_b_live"]), msg="新建轮播项")
        denied_post(
            self,
            client,
            reverse("wagtailsnippets_home_carouselitem:edit", args=[item.pk]),
            carousel_add_data(w["page_b_live"]),
            msg="改轮播既有项",
        )
        denied_post(
            self,
            client,
            reverse("wagtailsnippets_home_carouselitem:delete", args=[item.pk]),
            {},
            msg="删轮播既有项",
        )
