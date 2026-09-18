import { readFileSync } from "node:fs";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { stubMedia } from "./helpers/media";

// Node 24 的 ESM JSON import 需要 import attribute（Playwright 转译产物
// 直跑 Node），此处以 readFileSync 读取同一份契约夹具（与 mock 服务同源）。
const FIXTURES = new URL("../fixtures/api/", import.meta.url);
const chromeFixture = JSON.parse(
  readFileSync(new URL("chrome.json", FIXTURES), "utf8"),
) as typeof import("../fixtures/api/chrome.json");
const homeFixture = JSON.parse(
  readFileSync(new URL("home.json", FIXTURES), "utf8"),
) as typeof import("../fixtures/api/home.json");

// SPEC-001-F05 验收：首页请求时 SSR 的内容新鲜度（契约 4）、chrome 活数据、
// API 失败边界、轮播渐进增强（含 no-JS / reduced-motion）、键盘顺序、
// 三档视口无横向溢出，以及 CSP 同等约束对产物 HTML 的直接断言
// （check:csp 只扫 .html/.css 静态文件，SSR dist 无 .html——此处以运行时
// HTML 补齐同等检查面）。截图存 docs/evidence/f05-homepage/ 供 Gate 3
// 评审对照；G3 以 Human 代表性截图为准，不做跨平台像素断言。

const MOCK = "http://127.0.0.1:4319";
const VIEWPORTS = [
  { width: 390, height: 844, label: "核心（移动）" },
  { width: 768, height: 1024, label: "次要（平板）" },
  { width: 1440, height: 900, label: "桌面" },
] as const;

/** 控制面改写（测试末尾统一 afterEach reset 恢复夹具）。 */
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
  // /media/* 在生产由反代同源代理；e2e 拓扑分端口，浏览器侧补图（见 helper）
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

// ===== 代表态渲染 + 三档视口（默认夹具数据，不改控制面） =====

for (const { width, height, label } of VIEWPORTS) {
  test(`首页在 ${width}px（${label}）渲染完整冻结层级且无横向溢出`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    const resp = await page.goto("/");
    expect(resp?.status()).toBe(200);

    // 冻结层级：Header（F03）→ hero 轮播 → 五分类导航 → 校园快讯 → Footer
    await expect(page.locator("header.site-header")).toBeVisible();

    // 默认夹具 home.alert = null：例外性轻量条不渲染（v1 同口径）
    await expect(page.locator(".site-alert")).toHaveCount(0);

    // 全页恒一个 h1（visually-hidden 的 page.title）；轮播条目标题为 h2
    const h1 = page.locator("h1");
    await expect(h1).toHaveText("首页", { useInnerText: true });
    await expect(h1).toHaveClass(/visually-hidden/);

    // Hero 轮播（3 项夹具 → JS 增强后仅第 1 项可见；断言只看可见条目）
    const hero = page.locator("[data-carousel]");
    await expect(hero).toBeVisible();
    await expect(hero).toHaveAttribute("aria-label", "主打推荐");
    const activeSlide = page.locator("[data-carousel-item]").nth(0);
    await expect(activeSlide.locator(".hero-chip")).toHaveText("纪事");
    await expect(activeSlide.locator(".hero-title")).toHaveText("开学季专题");
    await expect(activeSlide.locator(".hero-cta")).toHaveText("查看全文");
    await expect(hero.locator("[data-carousel-item]")).toHaveCount(3);
    const enhanced = await hero.getAttribute("data-carousel-enhanced");
    if (enhanced === null) {
      // no-JS 等价断言在专用用例；JS 可用时应完成增强
      throw new Error("轮播未完成增强（carousel.js 未生效）");
    }
    await expect(page.locator(".carousel-controls")).toBeVisible();

    // 五分类导航（冻结顺序；身份 tone 类伴随）
    const cats = page.locator("nav.cats a.cat");
    await expect(cats).toHaveCount(5);
    await expect(cats.nth(0)).toHaveClass(/cat-jishi/);
    await expect(cats.nth(0)).toContainText("昆社纪事");
    await expect(cats.nth(4)).toHaveClass(/cat-zhinan/);

    // 校园快讯（3 项夹具：板块徽标 tone、部门、Asia/Shanghai MM-DD、活动状态）
    const news = page.locator(".news-card");
    await expect(news).toHaveCount(3);
    await expect(news.nth(0).locator(".tag")).toHaveText("纪事");
    await expect(news.nth(0).locator(".news-meta")).toContainText("图书馆");
    await expect(news.nth(0).locator("time")).toHaveAttribute(
      "datetime",
      "2026-09-10",
    );
    await expect(news.nth(0).locator("time")).toHaveText("09-10");
    await expect(news.nth(1).locator(".tag")).toHaveText("活动");
    await expect(news.nth(1).locator(".news-meta")).toContainText("即将开始");
    await expect(news.nth(2).locator("time")).toHaveText("09-08");

    await expect(page.locator("footer.site-footer")).toBeVisible();

    await assertNoHorizontalOverflow(page);

    // Gate 3 候选截图（worker 证据，非 G3 判定物）
    await page.screenshot({
      path: `docs/evidence/f05-homepage/${width}.png`,
      fullPage: true,
    });
  });
}

// ===== 五分类导航滑动条几何（F14 人工批准修正：滑动条延展至平板档） =====

// 验收（参考图构图）：390/430/768 静止时轨可滑（scrollWidth > clientWidth）
// 且右缘恒裁切第 3 张为部分卡（两张整卡 + ~65% 切面，构图与视口无关）；
// 1440 为五列桌面网格，轨零溢出、五卡同一行完整可见。截图存
// docs/evidence/f14-section-rail/ 供评审对照（worker 证据，非 G3 判定物）。
const RAIL_VIEWPORTS = [
  { width: 390, height: 844 },
  { width: 430, height: 932 },
  { width: 768, height: 1024 },
] as const;

/** 轨与五卡的静止几何（视口坐标；scrollLeft 恒 0 = 初始位）。 */
async function railGeometry(page: Page) {
  return page.locator("nav.cats").evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    scrollLeft: el.scrollLeft,
    railLeft: el.getBoundingClientRect().left,
    railRight: el.getBoundingClientRect().right,
    cards: [...el.querySelectorAll("a.cat")].map((c) => {
      const b = c.getBoundingClientRect();
      return { left: b.left, right: b.right, top: b.top };
    }),
  }));
}

for (const { width, height } of RAIL_VIEWPORTS) {
  test(`板块滑动条 ${width}px：轨可滑、静止右缘第 3 张部分可见、页面无横向溢出`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" }); // 截图确定性（轮播静止）
    await page.setViewportSize({ width, height });
    const resp = await page.goto("/");
    expect(resp?.status()).toBe(200);
    await expect(page.locator("nav.cats a.cat")).toHaveCount(5);

    const geo = await railGeometry(page);

    // 原生 overflow 滑动条成立：内容严格超轨
    expect(geo.scrollWidth, "滑动条应可横向滚动").toBeGreaterThan(
      geo.clientWidth,
    );
    expect(geo.scrollLeft, "静止位应为初始 0").toBe(0);

    // 构图：两张整卡完整在轨内，第 3 张右缘越轨被裁（右侧部分卡）、
    // 第 4 张完全轨外——滑动暗示成立且无「下一张几乎放得下」的弱切面
    expect(geo.cards[0].right, "第 1 张应完整可见").toBeLessThanOrEqual(
      geo.railRight,
    );
    expect(geo.cards[1].right, "第 2 张应完整可见").toBeLessThanOrEqual(
      geo.railRight,
    );
    expect(geo.cards[2].left, "第 3 张左缘应已入轨").toBeLessThan(
      geo.railRight,
    );
    expect(geo.cards[2].right, "第 3 张应被右缘裁切").toBeGreaterThan(
      geo.railRight,
    );
    expect(geo.cards[3].left, "第 4 张初始不可见").toBeGreaterThanOrEqual(
      geo.railRight,
    );

    // 切面有意义且稳定：可见部分占整卡 50%–85%（实现值恒 ≈65%）
    const slice =
      (geo.railRight - geo.cards[2].left) /
      (geo.cards[2].right - geo.cards[2].left);
    expect(slice, "第 3 张可见切面比例过小").toBeGreaterThan(0.5);
    expect(slice, "第 3 张可见切面比例过大").toBeLessThan(0.85);

    // 单行（原生横滑行，非换行/网格）
    const tops = geo.cards.map((c) => c.top);
    expect(
      Math.max(...tops) - Math.min(...tops),
      "五卡应同一行",
    ).toBeLessThanOrEqual(1);

    await assertNoHorizontalOverflow(page);

    await page.screenshot({
      path: `docs/evidence/f14-section-rail/${width}.png`,
    });
  });
}

test("板块滑动条：键盘聚焦轨外卡片时原生滚动将其带入可视区", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const rail = page.locator("nav.cats");
  const fifth = rail.locator("a.cat").nth(4);
  await fifth.focus();

  // 原生 focus 滚动（零 JS）：滚动位置前移且第 5 卡整体进入轨可视区
  await expect
    .poll(() => rail.evaluate((el) => el.scrollLeft), "聚焦未触发轨滚动")
    .toBeGreaterThan(0);
  const geo = await railGeometry(page);
  expect(geo.scrollLeft).toBeGreaterThan(0);
  expect(geo.cards[4].right, "聚焦后第 5 卡应完整可见").toBeLessThanOrEqual(
    geo.railRight,
  );
});

test("板块导航 1440px：五列桌面网格，轨零溢出、五卡同一行完整可见", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  const resp = await page.goto("/");
  expect(resp?.status()).toBe(200);
  await expect(page.locator("nav.cats a.cat")).toHaveCount(5);

  const geo = await railGeometry(page);
  expect(
    await page
      .locator("nav.cats")
      .evaluate((el) => getComputedStyle(el).display),
    "桌面档应为网格",
  ).toBe("grid");
  expect(geo.scrollWidth, "桌面轨不应横向溢出").toBeLessThanOrEqual(
    geo.clientWidth,
  );
  for (let i = 0; i < 5; i++) {
    expect(
      geo.cards[i].left,
      `第 ${i + 1} 卡左缘应入轨`,
    ).toBeGreaterThanOrEqual(geo.railLeft);
    expect(geo.cards[i].right, `第 ${i + 1} 卡应完整可见`).toBeLessThanOrEqual(
      geo.railRight,
    );
  }
  const tops = geo.cards.map((c) => c.top);
  expect(
    Math.max(...tops) - Math.min(...tops),
    "五卡应同一行",
  ).toBeLessThanOrEqual(1);

  await assertNoHorizontalOverflow(page);

  await page.screenshot({
    path: "docs/evidence/f14-section-rail/1440.png",
  });
});

test("CSP 同等约束：产物 HTML 无内联脚本/样式，资源引用全部同源", async ({
  request,
}) => {
  const resp = await request.get("/");
  expect(resp.status()).toBe(200);
  const html = await resp.text();

  // 无内联样式块与 style 属性（build.inlineStylesheets: "never"）
  expect(html, "出现 <style> 内联样式块").not.toMatch(/<style[\s>]/i);
  expect(html, "出现 style= 内联样式属性").not.toMatch(/\sstyle="/);

  // 脚本一律带 src 的同源外链（public/carousel.js + defer；无任何行内 JS，
  // Astro 自动内联行为不适用 is:inline 外链形态）
  const scriptTags = html.match(/<script\b[^>]*>/gi) ?? [];
  expect(scriptTags.length, "应存在轮播外链脚本").toBeGreaterThan(0);
  for (const tag of scriptTags) {
    expect(tag, `行内脚本：${tag}`).toMatch(/\bsrc="/);
  }

  // 样式必须外链（无 unsafe-inline 的 CSP 下样式仍可达）
  expect(html).toContain('rel="stylesheet"');

  // 资源引用（src/href）一律同源：http(s) 绝对地址只能是本站 origin
  const refs = [...html.matchAll(/\b(?:src|href)="([^"]+)"/g)].map((m) => m[1]);
  const foreign = refs.filter(
    (ref) =>
      /^https?:\/\//.test(ref) && !ref.startsWith("http://127.0.0.1:4321/"),
  );
  expect(foreign, `出现第三方来源：${foreign.join(", ")}`).toEqual([]);
});

test("查询参数态：noindex + canonical 去参（v1 base.html 口径）", async ({
  request,
}) => {
  const clean = await request.get("/");
  const cleanHtml = await clean.text();
  expect(cleanHtml).not.toContain('name="robots"');
  expect(cleanHtml).not.toContain('rel="canonical"');

  const dirty = await request.get("/?utm_source=e2e&utm_campaign=f05");
  const dirtyHtml = await dirty.text();
  expect(dirtyHtml).toContain('name="robots" content="noindex"');
  expect(dirtyHtml).toContain('rel="canonical" href="http://127.0.0.1:4321/"');
});

// ===== 轮播渐进增强行为 =====

test("自动轮播：默认动效下 5.5s 周期切换；悬停暂停、离开恢复完整周期", async ({
  page,
}) => {
  await page.clock.install();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const hero = page.locator("[data-carousel]");
  await expect(hero).toHaveAttribute("data-carousel-enhanced", "");

  const slides = page.locator("[data-carousel-item]");
  await expect(slides.nth(0)).toBeVisible();

  // 一个完整周期后自动前进
  await page.clock.runFor(5600);
  await expect(slides.nth(1)).toBeVisible();
  await expect(slides.nth(0)).toBeHidden();
  await expect(page.locator(".carousel-dot").nth(1)).toHaveAttribute(
    "aria-current",
    "true",
  );

  // 悬停暂停（不抢焦点、无 aria-live，v1 同款）
  await hero.hover();
  await page.clock.runFor(12_000);
  await expect(slides.nth(1)).toBeVisible();

  // 离开恢复：重建完整周期（不立即切图）
  await page.mouse.move(5, 500);
  await page.clock.runFor(5600);
  await expect(slides.nth(2)).toBeVisible();
});

test("减弱动态效果：autoplay 停用，手动导航恒可用", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.clock.install();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const hero = page.locator("[data-carousel]");
  await expect(hero).toHaveAttribute("data-carousel-enhanced", "");

  const slides = page.locator("[data-carousel-item]");
  await page.clock.runFor(12_000);
  await expect(slides.nth(0)).toBeVisible();

  // 手动导航（按钮/圆点）在 reduce 下仍然工作
  await page.getByRole("button", { name: "下一张" }).click();
  await expect(slides.nth(1)).toBeVisible();
  await expect(slides.nth(0)).toBeHidden();
  await page.getByRole("button", { name: "转到第 3 张" }).click();
  await expect(slides.nth(2)).toBeVisible();
});

test("无 JS：SSR DOM 权威，全部条目按文档流自然可达、无控件残留", async ({
  browser,
}) => {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  await page.goto("/");

  const slides = page.locator("[data-carousel-item]");
  await expect(slides).toHaveCount(3);
  await expect(slides.nth(0)).toBeVisible();
  await expect(slides.nth(1)).toBeVisible();
  await expect(slides.nth(2)).toBeVisible();
  await expect(page.locator("[data-carousel]")).not.toHaveAttribute(
    "data-carousel-enhanced",
    "",
  );
  await expect(page.locator(".carousel-controls")).toHaveCount(0);
  await expect(page.locator("nav.cats a.cat")).toHaveCount(5);
  await assertNoHorizontalOverflow(page);
  await context.close();
});

test("单项轮播保持静态：零增强、无控件（v1 同口径）", async ({
  page,
  request,
}) => {
  await control(request, {
    endpoint: "home",
    mode: "ok",
    payload: { ...homeFixture, carousel: [homeFixture.carousel[0]] },
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const hero = page.locator("[data-carousel]");
  await expect(hero).toBeVisible();
  await expect(hero).not.toHaveAttribute("data-carousel-enhanced", "");
  await expect(page.locator(".carousel-controls")).toHaveCount(0);
  await expect(page.locator(".hero-title")).toHaveText("开学季专题");
});

// ===== 键盘顺序（WCAG 2.2 AA 预留硬门） =====

test("键盘顺序：skip → 品牌 → 搜索 → hero 卡 → 轮播控件 → 分类 → 快讯", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.locator("[data-carousel]")).toHaveAttribute(
    "data-carousel-enhanced",
    "",
  );

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "跳到主要内容" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Peiligo 首页" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("searchbox", { name: "搜索站内内容" }),
  ).toBeFocused();

  // 隐藏轮播条目不可聚焦：第 1 个 tab 到的是可见条目卡
  await page.keyboard.press("Tab");
  await expect(page.locator(".hero-card").nth(0)).toBeFocused();

  // JS 创建的控件按 DOM 序插入条目之后：上一张 → 3 圆点 → 下一张
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "上一张" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator(".carousel-dot").nth(0)).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const next = page.getByRole("button", { name: "下一张" });
  await expect(next).toBeFocused();

  // 键盘手动导航：回车前进一张，aria-current 同步到第 2 圆点
  await page.keyboard.press("Enter");
  await expect(page.locator("[data-carousel-item]").nth(1)).toBeVisible();
  await expect(page.locator("[data-carousel-item]").nth(0)).toBeHidden();
  await expect(page.locator(".carousel-dot").nth(1)).toHaveAttribute(
    "aria-current",
    "true",
  );

  // 控件之后进入五分类导航
  await page.keyboard.press("Tab");
  await expect(page.locator("nav.cats a.cat").nth(0)).toBeFocused();
});

// ===== 请求时新鲜度（契约 4）与 chrome 活数据 =====

test("每请求直连：chrome/home 计数随每次页面请求递增（无缓存）", async ({
  page,
  request,
}) => {
  const readCounts = async () =>
    (await (await request.get(`${MOCK}/__requests`)).json()) as {
      chrome: number;
      home: number;
    };
  const before = await readCounts();
  await page.goto("/");
  await page.goto("/");
  const after = await readCounts();
  expect(after.chrome - before.chrome, "chrome 未按每请求直连").toBe(2);
  expect(after.home - before.home, "home 未按每请求直连").toBe(2);
});

test("Wagtail 发布在下一次请求可见：home 内容更新无需重建", async ({
  page,
  request,
}) => {
  const published = {
    ...homeFixture,
    title: "首页（已发布更新）",
    alert: { text: "明日上午校园网络检修" },
    campus_news: [
      {
        ...homeFixture.campus_news[0],
        title: "新发布的通告",
        published_at: "2026-09-15T08:00:00+08:00",
      },
      ...homeFixture.campus_news.slice(1),
    ],
  };
  await control(request, { endpoint: "home", mode: "ok", payload: published });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.locator("h1")).toHaveText("首页（已发布更新）", {
    useInnerText: true,
  });
  const alert = page.locator(".site-alert");
  await expect(alert).toBeVisible();
  await expect(alert).toHaveAttribute("role", "alert");
  await expect(alert).toHaveText("明日上午校园网络检修");
  await expect(page.locator(".news-card h3").first()).toHaveText(
    "新发布的通告",
  );
  await expect(page.locator(".news-card time").first()).toHaveText("09-15");

  // 高价值状态证据：1440 桌面紧急提示条（Gate 3 附加态）
  await page.screenshot({
    path: "docs/evidence/f05-homepage/alert-1440.png",
    fullPage: true,
  });
});

test("chrome 活数据：站名与反馈邮箱随后台修改在下一次请求可见", async ({
  page,
  request,
}) => {
  await control(request, {
    endpoint: "chrome",
    mode: "ok",
    payload: {
      ...chromeFixture,
      site_name: "裴立阁",
      feedback_email: "ops@peiligo.example",
    },
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  // 页头字标与品牌 aria-label 用新站名
  await expect(page.locator(".wordmark")).toHaveText("裴立阁.");
  await expect(page.getByRole("link", { name: "裴立阁 首页" })).toBeVisible();
  // 页脚品牌、版权与反馈链接全部跟随
  await expect(page.locator(".footer-brand")).toContainText("裴立阁.");
  await expect(page.locator(".footer-meta")).toHaveText(
    `© ${new Date().getFullYear()} 裴立阁`,
  );
  const feedback = page.locator(".footer-notes a");
  await expect(feedback).toHaveText("ops@peiligo.example");
  await expect(feedback).toHaveAttribute(
    "href",
    /^mailto:ops@peiligo\.example\?subject=[^&]+&body=/,
  );
});

// ===== API 失败边界 =====

test("chrome 失败 → 500 错误边界（chrome 永不陈旧，契约 4）", async ({
  page,
  request,
}) => {
  await page.goto("/"); // 预热：home 陈旧缓存就位，chrome 仍不允许陈旧
  await control(request, { endpoint: "chrome", mode: "fail" });

  const resp = await page.goto("/");
  expect(resp?.status()).toBe(500);
  const h1 = page.locator("h1");
  await expect(h1).toHaveText("服务暂时不可用");
  const back = page.getByRole("link", { name: "返回首页" });
  await expect(back).toHaveAttribute("href", "/");
  // 独立错误页：无共享外壳输出（chrome 不可用即整页边界）
  await expect(page.locator("header.site-header")).toHaveCount(0);
  await expect(page.locator("footer.site-footer")).toHaveCount(0);
});

test("home 失败 → ≤5min 陈旧回退 200（普通内容 stale-while-error）", async ({
  page,
  request,
}) => {
  await page.goto("/"); // 预热最近成功版本
  await control(request, { endpoint: "home", mode: "fail" });

  const resp = await page.goto("/");
  expect(resp?.status()).toBe(200);
  await expect(page.locator("[data-carousel]")).toBeVisible();
  await expect(page.locator(".hero-title").first()).toHaveText("开学季专题");
  await expect(page.locator("footer.site-footer")).toBeVisible();
});

test("响应不合契约（schema-violation）→ 500，不回退不渲染坏数据", async ({
  page,
  request,
}) => {
  await control(request, { endpoint: "chrome", mode: "invalid" });

  const resp = await page.goto("/");
  expect(resp?.status()).toBe(500);
  await expect(page.locator("h1")).toHaveText("服务暂时不可用");
});

test("全部端点失败 → 独立 500 错误页可返回首页恢复", async ({
  page,
  request,
}) => {
  await control(request, { endpoint: "all", mode: "fail" });

  const resp = await page.goto("/");
  expect(resp?.status()).toBe(500);
  await expect(page.locator("h1")).toHaveText("服务暂时不可用");
  await expect(page.locator("body")).toContainText(
    "抱歉，Peiligo 出现了临时故障，请稍后重试。",
  );
  // 错误页自包含：无样式依赖也能读（v1 500.html 口径，无 robots meta）
  const html = await page.content();
  expect(html).not.toContain('name="robots"');

  // 返回首页链接在故障恢复后可正常回站
  await request.post(`${MOCK}/__control/reset`);
  await page.getByRole("link", { name: "返回首页" }).click();
  await expect(page.locator("header.site-header")).toBeVisible();
});

// ===== 低数据构图（稀疏态，空库不算故障） =====

test("稀疏态：轮播/快讯为空时不渲染对应区块，页面完整可读", async ({
  page,
  request,
}) => {
  await control(request, {
    endpoint: "home",
    mode: "ok",
    payload: {
      title: "首页",
      alert: null,
      carousel: [],
      sections: homeFixture.sections,
      campus_news: [],
    },
  });

  await page.setViewportSize({ width: 390, height: 844 });
  const resp = await page.goto("/");
  expect(resp?.status()).toBe(200);
  await expect(page.locator("[data-carousel]")).toHaveCount(0);
  await expect(page.locator(".news")).toHaveCount(0);
  await expect(page.locator("nav.cats a.cat")).toHaveCount(5);
  await expect(page.locator("footer.site-footer")).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.screenshot({
    path: "docs/evidence/f05-homepage/sparse-390.png",
    fullPage: true,
  });
});
