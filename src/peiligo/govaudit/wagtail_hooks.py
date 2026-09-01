"""F-08B：官方 log registry 注册 ＋ 治理总览入口。

注册后（SB §6.1 R-05 方案 B 落地）：
- auth.User/Group 的后台 CRUD 由 Wagtail generic 视图原生写入
  ModelLogEntry——action 用官方 wagtail.create/edit/delete，actor 来自
  require_admin_access 激活的 LogContext（真实请求操作者，§9 不伪造）；
- /admin/users/<pk>/history/ 官方 History 视图即刻可用（User viewset
  自带 history 路由）；
- 审计行凭 content_type＋object_id 指向对象，对象删除后行不消失
  （BaseLogEntry.user FK＝DO_NOTHING，§8 删除可追溯）。

CRUD 主行动作用官方码；治理明细动作（组员/权限逐项变更）自注册为
``peiligo.gov.*``，message 由 data['summary'] 渲染。
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.log_actions import LogFormatter
from wagtail.models import ModelLogEntry

MEMBERSHIP_CHANGED = "peiligo.gov.membership_changed"
GROUP_PERMS_CHANGED = "peiligo.gov.group_permissions_changed"
PAGE_PERMS_CHANGED = "peiligo.gov.group_page_permissions_changed"
USER_STATE_CHANGED = "peiligo.gov.user_active_state_changed"


class _DetailFormatter(LogFormatter):
    """message 渲染 data['summary']（History 列表即治理台账）。"""

    def format_message(self, log_entry):
        detail = (log_entry.data or {}).get("summary", "")
        return f"{self.message}：{detail}" if detail else self.message


def _detail_action(action, label, message):
    def register(cls_registry):
        formatter = type("_GovFormatter", (_DetailFormatter,), {"label": label, "message": message})
        cls_registry.register_action(action)(formatter)

    return register


@hooks.register("register_log_actions")
def register_gov_audit_actions(actions):
    actions.register_model(get_user_model(), ModelLogEntry)
    actions.register_model(Group, ModelLogEntry)
    _detail_action(MEMBERSHIP_CHANGED, "组员变动", "组员变动")(actions)
    _detail_action(GROUP_PERMS_CHANGED, "组权限变更", "组权限变更")(actions)
    _detail_action(PAGE_PERMS_CHANGED, "组页面权限变更", "组页面权限变更")(actions)
    _detail_action(USER_STATE_CHANGED, "账号启停", "账号启停")(actions)


@hooks.register("register_admin_urls")
def register_gov_audit_urls():
    from peiligo.govaudit.views import GovAuditIndexView

    return [path("gov-audit/", GovAuditIndexView.as_view(), name="govaudit")]


@hooks.register("register_settings_menu_item")
def register_gov_audit_menu_item():
    return MenuItem(
        "治理审计",
        reverse("govaudit"),
        name="govaudit",
        icon_name="history",
        order=900,
    )


@hooks.register("construct_settings_menu")
def hide_gov_audit_without_governance_perms(request, menu_items):
    # 独立审查 P2 修复：入口按 R1 行权面过滤（与 GovAuditIndexView.dispatch
    # 同一条件），无权限账号不再看到点了才被拒的菜单项。
    user = request.user
    if not (
        user.is_superuser or user.has_perm("auth.change_user") or user.has_perm("auth.change_group")
    ):
        menu_items[:] = [item for item in menu_items if item.name != "govaudit"]
