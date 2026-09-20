import { expect, test } from "@playwright/test";

// SPEC-002 #47（R2）→ #49（R5，Human 驳回整改后语义）：首页轮播回归夹具。
//
// R5 语义（Human 裁定「容器高度恒定 ≠ 视觉通过」后收窄）：高度稳定改由
// CSS 槽位锁定保证（标题/摘要 line-clamp 2 行＋min-height 槽位，
// HeroCarousel.astro），JS 实测预留已移除。断言：
// - 切换前后容器高度稳定（≤1px）——R2 症状（长题增高推挤下方内容）不回归；
// - 导航（prev/next/dots）必须整体落在活动卡片内（R5 驳回症状：预留拉伸
//   容器把导航推到卡外白底上）；
// - 容器不得在卡片下方产生拉伸空白区（section 底 == 卡片底）；
// - 长题视觉两行封顶（省略号），DOM 文本保留全文（全文经 CTA 链接可达）；
// - 长题激活时卡内布局不得溢出（card scrollHeight ≤ clientHeight）。
//
// 场景：mock API home fixture 的长短交替轮播（第 2 条为 41 字长题通知——
// 见 fixtures/api/home.json carousel[1]；既有断言仅钉住第 1 条标题）。
// reducedMotion: reduce → 停 autoplay，手动导航完全确定。

const SHORT_TITLE_1 = "开学季专题";
const LONG_TITLE =
  "关于组织全校学生积极参加第38届校园运动会暨田径项目选拔与各班级报名赛程安排的通知";
const SHORT_TITLE_3 = "实验室数据绘图工具更新";

for (const viewport of [
  { width: 390, height: 844 },
  { width: 1440, height: 900 },
]) {
  test.describe(`轮播高度稳定 @${viewport.width}x${viewport.height}`, () => {
    test.use({ viewport, reducedMotion: "reduce" });

    test("长短交替切换（三态往返），容器高度稳定且内容不裁切", async ({
      page,
    }) => {
      await page.goto("/");
      const hero = page.locator("section.hero[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");
      const slides = hero.locator("[data-carousel-item]");
      await expect(slides).toHaveCount(3);

      const activeTitle = page.locator(
        "[data-carousel-item].is-active .hero-title",
      );
      const activeCard = page.locator(
        "[data-carousel-item].is-active .hero-card",
      );
      const heroHeight = async () => (await hero.boundingBox())!.height;

      await expect(activeTitle).toHaveText(SHORT_TITLE_1);
      const h1 = await heroHeight();

      // 短 → 长（bug 触发方向：41 字长题多行换行）
      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2 = await heroHeight();

      // 长 → 短（第 3 条；离开返回同验）
      await hero.locator(".carousel-next").click();
      await expect(activeTitle).toHaveText(SHORT_TITLE_3);
      const h3 = await heroHeight();

      // 短 → 长（返回长题，验证往复一致性）
      await hero.locator(".carousel-prev").click();
      await expect(activeTitle).toHaveText(LONG_TITLE);
      const h2b = await heroHeight();

      console.log(
        `[fixture ${viewport.width}x${viewport.height}] short1=${h1} long=${h2} short3=${h3} long-again=${h2b}`,
      );

      // 高度稳定：任意两态高度差 ≤1px（修复验收线）。
      const heights = [
        ["短1", h1],
        ["长", h2],
        ["短3", h3],
        ["长·返", h2b],
      ] as const;
      for (const [name, h] of heights) {
        expect(Math.abs(h - h1), `${name} 态高度跳变`).toBeLessThanOrEqual(1);
      }

      // 内容完整性：长题激活时卡内不得被裁切（scrollHeight 不得超出可视高）。
      const clip = await activeCard.evaluate(
        (el) => el.scrollHeight - el.clientHeight,
      );
      expect(clip, "长题卡内容被裁切").toBeLessThanOrEqual(0);

      // R5（Human 驳回整改）：导航必须整体落在活动卡片内；容器不得在卡片
      // 下方产生拉伸空白区；长题视觉两行封顶、DOM 保留全文。
      const layout = await page.evaluate(() => {
        const hero = document.querySelector("section.hero[data-carousel]")!;
        const card = hero.querySelector(
          "[data-carousel-item].is-active .hero-card",
        )!;
        const controls = hero.querySelector(".carousel-controls")!;
        const title = hero.querySelector(
          "[data-carousel-item].is-active .hero-title",
        )!;
        const c = card.getBoundingClientRect();
        const k = controls.getBoundingClientRect();
        const t = title.getBoundingClientRect();
        const cs = getComputedStyle(title);
        const h = hero.getBoundingClientRect();
        return {
          controlsInCard:
            k.left >= c.left - 2 &&
            k.right <= c.right + 2 &&
            k.top >= c.top - 2 &&
            k.bottom <= c.bottom + 2,
          sectionBelowCard: +(h.bottom - c.bottom).toFixed(1),
          titleLines: Math.round(t.height / parseFloat(cs.lineHeight)),
          titleDomFull:
            (title.textContent ?? "").length > 20 &&
            title.textContent!.includes("田径项目选拔"),
        };
      });
      expect(layout.controlsInCard, "导航落在活动卡片外").toBe(true);
      expect(
        layout.sectionBelowCard,
        "容器在卡片下方拉伸（导航落白底区）",
      ).toBeLessThanOrEqual(2);
      expect(layout.titleLines, "长题未两行封顶").toBeLessThanOrEqual(2);
      expect(layout.titleDomFull, "DOM 标题全文丢失").toBe(true);
    });
  });
}
