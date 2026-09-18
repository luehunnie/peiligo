import { expect, test, type APIRequestContext } from "@playwright/test";
import { stubMedia } from "./helpers/media";
import { assertNoHorizontalOverflow } from "./helpers/assert";

// SPEC-001-F08 验收（Issue #10）：错误/空状态的样式化统一处理 + 恢复行为。
// 逐项覆盖：未匹配路由与容器 URL 的样式化 404（v1 templates/404.html 同
// 口径：壳 + 引导链接）；内容失败注入 → 站内壳样式化失败态（F08 统一
// FailureState，状态 500，刷新重试出路）；恢复后同一 URL 下一请求即 live
// 内容（契约 4/5）；普通内容 ≤5min 陈旧回退的浏览器可见行为（契约 4）；
// chrome 失败＝全站取数边界 → v1 最小 500/无壳 404；外链确认（永不陈旧
// 面）失败绝不回退陈旧确认页；/healthz 探针恒 200（healthcheck 友好）。
// 截图存 docs/evidence/f08-error-states/ 供视觉门评审对照（390 为主档）。

const MOCK = "http://127.0.0.1:4319";

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

test.describe("样式化 404（v1 templates/404.html 等价）", () => {
  test("未匹配路由 → 站内壳 404：H1/引导文案/板块直达链接，状态 404", async ({
    page,
  }) => {
    const res = await page.goto("/f08-not-a-page/");
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    await expect(page.locator("main p")).toContainText(
      "你访问的地址不存在或已移动",
    );
    // v1 引导清单：站内搜索 + 五板块 + 返回首页（.section-links 药丸链接）
    const links = page.locator("ul.section-links a");
    await expect(links).toHaveCount(7);
    await expect(links.first()).toHaveText("站内搜索");
    await expect(links.nth(1)).toHaveAttribute("href", "/chronicle/");
    await expect(links.last()).toHaveText("返回首页");
    // 站内壳完整（页头/页脚）；v1 404 页无 noindex meta（HTTP 状态即信号）
    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(page.locator("footer.site-footer")).toBeVisible();
    expect(await page.locator('meta[name="robots"]').count()).toBe(0);
    expect(await page.locator("body").getAttribute("class")).toContain(
      "template-404",
    );
    // v1 内容页零 JS 同口径：404 页零脚本、零内联样式
    expect(await page.locator("script").count()).toBe(0);
    expect(await page.locator("[style]").count()).toBe(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator("ul.section-links")).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: "docs/evidence/f08-error-states/404-390.png",
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.screenshot({
      path: "docs/evidence/f08-error-states/404-1440.png",
      fullPage: true,
    });
  });

  test("容器 URL（未知内容 slug）→ 契约 not_found 封装 → 同一样式化 404", async ({
    page,
  }) => {
    const res = await page.goto("/chronicle/jwc/f08-bogus-slug/");
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(page.locator("ul.section-links a")).toHaveCount(7);
  });
});

test.describe("内容失败注入 → 样式化失败态与恢复（契约 4/5）", () => {
  // 陈旧回退按完整 URL（含查询串）取键：本 spec 用当次运行唯一的探针
  // 查询串保证该键从未成功过——失败必然无陈旧版本可回退，直达失败态。
  const probeQ = `f08-probe-${Date.now()}`;
  const probeUrl = `/chronicle/?q=${probeQ}`;

  test("列表失败且无陈旧版本 → 站内壳失败态（500）：标题/alert/刷新重试", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "section-list", mode: "fail" });
    const res = await page.goto(probeUrl);
    expect(res?.status()).toBe(500);
    await expect(page.locator("h1")).toHaveText("内容暂时无法加载");
    await expect(page.getByRole("alert")).toContainText(
      "内容服务出现临时故障，请稍后重试。",
    );
    // 站内壳保留；零成功态伪装（无列表行/空态/页头大搜索）
    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(page.locator("footer.site-footer")).toBeVisible();
    expect(await page.locator("a.r-row").count()).toBe(0);
    expect(await page.locator(".empty-state, .big-search").count()).toBe(0);
    // 可操作出路：刷新重试＝原样重放本请求；返回首页
    await expect(page.locator(".fail-home a").first()).toHaveAttribute(
      "href",
      probeUrl,
    );
    await expect(page.locator(".fail-home a").last()).toHaveAttribute(
      "href",
      "/",
    );
    expect(await page.locator("script").count()).toBe(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: "docs/evidence/f08-error-states/failure-390.png",
      fullPage: true,
    });
  });

  test("恢复后同一 URL 下一请求即 live 内容（自动回到实时内容）", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "section-list", mode: "fail" });
    expect((await page.goto(probeUrl))?.status()).toBe(500);
    await control(request, { endpoint: "section-list", mode: "ok" });
    // 刷新重试路径：原样重放（与 .fail-home「刷新重试」链接同语义）
    const res = await page.goto(probeUrl);
    expect(res?.status()).toBe(200);
    await expect(page.locator("h1")).not.toContainText("内容暂时无法加载");
    await expect(page.locator("a.r-row").first()).toBeVisible();
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({
      path: "docs/evidence/f08-error-states/recovery-768.png",
      fullPage: true,
    });
  });

  test("普通内容 ≤5min 陈旧回退（浏览器可见行为）：失败仍出最近成功版本", async ({
    page,
    request,
  }) => {
    // 预热：同键先成功一次（建立「最近成功版本」）
    const detailUrl = "/chronicle/jwc/library-hours/";
    expect((await page.goto(detailUrl))?.status()).toBe(200);
    await expect(page.locator("h1")).toContainText("开放时间");

    await control(request, { endpoint: "page-detail", mode: "fail" });
    const res = await page.goto(detailUrl);
    // 契约 4：普通内容失败时回退 ≤5min 最近成功版本——200 + 正常内容，
    // 不出失败态（页面无陈旧标注＝v1 观感不变）
    expect(res?.status()).toBe(200);
    await expect(page.locator("h1")).toContainText("开放时间");
    expect(await page.locator("script").count()).toBe(0);
  });
});

test.describe("板块上游 404 ⇒ v1 同语义 404（SectionPage 缺失；SPEC-001-F14）", () => {
  // v1 同数据态：合法冻结 slug 但 Wagtail 树无该板块页 → 列表走 Wagtail
  // 树路由 404、归档视图显式 Http404 ⇒ 一律 404 页。重建客户端已把上游
  // 404 分类为 not-found（不计健康信号），页面须映射为样式化 404，而非
  // 误入「内容失败」500 边界（诊断包 F-chronicle-500，Issue #37）。
  // 陈旧回退按完整 URL 取键（契约 4 普通内容面）：列表页转发查询串，用
  // 当次运行唯一探针保证冷键；归档页按 v1 语义不转发任何查询参数（上游
  // 键恒为裸 /sections/<slug>/archive），故归档用例改用本套件不预热的
  // /materials/ 板块保证冷键——即「无最近成功版本可回退」的现实场景（含
  // 空 DB）；既定契约 4 温缓存语义不改。按任务边界不落截图入库（断言留档）。
  const probeQ = `f14-probe-${Date.now()}`;

  test("列表上游 not_found → 样式化 404（HTTP 404），不再 500", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "section-list", mode: "notfound" });
    const res = await page.goto(`/chronicle/?q=${probeQ}`);
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    // chrome 并行已取得 → 样式化 404（壳 + v1 引导清单：站内搜索+五板块+返回首页）
    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(page.locator("ul.section-links a")).toHaveCount(7);
    // 不伪装成功态（无列表行/空态/页头大搜索），零脚本（v1 内容页同口径）
    expect(
      await page.locator(".empty-state, .big-search, a.r-row").count(),
    ).toBe(0);
    expect(await page.locator("script").count()).toBe(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await assertNoHorizontalOverflow(page);
  });

  test("归档上游 not_found → 同语义样式化 404", async ({ page, request }) => {
    await control(request, { endpoint: "section-archive", mode: "notfound" });
    const res = await page.goto("/materials/archive/");
    expect(res?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    await expect(page.locator("header.site-header")).toBeVisible();
    expect(await page.locator("script").count()).toBe(0);
  });

  test("上游 500 仍是站内失败态（不折叠为 404）", async ({ page, request }) => {
    await control(request, { endpoint: "section-archive", mode: "fail" });
    const res = await page.goto("/materials/archive/");
    expect(res?.status()).toBe(500);
    await expect(page.locator("h1")).toHaveText("内容暂时无法加载");
    await expect(page.getByRole("alert")).toContainText(
      "内容服务出现临时故障，请稍后重试。",
    );
  });
});

test.describe("全站取数边界（chrome 失败＝v1 最小错误页）", () => {
  test("chrome 失败 → 无壳最小 500（自包含）；未知路径 → 无壳最小 404", async ({
    page,
    request,
  }) => {
    await control(request, { endpoint: "chrome", mode: "fail" });
    const res = await page.goto("/");
    expect(res?.status()).toBe(500);
    await expect(page.locator("h1")).toHaveText("服务暂时不可用");
    // v1 500 页同构：零页头/页脚（壳数据不可得）、零外链资源、零脚本
    expect(await page.locator("header.site-header").count()).toBe(0);
    expect(await page.locator("footer.site-footer").count()).toBe(0);
    expect(await page.locator("script").count()).toBe(0);
    expect(await page.locator("[style]").count()).toBe(0);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: "docs/evidence/f08-error-states/minimal-500-390.png",
      fullPage: true,
    });

    const missing = await page.goto("/f08-not-a-page/");
    expect(missing?.status()).toBe(404);
    await expect(page.locator("h1")).toHaveText("页面不存在");
    expect(await page.locator("header.site-header").count()).toBe(0);
  });
});

test.describe("外链确认（永不陈旧面）", () => {
  test("确认服务失败 → 样式化失败态，绝不回退陈旧确认页", async ({
    page,
    request,
  }) => {
    const confirmUrl = "/link-confirm/?url=https%3A%2F%2Ff08.example%2F";
    // 预热成功（若有无缓存回退通道，此处即建立「陈旧确认页」）
    expect((await page.goto(confirmUrl))?.status()).toBe(200);
    await expect(page.locator(".confirm-card")).toBeVisible();

    await control(request, { endpoint: "link-confirm", mode: "fail" });
    const res = await page.goto(confirmUrl);
    expect(res?.status()).toBe(500);
    await expect(page.locator("h1")).toHaveText("链接确认暂时不可用");
    await expect(page.getByRole("alert")).toContainText(
      "链接确认服务出现临时故障",
    );
    // 绝不出陈旧确认内容（契约 4 NEVER_STALE 面）
    expect(await page.locator(".confirm-card").count()).toBe(0);
    await expect(page.locator("header.site-header")).toBeVisible();
  });
});

test.describe("healthcheck（契约 5：healthcheck 友好）", () => {
  test("上游故障期间 /healthz 仍 200：进程健康与上游健康解耦", async ({
    request,
  }) => {
    await control(request, { endpoint: "section-list", mode: "fail" });
    // 两次失败请求使连续计数达到 degraded 阈值（≥2，抖动不算降级）
    await request.get("http://127.0.0.1:4321/chronicle/?q=f08-health-probe-1");
    await request.get("http://127.0.0.1:4321/chronicle/?q=f08-health-probe-2");
    const res = await request.get("http://127.0.0.1:4321/healthz");
    expect(res.status()).toBe(200);
    const body = (await res.json()) as {
      status: string;
      upstream: { degraded: boolean };
    };
    expect(body.status).toBe("ok");
    expect(body.upstream.degraded).toBe(true);
  });
});
