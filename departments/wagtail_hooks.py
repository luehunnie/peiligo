"""页面移动/复制/删除路径的内容模型硬约束兜底（CONTENT_MODEL §1.4/§4/§7.2/§17.4）
与「永久删除仅总管理员」双钩子只拒绝守卫（ROLE_PERMISSION_MATRIX §3.4）。

板块白名单与部门一致性在创建/编辑经 ``clean()`` 生效；树内移动与递归
复制不经编辑表单（wagtail 递归子页 ``save(clean=False)`` 绕过 clean），
故挂官方 ``before_move_page``/``before_copy_page`` 钩子（返回响应即取消
操作，wagtail/admin/views/pages/move.py、copy.py）同口径兜底。
非空结构页拒删（§17.4）挂 ``before_delete_page``（返回响应即取消删除，
wagtail/admin/views/pages/delete.py）与 ``before_bulk_action``（批量删除
动线：``DeleteBulkAction.execute_action`` 直调 ``page.delete()`` 不经单页
钩子，返回响应即在事务内取消整个动作，wagtail/admin/views/bulk_action/
base_bulk_action.py）。直接 ORM ``delete()`` 属产品外路径，删除默认走
下线/到期而非删除（§17.1）。批量移动同理（``MoveBulkAction`` 直调
``page.move()`` 不经 ``before_move_page``），故 ``before_bulk_action``
对 move 与 delete 同口径兜底，规则核心与单页动线共用一套（终审 L-9）。

M4.4 增设权限面守卫（矩阵 §3.4 关闭措施，M4.2 PoC/M4.3 T08 已验证的
最小方案）：Wagtail 页面树权限无独立 delete 类型，``change``@容器附带
子树内任意页删除面（PagePermissionTester.can_delete 对 change 放行），
而 PRD §8 要求永久删除仅总管理员——故以同两条钩子（单条+批量）拒绝
非特权用户的一切页面永久删除。守卫 fail-closed：特权判定
（superuser 或总管理员组成员，departments.permissions）只用于放行，
从不新增授权；非页面模型的批量动作不在守卫面。

H-1（终审，矩阵 M-C3）补充同类只拒绝守卫：结构边界页（首页/板块/部门
容器）是权限边界载体——容器＝GPP 挂载点、板块/首页＝IA 层级节点——
非特权后台账号对三者的编辑面（含 slug/department 等结构字段）经
``before_edit_page`` 服务端整体拒绝（非隐藏 panel 的展示层方案）。
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
from departments.permissions import is_privileged

# 五类内容页（§1.4）：移动目标必须仍是本部门容器，且板块语义不变。
CONTENT_PAGE_CLASSES = (
    NoticePage,
    ArticlePage,
    MaterialPage,
    SoftwareToolPage,
    GuidePage,
)

# 结构边界页（矩阵 M-C3）：权限边界载体，编辑面仅总管理员（H-1 守卫谓词）。
STRUCTURE_PAGE_CLASSES = (HomePage, SectionPage, DepartmentContainerPage)


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


def _move_violation(page, destination):
    """单页/批量移动共用的内容模型规则核心（§1.4/§4/§7.2）。

    返回拒绝文案（None＝放行）。终审 L-9：批量移动（``MoveBulkAction``
    ``execute_action`` 直调 ``page.move()``）不经 ``before_move_page``，
    两条动线必须共用本判定——不复制第二套规则。
    """
    specific = page.specific
    if isinstance(specific, DepartmentContainerPage):
        dest = destination.specific
        if not isinstance(dest, SectionPage):
            return "部门容器只能移动到板块页下（CONTENT_MODEL §1.4）"
        if department_clash_exists(specific, destination):
            return "该板块下已存在绑定此部门的容器（CONTENT_MODEL §4）"
        # 容器移动＝子树随迁换板块：按目标板块复检子树（§1.4 冻结约束为
        # 任何时点树上不存在违约内容页；同板块移动复检平凡通过，不误伤）。
        violation = _subtree_violation(specific, dest.slug)
        if violation:
            return f"容器移动被内容模型校验拒绝：{violation}"
        return None
    if isinstance(specific, CONTENT_PAGE_CLASSES):
        dest = destination.specific
        if not isinstance(dest, DepartmentContainerPage):
            return "公开内容只能挂在本部门容器下（CONTENT_MODEL §1.4）"
        errors = {}
        section = clean_content_page(specific, errors, parent_override=dest)
        if isinstance(specific, (NoticePage, ArticlePage)):
            # §7.2：跨板块移动时活动字段必填性随目标板块变化，同口径复校。
            specific.clean_event_fields(section, errors)
        if errors:
            detail = "；".join(msg for msgs in errors.values() for msg in msgs)
            return f"移动被内容模型校验拒绝：{detail}"
    return None


@hooks.register("before_move_page")
def enforce_content_model_rules_on_move(request, page, destination):
    """移动前校验：容器仅可移至板块页且不撞部门、子树按目标板块复检；
    内容页仅可移至容器，且目标板块须在本类型白名单内、部门一致、
    活动字段板块语义仍成立（规则核心＝``_move_violation``，批量动线共用）。"""
    violation = _move_violation(page, destination)
    if violation:
        return _cancel_move(request, page, violation)
    return None


@hooks.register("before_bulk_action")
def refuse_illegal_bulk_move(request, action_type, objects, bulk_action):
    """内容模型守卫——批量移动动线（终审 L-9）：与单页移动同一规则核心。

    后台列表勾选移动经 ``MoveBulkAction``（/admin/bulk/wagtailcore/page/
    move/），``execute_action`` 直调 ``page.move()`` 不经
    ``before_move_page``。目的地取确认表单 ``chooser`` 字段（wagtail
    ``BulkAction.form_valid`` 先置 ``cleaned_form`` 再触发本钩子）；
    逐页复检，任一违规即返回响应＝事务内取消整个动作（含同批其余
    页面，与批量删除守卫同口径）。目的地缺失（表单展示期/无目的地
    短路）无移动发生，不拦。
    """
    if action_type != "move":
        return None
    form = getattr(bulk_action, "cleaned_form", None)
    destination = form.cleaned_data.get("chooser") if form is not None else None
    if destination is None:
        return None
    for obj in objects:
        violation = _move_violation(obj, destination)
        if violation:
            messages.error(request, f"批量移动已取消：{violation}")
            return HttpResponseRedirect(reverse("wagtailadmin_home"))
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


# ---------------------------------------------------------------------------
# M4.4（矩阵 §3.4）「永久删除仅总管理员」只拒绝守卫——单条+批量双钩子，
# 缺一不可（批量动线 DeleteBulkAction.execute_action 直调 page.delete()
# 绕过单页钩子）。与上方内容模型守卫共存：任一钩子返回响应即在
# transaction.atomic() 内短路返回并回滚（"零库变更"语义）。
# ---------------------------------------------------------------------------


@hooks.register("before_delete_page")
def refuse_non_admin_page_deletion(request, page):
    """权限面守卫——单页删除动线：非特权用户删除任何页面一律拒绝。

    覆盖矩阵 M-A8/N02（部门岗位账号对任何对象无永久删除权，含自己
    创建/拥有的页面）与 M-B7/M-C5 横向面（外部门/结构对象本就无
    can_delete，此处为纵深防御）。特权用户（superuser 或总管理员组，
    R1 走组权限行权）放行后仍须过 Wagtail 默认 can_delete——守卫从不
    新增授权。
    """
    if is_privileged(request.user):
        return None
    messages.error(
        request,
        f"「{page.title}」未删除：永久删除仅限总管理员（PRD §8；ROLE_PERMISSION_MATRIX §3.4）。",
    )
    return HttpResponseRedirect(reverse("wagtailadmin_explore", args=[page.get_parent().id]))


@hooks.register("before_bulk_action")
def refuse_non_admin_bulk_page_deletion(request, action_type, objects, bulk_action):
    """权限面守卫——批量删除动线：非特权用户的页面批量删除整批取消。

    仅拦 ``delete`` 且批内全为 Page 的动作；词表等非页面模型的批量
    删除不在本守卫面（其模型级权限只授总管理员组，矩阵 §3.2）。
    返回响应即在事务内取消整个动作（含同批其余页面）。
    """
    if action_type != "delete":
        return None
    if not objects or not all(isinstance(o, Page) for o in objects):
        return None
    if is_privileged(request.user):
        return None
    messages.error(
        request,
        f"批量删除已取消：永久删除仅限总管理员（PRD §8；ROLE_PERMISSION_MATRIX §3.4，"
        f"涉及 {len(objects)} 页）。",
    )
    return HttpResponseRedirect(reverse("wagtailadmin_home"))


@hooks.register("before_edit_page")
def refuse_structure_page_edit_for_non_privileged(request, page):
    """权限面守卫——结构边界页编辑动线（矩阵 M-C3；终审 H-1）。

    首页/板块/部门容器是权限边界载体（容器＝GPP 挂载点、板块/首页＝
    IA 层级节点），非特权账号编辑任一结构边界页（含改 slug/department
    等结构字段）一律服务端拒绝。``before_edit_page`` 在 wagtail 默认
    ``can_edit`` 判定之后、表单装配之前触发（GET/POST 同路，
    wagtail/admin/views/pages/edit.py ``EditView.setup``），返回响应即
    取消本次编辑。特权判定复用 ``is_privileged``（superuser 或总管理员
    组，R1 走组权限行权）；守卫只拒绝、从不授权（fail-closed），
    五类内容页编辑不受影响。
    """
    if is_privileged(request.user):
        return None
    if isinstance(page.specific, STRUCTURE_PAGE_CLASSES):
        messages.error(
            request,
            f"「{page.title}」是结构边界页（首页/板块/部门容器），仅总管理员可编辑"
            "（ROLE_PERMISSION_MATRIX M-C3）。",
        )
        return HttpResponseRedirect(reverse("wagtailadmin_explore", args=[page.get_parent().id]))
    return None
