import { expect, test, type Locator } from "@playwright/test";

// SPEC-002 #49（R3，仅 Astro）：多视口 × 可见性状态验收矩阵。
//
// 在 #47 修复（增强态实测高度预留）之上按工单验收口径实跑：
// - 视口：390×844 / 1440×900（必测）＋断点间抽查 601（<761 移动档）、
//   981（≥761 桌面档）；768 恰过桌面恢复阈值。
// - 可见性状态：完全可见 / 部分可见（半出视口）/ 离开后返回——均验证
//   切换高度稳定（任意两态差 ≤1px）。
// - 内容：长短标题交替序列（mock API home fixture，第 2 条 41 字长题）。
// - 附带守护：长题激活时卡内内容不得被裁切。
//
// reducedMotion: reduce → 停 autoplay，手动导航完全确定。
// 「线上不跳≠已修复」：验收只认本地夹具＋矩阵证据（工单口径）。

const SHORT_TITLE_1 = "开学季专题";
const LONG_TITLE =
  "关于组织全校学生积极参加第38届校园运动会暨田径项目选拔与各班级报名赛程安排的通知";
const SHORT_TITLE_3 = "实验室数据绘图工具更新";

const VIEWPORTS = [
  { width: 390, height: 844 }, // 手机（必测）
  { width: 601, height: 900 }, // 断点间抽查：移动档（<761）
  { width: 768, height: 1024 }, // 平板：恰过桌面恢复阈值（≥761）
  { width: 981, height: 900 }, // 断点间抽查：桌面档
  { width: 1440, height: 900 }, // 桌面（必测）
] as const;

// 高度读取：getBoundingClientRect（与滚动位置无关）。
const heroHeight = (hero: Locator) =>
  hero.evaluate((el) => el.getBoundingClientRect().height);

for (const viewport of VIEWPORTS) {
  const tag = `${viewport.width}x${viewport.height}`;

  test.describe(`轮播验收矩阵 @${tag}`, () => {
    test.use({ viewport, reducedMotion: "reduce" });

    test("完全可见：长短交替四态高度稳定，截图存证", async ({ page }) => {
      await page.goto("/");
      const hero = page.locator("section.hero[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");
      const activeTitle = page.locator(
        "[data-carousel-item].is-active .hero-title",
      );
      const activeCard = page.locator(
        "[data-carousel-item].is-active .hero-card",
      );

      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      const h1 = await heroHeight(hero);

      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2 = await heroHeight(hero);

      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(SHORT_TITLE_3);
      const h3 = await heroHeight(hero);

      await hero.locator(".carousel-prev").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2b = await heroHeight(hero);

      console.log(
        `[完全可见 ${tag}] short1=${h1} long=${h2} short3=${h3} long-again=${h2b}`,
      );

      const heights = [
        ["短1", h1],
        ["长", h2],
        ["短3", h3],
        ["长·返", h2b],
      ] as const;
      for (const [name, h] of heights) {
        expect(Math.abs(h - h1), `${name} 态高度跳变`).toBeLessThanOrEqual(1);
      }

      const clip = await activeCard.evaluate(
        (el) => el.scrollHeight - el.clientHeight,
      );
      expect(clip, "长题卡内容被裁切").toBeLessThanOrEqual(0);

      // R5（Human 驳回整改）：五视口一致要求——导航整体在活动卡片内、
      // 容器无卡下拉伸区（「容器高度恒定≠视觉通过」的落地断言）。
      const layout = await page.evaluate(() => {
        const hero = document.querySelector("section.hero[data-carousel]")!;
        const card = hero.querySelector(
          "[data-carousel-item].is-active .hero-card",
        )!;
        const controls = hero.querySelector(".carousel-controls")!;
        const c = card.getBoundingClientRect();
        const k = controls.getBoundingClientRect();
        const h = hero.getBoundingClientRect();
        return {
          controlsInCard:
            k.left >= c.left - 2 &&
            k.right <= c.right + 2 &&
            k.top >= c.top - 2 &&
            k.bottom <= c.bottom + 2,
          sectionBelowCard: +(h.bottom - c.bottom).toFixed(1),
          overflowX:
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
        };
      });
      expect(layout.controlsInCard, "导航落在活动卡片外").toBe(true);
      expect(
        layout.sectionBelowCard,
        "容器在卡片下方拉伸（导航落白底区）",
      ).toBeLessThanOrEqual(2);
      expect(layout.overflowX, "页面出现横向溢出").toBeLessThanOrEqual(0);

      // 截图存证：短/长两态同高（视觉证据，随提交入库）。
      await hero.locator(".carousel-prev").click(); // 回到短1
      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      await hero.screenshot({
        path: `docs/evidence/spec-002-r3/${viewport.width}-short.png`,
      });
      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      await hero.screenshot({
        path: `docs/evidence/spec-002-r3/${viewport.width}-long.png`,
      });
    });

    test("部分可见（半出视口）：切换高度稳定且切换仍生效", async ({ page }) => {
      await page.goto("/");
      const hero = page.locator("section.hero[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");
      const activeTitle = page.locator(
        "[data-carousel-item].is-active .hero-title",
      );

      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      const h1 = await heroHeight(hero);

      // 滚动使轮播上半部滚出视口（部分可见）；此后所有切换用
      // evaluate 直接派发 click，避免 Playwright 自动滚动回正——
      // 保持「部分可见」前提成立。
      await page.evaluate(() => {
        const el = document.querySelector("section.hero");
        const rect = el!.getBoundingClientRect();
        window.scrollTo(0, window.scrollY + rect.height / 2);
      });
      const box = await hero.boundingBox();
      expect(box!.y, "轮播应已部分滚出视口顶部").toBeLessThan(0);
      // 复核（不依赖 boundingBox 坐标系语义）：视口坐标 top 应为负。
      const top = await hero.evaluate((el) => el.getBoundingClientRect().top);
      expect(top).toBeLessThan(0);

      await hero
        .locator(".carousel-next")
        .evaluate((el) => (el as HTMLElement).click());
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2 = await heroHeight(hero);

      await hero
        .locator(".carousel-prev")
        .evaluate((el) => (el as HTMLElement).click());
      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      const h1b = await heroHeight(hero);

      console.log(
        `[部分可见 ${tag}] short1=${h1} long=${h2} short-again=${h1b}`,
      );
      expect(Math.abs(h2 - h1), "长题态高度跳变").toBeLessThanOrEqual(1);
      expect(Math.abs(h1b - h1), "返回短题态高度跳变").toBeLessThanOrEqual(1);
    });

    test("离开后返回：滚动远离再回顶，切换高度稳定", async ({ page }) => {
      await page.goto("/");
      const hero = page.locator("section.hero[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");
      const activeTitle = page.locator(
        "[data-carousel-item].is-active .hero-title",
      );

      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      const h1 = await heroHeight(hero);

      // 离开：滚到页底（轮播完全出视口），再返回页顶。
      await page.evaluate(() =>
        window.scrollTo(0, document.documentElement.scrollHeight),
      );
      await page.waitForTimeout(100);
      await page.evaluate(() => window.scrollTo(0, 0));
      await expect(hero).toBeInViewport();

      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2 = await heroHeight(hero);

      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(SHORT_TITLE_3);
      const h3 = await heroHeight(hero);

      console.log(`[离开后返回 ${tag}] short1=${h1} long=${h2} short3=${h3}`);
      expect(Math.abs(h2 - h1), "长题态高度跳变").toBeLessThanOrEqual(1);
      expect(Math.abs(h3 - h1), "短题态高度跳变").toBeLessThanOrEqual(1);
    });
  });
}
