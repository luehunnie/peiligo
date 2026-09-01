"""F-05R（SB §2.4 ②）：把「后台设置/重置密码」动线接入闸门。

挂 Wagtail users 动线官方钩子（before_edit_user/after_edit_user/
after_create_user，签名与 wagtail.users.views.users 一致）：
- 后台编辑用户且密码哈希发生变化（管理员填了新密码＝重置）→ 置空
  密码设定时刻，目标账号强制改密；
- 后台新建用户（表单必填密码）→ 同置空 → 该账号首登即强制改密
  （SB §2.4 ④「首登改密视为同一机制」）；
- 未触碰密码的普通编辑 → 不动状态（零误伤）。

ORM/CLI 路径（create_user/createsuperuser/changepassword）不触发任何
钩子——播种与脚本用户不受闸门影响；需要人工解除时用 break-glass
命令 clear_password_must_change（见 management/commands）。
"""

from django.contrib.auth import get_user_model
from django.urls import path
from wagtail import hooks

from .middleware import needs_forced_password_change  # noqa: F401  供测试复用
from .models import PasswordState


def _flag_for_reset(user):
    """后台密码设置/重置 → 密码设定时刻置空（幂等）。"""
    PasswordState.objects.update_or_create(user=user, defaults={"password_last_set": None})


@hooks.register("before_edit_user")
def stash_password_hash(request, user):
    user._passwordgate_old_hash = (
        get_user_model().objects.filter(pk=user.pk).values_list("password", flat=True).first()
    )


@hooks.register("after_edit_user")
def flag_if_password_reset(request, user):
    old_hash = getattr(user, "_passwordgate_old_hash", None)
    if old_hash is not None and old_hash != user.password:
        _flag_for_reset(user)


@hooks.register("after_create_user")
def flag_on_admin_created(request, user):
    _flag_for_reset(user)


@hooks.register("register_admin_urls")
def register_password_change_url():
    from .views import ForcedPasswordChangeView

    return [
        path(
            "password-change/",
            ForcedPasswordChangeView.as_view(),
            name="passwordgate_change",
        )
    ]
