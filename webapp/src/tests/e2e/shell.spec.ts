import { expect, test } from "@playwright/test";
import { stubMedia } from "./helpers/media";

// SPEC-001-F02 验收 2：布局壳在 390/768/1440 无结构性破坏，并建立
// Playwright 截图基线（docs/evidence/f02-shell/，供评审对照；G3 视觉门
// 以 Human 代表性截图为准，本基线不做跨平台像素断言——字体栅格差异
// 会导致不稳定失败，等价判定归 Human 视觉门）。
const VIEWPORTS = [
  { width: 390, height: 844, label: "核心（移动）" },
  { width: 768, height: 1024, label: "次要（平板）" },
  { width: 1440, height: 900, label: "桌面" },
] as const;

// /media/* 在生产由反代同源代理；e2e 拓扑分端口，浏览器侧补图（helpers/media）
test.beforeEach(async ({ page }) => {
  await stubMedia(page);
});

for (const { width, height, label } of VIEWPORTS) {
  test(`布局壳在 ${width}px（${label}）无结构性破坏`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/");

    // 语言与壳结构（v1 base.html 等价）
    await expect(page.locator("html")).toHaveAttribute("lang", "zh-Hans");
    await expect(page.locator("main#main-content.wrap")).toBeVisible();
    await expect(page.locator("body > .skip-link")).toBeAttached();

    // 契约 6：文档不横向溢出（含 20px 版心内距下的最小宽度）
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow, "文档出现横向溢出").toBeLessThanOrEqual(0);

    // 截图基线（静止壳状态）
    await page.screenshot({
      path: `docs/evidence/f02-shell/${width}.png`,
      fullPage: true,
    });

    // 跳转主内容链接是首个可聚焦元素（PRD §13），且键盘焦点可见
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "跳到主要内容" });
    await expect(skipLink).toBeFocused();
    const outline = await skipLink.evaluate((el) => {
      const s = getComputedStyle(el);
      return `${s.outlineWidth} ${s.outlineStyle} ${s.outlineColor}`;
    });
    expect(outline).toBe("2px solid rgb(47, 122, 110)");
  });
}
