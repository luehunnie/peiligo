"""ORM 模型注册入口。

import 本包即注册 Content / AdminUser 到 Base.metadata。
"""

from app.database import Base
from app.models.admin_user import AdminUser
from app.models.content import Content

__all__ = ["Base", "Content", "AdminUser"]
