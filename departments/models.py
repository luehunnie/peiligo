"""部门受控词表、部门容器与内容页挂载校验核心（CONTENT_MODEL §1.4/§4/§13.1）。

- ``Department``：部门 Snippet（名称/代号/排序/停用，§13.1）；
- ``DepartmentContainerPage``：容器增设 ``department`` 外键（§4 容器绑定）；
- ``clean_content_page`` 等共享校验：五类内容页 clean 公共核心
  （板块白名单 §1.4＋部门一致性 §4），供 notices/resources/guides 复用。
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.http import Http404
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

# 表单类在类体处直接引用（Wagtail base_form_class 无字符串解析）；
# departments.forms 对本模块零顶层依赖（Department 迟导入），无环。
from departments.forms import DepartmentContainerForm


@register_snippet
class Department(models.Model):
    """部门受控词表（CONTENT_MODEL §13.1；ADR-0005 载体表 #7）。

    权限锚点、URL 部门段与内容作者元数据的单一来源；总管理员维护。
    停用即退出新建选择与筛选词表，既有内容展示保留部门名称；
    引用期间删除受 PROTECT 保护（删除政策 DEFERRED_TO_M3_3）。
    """

    name = models.CharField("名称", max_length=100, unique=True)
    slug = models.SlugField("代号（URL 部门段）", max_length=64, unique=True)
    sort_order = models.IntegerField("排序", default=0)
    is_active = models.BooleanField(
        "启用",
        default=True,
        help_text="停用（取消勾选）即退出新建选择与筛选词表；既有内容保留部门名称",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("sort_order"),
        FieldPanel("is_active"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "部门"
        verbose_name_plural = "部门"

    def __str__(self):
        return self.name


def _provisional_parent(page):
    """创建提交流程中由表单注入的父级（CONTENT_MODEL §1.4：
    "创建表单的父容器在提交流程中可得"——注入机制见 departments.forms）。"""
    return getattr(page, "_provisional_parent", None)


def get_parent_container(page, parent_override=None):
    """内容页的（预期）父容器。

    优先级：parent_override（移动路径校验）＞ 树内父级（path 已定位——
    已保存或 add_child 提入树后的 full_clean 期）＞ 表单注入父级（后台
    创建表单校验期）。返回 DepartmentContainerPage（specific）或 None
    （无父级上下文，或父级不是容器——后者由 parent_page_types 结构性排除）。
    """
    if parent_override is not None:
        parent = parent_override
    elif page.path:
        parent = page.get_parent()
    else:
        parent = _provisional_parent(page)
    if parent is None:
        return None
    if not isinstance(parent, DepartmentContainerPage):
        parent = getattr(parent, "specific", parent)
    return parent if isinstance(parent, DepartmentContainerPage) else None


class SectionContextMixin:
    """所属板块推导 property（CONTENT_MODEL §1.4 末段，只读）。

    板块由树位置推导（自身 → 父容器 → 父容器父级＝板块页），无存储字段、
    单一事实源；全站（列表、筛选、前台展示、面包屑）一律消费此推导值。
    """

    @property
    def section_slug(self):
        container = get_parent_container(self)
        if container is None:
            return None
        section = container.get_parent()
        return section.slug if section else None

    @property
    def section_title(self):
        container = get_parent_container(self)
        if container is None:
            return None
        section = container.get_parent()
        return section.title if section else None


def department_clash_exists(container, parent):
    """§4：同一父级下是否已存在绑定同 Department 的容器（排除自身）。

    供容器 ``clean()``（创建/编辑）与移动钩子（目标板块）同口径使用；
    ``parent`` 取板块页（base Page 即含 path/depth）。
    """
    return (
        DepartmentContainerPage.objects.filter(
            path__startswith=parent.path,
            depth=parent.depth + 1,
            department_id=container.department_id,
        )
        .exclude(pk=container.pk)
        .exists()
    )


def clean_content_page(page, errors, parent_override=None, section_override=None):
    """内容页 clean 公共核心（CONTENT_MODEL §1.4/§4）。

    板块白名单：推导所属板块 slug 不在 ``page.ALLOWED_SECTIONS`` 即非字段错误；
    部门一致性：``department`` 必须与父容器绑定部门相等（零漂移，§4）。
    就地向 ``errors``（field→messages）填充并返回所属板块 slug（推导失败 None）。

    ``section_override``：按显式给出的板块 slug 校验——容器整体移动/递归复制时
    子树内容页将随容器换板块，而树内 ``container.get_parent()`` 仍指旧板块，
    故目标板块由调用方（wagtail_hooks）显式传入，与 ``parent_override`` 组合。
    """
    container = get_parent_container(page, parent_override)
    section = None
    if container is not None:
        if section_override is not None:
            section = section_override
        else:
            section_parent = container.get_parent()
            section = section_parent.slug if section_parent else None
        if section not in page.ALLOWED_SECTIONS:
            allowed = "、".join(sorted(page.ALLOWED_SECTIONS))
            errors["__all__"] = [
                f"所属板块“{section}”不在 {type(page).__name__} 允许的板块"
                f"（{allowed}）内（CONTENT_MODEL §1.4）"
            ]
        if page.department_id and page.department_id != container.department_id:
            errors["department"] = ["发布部门必须与本部门容器一致（CONTENT_MODEL §4）"]
    return section


class DepartmentContainerPage(Page):
    """部门容器节点（第 3 层；权限挂载点 + 路由分组，非内容页）。

    落实 ADR-0004 决策 2 与 IA §3 的硬约束——容器节点不构成前台部门主页：

    - 前台访问容器 URL 一律 404（serve 抛 Http404，等效不可达）；
    - 不进导航/默认列表：前台无任何导航/列表消费容器节点；
    - 不进 sitemap：get_sitemap_urls 返回空列表整类排除（IA §10 #5）；
    - 不进默认搜索：``search_fields = []`` 使容器不进入搜索索引。

    A3.1 起容器绑定部门（CONTENT_MODEL §4）：``department`` 外键必填、
    PROTECT；slug 默认取 ``department.slug``（departments.forms 落实）；
    同一板块下不得存在两个指向同一 Department 的容器（clean 兜底）。
    子页＝五类内容页白名单（§1.4 挂载表终态；容器下不得再建容器）。
    """

    # M5.1 admin 中文化：后台展示层类型名（列表/新建选择器/历史）。
    class Meta:
        verbose_name = "部门容器"
        verbose_name_plural = "部门容器"

    parent_page_types = ["home.SectionPage"]  # 仅板块页下，不嵌套容器
    subpage_types = [
        "notices.NoticePage",
        "notices.ArticlePage",
        "resources.MaterialPage",
        "resources.SoftwareToolPage",
        "guides.GuidePage",
    ]
    # slug 默认取 department.slug ＋提交流程父级注入（departments.forms）。
    base_form_class = DepartmentContainerForm

    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="部门")

    content_panels = Page.content_panels + [FieldPanel("department")]

    # 容器无前台页面可预览（serve 恒 404），关闭后台预览（官方机制：preview_modes=[]）。
    preview_modes = []

    # 容器不出现在默认搜索结果（IA-04）：清空搜索索引字段（含基类索引的 title）。
    search_fields = []

    def clean(self):
        super().clean()
        # §4 词源级唯一兜底：同一板块页下不得存在两个指向同一 Department 的容器。
        if self.path:
            parent = self.get_parent()
        else:
            parent = _provisional_parent(self)
        if parent is None:
            return
        if department_clash_exists(self, parent):
            raise ValidationError(
                {"department": ["本板块下已存在绑定该部门的容器（CONTENT_MODEL §4）"]}
            )

    def serve(self, request, *args, **kwargs):
        # 容器 URL 不渲染任何页面（IA §3.2/§4.1：容器段不渲染任何部门聚合页）。
        raise Http404

    def get_sitemap_urls(self, request=None):
        # 容器不出现在 sitemap.xml（IA-03 / IA §3.2、§10 #5）：前台 404 的节点
        # 无可收录页面；返回空列表即整类排除；query 状态页不在页面树，天然不进入。
        return []
