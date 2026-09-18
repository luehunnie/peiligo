import { readFileSync } from "node:fs";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { stubMedia } from "./helpers/media";
import { assertNoHorizontalOverflow } from "./helpers/assert";
import {
  contrastRatio,
  parseColor,
  readPair,
  type Pair,
} from "./helpers/contrast";

// SPEC-001-F09 全站 WCAG 2.2 AA 审计（自动化面，首页之外的代表页族）：
// 首页对比度/焦点环已由 F05-G3 视觉门（contrast.spec.ts，计算样式判定）
// 硬门；本审计把同一「计算样式事实源」原语（helpers/contrast.ts）与结构/
// 键盘/目标尺寸/回流检查扩展到列表、详情、搜索、404、外链确认与失败态：
//   1.4.3/1.4.11 对比度（390/1440 代表页逐对计算）
//   1.3.1/2.4.2/3.1.1 唯一 h1 且不跳级、页面标题、lang
//   1.1.1 图片 alt；3.3.2/4.1.2 输入框与按钮可达名称
//   2.4.1/2.4.3/2.4.7 键盘全页 Tab 游走：skip 链接居首、焦点环可见
//     （≥2px；搜索框以容器 focus-within 描边为指示——首页 G3 同口径）、
//     焦点循环回到起点（无键盘陷阱）
//   2.5.8 Target Size Minimum（2.2 新增 AA）：可点目标有效命中区 ≥24×24
//     （圆点经 ::after 零渲染外扩；行内文本链接按豁免不在判定面）
//   1.4.10 Reflow：320px（WCAG 参照宽度）无横向溢出
//   3.2.6 Consistent Help（2.2 新增 AA）：页脚反馈入口全页恒在
//   2.3.3 动效偏好：reduce 时内容面过渡时长归零（页头已测，此处测文章详情面）
// 豁免口径：纯装饰分隔符（.dot-sep「·」、面包屑 CSS「/」，列表结构已承载
// 分隔语义）与行内文本链接不参与目标尺寸判定；测量值与整改记录见
// docs/a11y-performance.md（F09 审计报告）。

const MOCK = "http://127.0.0.1:4319";
const SEARCH_URL = "/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86";

const VIEWPORTS = [
  { width: 390, height: 844 },
  { width: 1440, height: 900 },
] as const;

/** 代表页族（覆盖全部页面类型；首页对比度面由 contrast.spec 硬门） */
const PAGES = [
  { name: "列表页", path: "/chronicle/", status: 200 },
  { name: "详情页", path: "/chronicle/jwc/library-hours/", status: 200 },
  { name: "搜索结果页", path: SEARCH_URL, status: 200 },
  { name: "404 页", path: "/no-such-page/", status: 404 },
  {
    name: "外链确认页",
    path: "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
    status: 200,
  },
] as const;

const FIXTURES = new URL("../fixtures/api/", import.meta.url);
const listFixture = JSON.parse(
  readFileSync(new URL("section-list.json", FIXTURES), "utf8"),
);

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

// ===== 1. 结构 / 语义 / 命名（全代表页 × 390/1440） =====

for (const { width } of VIEWPORTS) {
  for (const { name, path, status } of PAGES) {
    test(`${name} ${width}px：结构语义（h1 唯一不跳级 / 标题 / lang / 地标 / alt / 可达名称 / 反馈恒在）`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 844 });
      const resp = await page.goto(path);
      expect(resp?.status()).toBe(status);

      // 3.1.1 页面语言；2.4.2 页面标题（非空且含站点后缀）
      expect(await page.locator("html").getAttribute("lang")).toBe("zh-Hans");
      const title = await page.title();
      expect(title.trim().length, "页面标题非空").toBeGreaterThan(0);
      expect(title).toContain("Peiligo");

      // 1.3.1 标题结构：全页恒一个 h1，标题级别不跳级
      const levels = await page.evaluate(() =>
        [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((h) =>
          Number(h.tagName[1]),
        ),
      );
      expect(
        levels.filter((l) => l === 1),
        "唯一 h1",
      ).toHaveLength(1);
      for (let i = 1; i < levels.length; i++) {
        expect(
          levels[i],
          `${name} 标题跳级：${levels.slice(0, i + 1).join("→")}`,
        ).toBeLessThanOrEqual(levels[i - 1] + 1);
      }

      // 地标：页头 / 主区 / 页脚；nav 均有可读名称
      await expect(page.locator("header.site-header")).toBeVisible();
      await expect(page.locator("main#main-content")).toBeVisible();
      await expect(page.locator("footer.site-footer")).toBeVisible();
      const navCount = await page.locator("nav").count();
      for (let i = 0; i < navCount; i++) {
        const nav = page.locator("nav").nth(i);
        expect(
          (await nav.getAttribute("aria-label"))?.trim(),
          `第 ${i + 1} 个 nav 缺 aria-label`,
        ).toBeTruthy();
      }

      // 1.1.1 图片均有 alt 属性（装饰图 alt=""）
      const imgs = await page.locator("img").count();
      for (let i = 0; i < imgs; i++) {
        expect(
          await page.locator("img").nth(i).getAttribute("alt"),
          `第 ${i + 1} 张 img 缺 alt 属性`,
        ).not.toBeNull();
      }

      // 3.3.2 / 4.1.2 输入框与按钮均有可达名称
      const unnamed = await page.evaluate(() => {
        const nameOf = (el: Element) => {
          const he = el as HTMLElement;
          return (
            he.getAttribute("aria-label") ??
            he.getAttribute("aria-labelledby") ??
            (he.id
              ? document.querySelector(`label[for="${he.id}"]`)?.textContent
              : null) ??
            (he.tagName === "BUTTON" ? (he.textContent ?? "").trim() : "")
          );
        };
        return [...document.querySelectorAll("input:not([type=hidden]),button")]
          .map((el) => nameOf(el).trim())
          .filter((name) => name === "");
      });
      expect(unnamed, `缺可达名称的控件：${unnamed.length} 个`).toEqual([]);

      // 3.2.6 Consistent Help（2.2 新增）：页脚反馈入口逐页恒在
      await expect(
        page.locator("footer.site-footer").locator('a[href^="mailto:"]'),
      ).toBeVisible();
    });
  }
}

// ===== 2. 非首页代表面对比度（390/1440；计算样式事实源与首页 G3 同口径） =====

for (const { width } of VIEWPORTS) {
  test(`非首页代表面 ${width}px：文本/非文本对比度全部达 AA`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width, height: 844 });

    type Row = { page: string; name: string; ratio: number; need: number };
    const allRows: Row[] = [];

    const runPage = async (
      pageName: string,
      path: string,
      plan: [string, number, () => Promise<Pair>][] = [],
    ) => {
      // 计划项惰性求值：readPair 必须在 goto 之后的执行上下文中调用
      // （预建 Promise 会在导航时随上下文销毁）。
      await page.goto(path);
      const rows: Row[] = [];
      for (const [name, need, read] of plan) {
        const pair = await read();
        const ratio = contrastRatio(parseColor(pair.fg), parseColor(pair.bg));
        rows.push({ page: pageName, name, ratio, need });
      }
      const lines = rows.map(
        ({ name, ratio: r, need }) =>
          `${r >= need ? "PASS" : "FAIL"}  ${r.toFixed(2)}:1 (need ${need})  ${name}`,
      );
      console.log(
        `\n[contrast ${pageName} @${width}px]\n${lines.join("\n")}\n`,
      );
      for (const { page: pg, name, ratio: r, need } of rows) {
        expect(r, `${pg}·${name} @${width}px`).toBeGreaterThanOrEqual(need);
        allRows.push({ page: pg, name, ratio: r, need });
      }
    };

    // --- 列表页（行流 + 面包屑 + 徽标；.r-meta 为 F09 整改对象）---
    await runPage("列表页", "/chronicle/", [
      ["列表行标题", 4.5, () => readPair(page, ".r-row .r-main h2")],
      ["列表行摘要", 4.5, () => readPair(page, ".r-row .r-main p")],
      [
        "列表行元信息（F09 整改：--ink-2）",
        4.5,
        () => readPair(page, ".r-row .r-meta"),
      ],
      ["行首栏目徽标", 4.5, () => readPair(page, ".r-row .tag")],
      ["面包屑链接", 4.5, () => readPair(page, ".breadcrumb a")],
      ["面包屑当前页", 4.5, () => readPair(page, ".breadcrumb [aria-current]")],
    ]);

    // --- 搜索结果页（chips / 汇总 / 高亮 / 大搜索框）---
    await runPage("搜索结果页", SEARCH_URL, [
      ["结果汇总文字", 4.5, () => readPair(page, ".s-sum")],
      ["栏目 chip（未激活）", 4.5, () => readPair(page, ".t-chip:not(.on)")],
      ["栏目 chip（激活）", 4.5, () => readPair(page, ".t-chip.on")],
      [
        "关键词高亮 mark",
        4.5,
        // mark 底为半透明黄（v1 原值）：祖先解析得白底为保守下界，
        // 实际合成底（黄 45% 上 ink）对比更高
        () => readPair(page, ".r-row mark"),
      ],
      ["大搜索框按钮", 4.5, () => readPair(page, ".big-search button")],
      [
        "大搜索框 placeholder（F09 整改：--teal-deep）",
        4.5,
        () => readPair(page, ".big-search input", "::placeholder"),
      ],
    ]);

    // --- 详情页（通知类：题头/正文/元信息；正文段落为裸片段无 <p> 元素，
    //     读容器继承色）---
    await runPage("详情页", "/chronicle/jwc/library-hours/", [
      ["详情 H1", 4.5, () => readPair(page, ".art-head h1")],
      ["详情元信息", 4.5, () => readPair(page, ".art-meta")],
      ["详情导语", 4.5, () => readPair(page, ".article-lede")],
      ["题头栏目徽标", 4.5, () => readPair(page, ".art-head .tag")],
      ["返回链接", 4.5, () => readPair(page, ".art-back a")],
      ["正文段落（容器继承色）", 4.5, () => readPair(page, ".article-body")],
    ]);

    // --- 文章详情（.file/.file-arrow 仅正文外链行渲染，通知夹具无；
    //     /events/xshd/spring-sports/ 夹具含 attachment/external_link 块）---
    await runPage("文章详情", "/events/xshd/spring-sports/", [
      ["正文段落（容器继承色）", 4.5, () => readPair(page, ".article-body")],
      ["附件链接文字", 4.5, () => readPair(page, ".block-attachment a")],
      ["外链行链接文字", 4.5, () => readPair(page, ".article-body a.file")],
      [
        "外链箭头图标（F09 整改，非文本 ≥3）",
        3,
        () => readPair(page, ".file-arrow"),
      ],
    ]);

    // --- 404 页（引导药丸链接）---
    await runPage("404 页", "/no-such-page/", [
      ["404 H1", 4.5, () => readPair(page, "main h1")],
      ["板块直达链接", 4.5, () => readPair(page, ".section-links li a")],
    ]);

    // --- 外链确认页（卡片全要素）---
    await runPage(
      "外链确认页",
      "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
      [
        ["确认页 kicker", 4.5, () => readPair(page, ".c-kicker")],
        ["确认页 H1", 4.5, () => readPair(page, ".confirm-card h1")],
        ["确认页说明", 4.5, () => readPair(page, ".c-lead")],
        ["目标域名", 4.5, () => readPair(page, ".c-domain")],
        ["继续访问按钮", 4.5, () => readPair(page, ".c-primary")],
        ["返回按钮", 4.5, () => readPair(page, ".c-ghost")],
        ["声明文案", 4.5, () => readPair(page, ".c-note p")],
      ],
    );

    // --- 失败态（列表失败注入；FailureState 通用语言）---
    // 陈旧回退按完整 URL（含查询串）取键（F08 契约 4）：本测试前面已把
    // /chronicle/ 无查询串的键成功缓存，故用当次运行唯一探针查询串保证
    // 该键从未成功过——失败必然无陈旧版本可回退，直达失败态
    // （error-states.spec 同口径）。
    const failUrl = `/chronicle/?q=f09-probe-${Date.now()}`;
    await control(request, { endpoint: "section-list", mode: "fail" });
    await runPage("失败态", failUrl, [
      ["失败标题", 4.5, () => readPair(page, ".fail-title")],
      ["失败错误条", 4.5, () => readPair(page, ".fail-note")],
      ["失败重试链接", 4.5, () => readPair(page, ".fail-home a")],
    ]);

    expect(allRows.length, "受检对总数").toBeGreaterThanOrEqual(25);
  });
}

// ===== 3. 键盘游走（2.4.1/2.4.3/2.4.7）：skip 居首、焦点环可见、无陷阱 =====

/** 焦点指示断言：普通元素读自身 outline；搜索框（input:focus outline
    关闭，指示由容器 focus-within 描边承担——首页 G3 同口径）读容器描边。 */
async function assertFocusIndicator(page: Page, step: number): Promise<void> {
  const indicator = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return null;
    const container = el.closest(".search, .big-search");
    if (container && el.tagName === "INPUT") {
      const cs = getComputedStyle(container);
      return { width: cs.borderTopWidth, color: cs.borderTopColor };
    }
    const cs = getComputedStyle(el);
    return { width: cs.outlineWidth, color: cs.outlineColor };
  });
  expect(indicator, "activeElement 计算失败").not.toBeNull();
  expect(
    parseFloat(indicator!.width),
    `第 ${step + 1} 站焦点指示宽度`,
  ).toBeGreaterThanOrEqual(2);
}

for (const path of ["/chronicle/jwc/library-hours/", SEARCH_URL]) {
  test(`键盘全页游走 + 焦点指示（${path}）`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);

    // 陷阱判定用「已访问」DOM 标记而非描述符去重：同类元素（如多个 chip）
    // 描述符相同，去重会把正常前进误判为卡死。Tab 回到任一已访问元素 =
    // 焦点循环闭合（无陷阱），游走终止。
    let visited = 0;
    for (let i = 0; i < 60; i++) {
      await page.keyboard.press("Tab");
      const probe = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body)
          return { revisited: true, descriptor: "body" };
        const cls =
          typeof el.className === "string" ? el.className.split(" ")[0] : "";
        const descriptor = `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ""}`;
        const revisited = el.hasAttribute("data-a11y-walk");
        el.setAttribute("data-a11y-walk", "");
        return { revisited, descriptor };
      });
      if (i === 0) {
        // 2.4.1 skip 链接为首个可聚焦元素
        expect(probe.descriptor, "首个 Tab 焦点应为 skip 链接").toContain(
          "skip-link",
        );
      }
      if (probe.revisited) break; // 焦点回到已访问元素：循环闭合，无陷阱
      visited++;
      await assertFocusIndicator(page, i);
    }
    expect(visited, "可聚焦元素游走数量").toBeGreaterThanOrEqual(4);
  });
}

// ===== 4. 目标尺寸（2.5.8，2.2 新增 AA）：有效命中区 ≥24×24 =====

test("可点目标 ≥24×24（轮播控件 / 分页 / chips / 搜索按钮 / 直达链接）", async ({
  page,
  request,
}) => {
  // 列表页注入分页态使 .pg 翻页链接出现
  await control(request, {
    endpoint: "section-list",
    mode: "ok",
    payload: {
      ...listFixture,
      pagination: {
        total: 2,
        page: 1,
        page_count: 2,
        per_page: 20,
        has_next: true,
        has_previous: false,
      },
    },
  });

  const measure = (selector: string) =>
    page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const box = el.getBoundingClientRect();
      // 命中区 = 边框盒 + 零渲染伪元素（::after inset 负值外扩，如轮播圆点）
      let w = box.width;
      let h = box.height;
      const after = getComputedStyle(el, "::after");
      if (after.position === "absolute") {
        const inset = after.inset.split(" ").map((v) => parseFloat(v) || 0);
        const [top, right = top, bottom = top, left = right] = inset;
        w += (left < 0 ? -left : 0) + (right < 0 ? -right : 0);
        h += (top < 0 ? -top : 0) + (bottom < 0 ? -bottom : 0);
      }
      return { w, h, visible: box.width > 0 && box.height > 0 };
    }, selector);

  const check = async (label: string, selector: string) => {
    const m = await measure(selector);
    expect(m, `${label} 未找到`).not.toBeNull();
    expect(m!.visible, `${label} 不可见`).toBe(true);
    expect(
      Math.round(m!.w),
      `${label} 命中区宽 ${m!.w}px`,
    ).toBeGreaterThanOrEqual(24);
    expect(
      Math.round(m!.h),
      `${label} 命中区高 ${m!.h}px`,
    ).toBeGreaterThanOrEqual(24);
  };

  // 首页轮播控件（增强态；圆点 10×10 视觉经 ::after 外扩为 24×24）
  await page.goto("/");
  await expect(page.locator("[data-carousel]")).toHaveAttribute(
    "data-carousel-enhanced",
    "",
  );
  await check("轮播 prev", ".carousel-prev");
  await check("轮播 next", ".carousel-next");
  await check("轮播圆点", ".carousel-dot");
  await check("激活圆点", ".carousel-dot[aria-current]");

  // 列表页分页（含「下一页」）
  await page.goto("/chronicle/");
  await check("分页链接", "a.pg");
  await check("下一页", ".next-pg");

  // 搜索页 chips 与提交按钮
  await page.goto(SEARCH_URL);
  await check("栏目 chip", ".t-chip");
  await check("搜索提交按钮", ".big-search button");

  // 404 直达链接药丸
  await page.goto("/no-such-page/");
  await check("404 直达链接", ".section-links li a");
});

// ===== 5. Reflow（1.4.10）：320px（WCAG 参照宽）无横向溢出 =====

for (const path of [
  "/",
  "/chronicle/",
  "/chronicle/jwc/library-hours/",
  SEARCH_URL,
]) {
  test(`320px 无横向溢出（1.4.10）：${path}`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 690 });
    await page.goto(path);
    await assertNoHorizontalOverflow(page);
  });
}

// ===== 6. 动效偏好（2.3.3 纪律）：reduce 时内容面过渡归零 =====

test("prefers-reduced-motion：文章详情外链行过渡时长归零", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  // .file-arrow 仅正文外链行渲染（通知夹具无）→ 用文章夹具页
  await page.goto("/events/xshd/spring-sports/");
  const duration = await page.evaluate(
    () =>
      getComputedStyle(document.querySelector(".file-arrow")!)
        .transitionDuration,
  );
  expect(parseFloat(duration)).toBeLessThanOrEqual(0.02);
});
