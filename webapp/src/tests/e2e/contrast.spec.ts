import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";
import { stubMedia } from "./helpers/media";
import {
  contrastRatio,
  parseColor,
  readPair,
  type Pair,
} from "./helpers/contrast";

// SPEC-001-F05-G3 视觉可达性门（WCAG 2.2 AA 对比度）：
// 以「计算样式」（getComputedStyle 解析后的实际前景/背景色）为唯一事实源，
// 在 390/768/1440 三档代表视口按 WCAG 相对亮度公式逐对计算对比率并断言阈值：
//   普通文本 ≥ 4.5:1；大字（≥24px 或 ≥18.66px 粗体）≥ 3:1；
//   非文本 UI（控件指示/焦点指示）≥ 3:1。
// 半透明色（rgba 前景/填充）先按 alpha 合成到视觉底色上再计算；轮播控件是
// .hero-panel 的 DOM 兄弟节点（绝对定位覆盖其上），合成底显式取面板计算
// 背景色（backdrop 参数），其余沿 DOM 祖先解析首个不透明背景。
// 纯装饰（aria-hidden 插画、警示条 4px 描边等非识别性元素）不在判定面，
// 测量值与豁免口径记录于 Draft PR #20 / issue #7。
// F09 起数学与取值原语上提至 helpers/contrast.ts（a11y.spec 同口径共用）。

const FIXTURES = new URL("../fixtures/api/", import.meta.url);
const homeFixture = JSON.parse(
  readFileSync(new URL("home.json", FIXTURES), "utf8"),
) as typeof import("../fixtures/api/home.json");

const MOCK = "http://127.0.0.1:4319";
const VIEWPORTS = [390, 768, 1440] as const;

// ===== 浏览器侧取值（hero 控件专用合成底读取；共享原语见 helpers/contrast） =====

/** 控件填充色 + 显式合成底（轮播控件视觉上覆盖 hero 面板）。 */
async function readFill(
  page: Page,
  selector: string,
  backdropSel: string,
): Promise<Pair> {
  return page.evaluate(
    ({ selector, backdropSel }) => {
      const el = document.querySelector(selector);
      const backdrop = document.querySelector(backdropSel);
      if (!el || !backdrop)
        throw new Error(`未找到元素：${selector} / ${backdropSel}`);
      return {
        fg: getComputedStyle(el).backgroundColor,
        bg: getComputedStyle(backdrop).backgroundColor,
      };
    },
    { selector, backdropSel },
  );
}

/** 字形色与其三层视觉底（半透明填充合成到面板上）的配对：
    白色箭头 → rgba 填充 → 面板实底，逐层合成后返回不透明底色。 */
async function readGlyphOnFill(
  page: Page,
  selector: string,
  backdropSel: string,
): Promise<Pair> {
  return page.evaluate(
    ({ selector, backdropSel }) => {
      const el = document.querySelector(selector);
      const backdrop = document.querySelector(backdropSel);
      if (!el || !backdrop)
        throw new Error(`未找到元素：${selector} / ${backdropSel}`);
      const parse = (css: string) =>
        css
          .match(
            /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)/,
          )
          ?.slice(1)
          .map((v) => (v === undefined ? 1 : Number(v))) as number[];
      const mix = (f: number[], b: number[]) =>
        `rgb(${f
          .slice(0, 3)
          .map((v, i) => Math.round(f[3] * v + (1 - f[3]) * b[i]))
          .join(", ")})`;
      const fill = parse(getComputedStyle(el).backgroundColor);
      const panel = parse(getComputedStyle(backdrop).backgroundColor);
      return { fg: getComputedStyle(el).color, bg: mix(fill, panel) };
    },
    { selector, backdropSel },
  );
}

test.describe("首页 WCAG 2.2 AA 对比度（计算样式判定）", () => {
  test.afterEach(async ({ request }) => {
    await request.post(`${MOCK}/__control/reset`);
  });

  for (const width of VIEWPORTS) {
    test(`${width}px：全部受检元素达到 AA 阈值`, async ({ page, request }) => {
      await stubMedia(page);
      await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });

      // 警示条非默认夹具态：经控制面注入后逐档复测（文本/底不随视口变化）
      await request.post(`${MOCK}/__control`, {
        data: {
          endpoint: "home",
          mode: "ok",
          payload: { ...homeFixture, alert: { text: "明日上午校园网络检修" } },
        },
      });
      await page.goto("/");
      const hero = page.locator("[data-carousel]");
      await expect(hero).toHaveAttribute("data-carousel-enhanced", "");

      const rows: { name: string; pair: Pair; ratio: number; need: number }[] =
        [];
      const judge = async (
        name: string,
        pairPromise: Promise<Pair> | Pair,
        need: number,
      ) => {
        const pair = await pairPromise;
        rows.push({
          name,
          pair,
          ratio: contrastRatio(parseColor(pair.fg), parseColor(pair.bg)),
          need,
        });
      };
      const PANEL = "[data-carousel] .hero-panel";

      // --- Hero（teal-deep 面板）---
      await judge(
        "hero 大题（大字）",
        readPair(page, "[data-carousel-item]:not([hidden]) .hero-title"),
        3,
      );
      await judge(
        "hero 副题（14–15.5px）",
        readPair(page, "[data-carousel-item]:not([hidden]) .hero-sub"),
        4.5,
      );
      await judge(
        "hero chip 文字/底",
        readPair(page, "[data-carousel-item]:not([hidden]) .hero-chip"),
        4.5,
      );
      await judge(
        "hero CTA 文字/底",
        readPair(page, "[data-carousel-item]:not([hidden]) .hero-cta"),
        4.5,
      );

      // --- 轮播控件（非文本 UI ≥3:1）---
      await judge(
        "轮播 prev 箭头字形",
        readGlyphOnFill(page, ".carousel-prev", PANEL),
        3,
      );
      await judge(
        "轮播 next 箭头字形",
        readGlyphOnFill(page, ".carousel-next", PANEL),
        3,
      );
      await judge(
        "轮播未激活圆点填充/面板",
        readFill(page, ".carousel-dot:not([aria-current])", PANEL),
        3,
      );
      await judge(
        "轮播激活圆点填充/面板",
        readFill(page, ".carousel-dot[aria-current]", PANEL),
        3,
      );

      // --- 焦点指示（≥3:1；键盘语境聚焦后读 outline/描边计算值）---
      const focusOutline = async (
        name: string,
        sel: string,
        backdropSel?: string,
      ) => {
        const el = page.locator(sel).first();
        await el.focus();
        expect(
          await el.evaluate((node) => node.matches(":focus-visible")),
          `${name}：程序化聚焦应命中 :focus-visible`,
        ).toBe(true);
        const pair = await page.evaluate(
          ({ sel, backdropSel }) => {
            const el = document.querySelector(sel)!;
            if (backdropSel) {
              const bd = document.querySelector(backdropSel)!;
              return {
                fg: getComputedStyle(el).outlineColor,
                bg: getComputedStyle(bd).backgroundColor,
                w: getComputedStyle(el).outlineWidth,
              };
            }
            let bg = "rgb(255, 255, 255)";
            let node: Element | null = el;
            while (node) {
              const c = getComputedStyle(node).backgroundColor;
              const m = c.match(/,\s*([\d.]+)\)$/);
              if (c !== "transparent" && (!m || Number(m[1]) > 0)) {
                bg = c;
                break;
              }
              node = node.parentElement;
            }
            return {
              fg: getComputedStyle(el).outlineColor,
              bg,
              w: getComputedStyle(el).outlineWidth,
            };
          },
          { sel, backdropSel },
        );
        expect(
          parseFloat(pair.w),
          `${name}：焦点环宽度`,
        ).toBeGreaterThanOrEqual(2);
        await judge(name, pair, 3);
      };
      await focusOutline(
        "焦点环：hero 卡（页面白底）",
        "[data-carousel-item]:not([hidden]) .hero-card",
      );
      await focusOutline(
        "焦点环：轮播 prev（深面板）",
        ".carousel-prev",
        PANEL,
      );
      await focusOutline(
        "焦点环：轮播激活圆点（深面板）",
        ".carousel-dot[aria-current]",
        PANEL,
      );
      await focusOutline(
        "焦点环：分类卡 1（coral-soft）",
        "nav.cats a.cat:nth-child(1)",
      );
      await focusOutline(
        "焦点环：分类卡 2（amber-soft）",
        "nav.cats a.cat:nth-child(2)",
      );
      // 搜索框 focus 时输入框 outline 关闭、容器 focus-within 描边承担指示；
      // 背景换色有 150ms 过渡，等稳定后读终值
      await page.locator(".search input").focus();
      await page.waitForTimeout(300);
      await judge(
        "焦点指示：搜索容器 focus-within 描边",
        await page.evaluate(() => {
          const box = document.querySelector(".search")!;
          return {
            fg: getComputedStyle(box).borderTopColor,
            bg: getComputedStyle(box).backgroundColor,
            w: getComputedStyle(box).borderTopWidth,
          };
        }),
        3,
      );
      expect(
        await page.evaluate(() =>
          parseFloat(
            getComputedStyle(document.querySelector(".search")!).borderTopWidth,
          ),
        ),
        "搜索 focus-within 描边宽度",
      ).toBeGreaterThanOrEqual(2);

      // --- 搜索 ---
      await judge(
        "搜索 placeholder",
        readPair(page, ".search input", "::placeholder"),
        4.5,
      );
      await judge("搜索输入文字", readPair(page, ".search input"), 4.5);

      // --- 五分类导航（coral/amber/blue/violet/teal soft 底）---
      const tones = ["coral", "amber", "blue", "violet", "teal"];
      for (let i = 1; i <= 5; i++) {
        await judge(
          `分类卡 ${i}（${tones[i - 1]}-soft）标签`,
          readPair(page, `nav.cats a.cat:nth-child(${i}) .cat-label`),
          4.5,
        );
      }

      // --- 校园快讯卡 ---
      await judge("快讯卡标题", readPair(page, ".news-card h3"), 4.5);
      await judge("快讯卡摘要", readPair(page, ".news-card .news-body p"), 4.5);
      await judge("快讯卡元信息", readPair(page, ".news-card .news-meta"), 4.5);
      await judge(
        "快讯卡板块徽标文字/底",
        readPair(page, ".news-card .tag"),
        4.5,
      );

      // --- 紧急提示条 ---
      await judge("警示条文字/底", readPair(page, ".site-alert p"), 4.5);

      // --- 页脚（teal-deep 实底）---
      await judge("页脚品牌字标", readPair(page, ".footer-brand"), 4.5);
      await judge("页脚说明文字", readPair(page, ".footer-notes p"), 4.5);
      await judge("页脚反馈链接", readPair(page, ".footer-notes a"), 4.5);

      // --- 页头与 skip 链接 ---
      await judge("页头字标", readPair(page, ".wordmark"), 4.5);
      await judge("skip 链接文字/底", readPair(page, ".skip-link"), 4.5);

      // 汇总证据表 + 阈值断言
      const lines = rows.map(
        ({ name, ratio: r, need }) =>
          `${r >= need ? "PASS" : "FAIL"}  ${r.toFixed(2)}:1 (need ${need})  ${name}`,
      );
      console.log(`\n[contrast @${width}px]\n${lines.join("\n")}\n`);
      for (const { name, ratio: r, need } of rows) {
        expect(r, `${name} @${width}px`).toBeGreaterThanOrEqual(need);
      }
    });
  }
});
