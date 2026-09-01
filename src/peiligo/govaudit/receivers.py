"""F-08B：变更明细留痕——信号与批量动作钩子。

CRUD 主行（wagtail.create/edit/delete）由 Wagtail generic 视图原生写入；
此处只补「变更明细」与批量动作缺口：
- User.groups m2m_changed        → 组员变动（正反向两个触发面都落行）；
- Group.permissions m2m_changed  → 组 Django 权限逐项变更；
- GroupPagePermission 行级信号   → 组页面权限变更（formset 删旧建新）；
- after_bulk_action 钩子         → 用户批量启停（queryset.update 绕过
  generic 视图，不触信号）；批量删除由 post_delete 兜底覆盖；
- User/Group post_delete 兜底    → generic 视图已先行写 wagtail.delete
  （同请求同 uuid）则去重跳过，其余删除路径（批量/shell）照记。

actor 口径（§9 不伪造）：一律由 registry.log 从 LogContext 取真实请求
操作者；无请求上下文（shell/migrate 播种等）时照记变更，但 user 置空、
data.actor_type='non_request' 显式标注操作者未知——绝不写成 system。
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from wagtail import hooks
from wagtail.log_actions import get_active_log_context, log
from wagtail.models import ModelLogEntry
from wagtail.models.pages import GroupPagePermission

from peiligo.govaudit.wagtail_hooks import (
    GROUP_PERMS_CHANGED,
    MEMBERSHIP_CHANGED,
    PAGE_PERMS_CHANGED,
    USER_STATE_CHANGED,
)

_CHANGE_VERB = {"post_add": "加入", "post_remove": "移除", "post_clear": "清空"}

User = get_user_model()


def _log_detail(instance, action, summary, **data):
    """写治理明细行；actor/uuid 交给 registry（有请求上下文则自动带）。"""
    in_request = get_active_log_context().user is not None
    log(
        instance,
        action,
        data={
            "summary": summary,
            "actor_type": "request" if in_request else "non_request",
            **data,
        },
    )


def _names(queryset):
    return sorted(queryset.values_list("name", flat=True))


# --- 组员变动（User.groups；反向 group.user_set.add 走同一张 through 表） --


@receiver(m2m_changed, sender=User.groups.through, dispatch_uid="govaudit.user_groups")
def handle_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    if action not in _CHANGE_VERB:
        return
    group_names = _names(Group.objects.filter(pk__in=pk_set or []))
    if isinstance(instance, User):
        # 正向：user.groups.add(...)——target＝该用户，逐组列名。
        summary = (
            f"{_CHANGE_VERB[action]}组：{'、'.join(group_names)}" if group_names else "清空全部组"
        )
        _log_detail(instance, MEMBERSHIP_CHANGED, summary, groups=group_names, change=action)
    else:
        # 反向：group.user_set.add(...)（如批量指派角色）——逐用户落行，
        # target 仍是被变更的用户（成员归属方）。
        for user in User.objects.filter(pk__in=pk_set or []):
            for name in group_names:
                _log_detail(
                    user,
                    MEMBERSHIP_CHANGED,
                    f"{_CHANGE_VERB[action]}组：{name}",
                    groups=[name],
                    change=action,
                )


# --- 组 Django 权限逐项变更（GroupForm permissions 复选框） ----------------


@receiver(m2m_changed, sender=Group.permissions.through, dispatch_uid="govaudit.group_perms")
def handle_group_permissions_changed(sender, instance, action, pk_set, **kwargs):
    if action not in _CHANGE_VERB:
        return
    perms = (
        Permission.objects.filter(pk__in=pk_set or [])
        .select_related("content_type")
        .values_list("content_type__app_label", "codename")
    )
    names = [f"{app_label}.{codename}" for app_label, codename in perms]
    summary = f"{_CHANGE_VERB[action]}{'、'.join(names)}" if names else "清空全部权限"
    _log_detail(instance, GROUP_PERMS_CHANGED, summary, permissions=names, change=action)


# --- 组页面权限（GroupPagePermission 行级；formset 删旧建新，无更新动线） --


def _page_perm_desc(perm):
    return f"{perm.permission.codename} → {perm.page.title}"


def _page_perm_data(perm):
    return {"page": perm.page.title, "permission": perm.permission.codename}


@receiver(post_save, sender=GroupPagePermission, dispatch_uid="govaudit.group_page_perm_save")
def handle_group_page_permission_saved(sender, instance, created, **kwargs):
    if not created:
        return  # 无更新动线：权限 formset 删旧建新
    _log_detail(
        instance.group,
        PAGE_PERMS_CHANGED,
        f"授予页面权限：{_page_perm_desc(instance)}",
        **_page_perm_data(instance),
    )


@receiver(
    post_delete,
    sender=GroupPagePermission,
    dispatch_uid="govaudit.group_page_perm_del",
)
def handle_group_page_permission_deleted(sender, instance, **kwargs):
    _log_detail(
        instance.group,
        PAGE_PERMS_CHANGED,
        f"移除页面权限：{_page_perm_desc(instance)}",
        **_page_perm_data(instance),
    )


# --- 用户批量启停（queryset.update 绕过信号；批量删除由 post_delete 兜底） -


@hooks.register("after_bulk_action")
def handle_user_bulk_active_state(request, action_type, objects, action):
    if action_type != "set_active_state" or action.model is not User:
        return
    state = "启用" if action.cleaned_form.cleaned_data["mark_as_active"] else "停用"
    for user in objects:
        _log_detail(user, USER_STATE_CHANGED, f"批量{state}", active=state == "启用")


# --- 删除兜底（视图路径去重；批量/shell 路径照记） -------------------------


def _log_delete(instance):
    """对象删除留痕：generic 视图已先行写 wagtail.delete（同请求同 uuid）→ 跳过。"""
    ctx = get_active_log_context()
    ct = ContentType.objects.get_for_model(instance, for_concrete_model=False)
    duplicated = (
        ctx.uuid
        and ModelLogEntry.objects.filter(
            uuid=ctx.uuid,
            action="wagtail.delete",
            content_type=ct,
            object_id=str(instance.pk),
        ).exists()
    )
    if duplicated:
        return
    log(instance, "wagtail.delete", deleted=True)


@receiver(post_delete, sender=User, dispatch_uid="govaudit.user_deleted")
def handle_user_deleted(sender, instance, **kwargs):
    _log_delete(instance)


@receiver(post_delete, sender=Group, dispatch_uid="govaudit.group_deleted")
def handle_group_deleted(sender, instance, **kwargs):
    _log_delete(instance)
