import { readFileSync } from "node:fs";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { stubMedia } from "./helpers/media";
import {
  assertNoHorizontalOverflow,
  assertStaticHtmlInvariants,
} from "./helpers/assert";

// SPEC-001-F07 验收：/search/ 请求时 SSR 迁移等价性。逐项覆盖：表单态/
// 筛选态/空态/失败态四状态、URL 参数透传（契约 2）、高亮转义与 XSS 形
// 查询注入面为零（契约 3，openapi /search 冻结管线）、无陈旧结果与每请
// 求直连（契约 4，NEVER_STALE 面）、dept 标题模式 §8.2、分页参数保留、
// 键盘可达（原生 GET 表单零 JS）、三档视口无横向溢出。
// 截图存 docs/evidence/f07-search/ 供 Gate 4 评审对照。

const MOCK = "http://127.0.0.1:4319";
const ORIGIN = "http://127.0.0.1:4321";
const VIEWPORTS = [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

// 与 content.spec 同款：readFileSync 读取同一份契约夹具（与 mock 服务同源）
const FIXTURES = new URL("../fixtures/api/", import.meta.url);
const searchFixture = JSON.parse(
  readFileSync(new URL("search.json", FIXTURES), "utf8"),
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

/** 构造 n 条分页用条目（标题含命中词，供高亮断言复用）。 */
function makeEntries(n: number, page: number) {
  return Array.from({ length: n }, (_, i) => ({
    type: "notice",
    id: (page - 1) * n + i + 1,
    title: `图书馆通知第${(page - 1) * n + i + 1}号`,
    url: `/chronicle/jwc/library-hours/`,
    expired: false,
    section_slug: "chronicle",
    section_title: "昆社纪事",
    department_name: "图书馆",
    published_at: "2026-09-10T09:00:00+08:00",
    event_status: null,
    list_summary: "即日起至本学期末调整开放时间。",
  }));
}

// ===== 状态矩阵：表单态 / 结果态 / 空态 =====

for (const { width, height } of VIEWPORTS) {
  test(`结果态在 ${width}px 渲染冻结层级且无横向溢出`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");

    // 页头层级：隐藏 H1 → 大搜索框（回显契约 q）→ 汇总 → 栏目 chips
    await expect(page.locator("h1")).toHaveText("站内搜索");
    await expect(page.locator(".big-search input")).toHaveValue("图书馆");
    await expect(page.locator(".s-sum")).toHaveText(
      "找到 1 条与「图书馆」相关的内容",
    );
    const chips = page.locator(".t-chip");
    await expect(chips).toHaveCount(6);
    await expect(chips.first()).toHaveText("全部");
    await expect(chips.first()).toHaveAttribute("aria-current", "true");
    // 板块 chip 渲染两字短名（v1 slug|section_short 口径）
    await expect(chips.nth(1)).toHaveText("纪事");
    await expect(chips.nth(1)).not.toHaveAttribute("aria-current");

    // 结果行：高亮 + 栏目徽标 + show_section 栏目归属段 + 内部链接
    const row = page.locator("a.r-row");
    await expect(row).toHaveCount(1);
    await expect(row).toHaveAttribute("href", "/chronicle/jwc/library-hours/");
    await expect(row.locator("mark")).toHaveText("图书馆");
    await expect(row.locator(".tag")).toHaveText("纪事");
    await expect(row.locator(".r-meta")).toHaveText(
      "图书馆 · 2026-09-10 · 昆社纪事",
    );
    await expect(page.locator(".pager .pg.on")).toHaveText("1");

    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: `docs/evidence/f07-search/results-${width}.png`,
      fullPage: true,
    });
  });
}

test("表单态（无参数）：仅大搜索框，无汇总/chips/结果/空态", async ({
  request,
}) => {
  const html = await (await request.get("/search/")).text();
  expect(html).toContain("<title>站内搜索 - ");
  expect(html).toContain('name="robots" content="noindex"');
  expect(html).toContain(
    'rel="canonical" href="http://127.0.0.1:4321/search/"',
  );
  expect(html).toContain('id="id_q" name="q" value'); // 输入框空回显（Astro 空 value 渲染为裸属性）
  expect(html).not.toContain("s-sum");
  expect(html).not.toContain("type-chips");
  expect(html).not.toContain('class="results"');
  expect(html).not.toContain("empty-state");
  // 无参数态查询词不可见高亮（v1 无高亮源）
  expect(html).not.toContain("<mark");
  // 隐藏 H1 在（页面可读身份＝大搜索框，v1 visually-hidden 同口径）
  expect(html).toContain('class="visually-hidden"');
});

test("dept 筛选态：H1/<title> 换 §8.2 模式文案", async ({ request }) => {
  await control(request, {
    endpoint: "search",
    mode: "ok",
    payload: {
      ...searchFixture,
      // 契约口径：顶层 q 与 filters.q 同为 strip 回显，恒一致
      q: "",
      filters: {
        q: "",
        section: null,
        dept: "library",
        type: null,
        tag: null,
        active: true,
        conditions: [{ label: "部门", value: "图书馆" }],
      },
    },
  });
  const html = await (await request.get("/search/?dept=library")).text();
  expect(html).toContain(
    "<title>站内搜索·图书馆发布的内容（筛选结果） - Peiligo</title>",
  );
  // 隐藏 H1 与 <title> 同文案（v1 §8.2 口径；\s* 容忍模板缩进）
  expect(html).toMatch(
    /<h1 id="ls-title"[^>]*>\s*站内搜索·图书馆发布的内容（筛选结果）\s*<\/h1>/,
  );
  // 无 q 的筛选态汇总用中性文案（v1 search_query 空口径；scoped 组件
  // 会在标签内注入 data-astro-cid-*，故只断言到标签开口）
  expect(html).toContain("找到 <strong");
  expect(html).toContain("符合当前条件的内容");
  expect(html).not.toContain("与「");
});

test("筛选无匹配空态：条件回显 + 清除搜索条件回基础 URL", async ({
  request,
  page,
}) => {
  await control(request, {
    endpoint: "search",
    mode: "ok",
    payload: {
      q: "不存在词",
      entries: [],
      pagination: {
        total: 0,
        page: 1,
        page_count: 1,
        per_page: 20,
        has_next: false,
        has_previous: false,
      },
      filters: {
        q: "不存在词",
        section: null,
        dept: null,
        type: null,
        tag: null,
        active: true,
        conditions: [
          { label: "关键词", value: "不存在词" },
          { label: "部门", value: "图书馆" },
        ],
      },
      chips: searchFixture.chips,
    },
  });
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/search/?q=%E4%B8%8D%E5%AD%98%E5%9C%A8%E8%AF%8D");
  await expect(page.locator(".empty-title")).toHaveText(
    "没有符合当前条件的内容",
  );
  await expect(page.locator(".empty-hint")).toContainText(
    "关键词「不存在词」；部门「图书馆」",
  );
  await expect(page.locator(".empty-state a")).toHaveAttribute(
    "href",
    "/search/",
  );
  await assertNoHorizontalOverflow(page);
  await page.screenshot({
    path: "docs/evidence/f07-search/empty-768.png",
    fullPage: true,
  });
});

// ===== 高亮转义（契约 3）：注入面为零 =====

test("XSS 形查询与结果：零脚本/零注入元素落 DOM，命中标记包裹字面文本", async ({
  request,
  page,
}) => {
  const hostile = "<script>alert(1)</script>";
  await control(request, {
    endpoint: "search",
    mode: "ok",
    payload: {
      q: hostile,
      entries: [
        {
          type: "notice",
          id: 1,
          title: `关于${hostile}的通知`,
          url: "/chronicle/jwc/library-hours/",
          expired: true,
          section_slug: "chronicle",
          section_title: "昆社纪事",
          department_name: "图书馆",
          published_at: "2026-09-10T09:00:00+08:00",
          event_status: null,
          list_summary: "摘要含 <img src=x onerror=alert(2)> 应原样转义",
        },
      ],
      pagination: {
        total: 1,
        page: 1,
        page_count: 1,
        per_page: 20,
        has_next: false,
        has_previous: false,
      },
      filters: {
        q: hostile,
        section: null,
        dept: null,
        type: null,
        tag: null,
        active: true,
        conditions: [{ label: "关键词", value: hostile }],
      },
      chips: searchFixture.chips,
    },
  });
  await page.goto(`/search/?q=${encodeURIComponent(hostile)}`);

  // 零脚本元素；结果区内零注入元素（svg/img/iframe/onerror 属性）
  expect(await page.locator("script").count()).toBe(0);
  expect(
    await page.locator(".results img, .results svg, .results iframe").count(),
  ).toBe(0);
  expect(await page.locator(".results [onerror]").count()).toBe(0);

  // 高亮 mark 包裹的是字面命中文本；标题其余部分原样可见
  const h2 = page.locator("a.r-row h2");
  await expect(h2.locator("mark")).toHaveText(hostile);
  await expect(h2).toContainText(`关于${hostile}的通知`);
  // 汇总行回显查询词亦为转义文本（可见即字面）
  await expect(page.locator(".s-sum")).toContainText(hostile);
  // 过期徽标仍在（historical 可见性口径不受高亮影响）
  await expect(page.locator(".badge-expired")).toHaveText("已过期");
});

// ===== 契约 4：无陈旧结果 + 每请求直连 =====

test("失败 → 500 搜索专属失败态（站内壳）且绝不出陈旧结果；恢复后下一请求即新结果", async ({
  request,
  page,
}) => {
  // 预热：先拿到一次成功结果（建立「若无防护会展示的陈旧版本」）
  await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  await expect(page.locator("a.r-row")).toHaveCount(1);

  // 故障：搜索永不回退（NEVER_STALE 面）——同查询必须 500，且为 F07
  // 样式化失败页：站内壳（页头/页脚）+ 语义标题 + alert 文案 + 重试表单
  //（q 回显），零结果行、零脚本、零内联样式、不冒充任何成功态
  await control(request, { endpoint: "search", mode: "fail" });
  const failed = await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  expect(failed?.status()).toBe(500);
  await expect(page.locator("h1")).toHaveText("搜索暂时不可用");
  await expect(page.locator("header.site-header")).toBeVisible();
  await expect(page.locator("footer.site-footer")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("搜索服务出现临时故障");
  await expect(page.locator(".big-search input")).toHaveValue("图书馆");
  await expect(page.locator(".fail-home a")).toHaveAttribute("href", "/");
  // noindex/canonical 与正常态同口径
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    "noindex",
  );
  expect(await page.locator("a.r-row").count()).toBe(0);
  expect(await page.locator("script").count()).toBe(0);
  expect(await page.locator("[style]").count()).toBe(0);
  expect(await page.locator(".s-sum, .type-chips, .empty-state").count()).toBe(
    0,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "docs/evidence/f07-search/failure-390.png",
    fullPage: true,
  });

  // 恢复：下一请求直连返回新结果（覆写验证「发布下一次请求可见」）
  await control(request, {
    endpoint: "search",
    mode: "ok",
    payload: {
      ...searchFixture,
      entries: makeEntries(1, 1).map((e) => ({
        ...e,
        title: "图书馆恢复后的新通知",
      })),
    },
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  await expect(page.locator("a.r-row h2")).toHaveText(/图书馆恢复后的新通知/);
});

test("每请求直连：chrome/search 计数随每次请求递增", async ({
  request,
  page,
}) => {
  const readCounts = async () =>
    (await (await request.get(`${MOCK}/__requests`)).json()) as Record<
      string,
      number
    >;
  const before = await readCounts();
  await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  const after = await readCounts();
  expect(after.chrome - before.chrome).toBe(2);
  expect(after.search - before.search).toBe(2);
});

// ===== 参数透传与分页（契约 2） =====

test("非法参数原样透传不重写；翻页链接保留全部筛选参数", async ({
  request,
  page,
}) => {
  const entries = makeEntries(20, 2);
  await control(request, {
    endpoint: "search",
    mode: "ok",
    payload: {
      ...searchFixture,
      entries,
      pagination: {
        total: 55,
        page: 2,
        page_count: 3,
        per_page: 20,
        has_next: true,
        has_previous: false,
      },
    },
  });
  // type=bogus 为词表外值：前端原样透传（校验在 B02 侧），响应仍 200
  const response = await page.goto(
    "/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86&type=bogus",
  );
  expect(response?.url()).toContain("type=bogus");
  await expect(page.locator("a.r-row")).toHaveCount(20);

  // 翻页链接保留 q/type、剔除并重写 page（v1 _querystring_without_page）
  const next = page.locator(".pager .next-pg");
  await expect(next).toHaveAttribute("href", /q=%E5%9B%BE%E4%B9%A6%E9%A6%86/);
  await expect(next).toHaveAttribute("href", /type=bogus/);
  await expect(next).toHaveAttribute("href", /page=3/);
  await expect(page.locator(".pager a.pg", { hasText: "1" })).toHaveAttribute(
    "href",
    /page=1/,
  );
  await expect(page.locator(".pager .pg.on")).toHaveText("2");
});

// ===== 可访问性与产物约束 =====

test("键盘顺序：skip 链接居首；页头/页内搜索原生表单零 JS 可用；chips 可聚焦", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "跳到主要内容" })).toBeFocused();

  // 页头小搜索 → /search/?q=（原生 GET 表单，无 JS 参与）
  await page.getByRole("searchbox", { name: "搜索词" }).first().fill("图书馆");
  await page.getByRole("button", { name: "搜索" }).first().click();
  expect(page.url()).toBe(`${ORIGIN}/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86`);

  // 页内大搜索框 + 栏目 chips 均为原生可聚焦元素
  await page.getByRole("searchbox", { name: "搜索词" }).last().fill("软件");
  const chips = page.locator(".t-chip");
  await chips.nth(2).focus();
  await expect(chips.nth(2)).toBeFocused();
});

test("产物 HTML 不变量：搜索页零脚本、无内联样式、全同源引用", async ({
  request,
}) => {
  await assertStaticHtmlInvariants(request, "/search/");
  await assertStaticHtmlInvariants(
    request,
    "/search/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86",
  );
});
