from django.apps import AppConfig


class GovAuditConfig(AppConfig):
    """F-08B（R-05 方案 B）：用户/组治理操作 DB 级审计。

    零自建模型：存储、字段、时间线 UI 全部复用 Wagtail 官方 log_actions
    基础设施（ModelLogEntry ＋ require_admin_access 的 LogContext ＋
    History 视图）。本 app 只做三件事——注册 auth.User/Group 与治理
    明细动作、挂变更明细信号、提供治理总览只读页。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "peiligo.govaudit"
    label = "govaudit"

    def ready(self):
        from peiligo.govaudit import receivers, wagtail_hooks  # noqa: F401
