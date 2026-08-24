"""页面移动/复制/删除路径的内容模型硬约束兜底（CONTENT_MODEL §1.4/§4/§7.2/§17.4）。

板块白名单与部门一致性在创建/编辑经 ``clean()`` 生效；树内移动与递归
复制不经编辑表单（wagtail 递归子页 ``save(clean=False)`` 绕过 clean），
故挂官方 ``before_move_page``/``before_copy_page`` 钩子（返回响应即取消
操作，wagtail/admin/views/pages/move.py、copy.py）同口径兜底。
非空结构页拒删（§17.4）挂 ``before_delete_page``（返回响应即取消删除，
wagtail/admin/views/pages/delete.py）与 ``before_bulk_action``（批量删除
动线：``DeleteBulkAction.execute_action`` 直调 ``page.delete()`` 不经单页
钩子，返回响应即在事务内取消整个动作，wagtail/admin/views/bulk_action/
base_bulk_action.py）。直接 ORM ``delete()`` 属产品外路径，删除默认走
下线/到期而非删除（§17.1）。
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from guides.models import GuidePage
from home.models import HomePage, SectionPage
from notices.models import ArticlePage, NoticePage
from resources.models import MaterialPage, SoftwareToolPage
from wagtail import hooks
from wagtail.models import Page

from departments.models import (
    DepartmentContainerPage,
    clean_content_page,
    department_clash_exists,
)

# 五类内容页（§1.4）：移动目标必须仍是本部门容器，且板块语义不变。
CONTENT_PAGE_CLASSES = (
    NoticePage,
    ArticlePage,
    MaterialPage,
    SoftwareToolPage,
    GuidePage,
)


def _cancel_move(request, page, error_text):
    messages.error(request, error_text)
    return HttpResponseRedirect(reverse("wagtailadmin_explore", args=[page.get_parent().id]))


def _subtree_violation(container, section_slug):
    """容器子树内容页按目标板块同口径复检（§1.4/§4/§7.2）。

    容器跨板块移动/递归复制＝子树内容页整体换板块：对每个内容页子页
    （§1.4：容器子页恰五类且内容页均叶子，直接子页即全部内容页子树）
    以目标板块 slug 复跑 clean 公共核心＋活动字段规则；返回首个违规
    描述（无违规 None）。部门一致性以本容器为准（复制件保留同部门）。
    """
    for child in container.get_children().specific():
        if not isinstance(child, CONTENT_PAGE_CLASSES):
            continue  # 防御性跳过：subpage_types 白名单外子页不应存在
        errors = {}
        section = clean_content_page(
            child, errors, parent_override=container, section_override=section_slug
        )
        if isinstance(child, (NoticePage, ArticlePage)):
            child.clean_event_fields(section, errors)
        if errors:
            detail = "；".join(msg for msgs in errors.values() for msg in msgs)
            return f"子页「{child.title}」：{detail}"
    return None


@hooks.register("before_move_page")
def enforce_content_model_rules_on_move(request, page, destination):
    """移动前校验：容器仅可移至板块页且不撞部门、子树按目标板块复检；
    内容页仅可移至容器，且目标板块须在本类型白名单内、部门一致、
    活动字段板块语义仍成立。"""
    specific = page.specific
    if isinstance(specific, DepartmentContainerPage):
        dest = destination.specific
        if not isinstance(dest, SectionPage):
            return _cancel_move(request, page, "部门容器只能移动到板块页下（CONTENT_MODEL §1.4）")
        if department_clash_exists(specific, destination):
            return _cancel_move(request, page, "该板块下已存在绑定此部门的容器（CONTENT_MODEL §4）")
        # 容器移动＝子树随迁换板块：按目标板块复检子树（§1.4 冻结约束为
        # 任何时点树上不存在违约内容页；同板块移动复检平凡通过，不误伤）。
        violation = _subtree_violation(specific, dest.slug)
        if violation:
            return _cancel_move(request, page, f"容器移动被内容模型校验拒绝：{violation}")
        return None
    if isinstance(specific, CONTENT_PAGE_CLASSES):
        dest = destination.specific
        if not isinstance(dest, DepartmentContainerPage):
            return _cancel_move(request, page, "公开内容只能挂在本部门容器下（CONTENT_MODEL §1.4）")
        errors = {}
        section = clean_content_page(specific, errors, parent_override=dest)
        if isinstance(specific, (NoticePage, ArticlePage)):
            # §7.2：跨板块移动时活动字段必填性随目标板块变化，同口径复校。
            specific.clean_event_fields(section, errors)
        if errors:
            detail = "；".join(msg for msgs in errors.values() for msg in msgs)
            return _cancel_move(request, page, f"移动被内容模型校验拒绝：{detail}")
    return None


def _section_subtree_violation(section, new_slug):
    """板块页递归复制的子树复检（§1.4/§4/§7.2）。

    复制件板块 slug＝new_slug，其下各容器子树逐一经容器复检口径复跑
    （伪 slug 不属任何内容页白名单即全拒；同 slug 复制在合法父级必撞
    CopyForm slug 唯一性，等效于禁递归复制出伪板块，复审附记 F-4）。
    """
    for container in section.get_children().specific():
        if not isinstance(container, DepartmentContainerPage):
            continue  # 防御性跳过：subpage_types 白名单外子页不应存在
        violation = _subtree_violation(container, new_slug)
        if violation:
            return f"容器「{container.title}」的{violation}"
    return None


@hooks.register("before_copy_page")
def enforce_content_model_rules_on_copy(request, page):
    """递归复制/递归别名容器、递归复制板块页前校验（§1.4/§4/§7.2）。

    wagtail 递归复制/别名的子页经 ``save(clean=False)`` 绕过 clean
    （wagtail/actions/copy_page.py、create_alias.py），且本钩子在表单
    校验前触发（wagtail/admin/views/pages/copy.py）——故仅 POST 期读
    表单值，非法值一律跳过交表单校验报错；单页（非递归）复制/别名的
    顶层经 ``add_child()`` 全链 clean，无需此处兜底。

    - 容器（复制或别名）：按目标板块页 slug 复检子树；
    - 板块页（仅复制——递归别名只造指向原页的别名行、不复制内容页
      记录，不计违约内容页，复审附记口径）：按复制件 slug＝new_slug
      复检各容器子树。
    """
    if request.method != "POST":
        return None  # 表单展示期（GET）无表单值，不拦截
    if not request.POST.get("copy_subpages"):
        return None  # 仅复制页自身：新页无子页，顶层 add_child→clean 兜底
    specific = page.specific
    if isinstance(specific, DepartmentContainerPage):
        parent_id = request.POST.get("new_parent_page")
        if not parent_id:
            return None  # 缺目标父级交由表单校验报错
        try:
            dest = Page.objects.get(pk=parent_id).specific
        except (ValueError, Page.DoesNotExist):
            return None  # 父级 pk 非数字/不存在：交由表单校验报错，不在此 500（F-5）
        if not isinstance(dest, SectionPage):
            return None  # 非板块页父级由 CopyForm 页面选择器与顶层 clean 兜底
        subject = "容器复制"
        violation = _subtree_violation(specific, dest.slug)
    elif isinstance(specific, SectionPage):
        if request.POST.get("alias"):
            return None  # 递归别名板块页不复制内容页记录（复审附记），不拦截
        new_slug = request.POST.get("new_slug")
        if not new_slug:
            return None  # 缺 slug 交由表单校验报错
        subject = "板块复制"
        violation = _section_subtree_violation(specific, new_slug)
    else:
        return None
    if violation:
        messages.error(request, f"{subject}被内容模型校验拒绝：{violation}")
        return HttpResponseRedirect(reverse("wagtailadmin_pages:copy", args=[page.id]))
    return None


def _is_nonempty_structure_page(page):
    """§17.4 拒删谓词：结构页（首页/板块/容器）且其下有任何子页面。

    单页与批量两条删除动线共用同一判定（PS-29）；内容页为叶子
    （§1.4 ``subpage_types=[]``）恒不命中，无子树删除面（§17.2/§17.3）。
    """
    specific = page.specific
    if not isinstance(specific, (HomePage, SectionPage, DepartmentContainerPage)):
        return False
    return page.get_children().exists()


def _cancel_nonempty_structure_deletion(request, page):
    """统一拒删响应：错误提示＋回到该页父级列表（§17.4）。"""
    messages.error(
        request,
        f"「{page.title}」下仍有子页面，不能删除：请先迁移子内容或逐条处理（CONTENT_MODEL §17.4）",
    )
    return HttpResponseRedirect(reverse("wagtailadmin_explore", args=[page.get_parent().id]))


@hooks.register("before_delete_page")
def refuse_nonempty_structure_page_deletion(request, page):
    """非空结构页拒删（CONTENT_MODEL §17.4；PS-29）——单页删除动线。

    容器下有内容页、板块页下有容器、首页下有板块＝"非空"，删除即整子树
    硬删（treebeard 连带子树、不可恢复，§17.2），一律拒绝；须先迁移子
    内容或按 §17.2 逐条处理。返回响应即取消删除
    （wagtail/admin/views/pages/delete.py 同 move/copy 钩子口径）。
    """
    if _is_nonempty_structure_page(page):
        return _cancel_nonempty_structure_deletion(request, page)
    return None


@hooks.register("before_bulk_action")
def refuse_nonempty_structure_page_bulk_deletion(request, action_type, objects, bulk_action):
    """非空结构页拒删（CONTENT_MODEL §17.4；PS-29）——批量删除动线。

    后台列表勾选删除经 ``DeleteBulkAction``（wagtail 默认注册，URL
    /admin/bulk/wagtailcore/page/delete/），其 ``execute_action`` 直调
    ``page.delete()`` 不经 ``before_delete_page``；``before_bulk_action``
    返回响应即在事务内取消整个动作（含同批其余页面，wagtail/admin/
    views/bulk_action/base_bulk_action.py ``form_valid``）。谓词与单页
    动线同一（``_is_nonempty_structure_page``）。仅拦 ``delete`` 类型；
    非页面模型的批量动作（词表等）不属本约束面（§17.2/PS-27）。
    """
    if action_type != "delete":
        return None
    for obj in objects:
        # 先按"有子页面"短路：叶子（含全部内容页）零谓词成本即放行。
        if not isinstance(obj, Page) or not obj.get_children().exists():
            continue
        if _is_nonempty_structure_page(obj):
            return _cancel_nonempty_structure_deletion(request, obj)
    return None
