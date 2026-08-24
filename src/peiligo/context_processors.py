"""全站页头/页脚上下文（M2.2 前台 IA）：固定清单数据源，零页面树查询。

IA §6.1：一级导航仅=首页+五板块+站内搜索入口（固定七类，顺序按 §2 #1–#5）；
IA §6.2：导航**永不查询、永不渲染部门容器**——本处理器仅消费
``home.models.SECTIONS`` 冻结常量，不触数据库，容器没有进入通道；
当前板块项判定供模板输出 ``aria-current``（§6.1；PRD §13 无障碍）。
"""

from django.conf import settings
from home.models import SECTIONS


def site_chrome(request):
    """页头导航固定清单 + 当前板块 slug + 页脚反馈邮箱与站名。"""
    current_section_slug = None
    for section in SECTIONS:
        section_path = f"/{section['slug']}/"
        if request.path == section_path or request.path.startswith(section_path):
            current_section_slug = section["slug"]
            break
    return {
        "nav_sections": SECTIONS,
        "current_section_slug": current_section_slug,
        "site_brand": settings.WAGTAIL_SITE_NAME,
        "feedback_email": settings.FEEDBACK_EMAIL,
    }
