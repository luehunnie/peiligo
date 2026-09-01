"""共享受控 StreamField Block 库（CONTENT_MODEL §11.1）。

全站 StreamField 唯一允许集＝六块：标题/受控富文本段落/图片/附件/表格/外链；
白名单之外一律不得出现（B 阶段以本库收口并以测试反射断言）。本模块不定义、
不导入任何原始 HTML 直写块（§11.1 禁项，CM-07）。

app 归属沿 03 计划 §2：notices 承载"通知、文章、活动 + 共享受控 Block 库"；
MaterialPage/ArticlePage 等消费方一律引用本模块常量，不自建块集。
"""

from wagtail.blocks import CharBlock, ChoiceBlock, RichTextBlock, StructBlock, URLBlock
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from peiligo.link_validation import validate_external_url

# RichText features 显式白名单（CONTENT_MODEL §11.2）：
# 编辑器工具条与入库内容转换双层收窄；排除各级标题（结构经标题块单轨）、
# image（插图经图片块）、文档链接 feature（附件经附件块）及 PRD 未要求项。
RICHTEXT_FEATURES = ["bold", "italic", "link", "ol", "ul"]


class HeadingBlock(StructBlock):
    """标题块（§11.1）：CharBlock＋级别 choices，仅 h2/h3（页面标题已是唯一 h1）。"""

    text = CharBlock(label="标题文字")
    level = ChoiceBlock(
        choices=[("h2", "H2（次级标题）"), ("h3", "H3（三级标题）")],
        default="h2",
        label="级别",
    )

    class Meta:
        icon = "title"
        label = "标题"
        template = "blocks/heading.html"


class ParagraphBlock(RichTextBlock):
    """正文段落块（§11.1）：受控富文本，features=§11.2 清单。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("features", RICHTEXT_FEATURES)
        super().__init__(**kwargs)

    class Meta:
        icon = "pilcrow"
        label = "正文段落"


class ImageBlock(ImageChooserBlock):
    """图片块（§11.1）：插图经 Wagtail 图片库治理。"""

    class Meta:
        icon = "image"
        label = "图片"
        template = "blocks/image.html"


class AttachmentBlock(DocumentChooserBlock):
    """附件块（§11.1）：文档附件（上传策略＝全站 WAGTAILDOCS 配置，§11.3）。"""

    class Meta:
        icon = "doc-full"
        label = "附件"
        template = "blocks/attachment.html"


class ExternalLinkBlock(StructBlock):
    """外链块（§11.1）：文内外部链接，存原始 URL；输出安全语义见 §11.4。"""

    url = URLBlock(label="链接地址", validators=[validate_external_url])
    link_text = CharBlock(label="链接文字")

    class Meta:
        icon = "link"
        label = "外部链接"
        template = "blocks/external_link.html"


# 全站 StreamField 唯一允许集（§11.1 六块，顺序＝设计表行序）。
CONTENT_BLOCKS = [
    ("heading", HeadingBlock()),
    ("paragraph", ParagraphBlock()),
    ("image", ImageBlock()),
    ("attachment", AttachmentBlock()),
    ("table", TableBlock(label="表格")),
    ("external_link", ExternalLinkBlock()),
]

# 类型级收窄（§11.1 末行）：SoftwareToolPage.body＝全集减附件块（不托管安装包）。
SOFTWARE_TOOL_BLOCKS = [
    ("heading", HeadingBlock()),
    ("paragraph", ParagraphBlock()),
    ("image", ImageBlock()),
    ("table", TableBlock(label="表格")),
    ("external_link", ExternalLinkBlock()),
]
