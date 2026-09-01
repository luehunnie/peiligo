"""F-05R：强制改密页（/admin/password-change/，经 register_admin_urls
挂入后台并获得 require_admin_access 门禁）。

表单＝Django 原生 PasswordChangeForm（服务端校验旧密码；落库走
set_password，零自建 hashing；密码校验器与后台重置同一套）。改密成功
即：update_session_auth_hash（本会话保持、其余会话按 SB 冻结规则
全部失效）＋密码设定时刻落值（闸门解除）＋结构化事件留痕。
"""

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.utils import timezone
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin

from .models import PasswordState

events_logger = __import__("logging").getLogger("peiligo.events")


class ForcedPasswordChangeView(WagtailAdminTemplateMixin, auth_views.PasswordChangeView):
    template_name = "passwordgate/change.html"
    success_url = reverse_lazy("wagtailadmin_home")
    page_title = "设置新密码"
    page_subtitle = "管理员已设置或重置您的密码，请先设置您自己的新密码再继续使用后台。"

    def form_valid(self, form):
        response = super().form_valid(form)  # set_password＋本会话 auth hash 刷新
        PasswordState.objects.update_or_create(
            user=self.request.user,
            defaults={"password_last_set": timezone.now()},
        )
        events_logger.info(
            "password.forced_change_completed",
            extra={
                "event": "password.forced_change_completed",
                "username": self.request.user.get_username(),
            },
        )
        return response
