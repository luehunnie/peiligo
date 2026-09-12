"""Phase 8D 文章详情壳（article_detail.html）：五类内容页共用同一文章壳。

断言面（final-reference pages/article-detail 转译）：
- 壳结构：面包屑（首页→板块→本页）→板块标签→标题→元信息→（可选封面）
  →正文→「← 返回{板块}」→页脚，五类内容页（通知/文章/资料/软件工具/指南）
  一壳同构；
- 板块身份只出现在板块标签（tone 类，small-text 用 *-deep 可访问色）；
  正文区保持中性，无整页背景着色；
- 封面有则整幅呈现、无则不虚构图片（无占位图/无几何 fallback）；
- 正文块（heading/paragraph/image/external_link）照常渲染，外链块一律
  经确认页包装不裸跳转；
- GuidePage 九字段结构化数据在同一壳内（无 StreamField 正文，零迁移）；
- 软件工具＝普通文章壳＋六项结构化信息（无产品目录/筛选 chips）；
- 无相关内容/上下篇/推荐/浏览数/评论/分享/作者档案（冻结口径）。
"""

import json
import re
import shutil
import tempfile
from urllib.parse import quote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from wagtail.images.models import Image
from wagtail.test.utils import WagtailPageTestCase

from tests.helpers import (
    _save,
    body_json,
    build_sections,
    future,
    make_article,
    make_container,
    make_department,
    make_guide,
    make_material,
    make_notice,
    make_software,
)

# 五类内容页 × 板块身份（SECTION_IDENTITY 冻结口径）：key → (URL 段, 板块
# slug, 板块标题, tone 后缀, 模板 body_class)。
SHELL_CASES = {
    "notice-chronicle": ("chronicle", "chronicle", "校园纪事", "jishi", "template-noticepage"),
    "article-events": ("events", "events", "校园活动", "huodong", "template-articlepage"),
    "material": ("materials", "materials", "学习资料", "ziliao", "template-materialpage"),
    "software": ("software", "software", "软件与工具", "gongju", "template-softwaretoolpage"),
    "guide": ("guide", "guide", "校园指南", "zhinan", "template-guidepage"),
}


def _cover_image(title):
    """真实 PNG 的 Wagtail Image（依赖类级临时 MEDIA_ROOT，源文件存续供
    rendition 生成；类末临时目录清理，不入仓库 media/）。"""
    from tests.permission_helpers import png_bytes

    img = Image(title=title)
    img.file = SimpleUploadedFile("cover.png", png_bytes(), content_type="image/png")
    img.save()
    return img


def _body(*blocks):
    return json.loads(json.dumps(list(blocks)))


class ArticleShellDataTestCase(WagtailPageTestCase):
    """五板块各置一容器与一已发布内容页；类级临时 MEDIA_ROOT 承载封面与
    正文插图源文件及 rendition。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp = tempfile.mkdtemp(prefix="peiligo-shell-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_tmp)
        cls._media_override.enable()
        cls.addClassCleanup(cls._media_override.disable)
        cls.addClassCleanup(shutil.rmtree, cls._media_tmp, ignore_errors=True)

    @classmethod
    def _register(cls, key, section_slug, container, page):
        cls.containers[key] = container
        cls.pages[key] = page
        cls.urls[key] = f"/{section_slug}/{container.slug}/{page.slug}/"

    @classmethod
    def setUpTestData(cls):
        cls.sections = build_sections()
        cls.pages = {}
        cls.containers = {}
        cls.urls = {}
        # chronicle：通知（无封面）
        dept = make_department("纪事部门", "dept-jishi")
        container = make_container(cls.sections["chronicle"], dept)
        cls._register(
            "notice-chronicle",
            "chronicle",
            container,
            make_notice(container, slug="chronicle-notice", title="纪事通知", publish=True),
        )
        # events：文章（活动字段齐备——events 板块 clean 强制，须先备齐再入树）
        from notices.models import ArticlePage

        dept = make_department("活动部门", "dept-huodong")
        container = make_container(cls.sections["events"], dept)
        cls._register(
            "article-events",
            "events",
            container,
            _save(
                ArticlePage(
                    title="活动文章",
                    slug="events-article",
                    summary="测试摘要",
                    department=container.department,
                    event_start_at=future(1),
                    event_end_at=future(2),
                    event_location="大礼堂",
                    body=json.loads(body_json()),
                ),
                container,
                publish=True,
            ),
        )
        # materials：资料（无封面）
        dept = make_department("资料部门", "dept-ziliao")
        container = make_container(cls.sections["materials"], dept)
        cls._register(
            "material",
            "materials",
            container,
            make_material(container, slug="material-page", title="学习资料", publish=True),
        )
        # software：软件工具
        dept = make_department("工具部门", "dept-gongju")
        container = make_container(cls.sections["software"], dept)
        cls._register(
            "software",
            "software",
            container,
            make_software(container, slug="software-page", title="软件工具", publish=True),
        )
        # guide：指南（无 StreamField 正文）
        dept = make_department("指南部门", "dept-zhinan")
        container = make_container(cls.sections["guide"], dept)
        cls._register(
            "guide",
            "guide",
            container,
            make_guide(container, slug="guide-page", title="校园指南", publish=True),
        )
        # 带封面与多类型正文块的文章（正文块/封面渲染断言用）
        dept = make_department("封面部门", "dept-cover")
        container = make_container(cls.sections["chronicle"], dept)
        cover_article = make_article(
            container, slug="cover-article", title="带封面的文章", publish=True
        )
        cover = _cover_image("封面文章·封面")
        cover_article.cover_image = cover
        cover_article.body = _body(
            {"type": "heading", "value": {"text": "使用说明", "level": "h2"}},
            {"type": "paragraph", "value": "<p>这是一段受控富文本正文。</p>"},
            {"type": "image", "value": cover.id},
            {
                "type": "external_link",
                "value": {"url": "https://example.com/doc", "link_text": "参考文档"},
            },
        )
        cover_article.save()
        cls._register("cover-article", "chronicle", container, cover_article)

    def _url(self, key):
        return self.urls[key]

    def _content(self, key):
        response = self.client.get(self._url(key))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()


class ArticleShellStructureTests(ArticleShellDataTestCase):
    """壳结构一致性：五类内容页一壳同构＋板块身份＋返回板块。"""

    def test_shared_shell_landmarks_all_five_types(self):
        for key, (_, section_slug, section_title, _, body_class) in SHELL_CASES.items():
            with self.subTest(page=key):
                html = self._content(key)
                self.assertIn(f'<body class="{body_class}', html)
                self.assertIn('class="content-article"', html)
                self.assertIn("art-head", html)
                self.assertIn(f"<h1>{self.pages[key].title}</h1>", html)
                self.assertIn("<footer", html)
                # 面包屑：首页→板块→本页（本页 aria-current 纯文本）。
                self.assertIn('aria-label="面包屑"', html)
                self.assertIn(f'<a href="/{section_slug}/">{section_title}</a>', html)
                self.assertIn(f'<span aria-current="page">{self.pages[key].title}</span>', html)
                # 返回板块：确定性站内链接（板块 slug 派生）。
                back_link = f'<a href="/{section_slug}/">← 返回{section_title}</a>'
                self.assertIn(back_link, html)

    def test_category_tag_tone_identity(self):
        """板块身份只在板块标签（tone 类）——五板块 tone 后缀各自正确。"""
        for key, (_, _, section_title, tone, _) in SHELL_CASES.items():
            with self.subTest(page=key):
                html = self._content(key)
                self.assertIn(f'<span class="tag tone-{tone}">{section_title}</span>', html)

    def test_no_cover_no_fake_image(self):
        """无封面＝不渲染封面区，也不虚构占位图（仅 art-cover 缺席）。"""
        for key in ("notice-chronicle", "material", "software", "guide"):
            with self.subTest(page=key):
                html = self._content(key)
                self.assertNotIn("art-cover", html)

    def test_no_related_or_prev_next_or_stats(self):
        """冻结口径：无相关内容/上下篇/推荐/浏览数/评论/分享/作者档案。"""
        forbidden = (
            "相关内容",
            "上一篇",
            "下一篇",
            "推荐阅读",
            "浏览量",
            "评论",
            "分享",
            "作者档案",
        )
        for key in SHELL_CASES:
            with self.subTest(page=key):
                html = self._content(key)
                for word in forbidden:
                    self.assertNotIn(word, html)


class ArticleShellContentTests(ArticleShellDataTestCase):
    """壳内内容：指南结构化字段、软件普通文章壳、活动信息、封面与正文块。"""

    def test_guide_structured_fields_in_shell(self):
        """GuidePage 九字段结构化数据在同一壳内（无 StreamField 正文，零迁移）。"""
        html = self._content("guide")
        self.assertIn("guide-fields", html)
        for label in (
            "地点",
            "开放时间",
            "联系方式",
            "责任来源或责任单位",
            "维护方式",
            "最后确认日期或更新时间",
        ):
            self.assertIn(f"<dt>{label}</dt>", html)
        self.assertIn("第一教学楼一层", html)
        # 指南无富文本正文段（helper 的测试段落不应出现）。
        self.assertNotIn("测试正文段落", html)

    def test_software_is_ordinary_article_shell(self):
        """软件工具＝普通文章壳＋六项结构化信息；来源链接经确认页包装；
        无产品目录/筛选 chips/版本元数据。"""
        page = self.pages["software"]
        html = self._content("software")
        self.assertIn("基本信息", html)
        self.assertIn("<dt>适用平台</dt>", html)
        self.assertIn("Windows", html)
        self.assertIn("<dt>来源链接</dt>", html)
        self.assertIn("<dt>授权或费用说明</dt>", html)
        self.assertIn("校园授权，免费使用", html)
        self.assertIn("用途说明", html)
        encoded = quote("https://example.com/tool", safe="/")
        self.assertIn(f"/link-confirm/?url={encoded}&from={page.pk}", html)
        self.assertNotIn('<a href="https://example.com/tool"', html)
        for word in ("产品目录", "筛选", "版本列表"):
            self.assertNotIn(word, html)

    def test_event_info_renders_in_shell(self):
        """events 板块文章：活动信息节随壳渲染（状态/时间/地点）。"""
        html = self._content("article-events")
        self.assertIn('aria-label="活动信息"', html)
        self.assertIn("<dt>开始时间</dt>", html)
        self.assertIn("<dt>活动地点</dt>", html)
        self.assertIn("大礼堂", html)

    def test_cover_image_renders_when_present(self):
        """封面有则整幅呈现（原始比例，无破坏性裁切）。"""
        html = self._content("cover-article")
        self.assertIn("art-cover", html)
        self.assertIn("<figure", html)
        self.assertIn("<img", html)

    def test_body_blocks_render_and_external_link_wrapped(self):
        """正文块照常渲染：标题/段落/图片；外链块一律经确认页包装不裸跳转。"""
        page = self.pages["cover-article"]
        html = self._content("cover-article")
        self.assertIn("<h2>使用说明</h2>", html)
        self.assertIn("<p>这是一段受控富文本正文。</p>", html)
        self.assertIn("block-image", html)
        encoded = quote("https://example.com/doc", safe="/")
        self.assertIn(f"/link-confirm/?url={encoded}&from={page.pk}", html)
        self.assertNotIn('<a href="https://example.com/doc"', html)
        # 板块标签存在且正文区不携带板块 tone 类（身份只入标签）。
        self.assertIn('class="tag tone-jishi"', html)
        article_body = re.search(r'<div class="article-body">.*?</div>', html, re.DOTALL)
        self.assertIsNotNone(article_body)
        self.assertNotIn("tone-jishi", article_body.group(0))
