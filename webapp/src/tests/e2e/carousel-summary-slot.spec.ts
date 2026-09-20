import { expect, test, type APIRequestContext } from "@playwright/test";

// SPEC-002 #49（R6，Human 验收后补充）：无摘要条目同样保留两行摘要槽位。
//
// 有/无/超长摘要混合轮播，在手机/平板/桌面三档验证：
// - 三个条目（短摘要 / 无摘要 / 超长摘要）卡高恒定（任意两态差 ≤1px）；
// - 导航整体落在活动卡片内（R5 语义延续）；
// - 超长摘要视觉两行封顶（省略），DOM 文本保留全文；
// - 无摘要条目的摘要槽存在且高为一个两行槽（min-height:3em），
//   空槽 aria-hidden，不产生读屏内容。
//
// 数据经 mock 控制面 /__control 以整份 home 载荷覆写（夹具其余字段原样），
// 测试结束 reset（各测试自清理）；reducedMotion: reduce → 手动导航确定。

const MOCK = "http://127.0.0.1:4319";

// 与 home.json 夹具同构的最小整份载荷（sections/campus_news 沿用夹具值，
// carousel 换成有/无/超长摘要混合序列）。
const SUMMARY_SHORT = "新学期各项安排汇总。";
const SUMMARY_LONG =
  "本条摘要远超两行：新版本支持课程实验常用图表模板，附安装指引与常见问题排查手册，同时整理了各院系实验室的预约流程、账号开通方式与数据导出注意事项，供同学们在学期初集中配置实验环境时参考使用。";

function homePayload() {
  return {
    title: "首页",
    alert: null,
    carousel: [
      {
        kind: "internal",
        title: "开学季专题",
        href: "/chronicle/jwc/2026-opening/",
        cover: null,
        summary: SUMMARY_SHORT,
        section_slug: "chronicle",
      },
      {
        kind: "internal",
        title: "实验室数据绘图工具更新",
        href: "/software/rjzx/plotkit-3/",
        cover: null,
        summary: "", // 无摘要（契约内空串）：R6 要求同样占两行槽
        section_slug: "software",
      },
      {
        kind: "internal",
        title:
          "关于组织全校学生积极参加第38届校园运动会暨田径项目选拔与各班级报名赛程安排的通知",
        href: "/events/tiyuzu/38-sports-meet/",
        cover: null,
        summary: SUMMARY_LONG,
        section_slug: "events",
      },
    ],
    sections: [
      { slug: "chronicle", title: "校园纪事", url: "/chronicle/" },
      { slug: "events", title: "校园活动", url: "/events/" },
      { slug: "materials", title: "学习资料", url: "/materials/" },
      { slug: "software", title: "软件与工具", url: "/software/" },
      { slug: "guide", title: "校园指南", url: "/guide/" },
    ],
    campus_news: [],
  };
}

async function overrideHome(request: APIRequestContext) {
  const res = await request.post(`${MOCK}/__control`, {
    data: { endpoint: "home", mode: "ok", payload: homePayload() },
  });
  expect(res.ok(), "覆写 home 载荷失败").toBe(true);
}

const TITLES = [
  "开学季专题",
  "实验室数据绘图工具更新",
  "关于组织全校学生",
] as const;

for (const viewport of [
  { width: 390, height: 844 }, // 手机
  { width: 768, height: 1024 }, // 平板
  { width: 1440, height: 900 }, // 桌面
]) {
  test.describe(`混合摘要轮播 @${viewport.width}x${viewport.height}`, () => {
    test.use({ viewport, reducedMotion: "reduce" });

    test("三态卡高恒定、导航在卡内、长摘要两行省略、空摘要占位", async ({
      page,
      request,
    }) => {
      await overrideHome(request);
      await page.goto("/");
      const hero = page.locator("section.hero[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");
      const activeTitle = page.locator(
        "[data-carousel-item].is-active .hero-title",
      );
      const activeCard = page.locator(
        "[data-carousel-item].is-active .hero-card",
      );

      const heights: number[] = [];
      for (let i = 0; i < 3; i++) {
        await expect(activeTitle).toContainText(TITLES[i]);
        const metrics = await page.evaluate(() => {
          const heroEl = document.querySelector("section.hero[data-carousel]")!;
          const cardEl = heroEl.querySelector(
            "[data-carousel-item].is-active .hero-card",
          )!;
          const controlsEl = heroEl.querySelector(".carousel-controls")!;
          const subEl = heroEl.querySelector(
            "[data-carousel-item].is-active .hero-sub",
          )!;
          const c = cardEl.getBoundingClientRect();
          const k = controlsEl.getBoundingClientRect();
          const s = subEl.getBoundingClientRect();
          const cs = getComputedStyle(subEl);
          return {
            cardHeight: +c.height.toFixed(1),
            controlsInCard:
              k.left >= c.left - 2 &&
              k.right <= c.right + 2 &&
              k.top >= c.top - 2 &&
              k.bottom <= c.bottom + 2,
            subLines: +(s.height / parseFloat(cs.lineHeight)).toFixed(2),
            subAriaHidden: subEl.getAttribute("aria-hidden"),
            subDomFull: (subEl.textContent ?? "").length,
            overflowX:
              document.documentElement.scrollWidth -
              document.documentElement.clientWidth,
          };
        });
        heights.push(metrics.cardHeight);
        // 逐态断言（第 2 条无摘要、第 3 条超长摘要）。
        if (i === 1) {
          expect(metrics.subAriaHidden, "空摘要槽未 aria-hidden").toBe("true");
          expect(metrics.subDomFull, "空摘要槽存在文本").toBe(0);
        }
        if (i === 2) {
          expect(metrics.subLines, "超长摘要未两行封顶").toBeLessThanOrEqual(
            2.01,
          );
          expect(metrics.subDomFull, "DOM 摘要全文丢失").toBeGreaterThan(
            SUMMARY_SHORT.length,
          );
          // 与 carousel-height.spec.ts 同款守护：line-clamp 布局下卡内
          // 不得出现溢出裁切（scrollHeight 不得超出可视高）。
          const clip = await activeCard.evaluate(
            (el) => el.scrollHeight - el.clientHeight,
          );
          expect(clip, "长摘要卡内容被裁切").toBeLessThanOrEqual(0);
        }
        expect(metrics.controlsInCard, `第 ${i + 1} 态导航落在卡外`).toBe(true);
        expect(metrics.overflowX, "页面出现横向溢出").toBeLessThanOrEqual(0);
        // 真实点击推进到下一态。
        await hero.locator(".carousel-next").click();
      }

      // 三态卡高恒定（验收线：任意两态差 ≤1px）。
      console.log(`[混合摘要 ${viewport.width}x${viewport.height}]`, heights);
      for (const [i, h] of heights.entries()) {
        expect(
          Math.abs(h - heights[0]),
          `第 ${i + 1} 态卡高跳变`,
        ).toBeLessThanOrEqual(1);
      }

      // 无摘要态的槽位高度 = 两行槽（line-height 1.5 × 2 行 = 3em）。
      await hero.locator(".carousel-next").click(); // 三连点后回到第 1 条，再进到第 2 条（无摘要）
      await expect(activeTitle).toContainText(TITLES[1]);
      const subSlot = await page.evaluate(() => {
        const sub = document.querySelector(
          "[data-carousel-item].is-active .hero-sub",
        )!;
        const s = sub.getBoundingClientRect();
        const cs = getComputedStyle(sub);
        return { lines: +(s.height / parseFloat(cs.lineHeight)).toFixed(2) };
      });
      expect(subSlot.lines, "空摘要槽未锁定两行高").toBeCloseTo(2, 1);
    });
  });
}
