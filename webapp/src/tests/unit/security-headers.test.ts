// F10 安全头单元测试：与 v1 冻结基线逐项对照（契约 3 parity 的可执行化）。
// v1 基线出处：luehunnie/peiligo src/peiligo/csp.py（CSP_POLICY）与
// src/peiligo/settings/production.py（F-10 HSTS）；nosniff/XFO/Referrer/COOP
// 为 Django 5.2 SecurityMiddleware 缺省（v1 base.py 未显式覆写）。
import { describe, expect, it } from "vitest";
import {
  CSP_POLICY,
  HSTS_POLICY,
  SECURITY_HEADERS,
  isSecureRequest,
} from "../../lib/security-headers";

// v1 src/peiligo/csp.py CSP_POLICY 逐字誊抄（改动任一侧即应红灯）。
const V1_CSP_POLICY =
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

describe("security headers（SPEC-001-F10 安全 parity）", () => {
  it("CSP 与 v1 csp.py CSP_POLICY 逐字节相同", () => {
    expect(CSP_POLICY).toBe(V1_CSP_POLICY);
  });

  it("严格 CSP：无 unsafe-inline / unsafe-eval（契约 3 硬性）", () => {
    expect(CSP_POLICY).not.toContain("unsafe-inline");
    expect(CSP_POLICY).not.toContain("unsafe-eval");
  });

  it("安全头集合与 v1/Django 缺省对齐（恒盖章五项）", () => {
    expect(SECURITY_HEADERS["content-security-policy"]).toBe(V1_CSP_POLICY);
    expect(SECURITY_HEADERS["x-content-type-options"]).toBe("nosniff");
    expect(SECURITY_HEADERS["x-frame-options"]).toBe("DENY");
    expect(SECURITY_HEADERS["referrer-policy"]).toBe("same-origin");
    expect(SECURITY_HEADERS["cross-origin-opener-policy"]).toBe("same-origin");
    expect(Object.keys(SECURITY_HEADERS)).toHaveLength(5);
  });

  it("HSTS 为 v1 F-10 终态：一年＋includeSubDomains、无 preload", () => {
    expect(HSTS_POLICY).toBe("max-age=31536000; includeSubDomains");
    expect(HSTS_POLICY).not.toContain("preload");
  });

  it("isSecureRequest 等价 Django is_secure 门", () => {
    expect(isSecureRequest("https:", null)).toBe(true);
    expect(isSecureRequest("http:", "https")).toBe(true);
    expect(isSecureRequest("http:", null)).toBe(false);
    expect(isSecureRequest("http:", "http")).toBe(false);
  });
});
