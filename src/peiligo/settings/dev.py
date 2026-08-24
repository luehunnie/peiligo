from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# A1.1（03 计划 S1）：密钥外置环境变量（哑值样例见 .env.example）——官方模板
# 内联 insecure 密钥不再是基线；未设置时快速失败。
SECRET_KEY = env_required("SECRET_KEY")

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass
