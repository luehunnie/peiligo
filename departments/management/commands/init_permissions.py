"""权限骨架初始化（M4.4；ROLE_PERMISSION_MATRIX §3.2 配置表的执行载体）。

按矩阵 §3.2 建三组骨架，幂等可重复（重跑收敛到期望配置、零删除既有
业务数据）：

- 总管理员组：根级 GPP(add/change/publish)＋全量 Django 模型权限（含
  ``bulk_delete_page``——非叶/批量删除需要）＋GCP@根集合
  （add/change_collection、add/change_image——集合治理只认 GCP 记录，
  堆 Django 权限不生效，A4.2 PoC 发现 3）；
- 部门组（每部门一个 ``dept-<slug>``）：GPP(add/change/publish)@本部门
  各容器节点＋Django 权限恰一枚 ``wagtailadmin.access_admin``＋
  GCP(add/change_image)@本部门集合（无则按部门名在根集合下建）；
- 技术维护组：零权限占位（矩阵 §3.2 R3 不入任何 Wagtail 组——加入
  本组不获得任何 CMS 权限，含后台入口）。

附带清理迁移自动创建的默认 Editors/Moderators 组（零成员惰性存在，
M4.3 报告 ④-6 建议初始化清理；有成员则告警跳过）。

账号创建（真实密码禁入库：口令只经 stdin 或环境变量传入，代码与
输出零明文）：

- ``--admin-user <username>``：V1 唯一 R1 账号（非 superuser，组权限
  行权）；总管理员组已有成员则告警跳过；
- ``--dept-user <username> --department <slug>``：R2 岗位账号；部门组
  已有成员则报错（PRD §4.3 每部门至多一个岗位账号）。
- 口令来源：``--password-stdin``（读一行）或环境变量
  ``PEILIGO_INIT_PASSWORD``（默认名，可 ``--password-env`` 改）；两者
  皆缺则拒绝创建（绝不落默认口令）。

用法示例::

    python manage.py init_permissions
    python manage.py init_permissions --admin-user admin --password-stdin < secret.txt
    PEILIGO_INIT_PASSWORD=... python manage.py init_permissions \
        --dept-user jwc --department jwc
"""

import os
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import (
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Page,
)

from departments.models import Department, DepartmentContainerPage
from departments.permissions import (
    ACCESS_ADMIN_PERMISSION,
    ADMIN_GROUP_NAME,
    DEPT_COLLECTION_CODENAMES,
    DEPT_GROUP_PREFIX,
    PAGE_PERMISSION_TYPES,
    ROOT_COLLECTION_CODENAMES,
    TECH_GROUP_NAME,
    dept_group_name,
)

PASSWORD_ENV_DEFAULT = "PEILIGO_INIT_PASSWORD"


def _permission(app_label, codename):
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _page_permission(perm_type: str) -> Permission:
    """页面树权限（GPP.permission 实体）：codename ``{add,change,publish}_page``。

    GPP 的 ``permission_type`` 简写仅 ``create()`` 支持（自定义管理器），
    ``get_or_create()`` 须显式解析 Permission（wagtail/models/pages.py）。
    """
    from wagtail.models import get_default_page_content_type

    return Permission.objects.get(
        content_type=get_default_page_content_type(), codename=f"{perm_type}_page"
    )


class Command(BaseCommand):
    help = (
        "幂等初始化权限骨架：总管理员组/部门组/技术维护组（ROLE_PERMISSION_MATRIX "
        "§3.2）；可选创建账号（口令仅经 --password-stdin 或环境变量传入）"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-user", metavar="USERNAME", help="创建 V1 唯一总管理员账号（入总管理员组）"
        )
        parser.add_argument(
            "--dept-user", metavar="USERNAME", help="创建部门岗位账号（须同时给 --department）"
        )
        parser.add_argument("--department", metavar="SLUG", help="部门岗位账号所属部门 slug")
        parser.add_argument(
            "--password-stdin",
            action="store_true",
            help="从标准输入读一行作为新建账号口令（不入命令行历史）",
        )
        parser.add_argument(
            "--password-env",
            metavar="VARNAME",
            default=PASSWORD_ENV_DEFAULT,
            help=f"口令环境变量名（默认 {PASSWORD_ENV_DEFAULT}）",
        )

    # —— 组骨架（幂等：get_or_create 补齐，不删除既有挂载） ——

    def _ensure_admin_group(self) -> Group:
        group, created = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
        if created:
            self.stdout.write(self.style.SUCCESS(f"创建总管理员组「{ADMIN_GROUP_NAME}」。"))
        group.permissions.set(Permission.objects.all())  # 全治理面（模型级）
        root = Page.get_first_root_node()
        for perm_type in PAGE_PERMISSION_TYPES:  # 根级全树（change 即 change_page）
            GroupPagePermission.objects.get_or_create(
                group=group, page=root, permission=_page_permission(perm_type)
            )
        root_collection = Collection.get_first_root_node()
        for app_label, codename in ROOT_COLLECTION_CODENAMES:
            GroupCollectionPermission.objects.get_or_create(
                group=group,
                collection=root_collection,
                permission=_permission(app_label, codename),
            )
        return group

    def _ensure_tech_group(self) -> Group:
        group, created = Group.objects.get_or_create(name=TECH_GROUP_NAME)
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"创建技术维护组「{TECH_GROUP_NAME}」（零权限占位：不入组亦无任何 CMS 权限）。"
                )
            )
        has_mounts = (
            group.permissions.exists()
            or group.page_permissions.exists()
            or group.collection_permissions.exists()
        )
        if has_mounts:
            group.permissions.set([])  # 收敛回零权限（矩阵 §3.2：R3 无 CMS 权限）
            self.stdout.write(self.style.WARNING("技术维护组曾有权限挂载，已收敛回零权限。"))
        return group

    def _ensure_department_collection(self, department) -> Collection:
        """本部门集合（§3.2 O6：每部门一个；无则按部门名挂根集合下）。"""
        root_collection = Collection.get_first_root_node()
        existing = root_collection.get_children().filter(name=department.name).first()
        if existing is not None:
            return existing
        collection = Collection(name=department.name)
        root_collection.add_child(instance=collection)
        self.stdout.write(
            self.style.SUCCESS(f"创建部门集合「{department.name}」（/{department.slug}）。")
        )
        return collection

    def _ensure_dept_group(self, department) -> tuple[Group, Collection]:
        group, created = Group.objects.get_or_create(name=dept_group_name(department))
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"创建部门组「{dept_group_name(department)}」（{department.name}）。"
                )
            )
        # Django 权限收敛为恰一枚 access_admin（§3.6 实测形态：set() 幂等收敛）
        group.permissions.set([_permission(*ACCESS_ADMIN_PERMISSION)])
        containers = DepartmentContainerPage.objects.filter(department=department)
        for container in containers:
            for perm_type in PAGE_PERMISSION_TYPES:
                GroupPagePermission.objects.get_or_create(
                    group=group, page=container, permission=_page_permission(perm_type)
                )
        collection = self._ensure_department_collection(department)
        for app_label, codename in DEPT_COLLECTION_CODENAMES:
            GroupCollectionPermission.objects.get_or_create(
                group=group,
                collection=collection,
                permission=_permission(app_label, codename),
            )
        return group, collection

    def _prune_default_groups(self) -> None:
        """迁移自动创建的 Editors/Moderators（零成员惰性存在，M4.3 ④-6）。"""
        for name in ("Editors", "Moderators"):
            group = Group.objects.filter(name=name).first()
            if group is None:
                continue
            if group.user_set.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"默认组「{name}」已有成员，保留不清理（请人工核对其授权面）。"
                    )
                )
                continue
            group.delete()
            self.stdout.write(f"清理迁移自动创建的空默认组「{name}」（M4.3 报告 ④-6）。")

    # —— 账号创建（口令只经 stdin/环境变量；零明文输出） ——

    def _read_password(self, options) -> str:
        if options["password_stdin"]:
            value = sys.stdin.readline().rstrip("\r\n")
            source = "--password-stdin（读到空行）"
        else:
            env_name = options["password_env"]
            value = os.environ.get(env_name, "")
            source = f"环境变量 {env_name}"
        if value:
            return value
        raise CommandError(
            f"未提供口令：请用 --password-stdin 或设置环境变量 {options['password_env']}"
            f"（真实密码禁入库/入命令行历史，不设默认口令；本次 {source}）。"
        )

    def _create_account(self, username: str, group: Group, password: str) -> None:
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"用户「{username}」已存在，跳过创建（不改动其属性与分组）。")
            )
            return
        user = user_model.objects.create_user(
            username=username, password=password, is_staff=False, is_active=True
        )
        user.groups.add(group)
        self.stdout.write(
            self.style.SUCCESS(
                f"创建账号「{username}」并入组「{group.name}」（非 superuser，组权限行权）。"
            )
        )

    def handle(self, *args, **options):
        if options["dept_user"] and not options["department"]:
            raise CommandError("--dept-user 须同时给 --department <slug>。")

        admin_group = self._ensure_admin_group()
        self._ensure_tech_group()

        departments = Department.objects.order_by("sort_order", "name")
        dept_groups: dict[str, Group] = {}
        for department in departments:
            group, _collection = self._ensure_dept_group(department)
            dept_groups[department.slug] = group
        self.stdout.write(
            f"部门组就位 {len(dept_groups)} 个（{DEPT_GROUP_PREFIX}<slug>×"
            f"{len(PAGE_PERMISSION_TYPES)} 权限类型挂本部门各容器＋GCP@本部门集合）。"
        )

        self._prune_default_groups()

        # 账号创建：先统一装载口令（缺失即快速失败，不建一半）
        password = None
        if options["admin_user"] or options["dept_user"]:
            password = self._read_password(options)
        if options["admin_user"]:
            if admin_group.user_set.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"总管理员组已有成员（{admin_group.user_set.count()} 个），"
                        "跳过 --admin-user（V1 恰一个 R1 账号，PRD §4.2）。"
                    )
                )
            else:
                self._create_account(options["admin_user"], admin_group, password)
        if options["dept_user"]:
            department = Department.objects.filter(slug=options["department"]).first()
            if department is None:
                raise CommandError(
                    f"部门 slug「{options['department']}」不存在（先建 Department 与容器）。"
                )
            group = dept_groups[options["department"]]
            if group.user_set.exists():
                raise CommandError(
                    f"部门「{department.name}」已有岗位账号（{group.user_set.count()} 个）："
                    "每部门至多一个岗位账号（PRD §4.3），交接须重置凭据而非另建。"
                )
            self._create_account(options["dept_user"], group, password)

        self.stdout.write(self.style.SUCCESS("权限骨架初始化完成（幂等，可重复执行）。"))
