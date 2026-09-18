import { expect, test, type Page } from "@playwright/test";
import { stubMedia } from "./helpers/media";

// SPEC-001-F03 验收：页头/页脚在 390/768/1440 的结构、信息层级与响应式
// 行为等价（v1 base.html + peiligo.css「共享外壳」逐字转写）；键盘可达与
// focus 顺序等价（WCAG 2.2 AA 预留硬门）。截图存 docs/evidence/f03-header-footer/
// 供评审对照；G3 视觉门以 Human 代表性截图为准，不做跨平台像素断言。

const VIEWPORTS = [
  { width: 390, height: 844, label: "核心（移动）" },
  { width: 768, height: 1024, label: "次要（平板）" },
  { width: 1440, height: 900, label: "桌面" },
] as const;

// 反馈邮箱为 chrome 夹具的活数据（F05 起每请求经 /chrome 直连；mock-api
// 服务端 fixtures/api/chrome.json 为本 e2e 的数据源，改动须两处同步）
const siteFeedbackEmail = "hello@peiligo.example";

// /media/* 在生产由反代同源代理；e2e 拓扑分端口，浏览器侧补图（helpers/media）
test.beforeEach(async ({ page }) => {
  await stubMedia(page);
});

async function assertNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(overflow, "文档出现横向溢出").toBeLessThanOrEqual(0);
}

for (const { width, height, label } of VIEWPORTS) {
  test(`页头/页脚结构与响应式在 ${width}px（${label}）等价`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/");

    // ===== 页头结构（v1 final-reference：校徽 + 字标 + 搜索入口） =====
    const brand = page.getByRole("link", { name: "Peiligo 首页" });
    await expect(brand).toBeVisible();
    await expect(brand.locator("img")).toHaveAttribute("alt", "");
    await expect(brand.locator(".wordmark")).toHaveText("Peiligo.");
    // 字标句点：页头 coral / 页脚 yellow（v1 冻结配色）
    await expect(brand.locator(".wm-dot")).toHaveCSS(
      "color",
      "rgb(232, 89, 12)",
    );

    // 搜索为真实 GET 表单：公开 URL 契约不变（action=/search/，q 参数）
    const search = page.getByRole("search", { name: "站内搜索" });
    await expect(search).toBeVisible();
    await expect(search).toHaveAttribute("action", "/search/");
    await expect(search).toHaveAttribute("method", "get");
    const input = search.getByRole("searchbox", { name: "搜索站内内容" });
    await expect(input).toHaveAttribute("placeholder", "搜资料、活动、软件…");

    // ===== 页脚结构（teal-deep 实底、品牌左/说明右） =====
    const footer = page.locator("footer.site-footer");
    await expect(footer).toBeVisible();
    await expect(footer.locator(".footer-brand")).toContainText("Peiligo.");
    await expect(footer.locator(".footer-brand .wm-dot")).toHaveCSS(
      "color",
      "rgb(255, 201, 64)",
    );
    await expect(footer.locator(".footer-notes p").first()).toContainText(
      "关于：本站面向校内学生",
    );
    // 反馈 mailto：mailto:{邮箱}?subject=…&body=…（v1 默认 feedback_mailto 块）
    const feedbackLink = footer.getByRole("link", {
      name: siteFeedbackEmail,
    });
    await expect(feedbackLink).toBeVisible();
    expect(await feedbackLink.getAttribute("href")).toMatch(
      /^mailto:hello@peiligo\.example\?subject=[^&]+&body=/,
    );
    await expect(footer.locator(".footer-meta")).toHaveText(
      `© ${new Date().getFullYear()} Peiligo`,
    );

    // ===== 响应式行为（v1 @media (max-width: 760px) 反向等价） =====
    const brandBox = await brand.boundingBox();
    const searchBox = await search.boundingBox();
    const brandFooterBox = await footer.locator(".footer-brand").boundingBox();
    const notesBox = await footer.locator(".footer-notes").boundingBox();
    expect(brandBox && searchBox && brandFooterBox && notesBox).toBeTruthy();

    if (width <= 760) {
      // 移动/平板档：页头单栏（搜索在品牌下方并通栏），页脚纵向堆叠
      expect(searchBox!.y).toBeGreaterThanOrEqual(
        brandBox!.y + brandBox!.height - 1,
      );
      expect(searchBox!.width).toBeGreaterThan(width * 0.8);
      expect(notesBox!.y).toBeGreaterThanOrEqual(
        brandFooterBox!.y + brandFooterBox!.height - 1,
      );
    } else {
      // 桌面档：品牌左/搜索右同排（搜索胶囊 ≤380px），页脚品牌左/说明右
      expect(Math.abs(searchBox!.y - brandBox!.y)).toBeLessThanOrEqual(8);
      expect(searchBox!.width).toBeLessThanOrEqual(382);
      expect(Math.abs(notesBox!.y - brandFooterBox!.y)).toBeLessThanOrEqual(8);
      expect(notesBox!.x).toBeGreaterThan(
        brandFooterBox!.x + brandFooterBox!.width,
      );
    }

    await assertNoHorizontalOverflow(page);

    // 截图基线（静止壳状态；worker 证据，非 G3 判定物）
    await page.screenshot({
      path: `docs/evidence/f03-header-footer/${width}.png`,
      fullPage: true,
    });
  });
}

test("键盘可达与 focus 顺序等价（skip link → 品牌 → 搜索框）", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "跳到主要内容" })).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Peiligo 首页" })).toBeFocused();

  // 搜索框聚焦：胶囊 :focus-within 亮起 teal 描边并回白底（v1 等价行为；
  // input 自身 outline:none 由容器承担可见焦点，v1 同款）
  await page.keyboard.press("Tab");
  const input = page.getByRole("searchbox", { name: "搜索站内内容" });
  await expect(input).toBeFocused();
  const search = page.getByRole("search", { name: "站内搜索" });
  await expect(search).toHaveCSS("border-color", "rgb(47, 122, 110)");
  await expect(search).toHaveCSS("background-color", "rgb(255, 255, 255)");

  // 键盘提交可达：回车即以 GET 提交至 /search/（同源相对路径）
  await input.fill("社团");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/search\/\?q=%E7%A4%BE%E5%9B%A2$/);
});

test("系统「减弱动态效果」时页头搜索过渡关闭（v1 全站纪律）", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const duration = await page
    .getByRole("search", { name: "站内搜索" })
    .evaluate((el) => getComputedStyle(el).transitionDuration);
  // Chromium 将 0.01ms 序列化为 1e-05s，二者同值
  expect(["0.01ms", "1e-05s"]).toContain(duration);
});
