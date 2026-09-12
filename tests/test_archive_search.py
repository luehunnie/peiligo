"""M5.2 到期归档与历史搜索测试（PUBLISH_ARCHIVE_SCHEDULING §6–§10；
附录 A 断言 PA-31..36；分级 A）。

成对断言要求（§10）：PA-31 与 PA-32/PA-33 对**同一 E7 后对象**先后断言
——先断默认位（首页/板块默认列表/推荐位）不含，再断归档视图含＋搜索
命中；禁止只在单一位置断言。

实现约束（PA-30 承接）：全程禁 sleep——E7 一律 ``queryset.update`` 直设
过期时刻后执行正式命令 ``publish_scheduled``（先例
tests/test_publish_scheduled_boundaries.py / tests/test_current_default.py）。

载体裁定留痕（B 阶段 MB8–MB9，分支 arch/m5.2-archive-search）：

- **载体①**（§6.3）：expired 页原 slug URL 放行渲染（路由叶子对 S3 消费
  HISTORICAL 谓词）＋页首「已过期」横幅。依据＝§2.2/§17.5 冻结到期页
  内容/修订/slug-URL 数据全保留——原 URL 本就是被保留的活数据，放行
  渲染零数据复制；载体②（原 URL 404＋列表内嵌正文）须把正文渲染路径
  复制进归档/搜索列表模板，且 §6.3 自认「链接 404 的保留名存实亡」。
  载体①字面差异已按 §6.3-4 义务登记于 CONTENT_MODEL §16.4 补记行。
- **URL 形态**：``/<板块>/archive/``（自定义视图不入页面树，ADR-0005
  载体表 #5 先例；正则封闭五冻结 slug）。
- **入口绑定**（§7 补充口径，两入口＝IA §9.1 双载体）：板块默认列表
  （SectionPage，含 q 筛选态）＝CURRENT_DEFAULT；``/search/`` ＝
  ARCHIVE-SEARCH；归档视图＝HISTORICAL。
"""

import datetime as dt
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from home.models import FeaturedItem, SectionPage
from notices.lifecycle import current_default_pages, historical_pages
from wagtail.models import Page, PageLogEntry

from .helpers import (
    build_sections,
    future,
    make_article,
    make_container,
    make_department,
    make_notice,
)

HOUR = dt.timedelta(hours=1)


def expire_page(page):
    """E7 到期（对象级回拨＋正式命令执行，绕开 clean 未来性；禁 sleep）。"""
    Page.objects.filter(pk=page.pk).update(expire_at=timezone.now() - HOUR)
    call_command("publish_scheduled", verbosity=0)
    page.refresh_from_db()
    return page


class HistoricalPredicateTests(TestCase):
    """§6.1 HISTORICAL 谓词：``Q(live) ∪ Q(expired)`` 恰为 S2 ∪ S3。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        cls.draft = make_notice(cls.container, slug="hp-s0", title="谓词草稿页")
        cls.scheduled = make_notice(
            cls.container, slug="hp-s1", title="谓词预约页", schedule_at=future(days=1)
        )
        cls.live = make_notice(cls.container, slug="hp-s2", title="谓词在线页", publish=True)
        cls.expired = expire_page(
            make_notice(cls.container, slug="hp-s3", title="谓词过期页", publish=True)
        )
        cls.unpublished = make_notice(cls.container, slug="hp-s4", title="谓词下线页", publish=True)
        cls.unpublished.unpublish()

    def test_historical_is_live_union_expired(self):
        pks = set(historical_pages().values_list("pk", flat=True))
        self.assertIn(self.live.pk, pks)  # S2 在集
        self.assertIn(self.expired.pk, pks)  # S3 在集
        for page in (self.draft, self.scheduled, self.unpublished):  # S0/S1/S4 恒不入
            with self.subTest(state=page.slug):
                self.assertNotIn(page.pk, pks)
        # 同源对照：CURRENT_DEFAULT 恰为 HISTORICAL 减 expired（§16.4）。
        current = set(current_default_pages().values_list("pk", flat=True))
        self.assertEqual(current, pks - {self.expired.pk})


class ArchivePairBase(TestCase):
    """PA-31..33 成对断言公共数据：同一 E7 对象跨全部消费位。"""

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.department = make_department("教务处", "jwc")
        cls.container = make_container(cls.sections["chronicle"], cls.department)
        # PA-33 状态中性锚点：过期文章同入（§7.1 类型口径裁决，下限＝过期通知）。
        cls.expired_article = expire_page(
            make_article(cls.container, slug="pa33-art", title="过期文章标题", publish=True)
        )
        # PA-31..33 主对象：过期通知（E7 正式命令执行）。
        cls.expired = expire_page(
            make_notice(cls.container, slug="pa31-notice", title="过期通知标题", publish=True)
        )
        cls.live = make_notice(cls.container, slug="pa-live", title="在线通知标题", publish=True)
        call_command("update_index", stdout=StringIO())

    def _default_list_pks(self, section_slug):
        response = self.client.get(f"/{section_slug}/")
        self.assertEqual(response.status_code, 200)
        return {page.pk for page in response.context["content_entries"]}

    def _search_pks(self, query):
        response = self.client.get("/search/", {"q": query})
        self.assertEqual(response.status_code, 200)
        return {page.pk for page in response.context["search_results"]}

    def _archive_pks(self, section_slug):
        response = self.client.get(f"/{section_slug}/archive/")
        self.assertEqual(response.status_code, 200)
        return {page.pk for page in response.context["archive_entries"]}


class Pa31DefaultPositionTests(ArchivePairBase):
    """PA-31：到期退出默认位（E7 后）——与 PA-32/33 成对（§10）。"""

    def test_pa31_exits_home_default_lists_featured(self):
        # 不可见侧：首页与全部五板块默认列表不含（CURRENT_DEFAULT 消费位）。
        html = self.client.get("/").content.decode()
        self.assertNotIn(self.expired.title, html)
        for slug in ("chronicle", "events", "materials", "software", "guide"):
            with self.subTest(section=slug):
                self.assertNotIn(self.expired.pk, self._default_list_pks(slug))
        # 推荐位即时失效（§7 总表行 2：expired 请求时即时失效，无任务依赖）。
        item = FeaturedItem.objects.create(
            content=self.expired,
            start_at=timezone.now() - HOUR,
            end_at=timezone.now() + dt.timedelta(days=7),
            enabled=True,
        )
        self.assertFalse(item.is_on_display())
        # 成对断言（§10，禁止只断不可见侧）：同一对象归档视图含＋搜索命中。
        self.assertIn(self.expired.pk, self._archive_pks("chronicle"))
        self.assertIn(self.expired.pk, self._search_pks(self.expired.title))

    def test_pa31_board_q_state_keeps_current_default(self):
        """§7 入口绑定守门：板块列表 q 筛选态仍 CURRENT_DEFAULT——
        expired 不得经共用过滤层泄入默认列表入口。"""
        miss = self.client.get("/chronicle/", {"q": "过期通知标题"})
        pks = {page.pk for page in miss.context["content_entries"]}
        self.assertNotIn(self.expired.pk, pks)  # 默认列表入口不放宽
        self.assertNotIn(self.expired_article.pk, pks)
        hit = self.client.get("/search/", {"q": "过期通知标题"})
        self.assertIn(self.expired.pk, {page.pk for page in hit.context["search_results"]})


class Pa32ArchiveViewTests(ArchivePairBase):
    """PA-32：板块历史归档视图＝HISTORICAL＋「已过期」徽标。"""

    def test_pa32_archive_contains_live_and_expired_with_badge(self):
        response = self.client.get("/chronicle/archive/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        # HISTORICAL＝live ∪ expired：两类同视图可见。
        self.assertIn(self.expired.title, html)
        self.assertIn(self.live.title, html)
        # 标注义务＝可见「已过期」文字徽标（非仅灰化/排序，§6.1）。
        self.assertIn("已过期", html)
        self.assertIn(self.live.pk, self._archive_pks("chronicle"))

    def test_pa32_badge_targets_expired_entries_only(self):
        """徽标仅挂 expired 条目（live 条目不带；与 §7 总表标注义务一致）。"""
        html = self.client.get("/chronicle/archive/").content.decode()
        # Phase 8B 行式结果行（<a class="r-row">，原 <li> 内容卡）：逐行切片，
        # 避免跨行窗口误判——测试意图（徽标仅挂 expired 行）不变。
        cards = html.split('<a class="r-row"')
        live_card = next(card for card in cards if self.live.title in card)
        expired_card = next(card for card in cards if self.expired.title in card)
        self.assertNotIn("已过期", live_card)
        self.assertIn("已过期", expired_card)

    def test_pa32_sort_and_state_neutral_mix(self):
        """§6.1 默认排序＝-first_published_at 同序混排无降权；过期文章
        （状态中性）同入归档视图。"""
        entries = self.client.get("/chronicle/archive/").context["archive_entries"]
        pks = [page.pk for page in entries]
        self.assertEqual(set(pks[:3]), {self.expired.pk, self.live.pk, self.expired_article.pk})
        # 混排无降权：排序键仅 first_published_at（expired 不后置）。
        published = [page.first_published_at for page in entries]
        self.assertEqual(published, sorted(published, reverse=True))

    def test_pa32_all_five_boards_have_archive_view(self):
        """五板块各设视图，不特判不省略（§6.1）：常青三板块 expired 子集
        结构性为空，视图仍设置且渲染 live 全集。"""
        for slug in ("events", "materials", "software", "guide"):
            with self.subTest(section=slug):
                response = self.client.get(f"/{slug}/archive/")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("已过期", response.content.decode())

    def test_pa32_unknown_section_slug_404(self):
        """URL 正则封闭五冻结 slug：未知板块归档路径 404。"""
        self.assertEqual(self.client.get("/bogus/archive/").status_code, 404)


class Pa33ArchiveSearchTests(ArchivePairBase):
    """PA-33：站内搜索默认命中 expired（ARCHIVE-SEARCH，无用户开关）。"""

    def test_pa33_expired_notice_hits_with_annotation(self):
        response = self.client.get("/search/", {"q": "过期通知标题"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.expired.pk, {page.pk for page in response.context["search_results"]})
        # 标注与归档徽标同语义同文案（§7.1）。
        self.assertContains(response, "已过期")

    def test_pa33_state_neutral_expired_article_hits(self):
        """§7.1 类型口径：状态中性（S3 全入，过期文章同命中）。"""
        self.assertIn(
            self.expired_article.pk,
            self._search_pks("过期文章标题"),
        )

    def test_pa33_no_toggle_and_unpublished_still_hidden(self):
        """含 expired 是缺省口径（无开关参数）；unpublished 恒不入任何
        搜索口径（PS-25 对照）。"""
        hidden = make_notice(self.container, slug="pa33-s4", title="下线对照通知", publish=True)
        hidden.unpublish()
        self.assertEqual(self._search_pks("下线对照通知"), set())
        self.assertNotIn(hidden.pk, self._archive_pks("chronicle"))


class CarrierRouteTests(ArchivePairBase):
    """§6.3 载体①路由断言（裁定留痕见文件头）：S3 原 URL 放行渲染。"""

    def test_expired_url_renders_with_banner_s0s1s4_404(self):
        response = self.client.get(self.expired.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "已过期")  # 页首横幅
        self.assertContains(response, self.expired.title)  # 正文可读（不变式）
        for maker, slug, kwargs in (
            (make_notice, "cr-s0", {}),
            (make_notice, "cr-s1", {"schedule_at": future(days=1)}),
        ):
            page = maker(self.container, slug=slug, title=f"载体{slug}", **kwargs)
            self.assertEqual(self.client.get(page.url).status_code, 404)
        unpublished = make_notice(self.container, slug="cr-s4", title="载体下线页", publish=True)
        unpublished.unpublish()
        self.assertEqual(self.client.get(unpublished.url).status_code, 404)

    def test_pa34_manual_unpublish_contrasts_expired(self):
        """PA-34：E8 手动下线＝具名 URL 404＋搜索/归档均不可见（与 S3
        可达的刻意对比，§6.3/§8）。"""
        page = make_notice(self.container, slug="pa34", title="下线对比通知", publish=True)
        page.unpublish()
        self.assertEqual(self.client.get(page.url).status_code, 404)
        self.assertEqual(self._search_pks("下线对比通知"), set())
        self.assertNotIn(page.pk, self._archive_pks("chronicle"))
        # 刻意对比（同一用例内）：expired 对象三位置全可达。
        self.assertEqual(self.client.get(self.expired.url).status_code, 200)
        self.assertIn(self.expired.pk, self._search_pks(self.expired.title))
        self.assertIn(self.expired.pk, self._archive_pks("chronicle"))


class Pa36DraftScheduledTests(ArchivePairBase):
    """PA-36：S0/S1 任何匿名路径（URL/首页/默认列表/归档/搜索）不可见。"""

    def test_pa36_draft_and_scheduled_invisible_everywhere(self):
        draft = make_notice(self.container, slug="pa36-s0", title="草稿路径通知")
        scheduled = make_notice(
            self.container, slug="pa36-s1", title="预约路径通知", schedule_at=future(days=1)
        )
        for page, label in ((draft, "draft"), (scheduled, "scheduled")):
            with self.subTest(state=label):
                self.assertEqual(self.client.get(page.url).status_code, 404)
                self.assertNotIn(page.title, self.client.get("/").content.decode())
                self.assertNotIn(page.pk, self._default_list_pks("chronicle"))
                self.assertNotIn(page.pk, self._archive_pks("chronicle"))
                self.assertEqual(self._search_pks(page.title), set())


class Pa35PermanentDeleteTests(TestCase):
    """PA-35：永久删除仅总管理员；审计＝内建页面日志 ``wagtail.delete``；
    FeaturedItem 级联零悬挂（§17.2/§17.3）。"""

    PASSWORD = "pa35-pass-12345"

    @classmethod
    def setUpTestData(cls):
        # 顺序敏感：init_permissions 按既有 Department/容器生成 dept-<slug> 组
        # 与 GPP（permission_helpers 先例）——部门与容器须先就位。
        call_command("bootstrap_sections", stdout=StringIO())
        cls.section = SectionPage.objects.get(slug="chronicle")
        cls.department = make_department("学生处", "xsc-pa35")
        cls.container = make_container(cls.section, cls.department)
        # 正式权限骨架（init_permissions）＝被测配置载体。
        call_command("init_permissions", stdout=StringIO())
        page = make_notice(cls.container, slug="pa35-page", title="删除审计通知", publish=True)
        cls.page = page
        cls.featured = FeaturedItem.objects.create(
            content=page,
            start_at=timezone.now() - HOUR,
            end_at=timezone.now() + dt.timedelta(days=7),
        )
        cls.admin = cls._make_user("pa35-admin", "总管理员")
        cls.dept_user = cls._make_user("pa35-dept", f"dept-{cls.department.slug}")

    @classmethod
    def _make_user(cls, username, group_name):
        user = get_user_model().objects.create_user(
            username=username, password=cls.PASSWORD, is_staff=True
        )
        user.groups.add(Group.objects.get(name=group_name))
        return user

    def test_pa35_dept_account_denied_no_db_change(self):
        client = Client()
        self.assertTrue(client.login(username=self.dept_user.username, password=self.PASSWORD))
        response = client.post(reverse("wagtailadmin_pages:delete", args=[self.page.pk]), {})
        self.assertIn(response.status_code, (200, 302))  # 拒绝与成功同为 302（M4.4 口径）
        self.assertTrue(Page.objects.filter(pk=self.page.pk).exists(), "部门账号删除被拒")

    def test_pa35_admin_deletes_with_audit_and_cascade(self):
        client = Client()
        self.assertTrue(client.login(username=self.admin.username, password=self.PASSWORD))
        page_id = self.page.pk
        response = client.post(reverse("wagtailadmin_pages:delete", args=[page_id]), {})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Page.objects.filter(pk=page_id).exists(), "总管理员删除成功")
        # 审计载体＝内建页面日志 wagtail.delete（操作者＋时间，§9.2 口径）。
        self.assertTrue(
            PageLogEntry.objects.filter(
                page_id=page_id, action="wagtail.delete", user=self.admin
            ).exists(),
            "删除动作进入内建页面日志",
        )
        # §17.3 CASCADE：FeaturedItem 级联同删，零悬挂引用。
        self.assertFalse(FeaturedItem.objects.filter(content_id=page_id).exists())
