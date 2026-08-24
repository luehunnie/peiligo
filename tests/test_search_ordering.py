"""M3.4 搜索排序契约测试（PS-35 第六子句/§21.6；实现审查 F-1 补锚）。

实现审查（docs/reviews/A3.3.review.md F-1）：既有行为断言均集合序不敏感
（_pks 构造 set），「默认排序＝发布时间倒序」（PS-35 第六子句/IA §9.2 #4）
全套件零锚定——仅有的两处列表断言锚定确定性与空态，非排序契约。本文件
以同 token 错峰三页做列表序敏感断言：/search/?q= 严格倒序（审查探针一）、
q+tag 双通道组合保序（探针二，§21.6 filter-first＋保序旋钮）、板块页 ?q=
同锚（探针三，同一过滤层）、跨类型合并稳定序（§21.1 五类型各查一次→
Python 稳定降序）。复用 test_search_contract 公共 fixture（TOKEN 与既有
标题零碰撞）。

靶法要点（锚定强度）：①创建序＝期望序 [新, 中, 旧]（pk 随创建递增）——
排序若回归为 rank 平局的 -pk 兜底或时间正序，结果反转为 [旧, 中, 新]，
与期望可区分；②first_published_at 于发布后直改页面表实列（索引条目仅
承载文本匹配，非排序键），且须在任何 save/publish 之后——对象保存会以
内存态覆写直改值；③页面 tags 系 ClusterTaggableManager，set 后须经
save_revision().publish() 落库（类 fixture 同法）——故错峰直改列置最后。
"""

from io import StringIO

from django.core.management import call_command
from notices.models import Tag
from wagtail.models import Page

from tests.helpers import make_guide, make_material, make_notice, past
from tests.test_search_contract import SearchContractTestCase


class OrderingTests(SearchContractTestCase):
    """§21.6/PS-35 第六子句：默认排序＝-first_published_at（列表序敏感）。"""

    TOKEN = "错峰排序靶点通知"

    def _ordered_pks(self, path, params=None):
        """列表序敏感版 _pks——排序断言不得退化为集合比较。"""
        response = self.client.get(path, params or {})
        self.assertEqual(response.status_code, 200)
        key = "search_results" if path == "/search/" else "content_entries"
        return [page.pk for page in response.context[key]]

    def _hit(self, maker, container, slug):
        return maker(container, slug=slug, title=self.TOKEN, publish=True)

    def _stagger(self, pages):
        """按 [新, 中, 旧] 传入，错峰 0/-24/-48h（直改列＝最后写）并重建索引。"""
        for page, days in zip(pages, (0, 1, 2), strict=True):
            Page.objects.filter(pk=page.pk).update(first_published_at=past(days))
        call_command("update_index", stdout=StringIO())
        return pages

    def _hits(self, maker, prefix):
        """同 token 三页挂 chronicle 容器（创建序＝期望序），错峰后返回 [新, 中, 旧]。"""
        container = self.notice.get_parent().specific
        return self._stagger(
            [self._hit(maker, container, f"{prefix}-{s}") for s in ("new", "mid", "old")]
        )

    def test_search_q_results_strictly_desc(self):
        """审查探针一：/search/?q= 多命中严格 [新, 中, 旧]——rank 不得替换排序。"""
        new, mid, old = self._hits(make_notice, "ord")
        self.assertEqual(self._ordered_pks("/search/", {"q": self.TOKEN}), [new.pk, mid.pk, old.pk])

    def test_q_with_tag_channels_preserve_order(self):
        """审查探针二：q+tag 组合经 slug/name 双通道仍保序（filter-first＋保序旋钮）。"""
        tag = Tag.objects.create(name="排序锚", slug="order-anchor")
        container = self.notice.get_parent().specific
        pages = [self._hit(make_notice, container, f"ordt-{s}") for s in ("new", "mid", "old")]
        for page in pages:
            page.tags.set([tag])
            page.save_revision().publish()
        new, mid, old = self._stagger(pages)
        for value in (tag.slug, tag.name):
            with self.subTest(tag=value):
                self.assertEqual(
                    self._ordered_pks("/search/", {"q": self.TOKEN, "tag": value}),
                    [new.pk, mid.pk, old.pk],
                )

    def test_section_page_q_preserves_order(self):
        """审查探针三：板块页 ?q= 同锚（同一过滤层，content_entries 序）。"""
        new, mid, old = self._hits(make_notice, "ords")
        self.assertEqual(
            self._ordered_pks("/chronicle/", {"q": self.TOKEN}), [new.pk, mid.pk, old.pk]
        )

    def test_cross_type_merge_strictly_desc(self):
        """§21.1 五类型各查一次→Python 稳定合并：跨类型命中仍 [新, 中, 旧]。"""
        new, mid, old = self._stagger(
            [
                self._hit(make_guide, self.guide.get_parent().specific, "ordx-new"),
                self._hit(make_material, self.material.get_parent().specific, "ordx-mid"),
                self._hit(make_notice, self.notice.get_parent().specific, "ordx-old"),
            ]
        )
        self.assertEqual(self._ordered_pks("/search/", {"q": self.TOKEN}), [new.pk, mid.pk, old.pk])
