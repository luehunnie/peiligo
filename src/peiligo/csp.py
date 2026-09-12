"""Phase 9 · 最小 CSP 响应头中间件（发布安全门 C 项落地）。

全仓审计事实（Phase 9）：前台模板零 inline <script>、零 inline 事件处理、
零 javascript: URL、零 <style>/style= 内联样式、零远程资源（脚本/字体/
CSS/图片全部本地 static/media，SVG 图标为 HTML 内联但不受 CSP 约束）；
Wagtail 7.4 前台 userbar 亦仅加载同源 JS 文件。故公开页面可与 restrictive
CSP 完全兼容。

范围收口：/admin/ 与 /django-admin/ 豁免——Wagtail 管理界面自带 inline
脚本（React 侧栏/表单组件），收紧将破坏后台；后台由登录＋axes＋
PasswordChangeGate 把守，与前台风险面隔离。策略取任务基线（default-src
'self' 起、object-src 'none'、frame-ancestors/form-action/base-uri 'self'），
另显式 connect-src/script-src/style-src/font-src 'self'、img-src
'self' data:。原生中间件实现（不引入第三方 CSP 包）。

中间件置于 MIDDLEWARE 首位（SecurityMiddleware 之后）：响应相位由外向内，
内层短路响应（axes 锁定、PasswordGate 强制改密）同样被盖章。
"""

CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'self'; "
    "form-action 'self'"
)

# 管理面前缀豁免（含 passwordgate 等经 register_admin_urls 挂载的路由）。
EXEMPT_PREFIXES = ("/admin/", "/django-admin/")


class ContentSecurityPolicyMiddleware:
    """公开响应加 Content-Security-Policy；管理面前缀豁免。幂等盖章
    （setdefault，不覆盖既有头）。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(EXEMPT_PREFIXES):
            response.headers.setdefault("Content-Security-Policy", CSP_POLICY)
        return response
