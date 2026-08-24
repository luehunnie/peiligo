"""A3.2（M3.3）修订与预览政策测试（CONTENT_MODEL §15；PS-11；E5/E6）。

内置修订全保留（V1 无上限/清理）；每次保存产生修订并记录操作者与时间；
发布标记 live 修订；回退＝产生新修订不覆写历史（修订快照不可变）。
E5/E6：live 页编辑存修订前台不中断；发布修订后前台更新。
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .helpers import build_sections, future, make_container, make_department, make_notice


class RevisionPolicyBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(sections["chronicle"], cls.department)
        cls.editor = get_user_model().objects.create_user("editor-rev", "e@rev.test", "pw-rev")


class RevisionBookkeepingTests(RevisionPolicyBase):
    """PS-11：修订记录（操作者/时间）＋发布标记＋回退不覆写。"""

    def test_each_save_creates_revision_with_user_and_time(self):
        page = make_notice(self.container, slug="rv-log")
        self.assertEqual(page.revisions.count(), 1)  # 创建即首修订
        before = timezone.now()
        page.title = "第二版标题"
        page.save_revision(user=self.editor)
        revisions = list(page.revisions.order_by("created_at"))
        self.assertEqual(len(revisions), 2)
        second = revisions[1]
        self.assertEqual(second.user, self.editor)
        self.assertIsNotNone(second.created_at)
        self.assertGreaterEqual(second.created_at, before - timedelta(seconds=1))

    def test_publish_marks_live_revision(self):
        page = make_notice(self.container, slug="rv-live")
        revision = page.save_revision(user=self.editor)
        revision.publish()
        page.refresh_from_db()
        self.assertEqual(page.live_revision, revision)

    def test_revert_creates_new_revision_without_overwriting(self):
        page = make_notice(self.container, slug="rv-revert", publish=True)
        v1 = page.revisions.order_by("created_at").first()
        page.title = "改版标题"
        page.expire_at = future(days=14)
        v2 = page.save_revision(user=self.editor)
        v2.publish()
        page.refresh_from_db()
        # 回退＝以旧修订内容另存新修订（E6 口径），历史快照零覆写。
        reverted = v1.as_object().save_revision(user=self.editor, previous_revision=v1)
        reverted.publish()
        page.refresh_from_db()
        self.assertEqual(page.revisions.count(), 3)
        self.assertEqual(page.live_revision, reverted)
        self.assertEqual(page.title, "测试通知")  # 回到 v1 内容
        v2.refresh_from_db()
        self.assertIn("改版标题", v2.content["title"])  # v2 快照仍完整保留


class LiveContinuityTests(RevisionPolicyBase):
    """E5/E6（PS-11）：编辑存修订 live 不中断、前台不变；发布后更新。"""

    def test_e5_save_revision_keeps_front_unchanged(self):
        page = make_notice(self.container, slug="rv-e5", publish=True)
        page.title = "尚未发布的新标题"
        page.save_revision(user=self.editor)
        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertTrue(page.has_unpublished_changes)  # S2b
        html = self.client.get(page.url).content.decode()
        self.assertNotIn("尚未发布的新标题", html)  # 前台仍渲染已发布版

    def test_e6_publish_revision_updates_front(self):
        page = make_notice(self.container, slug="rv-e6", publish=True)
        last_published_before = page.last_published_at
        page.title = "已发布的新标题"
        page.expire_at = future(days=14)
        revision = page.save_revision(user=self.editor)
        revision.publish()
        page.refresh_from_db()
        self.assertGreater(page.last_published_at, last_published_before)
        html = self.client.get(page.url).content.decode()
        self.assertIn("已发布的新标题", html)
