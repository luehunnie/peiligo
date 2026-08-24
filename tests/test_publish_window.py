"""A3.2（M3.3）发布窗口 clean 政策测试（CONTENT_MODEL §16.1/§16.2；PS-20/23）。

政策矩阵（§16.1）×未来性（§16.2）逐格验证，经 ``full_clean()``（E1/E9/
E10/E11 各路径共同闸口：编辑表单提交与 ``save_revision`` 均过 clean）。
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from .helpers import build_sections, future, make_container, make_department, make_notice


class PublishWindowBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.containers = {
            slug: make_container(section, cls.department) for slug, section in cls.sections.items()
        }


class NoticeWindowTests(PublishWindowBase):
    """PS-20：通知 expire_at 必填＋必未来（CM-01/§16.2）。"""

    def test_missing_expire_at_rejected(self):
        page = make_notice(self.containers["chronicle"], slug="pw-n-miss")
        page.expire_at = None
        with self.assertRaises(ValidationError) as ctx:
            page.full_clean()
        self.assertIn("expire_at", ctx.exception.error_dict)

    def test_past_expire_at_rejected(self):
        page = make_notice(self.containers["chronicle"], slug="pw-n-past")
        page.expire_at = future(days=-7)
        with self.assertRaises(ValidationError) as ctx:
            page.full_clean()
        self.assertIn("expire_at", ctx.exception.error_dict)

    def test_future_expire_at_accepted(self):
        page = make_notice(self.containers["chronicle"], slug="pw-n-ok")
        page.expire_at = future(days=7)
        page.full_clean()  # 不抛即通过


class ArticleWindowTests(PublishWindowBase):
    """PS-20：文章 expire_at 可选；填则必未来。"""

    def test_absent_expire_at_accepted(self):
        from .helpers import make_article

        page = make_article(self.containers["chronicle"], slug="pw-a-none")
        page.expire_at = None
        page.full_clean()

    def test_past_expire_at_rejected(self):
        from .helpers import make_article

        page = make_article(self.containers["chronicle"], slug="pw-a-past")
        page.expire_at = future(days=-7)
        with self.assertRaises(ValidationError) as ctx:
            page.full_clean()
        self.assertIn("expire_at", ctx.exception.error_dict)

    def test_future_expire_at_accepted(self):
        from .helpers import make_article

        page = make_article(self.containers["chronicle"], slug="pw-a-ok")
        page.expire_at = future(days=30)
        page.full_clean()


class ForbiddenWindowTests(PublishWindowBase):
    """PS-23：资料/软件工具/指南不设有效期——expire_at 强制空（§16.1）。"""

    def _assert_forbidden(self, maker, section_slug, slug):
        page = maker(self.containers[section_slug], slug=slug)  # 构造即 expire_at=None
        page.expire_at = future(days=7)
        with self.assertRaises(ValidationError) as ctx:
            page.full_clean()
        self.assertIn("expire_at", ctx.exception.error_dict)
        page.expire_at = None
        page.full_clean()  # 留空即合法

    def test_material_expire_at_forced_empty(self):
        from .helpers import make_material

        self._assert_forbidden(make_material, "materials", "pw-m")

    def test_software_expire_at_forced_empty(self):
        from .helpers import make_software

        self._assert_forbidden(make_software, "software", "pw-s")

    def test_guide_expire_at_forced_empty(self):
        from .helpers import make_guide

        self._assert_forbidden(make_guide, "guide", "pw-g")
