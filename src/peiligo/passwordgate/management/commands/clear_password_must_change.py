"""F-05R：break-glass 解除强制改密（运维恢复路径）。

仅用于运维通道（服务器 shell），典型场景：账号被后台重置后持有人
无法完成改密、或自动化脚本账号被误置闸门。解除＝把密码设定时刻记
为现在（不是伪造「密码正确」，而是显式的、留痕的人工裁定）。

用法：python manage.py clear_password_must_change --username <账号>
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from peiligo.passwordgate.models import PasswordState


class Command(BaseCommand):
    help = "解除指定账号的强制改密闸门（把密码设定时刻记为现在；仅限运维恢复）。"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="目标账号名")

    def handle(self, *args, **options):
        username = options["username"]
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"账号不存在：{username}")
        state, created = PasswordState.objects.get_or_create(user=user)
        state.password_last_set = timezone.now()
        state.save(update_fields=["password_last_set"])
        self.stdout.write(
            self.style.WARNING(
                f"已解除 {username} 的强制改密闸门"
                f"（password_last_set={state.password_last_set.isoformat()}）。"
                "此操作属人工裁定，请确认有相应运维授权。"
            )
        )
