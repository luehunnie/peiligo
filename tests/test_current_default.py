"""A3.2（M3.3）CURRENT_DEFAULT 前台可见性测试（CONTENT_MODEL §16.4；PS-24/25）。

§16.4 默认视图＝S2 恰一类：路由层、板块默认列表（content_entries）、
sitemap.xml 三消费位同口径；到期页不物理删除——内容/修订/URL 保留
（PS-24），E9 重发布即恢复可见。

M5.2 口径升级（PUBLISH_ARCHIVE_SCHEDULING §6.3/§7.2"显式登记差异"）：
expired 具名 URL 由 404 改放行渲染（载体①，差异登记＝CONTENT_MODEL
§16.4 补记行）——本文件路由断言随之更新；S0/S1/S4 三态 404 不变。
HISTORICAL/ARCHIVE-SEARCH 归档/搜索侧断言见 test_archive_search.py。
"""

import datetime as dt
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from notices.lifecycle import current_default_pages
from notices.models import NoticePage
from wagtail.models import Revision

from .helpers import build_sections, future, make_container, make_department, make_notice

HOUR = dt.timedelta(hours=1)


def expire_page(page):
    """E7 到期（对象级回拨＋任务执行，绕开 clean 未来性）。"""
    NoticePage.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)
    call_command("publish_scheduled", verbosity=0)
    page.refresh_from_db()
    return page


class VisibilityBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.section = build_sections()["chronicle"]
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.section, cls.department)

    def _one_of_each_state(self, prefix):
        """造 S0/S1/S2/S3/S4 各一（标题带态名以便断言区分），返回映射。"""
        draft = make_notice(self.container, slug=f"{prefix}-draft", title=f"{prefix}草稿页")
        scheduled = make_notice(
            self.container,
            slug=f"{prefix}-sch",
            title=f"{prefix}预约页",
            schedule_at=future(days=1),
        )
        live = make_notice(
            self.container, slug=f"{prefix}-live", title=f"{prefix}在线页", publish=True
        )
        expired = expire_page(
            make_notice(self.container, slug=f"{prefix}-exp", title=f"{prefix}过期页", publish=True)
        )
        unpublished = make_notice(
            self.container, slug=f"{prefix}-unpub", title=f"{prefix}下线页", publish=True
        )
        unpublished.unpublish()
        unpublished.refresh_from_db()
        return {
            "draft": draft,
            "scheduled": scheduled,
            "live": live,
            "expired": expired,
            "unpublished": unpublished,
        }


class RouteVisibilityTests(VisibilityBase):
    """PS-25：非 CURRENT_DEFAULT 态路由层判定。M5.2 载体①后口径＝
    S0/S1/S4 具名 URL 404；S3（expired）放行渲染＋页首「已过期」横幅
    （§6.3 语义不变式；完整载体断言见 test_archive_search.py）。"""

    def test_draft_scheduled_unpublished_404_expired_renders(self):
        pages = self._one_of_each_state("rt")
        for key, page in pages.items():
            with self.subTest(state=key):
                response = self.client.get(page.url)
                if key == "live":
                    self.assertEqual(response.status_code, 200)
                elif key == "expired":
                    # M5.2 §6.3 载体①：expired 页原 slug URL 放行渲染。
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "已过期")
                else:
                    self.assertEqual(response.status_code, 404)

    def test_scheduled_not_yet_due_404(self):
        page = make_notice(self.container, slug="rt-future", schedule_at=timezone.now() + HOUR)
        self.assertEqual(self.client.get(page.url).status_code, 404)
        later = timezone.now() + 2 * HOUR  # 越过预约点（E3）转 200
        with mock.patch("django.utils.timezone.now", return_value=later):
            call_command("publish_scheduled", verbosity=0)
        self.assertEqual(self.client.get(page.url).status_code, 200)


class SectionListingTests(VisibilityBase):
    """PS-25：板块默认列表仅消费 S2（§16.4）。"""

    def test_listing_contains_live_only(self):
        pages = self._one_of_each_state("ls")
        response = self.client.get(self.section.url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(pages["live"].title, html)
        for key in ("draft", "scheduled", "expired", "unpublished"):
            with self.subTest(state=key):
                self.assertNotIn(pages[key].title, html)

    def test_listing_expires_live_page_on_task_run(self):
        page = make_notice(self.container, slug="ls-flip", publish=True)
        response = self.client.get(self.section.url)
        self.assertIn(page.title, response.content.decode())
        expire_page(page)
        response = self.client.get(self.section.url)
        self.assertNotIn(page.title, response.content.decode())


class SitemapVisibilityTests(VisibilityBase):
    """PS-25：sitemap.xml 同口径仅含 live（wagtail sitemap 消费 .live()）。"""

    def test_sitemap_contains_live_only(self):
        pages = self._one_of_each_state("sm")
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertIn(pages["live"].slug, xml)
        for key in ("draft", "scheduled", "expired", "unpublished"):
            with self.subTest(state=key):
                self.assertNotIn(pages[key].slug, xml)


class ExpiredRetentionTests(VisibilityBase):
    """PS-24：到期＝下线非删除——记录/修订/slug/URL 保留，E9 可重发布。"""

    def test_expired_content_and_revisions_retained(self):
        page = make_notice(self.container, slug="ps24", publish=True)
        page.title = "到期前改版"
        page.expire_at = future(days=14)
        page.publish(page.save_revision())
        page.refresh_from_db()
        revisions_before = page.revisions.count()
        url_before, slug_before = page.url, page.slug
        expire_page(page)
        page.refresh_from_db()
        self.assertTrue(page.expired)
        self.assertEqual(page.slug, slug_before)  # slug/URL 不因到期改变
        self.assertEqual(page.url, url_before)
        self.assertEqual(page.revisions.count(), revisions_before)  # 修订史保留
        fetched = NoticePage.objects.get(pk=page.pk)  # 记录未删、正文可读
        self.assertEqual(fetched.title, "到期前改版")
        self.assertEqual(fetched.summary, page.summary)

    def test_expired_republish_restores_visibility(self):
        page = expire_page(make_notice(self.container, slug="ps24-re", publish=True))
        # M5.2 载体①：expired 期原 URL 放行渲染（带横幅、仍非默认列表）。
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "已过期")
        self.assertNotIn(page.pk, set(current_default_pages().values_list("pk", flat=True)))
        page.expire_at = future(days=7)  # §16.2：重发布须给新有效期
        page.publish(page.save_revision())  # E9
        page.refresh_from_db()
        response = self.client.get(page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "已过期")  # E9 即时回 CURRENT_DEFAULT
        self.assertIn(page.pk, set(current_default_pages().values_list("pk", flat=True)))
        self.assertEqual(Revision.objects.filter(object_id=page.pk).count(), page.revisions.count())
