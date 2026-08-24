"""A3.2（M3.3）删除政策测试（CONTENT_MODEL §17；PS-13/22/27/28/29）。

- PS-29：非空结构页（首页/板块/容器）删除被 ``before_delete_page`` 钩子拒，
  空容器可删；内容页为叶子（``subpage_types=[]``）无子树删除面；
- PS-27：Department/四词表 PROTECT——被引用拒删（ProtectedError）、
  无引用放行；部门退场＝``is_active=False`` 停用（记录与名称保留）；
- PS-28：删 Tag 仅 through 行级联、内容页零影响；
- PS-13/PS-22：FeaturedItem 随所指内容 CASCADE 同删零悬挂；展示有效性
  ＝四条件合取（``is_on_display``）。
"""

import datetime as dt

from departments.models import Department
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from home.models import FeaturedItem, HomePage
from notices.models import NoticePage, NoticeTag, Tag
from resources.models import MaterialType

from .helpers import build_sections, future, make_container, make_department, make_notice

HOUR = dt.timedelta(hours=1)


def delete_via_admin(client, page):
    return client.post(reverse("wagtailadmin_pages:delete", args=[page.pk]))


class NonemptyStructureDeletionTests(TestCase):
    """PS-29：非空结构页拒删（后台删除动线经钩子拦截）。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.admin = get_user_model().objects.create_superuser("admin-del", "a@del.test", "pw-del")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_nonempty_container_refused(self):
        container = make_container(self.sections["chronicle"], self.department)
        make_notice(container, slug="del-c", publish=True)
        response = delete_via_admin(self.client, container)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(container.pk))  # 钩子返回响应＝取消删除

    def test_nonempty_section_refused(self):
        make_container(self.sections["materials"], self.department)  # 板块下有容器即"非空"
        response = delete_via_admin(self.client, self.sections["materials"])
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(self.sections["materials"].pk))

    def test_nonempty_home_refused(self):
        home = HomePage.objects.first()
        response = delete_via_admin(self.client, home)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Page_exists(home.pk))

    def test_empty_container_deletable(self):
        container = make_container(self.sections["events"], self.department)
        response = delete_via_admin(self.client, container)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Page_exists(container.pk))

    def test_content_pages_are_leaves(self):
        """内容页无子树删除面（§1.4/§17.4 叶子终判）。"""
        from guides.models import GuidePage
        from notices.models import ArticlePage
        from resources.models import MaterialPage, SoftwareToolPage

        for model in (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage, GuidePage):
            with self.subTest(model=model.__name__):
                self.assertEqual(model.subpage_types, [])


def Page_exists(pk):
    from wagtail.models import Page

    return Page.objects.filter(pk=pk).exists()


class ProtectDeletionTests(TestCase):
    """PS-27：Department/词表 PROTECT——被引用拒删、无引用放行、退场＝停用。"""

    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.sections = sections
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)

    def test_referenced_department_refused(self):
        with self.assertRaises(ProtectedError):
            self.department.delete()
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_unreferenced_department_deletable(self):
        loner = make_department("临时处", "temp")
        loner.delete()
        self.assertFalse(Department.objects.filter(pk=loner.pk).exists())

    def test_department_retirement_via_is_active(self):
        """退场＝停用：记录保留、既有内容部门名保留、引用零变化。"""
        page = make_notice(self.container, slug="dp-ret", publish=True)
        self.department.is_active = False
        self.department.save()
        page.refresh_from_db()
        self.assertEqual(page.department.name, "教务处")  # 历史内容展示保留
        self.assertFalse(page.department.is_active)

    def test_referenced_vocabulary_refused(self):
        from .helpers import make_material

        materials_container = make_container(self.sections["materials"], self.department)
        material = make_material(materials_container, slug="dp-mat")  # 持有词表引用
        with self.assertRaises(ProtectedError):
            material.discipline.delete()  # 被资料页引用：内建拦截（拒绝信息即引用证据）
        with self.assertRaises(ProtectedError):
            material.material_type.delete()
        unused = MaterialType.objects.create(name="从未使用")
        unused.delete()  # 无引用放行（词表治理＝总管理员职责，无额外闸）
        self.assertFalse(MaterialType.objects.filter(pk=unused.pk).exists())


class TagSeveranceTests(TestCase):
    """PS-28：删除 Tag 仅解除关联（through CASCADE），内容页零影响。"""

    def test_tag_delete_severs_through_rows_only(self):
        sections = build_sections()
        department = make_department("教务处", "jwc")
        container = make_container(sections["chronicle"], department)
        page = make_notice(container, slug="tg-sev", publish=True)
        tag = Tag.objects.create(name="开学", slug="kaixue")
        NoticeTag.objects.create(tag=tag, content_object=page)  # 同 taggit add 的落库行
        self.assertEqual(page.tags.count(), 1)
        tag.delete()
        self.assertEqual(NoticeTag.objects.filter(content_object=page).count(), 0)
        page.refresh_from_db()  # 内容页本体零影响（标题/状态/正文不改）
        self.assertEqual(page.title, "测试通知")
        self.assertTrue(page.live)


class FeaturedItemPolicyTests(TestCase):
    """PS-13/PS-22：CASCADE 零悬挂＋展示有效性四条件合取。"""

    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.section = sections["chronicle"]
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.section, cls.department)

    def _featured(self, page, **overrides):
        fields = {
            "content": page,
            "start_at": timezone.now() - HOUR,
            "end_at": timezone.now() + dt.timedelta(days=7),
            "enabled": True,
        }
        fields.update(overrides)
        return FeaturedItem.objects.create(**fields)

    def test_cascade_on_content_deletion_zero_dangling(self):
        page = make_notice(self.container, slug="fi-cas", publish=True)
        self._featured(page)
        self.assertEqual(FeaturedItem.objects.count(), 1)
        page.delete()  # §17.3：违法内容净除动线不被运营位阻塞
        self.assertEqual(FeaturedItem.objects.count(), 0)  # 零悬挂引用

    def test_on_display_four_conditions(self):
        page = make_notice(self.container, slug="fi-cond", publish=True)
        item = self._featured(page)
        self.assertTrue(item.is_on_display())  # 四条件全成立
        self.assertFalse(
            FeaturedItem(
                content=page, start_at=timezone.now() - HOUR, end_at=future(days=7), enabled=False
            ).is_on_display()
        )
        self.assertFalse(
            self._featured(page, start_at=timezone.now() + dt.timedelta(days=1)).is_on_display()
        )  # now < start_at
        expired_item = self._featured(page, end_at=timezone.now() - HOUR)
        self.assertFalse(expired_item.is_on_display())  # now > end_at
        NoticePage.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)
        call_command("publish_scheduled", verbosity=0)  # 所指页退出 CURRENT_DEFAULT
        item = FeaturedItem.objects.get(pk=item.pk)  # FK 缓存持旧实例，须重取
        self.assertFalse(item.is_on_display())
