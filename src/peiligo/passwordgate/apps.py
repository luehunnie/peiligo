"""F-05R（SB §2.4）：强制改密闸门微 app。

职责单一：总管理员在后台设置/重置密码后，目标账号必须先自行改密才可
继续使用后台（PRD §5「重置后必须强制修改密码；不得使用长期统一默认
密码」的机制落地）。非第二套认证系统——登录/凭据校验/hashing 全部
仍是 Django 原生（ModelBackend＋AUTH_PASSWORD_VALIDATORS），本 app
只在「密码由他人设定」这一状态上做服务端路由级拦截。
"""

from django.apps import AppConfig


class PasswordGateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "peiligo.passwordgate"
    label = "passwordgate"
    verbose_name = "密码闸门（F-05R）"

    def ready(self):
        from . import wagtail_hooks  # noqa: F401  注册后台动线钩子与改密路由
