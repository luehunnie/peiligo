// 全响应安全头盖章（SPEC-001-F10 契约 3；v1 csp.py 中间件同语义：
// setdefault 不覆盖既有值，内层短路响应——404/500 最小页、失败态——同样被
// 盖章）。HSTS 仅 https（v1 SecurityMiddleware is_secure 门同语义）。
// 页面返回裸 Response（lib/responses.ts 最小 500/404 页）时 headers 仍可变
// （构造器创建的 Response guard＝response），此处统一补写安全。
import { defineMiddleware } from "astro:middleware";
import {
  HSTS_POLICY,
  SECURITY_HEADERS,
  isSecureRequest,
} from "./lib/security-headers";

export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    if (!response.headers.has(name)) {
      response.headers.set(name, value);
    }
  }
  if (
    !response.headers.has("strict-transport-security") &&
    isSecureRequest(
      context.url.protocol,
      context.request.headers.get("x-forwarded-proto"),
    )
  ) {
    response.headers.set("strict-transport-security", HSTS_POLICY);
  }
  return response;
});
