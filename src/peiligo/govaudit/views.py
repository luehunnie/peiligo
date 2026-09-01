"""F-08B：治理审计总览（§10 最小只读入口）。

/admin/gov-audit/——按时间倒序列 auth.User/Group 的全部审计行
（含 CRUD 主行与治理明细行），支持 操作者/动作/对象类型/日期 基本筛选。
单对象时间线走官方 /admin/users/<pk>/history/；本页补组对象与跨对象
查询面。权限门＝矩阵 §4 R1 行权面（is_superuser 或 auth.change_user /
auth.change_group）；部门内容账号不含。
"""

from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.log_actions import registry as log_registry
from wagtail.models import ModelLogEntry


class GovAuditIndexView(WagtailAdminTemplateMixin, ListView):
    """治理审计总览：只读列表＋GET 基本筛选（不新增任何写路径）。"""

    model = ModelLogEntry
    template_name = "govaudit/index.html"
    paginate_by = 25
    page_title = "治理审计"

    def get_queryset(self):
        # wagtail 页面走 PageLogEntry 另表；ModelLogEntry 表内 auth.*
        # 即用户/组治理全部行。
        qs = (
            ModelLogEntry.objects.filter(content_type__app_label="auth")
            .select_related("user", "content_type")
            .order_by("-timestamp", "-id")
        )
        get = self.request.GET
        if get.get("action"):
            qs = qs.filter(action=get["action"])
        if get.get("actor"):
            try:
                qs = qs.filter(user_id=int(get["actor"]))
            except (TypeError, ValueError):
                pass  # 非法 actor（非数字）即忽略该筛选，与日期同口径不 500
        if get.get("target") in ("user", "group"):
            qs = qs.filter(content_type__model=get["target"])
        for param, lookup in (
            ("date_from", "timestamp__date__gte"),
            ("date_to", "timestamp__date__lte"),
        ):
            value = get.get(param, "")
            try:
                qs = qs.filter(**{lookup: value}) if value else qs
            except (ValueError, TypeError):
                pass  # 非法日期即忽略该筛选，不 500
        return qs

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (
            user.is_superuser
            or user.has_perm("auth.change_user")
            or user.has_perm("auth.change_group")
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actions = (
            ModelLogEntry.objects.filter(content_type__app_label="auth")
            .values_list("action", flat=True)
            .distinct()
        )
        labels = dict(log_registry.get_choices())
        context["page_subtitle"] = "用户/组治理操作留痕（R-05）"
        context["action_choices"] = sorted((a, labels.get(a, a)) for a in actions)
        context["actor_choices"] = (
            ModelLogEntry.objects.filter(content_type__app_label="auth")
            .exclude(user=None)
            .values_list("user_id", "user__username")
            .distinct()
        )
        context["get_params"] = self.request.GET
        return context
