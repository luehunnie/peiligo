import { expect, test, type APIRequestContext } from "@playwright/test";
import { stubMedia } from "./helpers/media";

// SPEC-003 #48（M2）验收：首页「分区速览」模块（校园快讯正下方；
// 2026-09-20 Human 验收通过并裁定标题由「分区文章」改为「分区速览」）。
// 内容规则（PRD B 冻结口径，仅 Astro/零后端——数据为现有 E3
// /api/v1/sections/{slug}?page=1，经 mock 控制面按 slug 覆写）：
//   - 固定 3 槽：1/2 篇其余位置留白（无占位文字、无空可点击项、卡片不收缩）；
//   - 0 篇分区不渲染；home.sections 空 → 模块整体不渲染；
//   - 分区失败容忍：有 ≤5min 陈旧版本 → 陈旧内容照常渲染（契约 4，页面
//     不破损）；无陈旧版本 → 该分区隐藏（unit 单测覆盖隐藏路径）；
//   - 行＝仅可点击标题（无日期/缩略图/摘要）；「查看全部」落点 /<slug>/；
//   - 响应式（Human 验收裁定 2026-09-20，#50 重开）：任意视口恒为
//     单行横向滚动轨道——结构上 grid-auto-flow:column 不换行、卡片
//     同行等顶、页面无横向溢出、轨道内可滚动且恰好一张卡部分外露
//     （可滑提示）；轨道可聚焦（WCAG 滚动区模式），键盘经标题链接
//     Tab 链可达全部分区（聚焦即滚入视野）；
//   - 标题可聚焦可激活（原生链接键盘路径）。
// 配色仅既有 token（soft 底 deep 字徽标＋--teal 链接），由 tokens.test.ts
// 与截图存证守护（docs/evidence/spec-003-r1/）。

const MOCK = "http://127.0.0.1:4319";

/** 控制面改写（测试末尾统一 afterEach reset 恢复夹具）。 */
async function control(
  request: APIRequestContext,
  body: Record<string, unknown>,
): Promise<void> {
  const res = await request.post(`${MOCK}/__control`, { data: body });
  expect(res.ok()).toBeTruthy();
}

/** 构造完整契约合法的 SectionList payload（从既有夹具形状派生：
 *  ListEntry 全字段——ajv 运行时校验会拒绝缺字段/错型的 payload）。 */
function sectionListPayload(
  slug: string,
  title: string,
  entries: { title: string; url: string }[],
) {
  return {
    section: {
      slug,
      title,
      url: `/${slug}/`,
      archive_url: `/${slug}/archive/`,
    },
    entries: entries.map((entry, index) => ({
      type: "notice",
      id: 900 + index,
      title: entry.title,
      url: entry.url,
      expired: false,
      section_slug: slug,
      section_title: title,
      department_name: "教务处",
      published_at: "2026-09-10T09:00:00+08:00",
      event_status: null,
      list_summary: "",
    })),
    pagination: {
      total: entries.length,
      page: 1,
      page_count: 1,
      per_page: 20,
      has_next: false,
      has_previous: false,
    },
    filters: {
      q: "",
      section: slug,
      dept: null,
      type: null,
      tag: null,
      active: false,
      conditions: [],
    },
  };
}

test.afterEach(async ({ request }) => {
  await request.post(`${MOCK}/__control/reset`);
});

test.describe("分区速览模块（内容规则）", () => {
  test("固定 3 槽：2/1/0/3 篇的槽位、留白、0 篇隐藏与查看全部落点", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    await control(request, {
      endpoint: "section-list:chronicle",
      mode: "ok",
      payload: sectionListPayload("chronicle", "社史纪事", [
        { title: "纪事第一条", url: "/chronicle/jwc/library-hours/" },
        { title: "纪事第二条", url: "/chronicle/jwc/second/" },
      ]),
    });
    await control(request, {
      endpoint: "section-list:events",
      mode: "ok",
      payload: sectionListPayload("events", "社团活动", [
        { title: "活动唯一一条", url: "/events/jwc/only/" },
      ]),
    });
    await control(request, {
      endpoint: "section-list:software",
      mode: "ok",
      payload: sectionListPayload("software", "常用软件", []),
    });
    await control(request, {
      endpoint: "section-list:guide",
      mode: "ok",
      payload: sectionListPayload("guide", "生活指南", [
        { title: "指南一", url: "/guide/jwc/g1/" },
        { title: "指南二", url: "/guide/jwc/g2/" },
        { title: "指南三", url: "/guide/jwc/g3/" },
      ]),
    });
    // materials 不覆写＝回落共享夹具（1 条），单分区失败场景见下一用例

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    const module = page.locator("section.sec-articles");
    await expect(module).toBeVisible();
    // 紧跟校园快讯之后（DOM 顺序：.news → .sec-articles）
    await expect(
      page
        .locator(".news + section.sec-articles, .news ~ section.sec-articles")
        .first(),
    ).toBeVisible();

    // 0 篇分区（software）不渲染
    const cards = module.locator(".card");
    await expect(cards).toHaveCount(4);

    // 2 篇（chronicle）：2 链接＋1 留白；留白行无锚点无文本
    const chronicle = module.locator(".card", { hasText: "社史纪事" });
    await expect(chronicle.locator(".rows a")).toHaveCount(2);
    const chronicleRows = chronicle.locator(".rows li");
    await expect(chronicleRows).toHaveCount(3);
    await expect(chronicleRows.nth(2)).toHaveClass(/blank/);
    await expect(chronicleRows.nth(2).locator("a")).toHaveCount(0);
    await expect(chronicleRows.nth(2)).toHaveText("");

    // 1 篇（events）：1 链接＋2 留白；卡片不收缩（3 槽行高一致）
    const events = module.locator(".card", { hasText: "社团活动" });
    await expect(events.locator(".rows a")).toHaveCount(1);
    await expect(events.locator(".rows li")).toHaveCount(3);
    const blankBox = await events.locator(".rows li").nth(2).boundingBox();
    const filledBox = await events.locator(".rows li").nth(0).boundingBox();
    expect(Math.abs(blankBox!.height - filledBox!.height)).toBeLessThanOrEqual(
      1,
    );

    // 3 篇（guide）：3 链接、无留白
    const guide = module.locator(".card", { hasText: "生活指南" });
    await expect(guide.locator(".rows a")).toHaveCount(3);
    await expect(guide.locator(".rows li.blank")).toHaveCount(0);

    // 行＝仅可点击标题：无日期/时间/图片/摘要元素
    const html = await module.innerHTML();
    expect(html).not.toContain("<time");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<p");

    // 「查看全部」唯一可访问名＋落点分区列表页
    const more = chronicle.getByRole("link", { name: /查看全部/ });
    await expect(more).toHaveAttribute("href", "/chronicle/");
    await expect(more).toHaveAccessibleName(/社史纪事/);

    // 标题行可激活（原生链接导航到详情页）
    await chronicle.getByRole("link", { name: "纪事第一条" }).click();
    await expect(page).toHaveURL(/\/chronicle\/jwc\/library-hours\//);
  });

  test("单分区失败容忍：有陈旧版本→陈旧内容不破损；0 分区→模块隐藏", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    // 先给 materials 一次成功覆写（预热契约 4 陈旧缓存），再置障：
    // 有 ≤5min 陈旧版本时 api 层回退陈旧（ok+stale）——页面完整、卡片
    // 仍在（内容为最后成功版本）。无陈旧版本时的「分区隐藏」路径在
    // unit（section-articles.test.ts）覆盖。
    await control(request, {
      endpoint: "section-list:materials",
      mode: "ok",
      payload: sectionListPayload("materials", "资料专区", [
        { title: "资料一条", url: "/materials/jwc/only/" },
      ]),
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    const module = page.locator("section.sec-articles");
    await expect(module.locator(".card", { hasText: "资料专区" })).toHaveCount(
      1,
    );

    await control(request, {
      endpoint: "section-list:materials",
      mode: "fail",
    });
    await page.goto("/");
    await expect(module.locator(".card", { hasText: "资料专区" })).toHaveCount(
      1,
    );
    await expect(module.locator(".card")).toHaveCount(5);
    await expect(page.locator("footer.site-footer")).toBeVisible();
  });

  test("home.sections 为空（0 分区）：模块整体不渲染，页面其余完整", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    await control(request, {
      endpoint: "home",
      mode: "ok",
      payload: {
        title: "首页",
        alert: null,
        carousel: [],
        sections: [],
        campus_news: [],
      },
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.locator("section.sec-articles")).toHaveCount(0);
    await expect(page.locator("nav.cats a.cat")).toHaveCount(0);
    await expect(page.locator("footer.site-footer")).toBeVisible();
  });
});

test.describe("分区速览模块（单行横向滚动轨道）", () => {
  /** 轨道几何实况（真实 computed/布局值——无 CSS 时必然变红，杜绝
   *  11/11 式「DOM 代理断言假绿」：grid-auto-flow 缺省 none、卡片
   *  纵排时 tops 必不相等）。 */
  async function railFacts(page: import("@playwright/test").Page) {
    return page.locator("section.sec-articles .cards").evaluate((el) => {
      const boxes = [...el.querySelectorAll<HTMLElement>(".card")].map((c) =>
        c.getBoundingClientRect(),
      );
      const rail = el.getBoundingClientRect();
      const tops = boxes.map((b) => Math.round(b.top));
      // 「恰一张卡部分外露」＝左缘在轨内、右缘出轨的卡片数
      const straddling = boxes.filter(
        (b) => b.left < rail.right - 1 && b.right > rail.right + 1,
      ).length;
      return {
        flow: getComputedStyle(el).gridAutoFlow,
        count: boxes.length,
        sameRow: Math.max(...tops) - Math.min(...tops) <= 1,
        scrollable: el.scrollWidth > el.clientWidth,
        pageOverflow:
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
        straddling,
        scrollLeft: el.scrollLeft,
      };
    });
  }

  for (const [width, height] of [
    [390, 844],
    [768, 1024],
    [1440, 900],
  ] as const) {
    test(`${width}px：单行轨道/页面无溢出/下一卡外露/键盘可滚动，截图存证（首屏＋滚到末）`, async ({
      page,
    }) => {
      await stubMedia(page);
      await page.setViewportSize({ width, height });
      await page.goto("/");

      const rail = page.locator("section.sec-articles .cards");
      await expect(rail).toBeVisible();
      // 轨道键盘可达（WCAG 滚动区模式）：可聚焦滚动区
      await expect(rail).toHaveAttribute("tabindex", "0");
      await expect(rail).toHaveAttribute("role", "group");
      await expect(rail).toHaveAttribute("aria-label", /分区速览/);

      const facts = await railFacts(page);
      expect(facts.flow, "grid-auto-flow:column（结构性单行）").toBe("column");
      expect(facts.count, "默认夹具五分区全渲染").toBe(5);
      expect(facts.sameRow, "所有卡片同行等顶（单行，不换行）").toBe(true);
      expect(facts.pageOverflow, "页面无横向溢出").toBeLessThanOrEqual(0);
      expect(facts.scrollable, "轨道内可横向滚动").toBe(true);
      expect(facts.straddling, "恰好一张卡部分外露（可滑提示）").toBe(1);

      // 截图存证①：轨道起点（scrollLeft=0，首卡齐左、下一卡露边）
      await rail.evaluate((el) => {
        el.scrollTo({ left: 0 });
      });
      await page
        .locator("section.sec-articles")
        .screenshot({ path: `docs/evidence/spec-003-r1/${width}-start.png` });

      // 键盘可达全部分区（引擎无关路径）：从第一卡首个标题链接沿 Tab 链
      // 走到第五卡标题——浏览器必须把聚焦链接滚入视野（原生行为）。
      // 轨道 tabindex=0 另为 WCAG 滚动区模式（Firefox 支持聚焦后方向键
      // 滚动；Chromium 当前不响应方向键，故不作断言依赖）。
      const firstLink = rail
        .locator(".card")
        .first()
        .locator(".rows a")
        .first();
      await firstLink.focus();
      // 沿 Tab 前进直到焦点进入第五卡（上限 12 次防死循环）
      for (let i = 0; i < 12; i += 1) {
        await page.keyboard.press("Tab");
        const inside = await page.evaluate(() => {
          const last = document.querySelectorAll(
            "section.sec-articles .cards .card",
          )[4]!;
          const active = document.activeElement;
          return (
            active !== null && last.contains(active) && active.tagName === "A"
          );
        });
        if (inside) break;
      }
      const kbState = await page.evaluate(() => {
        const cards = [
          ...document.querySelectorAll("section.sec-articles .cards .card"),
        ];
        const last = cards[4]!;
        const active = document.activeElement;
        const box =
          active instanceof Element ? active.getBoundingClientRect() : null;
        return {
          reached:
            active !== null &&
            last.contains(active) &&
            active.tagName === "A" &&
            !!box &&
            box.left >= 0 &&
            box.left < document.documentElement.clientWidth,
          railScrollLeft: last.parentElement!.scrollLeft,
        };
      });
      expect(kbState.reached, "Tab 链可达第五分区且滚入视野").toBe(true);
      expect(kbState.railScrollLeft, "聚焦把轨道滚向末卡").toBeGreaterThan(0);

      // 截图存证②：滚到轨道末（末卡齐右、前卡露边）＋复验停在末尾
      await rail.evaluate((el) => {
        el.scrollLeft = el.scrollWidth;
      });
      await page
        .locator("section.sec-articles")
        .screenshot({ path: `docs/evidence/spec-003-r1/${width}-end.png` });
      const endFacts = await railFacts(page);
      expect(endFacts.scrollLeft, "滚到末尾后停在最右").toBeGreaterThan(0);
    });
  }

  test("五分区按 home.sections 顺序全渲染（各 1 篇，software 默认可见）", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    // 默认共享夹具对每个 slug 返回同一 payload（section 元数据全为
    // chronicle），故按 slug 逐一覆写为带各自分区元数据的单条列表，
    // 使跨分区顺序可判读（生产环境每个 slug 返回自己的 section 对象）。
    const five: [string, string][] = [
      ["chronicle", "社史纪事"],
      ["events", "社团活动"],
      ["materials", "资料专区"],
      ["software", "常用软件"],
      ["guide", "生活指南"],
    ];
    for (const [slug, title] of five) {
      await control(request, {
        endpoint: `section-list:${slug}`,
        mode: "ok",
        payload: sectionListPayload(slug, title, [
          { title: `${title}文章`, url: `/${slug}/jwc/a/` },
        ]),
      });
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    const module = page.locator("section.sec-articles");
    const cards = module.locator(".card");
    await expect(cards).toHaveCount(5);

    // 顺序 = home.sections 数组顺序（前端零重排的跨分区投影；tone 徽标
    // 类挂在卡内 .tag 上，按卡序取第一枚即分区序）
    const order = await module
      .locator(".card .tag")
      .evaluateAll((els) =>
        els.map(
          (el) => [...el.classList].find((c) => c.startsWith("tone-")) ?? "",
        ),
      );
    expect(order).toEqual([
      "tone-chronicle",
      "tone-events",
      "tone-materials",
      "tone-software",
      "tone-guide",
    ]);

    // 「查看全部」落点逐一对应分区列表页（software 在列）
    const hrefs = await module
      .locator(".more")
      .evaluateAll((els) =>
        els.map((el) => (el as HTMLAnchorElement).getAttribute("href")),
      );
    expect(hrefs).toEqual([
      "/chronicle/",
      "/events/",
      "/materials/",
      "/software/",
      "/guide/",
    ]);
  });
});
