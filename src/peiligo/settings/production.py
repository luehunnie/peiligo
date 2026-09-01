import os

from .base import *

DEBUG = False

# A1.1（03 计划 S1）：生产敏感项全部外置环境变量（哑值样例见 .env.example），
# 缺失即快速失败，杜绝以占位值上线。
SECRET_KEY = env_required("SECRET_KEY")

# A1.1（03 计划 S1）：允许主机外置（逗号分隔，剔除空项）。
ALLOWED_HOSTS = [host.strip() for host in env_required("ALLOWED_HOSTS").split(",") if host.strip()]

# F-10（SB §10-1 冻结值）：CSRF 可信来源外置（逗号分隔；形如
# https://host）。Caddy 已按 DOMAIN 收口，此项为 Django 表单保护口径。
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in env_required("CSRF_TRUSTED_ORIGINS").split(",") if origin.strip()
]

# F-10（SB §10-1 冻结值）：会话与 CSRF Cookie 全锁——24h 时效在 base.py、
# SameSite=Lax、仅 HTTPS 传输、会话 Cookie 禁 JS 读取（HttpOnly）。
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True

# F-10（SB §10-1 冻结值）：全站 HTTPS。TLS 由 Caddy 终结（冻结架构），
# 反代层转发头是 is_secure() 的判定来源；显式钉死信任的转发头键值，
# 且只在经代理时生效。SECURE_SSL_REDIRECT 作为直连 gunicorn 的兜底。
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

# F-10：HSTS——终态一年并含子域；不启用 preload（冻结口径：无 preload）。
# 首期可经 HSTS_SECONDS 环境变量取较短观察期（如 3600），终态缺省一年。
SECURE_HSTS_SECONDS = int(os.environ.get("HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

# F-10：SSL 重定向豁免容器健康探针——healthcheck 走容器内回环 http
# （不经 Caddy/TLS），301 到 https 会令探针自指不可达端口而误判。
SECURE_REDIRECT_EXEMPT = [r"^healthz/$", r"^readyz/$"]

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

try:
    from .local import *
except ImportError:
    pass
