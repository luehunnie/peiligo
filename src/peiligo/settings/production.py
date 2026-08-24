from .base import *

DEBUG = False

# A1.1（03 计划 S1）：生产敏感项全部外置环境变量（哑值样例见 .env.example），
# 缺失即快速失败，杜绝以占位值上线。
SECRET_KEY = env_required("SECRET_KEY")

# A1.1（03 计划 S1）：允许主机外置（逗号分隔，剔除空项）。
ALLOWED_HOSTS = [host.strip() for host in env_required("ALLOWED_HOSTS").split(",") if host.strip()]

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

try:
    from .local import *
except ImportError:
    pass
