"""M5.1 admin 保守美化（Wagtail 官方定制点，admin-zh 契约 §3）。

唯一动作：``insert_global_admin_css`` 钩子向全部 Wagtail admin 页面
注入 ``static/css/admin.css``（中文优先字体栈等小幅样式，构造见该文件
头注释）。品牌名沿用 settings 的 ``WAGTAIL_SITE_NAME = "peiligo"``
（契约：保留品牌名不造中文名），故不在此改名。禁改导航结构与模板。
"""

from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("insert_global_admin_css", order=100)
def global_admin_css():
    """注入 admin 专属样式（仅 /admin/ 页面，前台零影响）。"""
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin.css"))
