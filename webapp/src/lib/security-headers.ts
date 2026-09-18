// 安全响应头单一出处（SPEC-001-F10 契约 3：安全 parity）。数值逐字对齐 v1：
//   - CSP＝v1 src/peiligo/csp.py CSP_POLICY 逐字节相同（Phase 9 发布安全门；
//     严格 CSP：无 unsafe-inline/unsafe-eval）；
//   - HSTS＝v1 settings/production.py F-10 终态（max-age 一年＋includeSubDomains、
//     无 preload），且仅 https 生效——等价 Django SecurityMiddleware 的
//     request.is_secure() 门（经本站 Caddy 时 X-Forwarded-Proto 由 Caddy 覆写，
//     客户端不可伪造；TLS 终结属 B03 生产接线）；
//   - 其余四项＝Django 5.2 SecurityMiddleware 缺省行为（nosniff /
//     X-Frame-Options: DENY / Referrer-Policy: same-origin / COOP: same-origin），
//     与 v1 /legacy/ 实测响应一致（docs/evidence/f11-staging/headers.txt）。
// 消费方：src/middleware.ts（全部 SSR 响应盖章，不覆盖既有值＝v1 setdefault
// 同语义）。Astro 前端不伺服管理面（Caddyfile.staging 路由表归 Django），
// 故无需 v1 中间件的管理面前缀豁免。测试：tests/unit/security-headers.test.ts
// ＋ e2e security-headers.spec（含 CSP 浏览器实弹拦截探针）。

/** v1 src/peiligo/csp.py CSP_POLICY 逐字等价。 */
export const CSP_POLICY =
  "default-src 'self'; " +
  "script-src 'self'; " +
  "style-src 'self'; " +
  "img-src 'self' data:; " +
  "font-src 'self'; " +
  "connect-src 'self'; " +
  "object-src 'none'; " +
  "base-uri 'self'; " +
  "frame-ancestors 'self'; " +
  "form-action 'self'";

/** v1 settings/production.py F-10 终态值（冻结口径：无 preload）。 */
export const HSTS_POLICY = "max-age=31536000; includeSubDomains";

/** 恒盖章的非文档安全头（小写 name，与 Headers API 大小写无关但统一口径）。 */
export const SECURITY_HEADERS: Record<string, string> = {
  "content-security-policy": CSP_POLICY,
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "same-origin",
  "cross-origin-opener-policy": "same-origin",
};

/** Django request.is_secure() 等价判定：协议为 https，或请求经可信反代转发自
 *  https（本站拓扑 Caddy 恒覆写 X-Forwarded-Proto，等价 v1
 *  SECURE_PROXY_SSL_HEADER 的信任模型）。 */
export function isSecureRequest(
  protocol: string,
  forwardedProto: string | null,
): boolean {
  return protocol === "https:" || forwardedProto === "https";
}

/** 公开 origin（robots.txt Sitemap 行／sitemap.xml loc 绝对化用）。host 取
 *  请求 Host（Astro node 适配器按 Host 头构建 request.url，含非标端口，
 *  v1 request.get_host() 同口径）；scheme 按 isSecureRequest 同一信任模型
 *  ——生产经 Caddy TLS 终结时 X-Forwarded-Proto: https ⇒ 输出 https 绝对
 *  地址（v1 SECURE_PROXY_SSL_HEADER 同语义；纯 http 直连时无转发头，
 *  回退 http，本地/staging 行为逐字节不变）。 */
export function publicOrigin(url: URL, forwardedProto: string | null): string {
  const scheme = isSecureRequest(url.protocol, forwardedProto)
    ? "https"
    : "http";
  return `${scheme}://${url.host}`;
}
