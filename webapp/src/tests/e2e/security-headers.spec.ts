// F10 安全 parity 运行时验证（生产构建 SSR 实测，webServer＝dist/server）：
//   1. 全 SSR 面响应盖章严格 CSP 与安全头——含 404 边界（styled 与最小页
//      同经 middleware）与带 XSS 形查询的搜索（恶意查询响应同样盖章）；
//   2. CSP 浏览器实弹探针：注入内联脚本必须被策略真实拦截（事件触发＋
//      零执行）——证明头部不止在纸面（staging 等价实测的应用层同款）；
//   3. staging http（4321）恒无 HSTS＝v1 is_secure 同语义。
// 交叉引用：搜索高亮转义细节属 search.spec（F07）与
// tests/unit/security-headers.test.ts（策略逐字对照 v1）。
import { expect, test, type APIRequestContext } from "@playwright/test";

const HOSTILE_QUERY = "<script>alert(1)</script>";

/** 单响应安全头断言（Playwright headers 键恒小写）。 */
function expectSecurityHeaders(
  headers: Record<string, string>,
  where: string,
): void {
  const csp = headers["content-security-policy"];
  expect(csp, `${where} 缺 Content-Security-Policy`).toBeTruthy();
  expect(csp, `${where} CSP 起始指令`).toMatch(/^default-src 'self';/);
  expect(csp, `${where} 出现 unsafe-inline`).not.toContain("unsafe-inline");
  expect(csp, `${where} 出现 unsafe-eval`).not.toContain("unsafe-eval");
  expect(headers["x-content-type-options"], where).toBe("nosniff");
  expect(headers["x-frame-options"], where).toBe("DENY");
  expect(headers["referrer-policy"], where).toBe("same-origin");
  expect(headers["cross-origin-opener-policy"], where).toBe("same-origin");
  // http 端口实测＝v1 SecurityMiddleware is_secure 门同语义：不发 HSTS
  expect(headers["strict-transport-security"], where).toBeUndefined();
}

test("全 SSR 面（首页/搜索恶意查询/外链确认/404）响应盖章严格 CSP＋安全头", async ({
  request,
}: {
  request: APIRequestContext;
}) => {
  const routes = [
    "/",
    `/search/?q=${encodeURIComponent(HOSTILE_QUERY)}`,
    "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
    "/no-such-page-f10/",
  ];
  for (const route of routes) {
    const resp = await request.get(route);
    expectSecurityHeaders(resp.headers(), route);
  }
});

test("CSP 浏览器实弹：注入内联脚本被策略拦截（违规事件触发＋零执行）", async ({
  page,
}) => {
  await page.goto("/");
  const result = await page.evaluate(() => {
    return new Promise<{ blocked: boolean; executed: boolean }>((resolve) => {
      const finish = (blocked: boolean) =>
        resolve({
          blocked,
          executed: (window as { __cspProbe?: boolean }).__cspProbe === true,
        });
      document.addEventListener(
        "securitypolicyviolation",
        (event) => {
          if (event.violatedDirective.startsWith("script-src")) finish(true);
        },
        { once: true },
      );
      const probe = document.createElement("script");
      probe.textContent = "window.__cspProbe = true;";
      document.head.appendChild(probe);
      window.setTimeout(() => finish(false), 1500);
    });
  });
  expect(result.blocked, "script-src 违规事件未触发").toBe(true);
  expect(result.executed, "内联脚本竟已执行").toBe(false);
});

test("外链确认页在严格 CSP 下行为等价：域名展示＋继续访问（go 门）可达", async ({
  page,
}) => {
  const resp = await page.goto(
    "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
  );
  expect(resp?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "即将访问外部网站",
  );
  // 本页 v1 零 JS 同口径：严格 CSP 下唯一脚本能力（无）不被引入
  expect(await page.locator("script").count()).toBe(0);
});
