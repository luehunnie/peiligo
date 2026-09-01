"""F-05R（SB §2.4 ③）：后台入口强制改密中间件（服务端路由级）。

已登录且密码未设定（PasswordState.password_last_set 为空）的用户访问
任意路由时，一律 302 到改密页，直到改密完成；改密页与登出端点除外
（否则无法自救退出）。匿名请求不经过本闸门——登录仍走 Django/Wagtail
原生流程，axes 前置闸门不受影响。

路径口径与 src/peiligo/urls.py 的挂载点耦合（admin/ 前缀＋
register_admin_urls 注册的 password-change/）。
"""

from django.http import HttpResponseRedirect
from django.urls import reverse

# 闸门放行清单：改密页本身＋登出（被强制改密者必须仍能登出）。
# DEBUG 静态/媒体由 runserver 直供，同列放行；生产由 Caddy 直供不经此。
GATE_EXEMPT_PATHS = frozenset(
    {
        "/admin/password-change/",
        "/admin/logout/",
    }
)
_GATE_STATIC_PREFIXES = ("/static/", "/media/")


def needs_forced_password_change(user):
    """行存在且密码设定时刻为空 ⇒ 强制改密中（见 models 模块口径）。"""
    from .models import PasswordState

    return PasswordState.objects.filter(user=user, password_last_set__isnull=True).exists()


class PasswordChangeGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and request.path not in GATE_EXEMPT_PATHS
            and not request.path.startswith(_GATE_STATIC_PREFIXES)
            and needs_forced_password_change(user)
        ):
            return HttpResponseRedirect(reverse("passwordgate_change"))
        return self.get_response(request)
