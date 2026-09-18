// e2e 共享断言（SPEC-001-F07 自 content.spec 上提，两处消费方同口径）：
//   - 横向溢出：documentElement 滚动宽 ≤ 客户端宽（v1 无横向滚动纪律）；
//   - 产物 HTML 不变量（CSP 同等断言，F05 home.spec 口径）：无 <style>
//     内联块、无 style= 内联属性、零脚本（内容/搜索页 v1 零 JS 同口径）、
//     样式表外链、全同源引用。
import { expect, type APIRequestContext, type Page } from "@playwright/test";

const ORIGIN = "http://127.0.0.1:4321";

export async function assertNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(overflow, "文档出现横向溢出").toBeLessThanOrEqual(0);
}

export async function assertStaticHtmlInvariants(
  request: APIRequestContext,
  path: string,
) {
  const resp = await request.get(path);
  expect(resp.status()).toBe(200);
  const html = await resp.text();
  expect(html, "出现 <style> 内联样式块").not.toMatch(/<style[\s>]/i);
  expect(html, "出现 style= 内联样式属性").not.toMatch(/\sstyle="/);
  expect(html, "内容页不应有任何脚本（v1 内容页零 JS）").not.toMatch(
    /<script\b/i,
  );
  expect(html).toContain('rel="stylesheet"');
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]);
  const foreign = refs.filter(
    (ref) => /^https?:\/\//.test(ref) && !ref.startsWith(`${ORIGIN}/`),
  );
  expect(foreign, `出现第三方来源：${foreign.join(", ")}`).toEqual([]);
  return html;
}
