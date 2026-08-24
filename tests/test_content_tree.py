"""A3.1 页面树硬约束测试（CONTENT_MODEL §1.4/§4）。

- 五类内容页合法板块可建（后台真实编辑表单流，含 clean 全链）；
- 错误板块拒建、部门一致性拒建；
- 内容页均叶子；容器下禁建容器；同板块同部门容器唯一；
- 容器 slug 默认＝department.slug（§4）；
- before_move_page 移动兜底（§1.4 兜底手段）；
- before_move_page/before_copy_page 容器子树按目标板块复检（§1.4/§7.2）；
- 所属板块推导 property（§1.4 末段单一事实源）。
"""

import datetime as dt

from departments.models import Department, DepartmentContainerPage
from departments.wagtail_hooks import (
    enforce_content_model_rules_on_copy,
    enforce_content_model_rules_on_move,
)
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from guides.models import GuideCategory, GuidePage
from home.models import HomePage, SectionPage
from notices.models import ArticlePage, NoticePage
from resources.models import (
    Discipline,
    MaterialPage,
    MaterialType,
    Platform,
    SoftwareToolPage,
)
from wagtail.actions.copy_page import CopyPageAction
from wagtail.actions.create_alias import CreatePageAliasAction
from wagtail.test.utils import WagtailPageTestCase

from .helpers import (
    article_data,
    body_form_data,
    build_sections,
    make_container,
    make_department,
    notice_data,
)

FIVE_CONTENT_TYPES = (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage)


class ContentTreeBase(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.jwc = make_department("教务处", "jwc")
        cls.lib = make_department("图书馆", "lib")
        cls.xsc = make_department("学生处", "xsc")
        # 三板块各一个容器：chronicle=jwc / materials=lib / events=xsc / software=jwc / guide=lib
        cls.container_chronicle = make_container(cls.sections["chronicle"], cls.jwc)
        cls.container_materials = make_container(cls.sections["materials"], cls.lib)
        cls.container_events = make_container(cls.sections["events"], cls.xsc)
        cls.container_software = make_container(cls.sections["software"], cls.jwc)
        cls.container_guide = make_container(cls.sections["guide"], cls.lib)


class LegalCreationFlowTests(ContentTreeBase):
    """合法板块可建：真实后台编辑表单（form_class(data, parent_page=容器)）。"""

    def test_notice_creatable_in_chronicle(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container_chronicle), parent_page=self.container_chronicle
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_notice_creatable_in_events_with_event_fields(self):
        data = notice_data(
            self.container_events,
            event_start_at="2026-09-01 10:00:00",
            event_end_at="2026-09-01 12:00:00",
            event_location="大礼堂",
        )
        form = NoticePage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_events
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_article_creatable_in_events(self):
        data = article_data(
            self.container_events,
            event_start_at="2026-09-01 10:00:00",
            event_end_at="2026-09-01 12:00:00",
            event_is_online="on",
        )
        form = ArticlePage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_events
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_material_creatable_in_materials(self):
        discipline = Discipline.objects.create(name="计算机科学")
        material_type = MaterialType.objects.create(name="课件")
        data = {
            "title": "测试资料",
            "slug": "test-material",
            "summary": "测试摘要",
            "department": str(self.container_materials.department_id),
            "discipline": str(discipline.pk),
            "material_type": str(material_type.pk),
            **body_form_data(),
        }
        form = MaterialPage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_materials
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_software_creatable_in_software(self):
        windows = Platform.objects.create(name="Windows")
        mac = Platform.objects.create(name="macOS")
        data = {
            "title": "测试工具",
            "slug": "test-tool",
            "department": str(self.container_software.department_id),
            "platforms": [str(windows.pk), str(mac.pk)],
            "source_url": "https://example.com/tool",
            "license_note": "校园授权，免费使用",
            **body_form_data(),
        }
        form = SoftwareToolPage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_software
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_guide_creatable_in_guide(self):
        category = GuideCategory.objects.create(name="食堂")
        data = {
            "title": "测试指南",
            "slug": "test-guide",
            "department": str(self.container_guide.department_id),
            "category": str(category.pk),
            "location": "一食堂二楼",
            "opening_hours": "周一至周五 7:00-19:00",
            "contact": "电话 0000-0000",
            "responsible_party": "后勤处",
            "maintenance_mode": "self",
            "last_confirmed_on": "2026-08-01",
        }
        form = GuidePage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_guide
        )
        self.assertTrue(form.is_valid(), form.errors)


class IllegalPlacementTests(ContentTreeBase):
    """错误板块拒建与部门一致性（§1.4/§4，CM-02）。"""

    def test_notice_rejected_in_materials_section(self):
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container_materials), parent_page=self.container_materials
        )
        self.assertFalse(form.is_valid())
        self.assertIn("所属板块", str(form.errors))

    def test_material_rejected_in_chronicle_section(self):
        discipline = Discipline.objects.create(name="计算机科学")
        material_type = MaterialType.objects.create(name="课件")
        data = {
            "title": "测试资料",
            "slug": "test-material",
            "summary": "测试摘要",
            "department": str(self.container_chronicle.department_id),
            "discipline": str(discipline.pk),
            "material_type": str(material_type.pk),
            **body_form_data(),
        }
        form = MaterialPage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_chronicle
        )
        self.assertFalse(form.is_valid())
        self.assertIn("所属板块", str(form.errors))

    def test_guide_rejected_in_software_section(self):
        category = GuideCategory.objects.create(name="食堂")
        data = {
            "title": "测试指南",
            "slug": "test-guide",
            "department": str(self.container_software.department_id),
            "category": str(category.pk),
            "location": "一食堂",
            "opening_hours": "7:00-19:00",
            "contact": "0000",
            "responsible_party": "后勤处",
            "maintenance_mode": "curated",
            "last_confirmed_on": "2026-08-01",
        }
        form = GuidePage.get_edit_handler().get_form_class()(
            data=data, parent_page=self.container_software
        )
        self.assertFalse(form.is_valid())

    def test_department_mismatch_rejected(self):
        """§4 零漂移：内容 department 必须与父容器绑定部门相等。"""
        kyc = Department.objects.create(name="科研处", slug="kyc")
        form = NoticePage.get_edit_handler().get_form_class()(
            data=notice_data(self.container_chronicle, department=str(kyc.pk)),
            parent_page=self.container_chronicle,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("发布部门必须与本部门容器一致", str(form.errors))


class TreeShapeTests(ContentTreeBase):
    """内容页均叶子；容器层级限制；容器同板块同部门唯一。"""

    def test_all_content_pages_are_leaves(self):
        for model in FIVE_CONTENT_TYPES:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.subpage_types, [])
                self.assertEqual(model.creatable_subpage_models(), [])

    def test_content_only_under_container(self):
        for model in FIVE_CONTENT_TYPES:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.parent_page_types, ["departments.DepartmentContainerPage"])

    def test_container_only_under_section(self):
        self.assertCanNotCreateAt(HomePage, DepartmentContainerPage)
        self.assertCanNotCreateAt(DepartmentContainerPage, DepartmentContainerPage)

    def test_container_department_clash_rejected(self):
        """§4：同一板块下第二个同部门容器被 clean 拒。"""
        clash = DepartmentContainerPage(title="重复容器", slug="jwc-2", department=self.jwc)
        clash._provisional_parent = self.sections["chronicle"]
        with self.assertRaises(ValidationError) as ctx:
            clash.full_clean()
        self.assertIn("已存在绑定该部门的容器", str(ctx.exception))

    def test_container_different_department_ok(self):
        ok = DepartmentContainerPage(title="图书馆容器", slug="lib", department=self.lib)
        ok._provisional_parent = self.sections["chronicle"]
        ok.clean()  # 不抛即合法（path/depth 属树内建字段，入树时由 treebeard 赋值）

    def test_container_slug_defaults_to_department_slug(self):
        """§4/§13.1：容器 slug 默认取 department.slug（表单层落实）。"""
        form = DepartmentContainerPage.get_edit_handler().get_form_class()(
            data={"title": "新容器", "slug": "", "department": str(self.xsc.pk)},
            parent_page=self.sections["guide"],
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.slug, "xsc")


class SectionDerivationTests(ContentTreeBase):
    """§1.4 末段：所属板块＝树位置推导 property，无存储字段。"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        notice = NoticePage(
            title="推导用通知",
            slug="derive-notice",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=cls.xsc,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=dt.UTC),
            event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=dt.UTC),
            event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC),
            event_location="大礼堂",
        )
        cls.container_events.add_child(instance=notice)
        notice.save_revision().publish()

    def test_section_slug_and_title_derived_from_tree(self):
        notice = NoticePage.objects.get(slug="derive-notice").specific
        self.assertEqual(notice.section_slug, "events")
        self.assertEqual(notice.section_title, "校园活动")

    def test_no_stored_section_field(self):
        for model in FIVE_CONTENT_TYPES:
            with self.subTest(model=model.__name__):
                self.assertNotIn("section", [f.name for f in model._meta.get_fields()])
                self.assertNotIn("section_slug", [f.name for f in model._meta.get_fields()])


class MoveHookTests(ContentTreeBase):
    """before_move_page 兜底（§1.4：树内移动不经编辑表单）。"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        notice = NoticePage(
            title="活动通知",
            slug="event-notice",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=cls.xsc,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=dt.UTC),
            event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=dt.UTC),
            event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC),
            event_location="大礼堂",
        )
        cls.container_events.add_child(instance=notice)
        notice.save_revision().publish()

    def _request(self):
        request = RequestFactory().get("/")
        request.session = "s"
        request._messages = FallbackStorage(request)
        return request

    def test_move_content_to_legal_section_returns_none(self):
        notice = NoticePage.objects.get(slug="event-notice")
        # 同容器（即同板块同部门）移动应放行：结构层面父级类型＋板块语义均不变。
        result = enforce_content_model_rules_on_move(self._request(), notice, self.container_events)
        self.assertIsNone(result)

    def test_move_content_to_wrong_section_cancelled(self):
        notice = NoticePage.objects.get(slug="event-notice")
        result = enforce_content_model_rules_on_move(
            self._request(), notice, self.container_chronicle
        )
        self.assertIsNotNone(result, "移入纪事板块（活动字段将违反 §7.2）应被取消")

    def test_move_content_to_non_container_cancelled(self):
        notice = NoticePage.objects.get(slug="event-notice")
        result = enforce_content_model_rules_on_move(
            self._request(), notice, self.sections["chronicle"]
        )
        self.assertIsNotNone(result, "内容页移到板块页下应被取消")

    def test_move_container_to_non_section_cancelled(self):
        result = enforce_content_model_rules_on_move(
            self._request(),
            self.container_chronicle,
            self.container_events,
        )
        self.assertIsNotNone(result, "容器移到容器下应被取消")

    def test_move_container_to_section_with_clash_cancelled(self):
        """chronicle 板块已有 jwc 容器：把 software/jwc 容器移入 chronicle 应被拒。"""
        result = enforce_content_model_rules_on_move(
            self._request(), self.container_software, self.sections["chronicle"]
        )
        self.assertIsNotNone(result)


class ContainerSubtreeGuardTests(ContentTreeBase):
    """容器跨板块移动/递归复制须对子树内容页按目标板块同口径复检（§1.4/§4/§7.2）。

    wagtail 递归路径子页经 ``save(clean=False)`` 绕过 clean，树内移动亦
    不经编辑表单——钩子是这两条路径的唯一兜底。审查 A3.1.review F-1
    修复实证（含其 §5 表两条已证安全路径的回归）。
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # events 容器内一封合法活动通知：容器移/复制到 chronicle 即违反 §7.2 纪事五字段强制空。
        notice = NoticePage(
            title="子树活动通知",
            slug="subtree-event-notice",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=cls.xsc,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=dt.UTC),
            event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=dt.UTC),
            event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC),
            event_location="大礼堂",
        )
        cls.container_events.add_child(instance=notice)
        notice.save_revision().publish()

    def _request(self, **post):
        request = RequestFactory().post("/", post or None)
        request.session = "s"
        request._messages = FallbackStorage(request)
        return request

    def test_move_container_cross_section_with_noncompliant_child_cancelled_no_residue(self):
        """①跨板块移动含不合规通知的容器（events→chronicle）被拒且树零残留。"""
        result = enforce_content_model_rules_on_move(
            self._request(), self.container_events, self.sections["chronicle"]
        )
        self.assertIsNotNone(result, "子页活动字段移入 chronicle 违反 §7.2 应被取消")
        container = DepartmentContainerPage.objects.get(pk=self.container_events.pk)
        self.assertEqual(container.get_parent().slug, "events")
        notice = NoticePage.objects.get(slug="subtree-event-notice")
        self.assertEqual(notice.get_parent().pk, container.pk)
        self.assertEqual(notice.section_slug, "events")

    def test_recursive_copy_container_cross_section_cancelled_no_residue(self):
        """②递归复制容器到异板块（events→chronicle）被拒且目标板块零残留。"""
        result = enforce_content_model_rules_on_copy(
            self._request(
                new_parent_page=str(self.sections["chronicle"].pk),
                copy_subpages="on",
            ),
            self.container_events,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 302)
        # 零残留：chronicle 板块未新增 xsc 容器、其容器下未新增内容页。
        self.assertFalse(
            DepartmentContainerPage.objects.filter(
                path__startswith=self.sections["chronicle"].path,
                department=self.xsc,
            ).exists()
        )
        self.assertEqual(self.container_chronicle.get_children().count(), 0)

    def test_recursive_copy_container_same_section_allowed(self):
        """同板块递归复检平凡通过（不误伤合法复制）。"""
        result = enforce_content_model_rules_on_copy(
            self._request(
                new_parent_page=str(self.sections["events"].pk),
                copy_subpages="on",
            ),
            self.container_events,
        )
        self.assertIsNone(result)

    def test_copy_hook_passes_on_get(self):
        """表单展示期（GET）无目标父级，不拦截。"""
        request = RequestFactory().get("/")
        request.session = "s"
        request._messages = FallbackStorage(request)
        self.assertIsNone(enforce_content_model_rules_on_copy(request, self.container_events))

    def test_single_page_copy_to_wrong_section_container_rejected(self):
        """回归（审查 §5 安全路径①）：单页复制顶层经 add_child→clean 拒。"""
        notice = NoticePage.objects.get(slug="subtree-event-notice")
        with self.assertRaises(ValidationError):
            CopyPageAction(notice, to=self.container_chronicle, recursive=False).execute()
        self.assertEqual(self.container_chronicle.get_children().count(), 0)

    def test_single_page_alias_to_wrong_section_container_rejected(self):
        """回归（审查 §5 安全路径②）：单页别名顶层同经 add_child→clean 拒。"""
        notice = NoticePage.objects.get(slug="subtree-event-notice")
        with self.assertRaises(ValidationError):
            CreatePageAliasAction(
                notice, recursive=False, parent=self.container_chronicle, update_slug="alias-x"
            ).execute()
        self.assertEqual(self.container_chronicle.get_children().count(), 0)

    def test_non_numeric_parent_pk_post_returns_none(self):
        """F-5：父级 pk 非数字 POST 不抛 ValueError→500，交表单校验报错。"""
        result = enforce_content_model_rules_on_copy(
            self._request(new_parent_page="not-a-pk", copy_subpages="on"),
            self.container_events,
        )
        self.assertIsNone(result)


class SectionCopyGuardTests(ContentTreeBase):
    """递归复制板块页（SectionPage）按复制件 slug 复检子容器内容页
    （§1.4/§7.2，复审附记 F-4——伪板块下内容页 section_slug 出白名单
    且不可再保存；顶层无 clean、子树全 save(clean=False)）。"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.home = cls.sections["events"].get_parent()
        notice = NoticePage(
            title="板块复制用活动通知",
            slug="section-copy-notice",
            summary="摘要",
            body=[("paragraph", "<p>正文</p>")],
            department=cls.xsc,
            expire_at=dt.datetime(2026, 12, 31, 23, 0, tzinfo=dt.UTC),
            event_start_at=dt.datetime(2026, 9, 1, 10, 0, tzinfo=dt.UTC),
            event_end_at=dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC),
            event_location="大礼堂",
        )
        cls.container_events.add_child(instance=notice)
        notice.save_revision().publish()

    def _request(self, **post):
        request = RequestFactory().post("/", post or None)
        request.session = "s"
        request._messages = FallbackStorage(request)
        return request

    def test_recursive_copy_section_to_home_cancelled_no_residue(self):
        """①递归复制板块页到合法父级（首页，CopyForm 常规流程）被拒且零残留。"""
        result = enforce_content_model_rules_on_copy(
            self._request(
                new_parent_page=str(self.home.pk),
                new_slug="events-copy",
                copy_subpages="on",
            ),
            self.sections["events"],
        )
        self.assertIsNotNone(result, "伪板块 events-copy 下通知将出 §1.4 白名单应被取消")
        self.assertEqual(result.status_code, 302)
        self.assertFalse(SectionPage.objects.filter(slug="events-copy").exists())
        self.assertEqual(self.home.get_children().type(SectionPage).count(), 5)

    def test_section_copy_legal_paths_not_blocked(self):
        """②合法路径不误伤：非递归、同 slug 递归（表单 slug 唯一性拦）、
        递归别名（不复制内容页记录，复审附记口径）均放行。"""
        non_recursive = enforce_content_model_rules_on_copy(
            self._request(new_parent_page=str(self.home.pk), new_slug="events-copy"),
            self.sections["events"],
        )
        self.assertIsNone(non_recursive)
        same_slug = enforce_content_model_rules_on_copy(
            self._request(new_parent_page=str(self.home.pk), new_slug="events", copy_subpages="on"),
            self.sections["events"],
        )
        self.assertIsNone(same_slug)
        recursive_alias = enforce_content_model_rules_on_copy(
            self._request(
                new_parent_page=str(self.home.pk),
                new_slug="events-copy",
                copy_subpages="on",
                alias="on",
            ),
            self.sections["events"],
        )
        self.assertIsNone(recursive_alias)
