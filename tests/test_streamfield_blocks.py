"""A3.1 StreamField 白名单反射测试（CONTENT_MODEL §11）。

- 全站唯一允许集＝六块，块名与行序＝设计表冻结；
- SoftwareTool 收窄＝全集减附件块（不托管安装包，§11.1 末行）；
- RichText features 显式白名单恰为 bold/italic/link/ol/ul（§11.2）；
- RawHTML 全族禁入（§11.1 禁项，CM-07）：块级反射＋源码级扫描双闸。
"""

from pathlib import Path

from django.test import SimpleTestCase
from notices.blocks import CONTENT_BLOCKS, RICHTEXT_FEATURES, SOFTWARE_TOOL_BLOCKS
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from wagtail.blocks import RawHTMLBlock, StreamBlock
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock

REPO_ROOT = Path(__file__).resolve().parents[1]
# RawHTML 源码级扫描范围：全部生产 app＋配置（docs 留痕允许提及禁令本身）。
SOURCE_SCAN_DIRS = ["home", "departments", "notices", "resources", "guides", "src", "templates"]

FROZEN_SIX = ["heading", "paragraph", "image", "attachment", "table", "external_link"]


class BlockWhitelistTests(SimpleTestCase):
    """§11.1：六块白名单逐项反射（块名、行序、块类型）。"""

    def test_content_blocks_are_exactly_six_in_frozen_order(self):
        self.assertEqual([name for name, _ in CONTENT_BLOCKS], FROZEN_SIX)

    def test_block_types_match_design(self):
        by_name = dict(CONTENT_BLOCKS)
        self.assertIsInstance(by_name["image"], ImageChooserBlock)
        self.assertIsInstance(by_name["attachment"], DocumentChooserBlock)
        self.assertIsInstance(by_name["table"], TableBlock)
        # 外链块含 url/link_text 两子字段（§11.1 结构块）。
        self.assertEqual(set(by_name["external_link"].child_blocks.keys()), {"url", "link_text"})
        # 标题块级别仅 h2/h3（页面标题唯一 h1，§11.1）。
        level_choices = by_name["heading"].child_blocks["level"].field.choices
        self.assertEqual({value for value, _ in level_choices}, {"h2", "h3"})

    def test_software_blocks_drop_attachment_only(self):
        """§11.1 末行：软件工具正文＝全集减附件块。"""
        self.assertEqual(
            [name for name, _ in SOFTWARE_TOOL_BLOCKS],
            [name for name in FROZEN_SIX if name != "attachment"],
        )

    def test_richtext_features_whitelist_exact(self):
        """§11.2：features 恰为五项显式清单（无标题/image/文档链接）。"""
        self.assertEqual(RICHTEXT_FEATURES, ["bold", "italic", "link", "ol", "ul"])
        paragraph = dict(CONTENT_BLOCKS)["paragraph"]
        self.assertEqual(paragraph.features, RICHTEXT_FEATURES)
        software_paragraph = dict(SOFTWARE_TOOL_BLOCKS)["paragraph"]
        self.assertEqual(software_paragraph.features, RICHTEXT_FEATURES)

    def test_no_rawhtml_block_in_any_whitelist(self):
        for blocks in (CONTENT_BLOCKS, SOFTWARE_TOOL_BLOCKS):
            for _, block in blocks:
                self.assertNotIsInstance(block, RawHTMLBlock)
                self.assertNotIn("RawHTML", type(block).__name__)

    def test_page_bodies_consume_shared_libraries(self):
        """消费方一律引用共享库，不自建块集（03 计划 §2；§11.1 收口）。"""
        body_fields = {
            model: model._meta.get_field("body")
            for model in (NoticePage, ArticlePage, MaterialPage, SoftwareToolPage)
        }
        for model, field in body_fields.items():
            self.assertIsInstance(field, StreamField)
            stream_block = field.stream_block
            self.assertIsInstance(stream_block, StreamBlock)
            expected = SOFTWARE_TOOL_BLOCKS if model is SoftwareToolPage else CONTENT_BLOCKS
            self.assertEqual(
                list(stream_block.child_blocks.keys()),
                [name for name, _ in expected],
            )
            # min_num 落在 StreamBlock meta 上（stream_block.py:189 校验口径）。
            self.assertEqual(stream_block.meta.min_num, 1, f"{model.__name__}.body 须 min_num=1")


class RawHTMLSourceScanTests(SimpleTestCase):
    """§11.1 禁项源码级核对：生产代码与模板零 RawHTML 字面量。"""

    def test_rawhtml_absent_from_production_source(self):
        files = [
            path
            for directory in SOURCE_SCAN_DIRS
            for pattern in ("*.py", "*.html")
            for path in (REPO_ROOT / directory).rglob(pattern)
        ]
        self.assertGreater(len(files), 0)
        for path in files:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "RawHTML",
                content,
                msg=f"RawHTML 出现在 {path}（CONTENT_MODEL §11.1：原始 HTML 直写全族禁入）",
            )
