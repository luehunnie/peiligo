import { expect, test, type APIRequestContext } from "@playwright/test";
import { stubMedia } from "./helpers/media";
import { assertNoHorizontalOverflow } from "./helpers/assert";

// E9 预览消费页（SPEC-001 契约 openapi /preview 描述＋ADR-0008 §3.1）。
// 被测对象＝pages/preview.astro 的 Astro 侧义务：
//   - 正面：带票据 200 同模板渲染草稿（ContentArticle＋BaseLayout＋五型
//     body class），义务响应头 no-store / X-Robots-Tag: noindex /
//     Referrer-Policy: no-referrer 在位，全站安全头（CSP 等）照章盖章，
//     HTML 面 robots meta noindex 双保险；
//   - 负面：缺票/无效·过期·复用·越权票据（上游契约 404）/上游 500/
//     契约违约——一律同一样式化 404 失败闭合，无草稿数据外泄，不区分
//     原因（与 Django 兑换端点同口径防预言机）；
//   - 预览永不回退陈旧结果（NEVER_STALE 面）：成功后票据失效即 404，
//     绝不出旧草稿。
// 票据铸造/绑定/时效/权限校验本身（Django 侧）由 tests/test_api_preview.py
// 与 test_api_security.py 覆盖；经 Wagtail 后台真实铸造的浏览器全链路在
// 集成栈验证（PRODUCTION_RUNBOOK §12 切换前核验）。
// 票据值非空即可：mock 对任意 token 回草稿夹具——票据校验是 Django 职责。

const MOCK = "http://127.0.0.1:4319";
const TOKEN = "e2e-preview-token-not-a-real-signature";
const PREVIEW_URL = `/preview/?token=${TOKEN}`;

async function control(
  request: APIRequestContext,
  body: Record<string, unknown>,
): Promise<void> {
  const res = await request.post(`${MOCK}/__control`, { data: body });
  expect(res.ok()).toBeTruthy();
}

test.afterEach(async ({ request }) => {
  await request.post(`${MOCK}/__control/reset`);
});

test.beforeEach(async ({ page }) => {
  await stubMedia(page);
});

test.describe("预览成功面（同模板渲染草稿）", () => {
  test("带票据 → 200 草稿渲染＋义务响应头＋noindex＋同款 body class", async ({
    page,
    request,
  }) => {
    const res = await page.goto(PREVIEW_URL);
    expect(res?.status()).toBe(200);
    const headers = res!.headers();
    // 响应义务头（页面先置，middleware setdefault 不覆盖）
    expect(headers["cache-control"]).toBe("no-store");
    expect(headers["x-robots-tag"]).toBe("noindex");
    expect(headers["referrer-policy"]).toBe("no-referrer");
    // 全站安全纪律照章在位（严格 CSP 无 unsafe-inline/eval）
    expect(headers["content-security-policy"]).toContain("default-src 'self'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    // 同模板渲染：草稿标题/正文＋站内壳＋正式详情页同款 body class
    await expect(page.locator("h1")).toHaveText(
      "关于图书馆调整开放时间的通知（草稿）",
    );
    await expect(page.locator(".article-body")).toContainText("草稿正文");
    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(page.locator("footer.site-footer")).toBeVisible();
    expect(await page.locator("body").getAttribute("class")).toContain(
      "template-noticepage",
    );
    // HTML 面 noindex 双保险；预览面零 canonical、零脚本（v1 内容页同口径）
    expect(
      await page.locator('meta[name="robots"][content="noindex"]').count(),
    ).toBe(1);
    expect(await page.locator('link[rel="canonical"]').count()).toBe(0);
    expect(await page.locator("script").count()).toBe(0);
    // 每请求直连：本请求恰好一次预览取数
    const counts = (await (await request.get(`${MOCK}/__requests`)).json()) as {
      preview: number;
    };
    expect(counts.preview).toBe(1);
    // 票据不出现在页面任何外发内容（页脚 mailto 隐私覆盖后，DOM 零票据）
    expect(await page.content()).not.toContain(TOKEN);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.screenshot({
      path: "docs/evidence/e9-preview/preview-1440.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: "docs/evidence/e9-preview/preview-390.png",
      fullPage: true,
    });
  });
});

test.describe("失败闭合（无效/过期/复用/越权票据与上游故障同面）", () => {
  test("缺票据 → 样式化 404，且零预览取数", async ({ page, request }) => {
    const res = await page.goto("/preview/");
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    await expect(page.locator("header.site-header")).toBeVisible();
    expect(await page.locator(".article-body").count()).toBe(0);
    // 义务响应头在失败面同样盖章
    expect(res?.headers()["cache-control"]).toBe("no-store");
    expect(res?.headers()["x-robots-tag"]).toBe("noindex");
    expect(res?.headers()["referrer-policy"]).toBe("no-referrer");
    const counts = (await (await request.get(`${MOCK}/__requests`)).json()) as {
      preview: number;
    };
    expect(counts.preview).toBe(0);
  });

  test("无效票据（上游契约 404：无效/过期/复用/越权同应答）→ 同一样式化 404", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "preview", mode: "notfound" });
    const res = await page.goto(PREVIEW_URL);
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    await expect(page.locator("header.site-header")).toBeVisible();
    // 无任何草稿数据外泄（草稿标题/正文不出现在失败面）
    const html = await page.content();
    expect(html).not.toContain("草稿");
    expect(html).not.toContain(TOKEN);
    expect(await page.locator(".article-body").count()).toBe(0);
  });

  test("上游 500 → 仍闭合为同一样式化 404（失败不区分原因，防预言机）", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "preview", mode: "fail" });
    const res = await page.goto(PREVIEW_URL);
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    expect(await page.locator(".article-body").count()).toBe(0);
  });

  test("契约违约（不合 schema 的草稿）→ 同一样式化 404", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "preview", mode: "invalid" });
    const res = await page.goto(PREVIEW_URL);
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    expect(await page.locator(".article-body").count()).toBe(0);
  });

  test("永不回退陈旧预览：成功后票据失效 → 404 而非旧草稿（NEVER_STALE）", async ({
    page,
    request,
  }) => {
    expect((await page.goto(PREVIEW_URL))?.status()).toBe(200);
    await expect(page.locator("h1")).toContainText("草稿");
    // 票据失效（过期/复用作废/会话注销——mock 以 notfound 同应答）
    await control(request, { endpoint: "preview", mode: "notfound" });
    const res = await page.goto(PREVIEW_URL);
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    const html = await page.content();
    expect(html).not.toContain("草稿正文");
  });
});
