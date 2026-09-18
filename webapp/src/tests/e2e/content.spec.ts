import { readFileSync } from "node:fs";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { stubMedia } from "./helpers/media";
import {
  assertNoHorizontalOverflow,
  assertStaticHtmlInvariants,
} from "./helpers/assert";

// SPEC-001-F06 验收：五大板块内容页家族（列表/归档/五型详情）＋外链确认页
// ＋robots/sitemap 的请求时 SSR 迁移等价性。逐页覆盖：URL→路由→契约端点
// 对齐、内容层级与 v1 段序、查询参数态/归档/确认页 noindex＋canonical、
// 分页窗口、空态两型、失败边界（500/404/≤5min 陈旧回退）、每请求直连、
// 内容页零脚本（v1 无 JS 同口径）、三档视口无横向溢出。
// 截图存 docs/evidence/f06-content-pages/ 供 Gate 4 评审对照。

const MOCK = "http://127.0.0.1:4319";
const ORIGIN = "http://127.0.0.1:4321";
const VIEWPORTS = [
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

// Node 24 ESM JSON import 需要 import attribute；与 home.spec 同款
// readFileSync 读取同一份契约夹具（与 mock 服务同源）。
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

// ===== 板块列表页：代表态 + 三档视口 =====

for (const { width, height } of VIEWPORTS) {
  test(`列表页在 ${width}px 渲染冻结层级且无横向溢出`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    const resp = await page.goto("/chronicle/");
    expect(resp?.status()).toBe(200);

    await expect(page.locator("header.site-header")).toBeVisible();
    await expect(
      page.locator("nav.breadcrumb").getByText("昆社纪事"),
    ).toBeVisible();

    // 列表页头：图标 → H1 → 定位文案 → 归档入口 → 计数 → 板块内搜索
    await expect(page.locator("h1")).toHaveText("昆社纪事");
    await expect(page.locator(".ls-intro")).toHaveText(
      "记录校园动态、通知公告与长期报道的板块",
    );
    await expect(page.locator(".archive-entry a")).toHaveAttribute(
      "href",
      "/chronicle/archive/",
    );
    await expect(page.locator(".ls-count strong")).toHaveText("1");
    const search = page.getByRole("search", { name: "在本板块内搜索" });
    await expect(search).toHaveAttribute("action", "/chronicle/");
    await expect(search.locator("input[name=q]")).toBeVisible();

    // 结果行（v1 .r-row：徽标 tone → 标题 → 摘要 → 部门·日期）
    const row = page.locator("a.r-row");
    await expect(row).toHaveCount(1);
    await expect(row.locator(".tag")).toHaveText("纪事");
    await expect(row.locator(".tag")).toHaveClass(/tone-jishi/);
    await expect(row.locator("h2")).toHaveText("关于图书馆调整开放时间的通知");
    await expect(row.locator("p").first()).toHaveText(
      "即日起至本学期末调整开放时间。",
    );
    await expect(row.locator(".r-meta")).toHaveText("图书馆 · 2026-09-10");

    // 分页（v1 恒渲染；单页仅当前页占位，无翻页链接）
    const pager = page.locator("nav.pager");
    await expect(pager.locator(".pg.on")).toHaveText("1");
    await expect(pager.locator("a.pg")).toHaveCount(0);
    await expect(pager.locator(".next-pg")).toHaveCount(0);

    await expect(page.locator("footer.site-footer")).toBeVisible();
    await assertNoHorizontalOverflow(page);

    if (width === 390 || width === 1440) {
      await page.screenshot({
        path: `docs/evidence/f06-content-pages/listing-${width}.png`,
        fullPage: true,
      });
    }
  });
}

test("dept 筛选态：H1 换 §8.2 模式文案 + noindex + canonical 去参", async ({
  request,
}) => {
  await control(request, {
    endpoint: "section-list",
    mode: "ok",
    payload: {
      ...listFixture,
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

  const html = await (await request.get("/chronicle/?dept=library")).text();
  expect(html).toContain("昆社纪事·图书馆发布的内容（筛选结果）");
  expect(html).toContain('name="robots" content="noindex"');
  expect(html).toContain(
    'rel="canonical" href="http://127.0.0.1:4321/chronicle/"',
  );
});

test("无筛选带查询参数：noindex + canonical（任一参数即进参态）", async ({
  request,
}) => {
  const html = await (await request.get("/chronicle/?q=图书馆")).text();
  expect(html).toContain('name="robots" content="noindex"');
  expect(html).toContain(
    'rel="canonical" href="http://127.0.0.1:4321/chronicle/"',
  );
  // 无参数态不输出 robots/canonical（v1 base.html 口径）
  const clean = await (await request.get("/chronicle/")).text();
  expect(clean).not.toContain('name="robots"');
  expect(clean).not.toContain('rel="canonical"');
});

test("分页窗口：1/末页恒在、当前页 ±1、缺口折叠；翻页链接保留筛选参数", async ({
  request,
  page,
}) => {
  await control(request, {
    endpoint: "section-list",
    mode: "ok",
    payload: {
      ...listFixture,
      pagination: {
        total: 108,
        page: 3,
        page_count: 6,
        per_page: 20,
        has_next: true,
        has_previous: true,
      },
    },
  });

  await page.goto("/chronicle/?dept=library");
  const pager = page.locator("nav.pager");
  await expect(pager.locator(".pg.on")).toHaveText("3");
  const links = pager.locator("a.pg");
  await expect(links).toHaveCount(5); // 1、2、4、6 号页 + 下一页
  await expect(links.nth(0)).toHaveAttribute("href", "?dept=library&page=1");
  await expect(links.nth(1)).toHaveAttribute("href", "?dept=library&page=2");
  await expect(links.nth(2)).toHaveText("4");
  await expect(links.nth(3)).toHaveText("6");
  await expect(pager.locator(".pg-gap")).toHaveText("…");
  await expect(pager.locator(".next-pg")).toHaveAttribute(
    "href",
    "?dept=library&page=4",
  );
});

// ===== 空态两型 =====

test("筛选后空结果：条件回显 + 清除筛选", async ({ request, page }) => {
  await control(request, {
    endpoint: "section-list",
    mode: "ok",
    payload: {
      ...listFixture,
      entries: [],
      pagination: { ...listFixture.pagination, total: 0 },
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
  await page.goto("/chronicle/?dept=library");
  const empty = page.locator(".empty-state");
  await expect(empty.locator(".empty-title")).toHaveText(
    "没有符合当前条件的内容",
  );
  await expect(empty.locator(".empty-hint")).toContainText(
    "已选条件：部门「图书馆」",
  );
  await expect(empty.getByRole("link", { name: "清除筛选" })).toHaveAttribute(
    "href",
    "/chronicle/",
  );
});

test("板块空库：引导去其他板块与首页", async ({ request, page }) => {
  await control(request, {
    endpoint: "section-list",
    mode: "ok",
    payload: {
      ...listFixture,
      entries: [],
      pagination: { ...listFixture.pagination, total: 0 },
    },
  });
  await page.goto("/chronicle/");
  const empty = page.locator(".empty-state");
  await expect(empty.locator(".empty-title")).toHaveText("本板块暂无内容");
  const links = empty.locator(".section-links a");
  await expect(links).toHaveCount(5); // 4 个其他板块 + 返回首页
  await expect(links.nth(4)).toHaveAttribute("href", "/");
});

// ===== 归档页 =====

test("归档页：live/expired 混排、过期徽标、恒 noindex；空态回退", async ({
  request,
  page,
}) => {
  // 默认夹具 entries 为空 → 空态
  await page.goto("/chronicle/archive/");
  await expect(page.locator(".empty-title")).toHaveText("本板块暂无历史内容");
  const emptyHtml = await (await request.get("/chronicle/archive/")).text();
  expect(emptyHtml).toContain('name="robots" content="noindex"');
  expect(emptyHtml).toContain(
    'rel="canonical" href="http://127.0.0.1:4321/chronicle/archive/"',
  );

  const entries = [
    { ...listFixture.entries[0] },
    {
      ...listFixture.entries[0],
      id: 43,
      title: "2025 年秋季学期校园卡办理通知",
      url: "/chronicle/jwc/campus-card-2025/",
      expired: true,
      published_at: "2025-09-01T10:00:00+08:00",
    },
  ];
  await control(request, {
    endpoint: "section-archive",
    mode: "ok",
    payload: {
      section: { slug: "chronicle", title: "昆社纪事", url: "/chronicle/" },
      entries,
      total: 2,
    },
  });

  await page.goto("/chronicle/archive/");
  await expect(page.locator("h1")).toHaveText("昆社纪事·历史归档");
  const rows = page.locator("a.r-row");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(1).locator(".badge-expired")).toHaveText("已过期");
  await expect(
    page.locator("nav.breadcrumb").getByRole("link", { name: "昆社纪事" }),
  ).toHaveAttribute("href", "/chronicle/");
  await expect(page.locator("nav.pager")).toHaveCount(0); // 归档不分页
});

// ===== 五型详情页 =====

test("通知详情：元信息段序、正文、附件体积、标签、返回链接", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const resp = await page.goto("/chronicle/jwc/library-hours/");
  expect(resp?.status()).toBe(200);

  const crumbs = page.locator("nav.breadcrumb li");
  await expect(crumbs).toHaveCount(3);
  await expect(crumbs.nth(2).locator("[aria-current=page]")).toHaveText(
    "关于图书馆调整开放时间的通知",
  );

  await expect(page.locator("h1")).toHaveText("关于图书馆调整开放时间的通知");
  await expect(page.locator(".art-meta")).toHaveText(
    "图书馆·2026-09-10 发布·有效期至 2027-09-10",
  );
  await expect(page.locator(".article-lede")).toHaveText(
    "即日起至本学期末调整开放时间。",
  );
  await expect(page.locator(".article-body h2")).toHaveText("开放时间安排");
  await expect(page.locator(".article-body strong")).toHaveText("8:00–22:00");

  // 附件区：humanize 体积（Django filesizeformat 口径）
  const attachment = page.locator(".article-aside", { hasText: "附件" });
  await expect(attachment.locator("a")).toHaveAttribute(
    "href",
    "/documents/42/opening-hours.pdf",
  );
  await expect(attachment).toContainText("（100.0 KB）");
  await expect(
    page.locator(".article-aside", { hasText: "标签" }),
  ).toContainText("图书馆");

  await expect(
    page.getByRole("link", { name: "← 返回昆社纪事" }),
  ).toHaveAttribute("href", "/chronicle/");
  await expect(page.locator("body")).toHaveClass(/template-noticepage/);
  await expect(
    page.locator("img.art-cover, figure.art-cover img"),
  ).toBeVisible();

  await assertNoHorizontalOverflow(page);
  await page.screenshot({
    path: "docs/evidence/f06-content-pages/detail-notice-390.png",
    fullPage: true,
  });
});

test("文章详情：活动信息四要素、正文块（图片/表格/外链确认行）、外部链接区", async ({
  page,
}) => {
  await page.goto("/events/xshd/spring-sports/");

  // 活动信息（v1 event_info：状态/起止/地点；registration null → 无报名行）
  const event = page.locator("section.event-info", {
    has: page.locator("h2", { hasText: "活动信息" }),
  });
  await expect(event).toBeVisible();
  await expect(event.locator("dd").nth(0)).toHaveText("已结束");
  await expect(event.locator("dd").nth(1)).toHaveText("2026-04-18 08:30");
  await expect(event.locator("dd").nth(2)).toHaveText("2026-04-18 17:00");
  await expect(event.locator("dd").nth(3)).toHaveText("东区田径场");

  // 正文块
  await expect(page.locator(".block-image img")).toHaveAttribute(
    "loading",
    "lazy",
  );
  const table = page.locator(".article-body table");
  await expect(table.locator("thead th").first()).toHaveAttribute(
    "scope",
    "col",
  );
  await expect(table.locator("thead th").first()).toHaveText("项目");
  await expect(table.locator("tbody tr")).toHaveCount(2);

  // 正文外链块 → 确认跳转行（file 形态；href 为契约 confirm_href）
  const bodyLink = page
    .locator(".article-body a.file[href*='link-confirm']")
    .first();
  await expect(bodyLink).toHaveAttribute(
    "href",
    "/link-confirm/?url=https%3A%2F%2Fphotos.example.edu%2Fsports2026&from=51",
  );

  // 尾注外部链接区（file 形态，标题行即 URL 明文）
  const external = page.locator(".article-aside", { hasText: "外部链接" });
  await expect(external.locator(".file strong")).toHaveText(
    "https://photos.example.edu/sports2026",
  );
});

test("资料详情：资料元信息段序、体积空值省略、无有效期段", async ({ page }) => {
  await page.goto("/materials/library/calculus-review/");

  await expect(page.locator(".art-meta")).toHaveText(
    "图书馆·公共基础课·复习提纲·2026-05-12 发布",
  );
  const attachments = page.locator(".article-aside", { hasText: "附件" });
  await expect(attachments.locator("li")).toHaveCount(2);
  await expect(attachments).toContainText("（25.0 MB）");
  // file_size null → 体积段整体省略（v1 {% if file_size %}）
  await expect(
    attachments.locator("li", { hasText: "公式速查卡" }),
  ).not.toContainText("（");
  await expect(page.locator("body")).toHaveClass(/template-materialpage/);
});

test("软件详情：过期横幅、基本信息三要素、用途说明", async ({ page }) => {
  await page.goto("/software/its/zotero/");

  // expired: true → 页首横幅（role=status），原 slug URL 放行渲染
  const banner = page.locator(".expired-banner");
  await expect(banner).toHaveAttribute("role", "status");

  const info = page.locator("section.event-info", {
    has: page.locator("h2", { hasText: "基本信息" }),
  });
  await expect(info).toContainText("Windows、macOS");
  await expect(info.locator("dd.url-text a")).toHaveAttribute(
    "href",
    "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
  );
  await expect(info).toContainText("供校内师生免费使用。");
  await expect(page.locator("h2", { hasText: "用途说明" })).toBeVisible();
  await expect(page.locator("body")).toHaveClass(/template-softwaretoolpage/);
  // 软件型元信息无有效期段；lede 不渲染（v1 三型才输出摘要）
  await expect(page.locator(".art-meta")).toHaveText(
    "信息化办公室·2026-08-01 发布",
  );
  await expect(page.locator(".article-lede")).toHaveCount(0);
});

test("指南详情：九字段表、换行渲染、维护方式标签", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/guide/jwc/library-guide/");

  await expect(page.locator(".art-meta")).toHaveText(
    "学习场所·教务处·最后确认 2026-08-30",
  );
  const dl = page.locator("dl.guide-fields");
  await expect(dl.locator("dt")).toHaveText([
    "地点",
    "开放时间",
    "联系方式",
    "补充说明",
    "责任来源或责任单位",
    "维护方式",
    "最后确认日期或更新时间",
  ]);
  // v1 linebreaksbr：两行值渲染为 <br>
  const hours = dl.locator("dd").nth(1);
  await expect(hours.locator("br")).toHaveCount(1);
  await expect(hours).toContainText("周一至周五 8:00–22:00");
  await expect(hours).toContainText("周末及节假日 9:00–21:00");
  // extra_notes 空串 → 补充说明行仍输出？v1 {% if extra_notes %}：空值整行省略
  await expect(dl).toContainText("考试周延长开放，另行通知。");
  // 指南无正文块/尾注三区（v1 同口径）
  await expect(page.locator(".article-body > :not(dl)")).toHaveCount(0);
  await expect(page.locator("body")).toHaveClass(/template-guidepage/);
  await assertNoHorizontalOverflow(page);
  await page.screenshot({
    path: "docs/evidence/f06-content-pages/detail-guide-768.png",
    fullPage: true,
  });
});

// ===== 外链确认页 =====

test("确认页 ok 态：四要素、go_href 直出、恒 noindex、页脚反馈隐私覆盖", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const resp = await page.goto(
    "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
  );
  expect(resp?.status()).toBe(200);

  await expect(page.locator("h1")).toHaveText("即将访问外部网站");
  await expect(page.locator(".c-domain")).toHaveText("www.zotero.org");
  await expect(
    page.locator(".c-source").getByRole("link", { name: "Zotero 文献管理" }),
  ).toHaveAttribute("href", "/software/its/zotero/");
  await expect(page.locator(".c-note")).toContainText(
    "即将离开本校网站，前往外部链接。",
  );
  const primary = page.locator("a.c-primary");
  await expect(primary).toHaveAttribute(
    "href",
    "/link-confirm/go/?url=https%3A%2F%2Fwww.zotero.org%2F",
  );
  await expect(primary).toHaveAttribute("rel", "nofollow");
  await expect(page.locator("a.c-ghost")).toHaveAttribute(
    "href",
    "/software/its/zotero/",
  );

  const html = await page.content();
  expect(html).toContain('name="robots" content="noindex"');
  expect(html).toContain(
    'rel="canonical" href="http://127.0.0.1:4321/link-confirm/"',
  );
  // 隐私覆盖：反馈 mailto body 只带站内路径（非完整确认 URL）
  const mailto = await page.locator(".footer-notes a").getAttribute("href");
  expect(mailto).toContain(encodeURIComponent("/link-confirm/"));
  expect(mailto).not.toContain("www.zotero.org");

  await page.screenshot({
    path: "docs/evidence/f06-content-pages/link-confirm-1440.png",
    fullPage: true,
  });
});

test("确认页拒绝态：契约 ok:false → 阻止文案 + 无继续访问入口", async ({
  request,
  page,
}) => {
  await control(request, {
    endpoint: "link-confirm",
    mode: "ok",
    payload: {
      ok: false,
      target_domain: "",
      notice_text: "即将离开本校网站，前往外部链接。",
      source: null,
      go_href: null,
      problem: "目标域名不在允许列表",
    },
  });
  await page.goto("/link-confirm/?url=https%3A%2F%2Fevil.example%2F");
  const error = page.locator(".confirm-error");
  await expect(error).toContainText("目标域名不在允许列表");
  await expect(page.locator("a.c-primary")).toHaveCount(0);
  await expect(page.locator("a.c-ghost")).toHaveAttribute("href", "/");
});

// ===== robots.txt / sitemap.xml =====

test("robots.txt：禁抓口径与 Sitemap 行（text/plain）", async ({ request }) => {
  const resp = await request.get("/robots.txt");
  expect(resp.status()).toBe(200);
  expect(resp.headers()["content-type"]).toContain("text/plain");
  expect(await resp.text()).toBe(
    [
      "User-agent: *",
      "Disallow: /django-admin/",
      "Disallow: /admin/",
      "Disallow: /link-confirm/",
      "",
      `Sitemap: ${ORIGIN}/sitemap.xml`,
      "",
    ].join("\n"),
  );
});

test("sitemap.xml：urlset 绝对化 loc、Y-m-d lastmod、null 省略", async ({
  request,
}) => {
  const resp = await request.get("/sitemap.xml");
  expect(resp.status()).toBe(200);
  expect(resp.headers()["content-type"]).toContain("application/xml");
  const xml = await resp.text();
  expect(xml).toContain('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"');
  expect(xml).toContain(
    "<loc>http://127.0.0.1:4321/chronicle/jwc/library-hours/</loc>",
  );
  expect(xml).toContain("<lastmod>2026-09-10</lastmod>");
  expect(xml).toContain(
    "<loc>http://127.0.0.1:4321/software/its/zotero/</loc>",
  );
  // lastmod null → 整个元素不输出（v1 {% if %}）
  const zoteroBlock = xml.split("<url>")[2];
  expect(zoteroBlock).not.toContain("<lastmod>");
});

// ===== 路由边界与失败边界 =====

test("未知板块/未知详情/容器段 → 404（v1 恒 404 口径）", async ({
  request,
}) => {
  expect((await request.get("/nonexistent/")).status()).toBe(404);
  expect((await request.get("/chronicle/jwc/unknown-slug/")).status()).toBe(
    404,
  ); // slug 未入夹具 → 契约 not_found
  expect((await request.get("/chronicle/jwc/")).status()).toBe(404); // 容器 URL
  expect((await request.get("/nope/a/b/")).status()).toBe(404); // 越界 section
});

test("列表失败 → 500 错误边界；预热后失败 → ≤5min 陈旧回退 200", async ({
  request,
  page,
}) => {
  // 用 /guide/ 验证冷失败：其余测试只取 /chronicle/ 列表，F04 客户端
  // 缓存在 Astro 服务进程内跨测试存活，已预热板块无法回到「无陈旧」态
  await control(request, { endpoint: "section-list", mode: "fail" });
  const cold = await page.goto("/guide/");
  expect(cold?.status()).toBe(500);
  // F08：chrome 可用而列表冷失败 → 站内壳失败态（取代 F04 最小 500 页）
  await expect(page.locator("h1")).toHaveText("内容暂时无法加载");

  // 预热最近成功版本后故障 → 陈旧回退（普通内容 stale-while-error）
  await request.post(`${MOCK}/__control/reset`);
  await page.goto("/guide/");
  await control(request, { endpoint: "section-list", mode: "fail" });
  const stale = await page.goto("/guide/");
  expect(stale?.status()).toBe(200);
  await expect(page.locator("a.r-row")).toHaveCount(1);
});

test("每请求直连：chrome/section-list 计数随每次请求递增", async ({
  request,
  page,
}) => {
  const readCounts = async () =>
    (await (await request.get(`${MOCK}/__requests`)).json()) as Record<
      string,
      number
    >;
  const before = await readCounts();
  await page.goto("/chronicle/");
  await page.goto("/chronicle/");
  const after = await readCounts();
  expect(after.chrome - before.chrome).toBe(2);
  expect(after["section-list"] - before["section-list"]).toBe(2);
});

// ===== 可访问性与产物约束 =====

test("键盘顺序：skip 链接居首并可聚焦；板块内搜索可键盘操作", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/chronicle/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "跳到主要内容" })).toBeFocused();

  // 板块内搜索：填词回车 → 同板块带 q 结果页（原生表单，零 JS）
  await page.getByRole("searchbox", { name: "搜索词" }).fill("图书馆");
  await page.getByRole("button", { name: "搜索" }).click();
  expect(page.url()).toBe(`${ORIGIN}/chronicle/?q=%E5%9B%BE%E4%B9%A6%E9%A6%86`);
});

test("产物 HTML 不变量：内容页零脚本、外链样式、全同源引用", async ({
  request,
}) => {
  await assertStaticHtmlInvariants(request, "/chronicle/");
  await assertStaticHtmlInvariants(request, "/chronicle/archive/");
  await assertStaticHtmlInvariants(request, "/chronicle/jwc/library-hours/");
  await assertStaticHtmlInvariants(request, "/events/xshd/spring-sports/");
  await assertStaticHtmlInvariants(
    request,
    "/materials/library/calculus-review/",
  );
  await assertStaticHtmlInvariants(request, "/software/its/zotero/");
  await assertStaticHtmlInvariants(request, "/guide/jwc/library-guide/");
  await assertStaticHtmlInvariants(
    request,
    "/link-confirm/?url=https%3A%2F%2Fwww.zotero.org%2F&from=7",
  );
});
