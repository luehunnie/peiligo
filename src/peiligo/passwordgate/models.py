"""F-05R（SB §2.4 ①）：密码设定时刻属性。

单字段状态表（非 profile 大表）：
- 行不存在         → 密码从未经后台动线设置（ORM/CLI 播种、createsuperuser
                     等程序路径）→ 不拦截；
- 行存在、时刻为空 → 总管理员已在后台设置/重置该账号密码、用户尚未
                     自行改密（SB §2.4 ②置空语义）→ 强制改密；
- 行存在、时刻有值 → 用户已完成改密（含首登改密，SB §2.4 ④同机制）。

不存任何口令派生物，只有时刻；删除用户随 CASCADE 清理。
"""

from django.conf import settings
from django.db import models


class PasswordState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="password_state",
        verbose_name="用户",
    )
    password_last_set = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="密码设定时刻",
        help_text="为空＝后台设置/重置后尚未改密（强制改密中）。",
    )

    class Meta:
        verbose_name = "密码状态"
        verbose_name_plural = "密码状态"

    def __str__(self):
        return f"PasswordState(user={self.user_id}, password_last_set={self.password_last_set!r})"
