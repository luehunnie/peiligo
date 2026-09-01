from django.apps import AppConfig


class AppLogConfig(AppConfig):
    """F-07 应用日志微 app：只挂信号接收器与包装命令，零模型零迁移。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "peiligo.applog"
    label = "applog"

    def ready(self):
        from peiligo.applog import signals  # noqa: F401  连接即生效
