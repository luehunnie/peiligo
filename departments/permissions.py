"""权限骨架共享常量与特权判定（ROLE_PERMISSION_MATRIX §3.2/§3.4）。

组名是删除守卫（wagtail_hooks）与初始化命令（init_permissions）的共享
单一事实源：守卫按「总管理员组成员或 superuser」放行永久删除（§3.4
关闭措施），初始化命令按同名骨架建组（§3.2 配置表）。矩阵未钉死组名
字符串，此处取后台中文界面对应称谓（部门组沿矩阵示例 ``dept-<slug>``），
与矩阵的出入登记于工作汇报 OPEN_ITEMS，不改矩阵。
"""

ADMIN_GROUP_NAME = "总管理员"
TECH_GROUP_NAME = "技术维护"
DEPT_GROUP_PREFIX = "dept-"

# 部门组 Django 权限恰一枚：进后台必要条件（矩阵 §3.6；PoC CHECK6 实证
# 部门组权限清单恰为 [wagtailadmin.access_admin]）。
ACCESS_ADMIN_PERMISSION = ("wagtailadmin", "access_admin")

# GPP permission_type 实取 add/change/publish（矩阵 §3.6：不是 edit，
# change 对应 codename change_page）。
PAGE_PERMISSION_TYPES = ("add", "change", "publish")

# 总管理员组 GCP@根集合（§3.2：集合治理只认 GCP 记录，堆 Django 模型
# 权限不生效——A4.2 PoC 发现 3）。
ROOT_COLLECTION_CODENAMES = (
    ("wagtailcore", "add_collection"),
    ("wagtailcore", "change_collection"),
    ("wagtailimages", "add_image"),
    ("wagtailimages", "change_image"),
)

# 部门组 GCP@本部门集合（§3.2 O6：本部门集合内上传/改自己素材）。
DEPT_COLLECTION_CODENAMES = (
    ("wagtailimages", "add_image"),
    ("wagtailimages", "change_image"),
)


def dept_group_name(department) -> str:
    """部门组名（矩阵 §3.2 示例形态 ``dept-<slug>``）。"""
    return f"{DEPT_GROUP_PREFIX}{department.slug}"


def is_privileged(user) -> bool:
    """删除守卫特权判定：superuser（R3 故障恢复通道，M-G5）或总管理员组成员。

    匿名/未认证一律非特权（fail-closed：守卫只拒绝、从不授权，§3.4）。
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=ADMIN_GROUP_NAME).exists()
