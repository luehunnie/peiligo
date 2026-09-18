import {
  expect,
  test,
  devices,
  type BrowserContext,
  type Page,
} from "@playwright/test";
import { stubMedia } from "./helpers/media";

// SPEC-001-F09 性能预算门（防回退基线；G5 输入）：
// 首页 + 代表内容页（详情）+ 搜索结果页在「模拟移动 4G」下的实测：
//   LCP ≤ 2500ms · CLS < 0.1 · INP ≤ 200ms；首屏无不必要 JS；
//   静态内容页零脚本（≤ v1 基线——v1 全站挂载脚本，重建后内容页零 JS）。
// 口径（记录于 docs/a11y-performance.md）：
//   - 节流＝CDP 注入：RTT 150ms / 下行 1.6Mbps / 上行 750Kbps（Lighthouse
//     移动预设同值）+ CPU 4× 慢速；视口 390×844（验收核心档）；
//   - 指标＝页面内原生 PerformanceObserver（largest-contentful-paint /
//     layout-shift / event-timing），INP 取脚本化代表交互（轮播控件、
//     搜索框点击）中的最差交互时延（交互集小，max 即 98 分位的可复现代理）；
//   - 媒体图由本地 stub 提供（不经节流，对 LCP 偏乐观、利于稳定判定）；
//     服务端 SSR 取数在本机 mock 上不节流。真机/真网评审属 G5（Human）。
// 预算即基线：超预算 = CI 红（本文件随 Playwright Smoke 门运行）。

const BUDGETS = {
  lcpMs: 2500,
  cls: 0.1,
  inpMs: 200,
  /** 首页脚本字节预算：唯一脚本 = public/carousel.js（defer，约 5.7KB 源码）*/
  homeScriptBytes: 8 * 1024,
  /** 静态内容页脚本预算：零 JS（v1 内容页挂全站脚本，重建后 ≤ 基线且更低）*/
  contentScriptBytes: 0,
} as const;

const DETAIL_PATH = "/chronicle/jwc/library-hours/";
const SEARCH_URL = "/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86";

/** 页面内原生指标采集（导航前注入；指标语义见文件头注）。 */
const COLLECT_INIT = `
  window.__perf = { lcpMs: 0, cls: 0, inpMs: 0 };
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        if (e.startTime > window.__perf.lcpMs) window.__perf.lcpMs = e.startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch {}
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        if (!e.hadRecentInput) window.__perf.cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  } catch {}
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        if (e.interactionId > 0 && e.duration > window.__perf.inpMs)
          window.__perf.inpMs = e.duration;
    }).observe({ type: "event", durationThreshold: 40, buffered: true });
  } catch {}
`;

interface Measured {
  path: string;
  lcpMs: number;
  cls: number;
  inpMs: number;
  scriptBytes: number;
}

/** 模拟移动 4G 节流（Lighthouse 移动预设同值）+ 4× CPU。CDP 会话按页面
    绑定：每张被测页面各自开 session 注入。 */
async function throttle(page: Page): Promise<void> {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 150,
    downloadThroughput: (1.6 * 1024 * 1024) / 8,
    uploadThroughput: (750 * 1024) / 8,
  });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
}

async function measurePage(
  context: BrowserContext,
  path: string,
  interact: (page: Page) => Promise<void>,
): Promise<Measured> {
  const page = await context.newPage();
  await context.addInitScript(COLLECT_INIT);
  await throttle(page);

  await stubMedia(page);
  let scriptBytes = 0;
  page.on("response", async (response) => {
    if (response.request().resourceType() === "script") {
      try {
        scriptBytes += (await response.body()).byteLength;
      } catch {
        // 计量失败不计入（预算按「不超过」判定，漏计只会宽松不会误伤）
      }
    }
  });

  await page.goto(path, { waitUntil: "load" });
  await page.waitForTimeout(4000); // 覆盖轮播首个自动切换周期（5500ms 内）
  await interact(page);
  await page.waitForTimeout(800);
  const perf = (await page.evaluate(
    () =>
      (window as unknown as { __perf: Omit<Measured, "path" | "scriptBytes"> })
        .__perf,
  )) as Omit<Measured, "path" | "scriptBytes">;
  await page.close();
  return { path, ...perf, scriptBytes };
}

test("性能预算实测（模拟移动 4G：LCP/CLS/INP + JS 字节）", async ({
  browser,
}) => {
  const context = await browser.newContext({
    ...devices["Pixel 7"],
    viewport: { width: 390, height: 844 },
  });

  const next = (p: Page) => p.locator(".carousel-next").click();
  const dot = (p: Page) => p.locator(".carousel-dot").nth(1).click();
  const prev = (p: Page) => p.locator(".carousel-prev").click();
  const searchFocus = (p: Page) => p.locator(".search input").click();

  const report: Measured[] = [
    await measurePage(context, "/", async (p) => {
      await next(p);
      await dot(p);
      await prev(p);
    }),
    await measurePage(context, DETAIL_PATH, searchFocus),
    await measurePage(context, SEARCH_URL, searchFocus),
  ];
  await context.close();

  // 证据表
  const rows = report.map((m) => ({
    页面: m.path,
    "LCP(ms)": Math.round(m.lcpMs),
    CLS: m.cls.toFixed(3),
    "INP(ms)": Math.round(m.inpMs),
    "JS(bytes)": m.scriptBytes,
  }));
  console.log(
    "\n[perf-budget @390 模拟移动 4G]\n" + JSON.stringify(rows, null, 2),
  );

  for (const m of report) {
    const label = `预算超限（${m.path}）`;
    expect(
      m.lcpMs,
      `${label} LCP ${Math.round(m.lcpMs)}ms`,
    ).toBeLessThanOrEqual(BUDGETS.lcpMs);
    expect(m.cls, `${label} CLS ${m.cls.toFixed(3)}`).toBeLessThan(BUDGETS.cls);
    expect(
      m.inpMs,
      `${label} INP ${Math.round(m.inpMs)}ms`,
    ).toBeLessThanOrEqual(BUDGETS.inpMs);
  }
  const home = report.find((m) => m.path === "/");
  expect(home, "首页测量缺失").toBeDefined();
  expect(
    home!.scriptBytes,
    `首页脚本 ${home!.scriptBytes}B（预算 ${BUDGETS.homeScriptBytes}B）`,
  ).toBeLessThanOrEqual(BUDGETS.homeScriptBytes);
  for (const m of report.filter((m) => m.path !== "/")) {
    expect(
      m.scriptBytes,
      `${m.path} 脚本字节应为零（内容页零 JS 基线）`,
    ).toBeLessThanOrEqual(BUDGETS.contentScriptBytes);
  }
});
