"""F-07 关键后台业务事件 → 结构化日志（SB §6.2 脱敏纪律）。

事件面（event 稳定码）：
- ``auth.login`` / ``auth.login_failed`` / ``auth.logout``：Django auth 信号；
- ``auth.locked_out``：axes 锁定信号（SB §6.3 监控点的取数源，F-13 告警消费）；
- ``content.published`` / ``content.unpublished``：Wagtail 页面信号
  （定时发布经 publish_scheduled 走同一 publish 链路，自然入日志）。

身份口径＝SB §6.2 #3：仅岗位账号名（username），不记姓名；IP 取
REMOTE_ADDR，无请求时缺省 "-"。接收器一律只传明确小字典，绝不倾倒
请求体/凭据/环境变量（脱敏第一层），JsonFormatter 敏感键清洗为第二层。
"""

import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from wagtail.signals import page_published, page_unpublished

logger = logging.getLogger("peiligo.events")


def _client_ip(request):
    meta = getattr(request, "META", None) or {}
    return meta.get("REMOTE_ADDR") or "-"


def _username_from_user(user):
    name = getattr(user, "username", None)
    return name if name else "-"


def handle_user_logged_in(sender, request, user, **kwargs):
    logger.info(
        "后台登录成功",
        extra={
            "event": "auth.login",
            "username": _username_from_user(user),
            "ip": _client_ip(request),
        },
    )


def handle_user_login_failed(sender, credentials, request=None, **kwargs):
    username = (credentials or {}).get("username") or "-"
    logger.warning(
        "后台登录失败",
        extra={"event": "auth.login_failed", "username": username, "ip": _client_ip(request)},
    )


def handle_user_logged_out(sender, request, user, **kwargs):
    logger.info(
        "后台登出",
        extra={
            "event": "auth.logout",
            "username": _username_from_user(user),
            "ip": _client_ip(request),
        },
    )


def handle_locked_out(sender, request, username=None, ip_address=None, **kwargs):
    logger.warning(
        "登录限速锁定（axes）",
        extra={
            "event": "auth.locked_out",
            "username": username or "-",
            "ip": str(ip_address) if ip_address else "-",
        },
    )


def _page_data(page, revision=None):
    """页面事件元数据（内容元信息，非敏感正文；身份仅 username）。"""
    revision_id = getattr(revision, "pk", None)
    user = getattr(revision, "user", None)
    return {
        "page_id": page.pk,
        "title": page.title,
        "slug": page.slug,
        "revision_id": revision_id,
        "username": _username_from_user(user),
    }


def handle_page_published(sender, instance, revision=None, **kwargs):
    logger.info("页面发布", extra={"event": "content.published", **_page_data(instance, revision)})


def handle_page_unpublished(sender, instance, **kwargs):
    logger.info("页面下线", extra={"event": "content.unpublished", **_page_data(instance)})


user_logged_in.connect(handle_user_logged_in, dispatch_uid="applog.user_logged_in")
user_login_failed.connect(handle_user_login_failed, dispatch_uid="applog.user_login_failed")
user_logged_out.connect(handle_user_logged_out, dispatch_uid="applog.user_logged_out")

# axes 锁定信号：soft-import——axes 恒在 INSTALLED_APPS（F-05），缺依赖即 fail-fast。
from axes.signals import user_locked_out  # noqa: E402

user_locked_out.connect(handle_locked_out, dispatch_uid="applog.user_locked_out")

page_published.connect(handle_page_published, dispatch_uid="applog.page_published")
page_unpublished.connect(handle_page_unpublished, dispatch_uid="applog.page_unpublished")
