"""全站页头/页脚上下文（M2.2 前台 IA）：固定清单数据源，零页面树查询。

IA §6.1：一级导航仅=首页+五板块+站内搜索入口（固定七类，顺序按 §2 #1–#5）；
IA §6.2：导航**永不查询、永不渲染部门容器**——导航清单仅消费
``home.models.SECTIONS`` 冻结常量，容器没有进入通道；当前板块项判定供
模板输出 ``aria-current``（§6.1；PRD §13 无障碍）。
反馈邮箱一项（终审 M-1）按站点查 SiteSettings——这是本处理器唯一的
非导航查询面，失败回落 settings.FEEDBACK_EMAIL（见 ``_feedback_email``）。
"""

from django.conf import settings
from home.models import SECTIONS, SiteSettings
from wagtail.models import Site


def _feedback_email(request):
    """反馈邮箱取值（终审 M-1/L-11）：站点设置优先，环境缺省兜底。

    ``SiteSettings.feedback_email``（后台 M-E1 可改，反馈/投稿同源单值）
    非空即用；站点解析失败或设置行缺失（``for_site(None)`` 抛
    ``SiteSettings.DoesNotExist``）等未就绪场景 fail-soft 回落
    ``settings.FEEDBACK_EMAIL``——前台渲染永不因设置缺失而 500。
    """
    try:
        site_value = SiteSettings.for_request(request).feedback_email
    except (SiteSettings.DoesNotExist, Site.DoesNotExist):
        site_value = ""
    return site_value or settings.FEEDBACK_EMAIL


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
        "feedback_email": _feedback_email(request),
    }
