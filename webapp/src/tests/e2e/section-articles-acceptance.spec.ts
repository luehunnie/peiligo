import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
} from "@playwright/test";
import { stubMedia } from "./helpers/media";

// SPEC-003 #50（M3 lite）验收矩阵——在 #48 e2e（section-articles.spec.ts，
// 内容规则/失败容忍/390-768-1440 三档列数）之上补齐四件事：
//   ① 排序：前端零重排＝按 E3 entries 数组顺序原样渲染；「旧文修改后
//      不重排」——排序键是服务端 first_published_at（非 updated_at），
//      旧文改标题不改 first_published_at → 顺序与槽位不变、修订下一次
//      请求即可见（契约 4 每请求直连）。真实 B02 的排序正确性属服务端
//      职责（E3 自有测试）；此处锁定的是前端消费面。
//   ② 断点间抽查＋边界（Human 验收裁定 2026-09-20：单行横向滚动轨道，
//      无列数断点）：600/601/980/981 sharp 边界与 768/1440 逐一验证
//      轨道不变量——恒单行（卡片同行等顶）、页面无横向溢出、恰好一张
//      卡部分外露（可滑提示）；390/768/1440 键盘滚动与首末截图在
//      section-articles.spec.ts 存证（docs/evidence/spec-003-r1/）。
//   ③ 固定 3 槽空间稳定（同一布局内，非跨设备同像素）：任一宽度下所有
//      卡片行区（ul.rows）高度一致——1 篇卡的留白与 3 篇卡的满槽占同
//      样空间，卡片不收缩。
//   ④ 可访问性/视觉：分区徽标（deep 字小字）WCAG 对比度 ≥4.5:1（按
//      计算样式实算，5 个 tone 全查）；文章行标题聚焦后 Enter 激活导航
//      （原生链接键盘路径）；「查看全部」小字对比度同查。
//   ⑤ /home 既有字段零变化复验：运行时抽验顶层字段冻结集合；
//      openapi/夹具零 diff 由 git diff 佐证（见 PR 描述）。

const MOCK = "http://127.0.0.1:4319";

async function control(
  request: APIRequestContext,
  body: Record<string, unknown>,
): Promise<void> {
  const res = await request.post(`${MOCK}/__control`, { data: body });
  expect(res.ok()).toBeTruthy();
}

/** 契约合法 SectionList payload（#48 同款工厂，条目附独立 published_at
 *  以表达服务端 -first_published_at 排序）。 */
function sectionListPayload(
  slug: string,
  title: string,
  entries: { title: string; url: string; published_at: string }[],
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
      id: 950 + index,
      title: entry.title,
      url: entry.url,
      expired: false,
      section_slug: slug,
      section_title: title,
      department_name: "教务处",
      published_at: entry.published_at,
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

/** WCAG 2.x 相对亮度与对比度（实算计算样式，不采样像素）。 */
function luminance(rgb: string): number {
  const [r, g, b] = (rgb.match(/\d+/g) ?? []).slice(0, 3).map(Number);
  const lin = [r, g, b].map((v) => {
    const s = (v ?? 0) / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return (
    0.2126 * (lin[0] ?? 0) + 0.7152 * (lin[1] ?? 0) + 0.0722 * (lin[2] ?? 0)
  );
}

function contrastRatio(foreground: string, background: string): number {
  const l1 = luminance(foreground);
  const l2 = luminance(background);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

/** 前景色＋有效底色（元素透明时沿祖先链上溯到第一个不透明底——
 *  如 .more 链接透明，实际底是卡片 var(--bg)）。 */
async function computedColors(
  locator: Locator,
): Promise<{ color: string; background: string }> {
  return locator.evaluate((el) => {
    const parse = (s: string) => s.match(/[\d.]+/g)?.map(Number) ?? [];
    let node: Element | null = el;
    let background = "rgb(0, 0, 0)";
    while (node) {
      const bg = getComputedStyle(node).backgroundColor;
      const [r, g, b, a = 1] = parse(bg);
      if ((a ?? 1) > 0) {
        background = `rgb(${r ?? 0}, ${g ?? 0}, ${b ?? 0})`;
        break;
      }
      node = node.parentElement;
    }
    return { color: getComputedStyle(el).color, background };
  });
}

test.describe("分区速览模块（SPEC-003 #50 验收矩阵）", () => {
  test("排序：服务端顺序原样消费；旧文修改（first_published_at 不变）不重排、修订可见", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    // 数组顺序即服务端 -first_published_at 排序（新 → 旧）
    const entries = [
      {
        title: "最新发布",
        url: "/chronicle/jwc/latest/",
        published_at: "2026-09-15T08:00:00+08:00",
      },
      {
        title: "中间发布",
        url: "/chronicle/jwc/middle/",
        published_at: "2026-09-12T08:00:00+08:00",
      },
      {
        title: "最早发布",
        url: "/chronicle/jwc/oldest/",
        published_at: "2026-09-01T08:00:00+08:00",
      },
    ];
    await control(request, {
      endpoint: "section-list:chronicle",
      mode: "ok",
      payload: sectionListPayload("chronicle", "社史纪事", entries),
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    const rows = page
      .locator("section.sec-articles .card", { hasText: "社史纪事" })
      .locator(".rows a");
    await expect(rows).toHaveText(["最新发布", "中间发布", "最早发布"]);

    // 旧文修改：仅改标题，first_published_at 与数组顺序不变
    await control(request, {
      endpoint: "section-list:chronicle",
      mode: "ok",
      payload: sectionListPayload("chronicle", "社史纪事", [
        entries[0]!,
        entries[1]!,
        { ...entries[2]!, title: "最早发布（已修订）" },
      ]),
    });
    await page.goto("/");
    // 顺序与槽位不变（不重排），修订后的标题下一次请求即可见
    await expect(rows).toHaveText([
      "最新发布",
      "中间发布",
      "最早发布（已修订）",
    ]);
  });

  test("断点边界抽查：600/601/980/981/768/1440 恒单行轨道＋无页面溢出＋下一卡外露", async ({
    page,
  }) => {
    await stubMedia(page);
    const rail = page.locator("section.sec-articles .cards");
    for (const width of [600, 601, 980, 981, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      const facts = await rail.evaluate((el) => {
        const boxes = [...el.querySelectorAll<HTMLElement>(".card")].map((c) =>
          c.getBoundingClientRect(),
        );
        const box = el.getBoundingClientRect();
        const tops = boxes.map((b) => Math.round(b.top));
        return {
          flow: getComputedStyle(el).gridAutoFlow,
          sameRow: Math.max(...tops) - Math.min(...tops) <= 1,
          pageOverflow:
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
          straddling: boxes.filter(
            (b) => b.left < box.right - 1 && b.right > box.right + 1,
          ).length,
        };
      });
      expect(facts.flow, `${width}px grid-auto-flow:column`).toBe("column");
      expect(facts.sameRow, `${width}px 单行（同行等顶）`).toBe(true);
      expect(facts.pageOverflow, `${width}px 无横向溢出`).toBeLessThanOrEqual(
        0,
      );
      expect(facts.straddling, `${width}px 恰一张卡外露`).toBe(1);
      await page
        .locator("section.sec-articles")
        .screenshot({ path: `docs/evidence/spec-003-r1/edge-${width}.png` });
    }
  });

  test("固定 3 槽空间稳定（同一布局内）：所有卡片行区高度一致，留白不收缩", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    await control(request, {
      endpoint: "section-list:events",
      mode: "ok",
      payload: sectionListPayload("events", "社团活动", [
        {
          title: "活动唯一",
          url: "/events/jwc/only/",
          published_at: "2026-09-10T08:00:00+08:00",
        },
      ]),
    });
    await control(request, {
      endpoint: "section-list:guide",
      mode: "ok",
      payload: sectionListPayload("guide", "生活指南", [
        {
          title: "指南一",
          url: "/guide/jwc/g1/",
          published_at: "2026-09-10T08:00:00+08:00",
        },
        {
          title: "指南二",
          url: "/guide/jwc/g2/",
          published_at: "2026-09-09T08:00:00+08:00",
        },
        {
          title: "指南三",
          url: "/guide/jwc/g3/",
          published_at: "2026-09-08T08:00:00+08:00",
        },
      ]),
    });

    // 轨道布局两种宽度各自验证：行区高度 max-min ≤1px
    for (const width of [768, 1440]) {
      await page.setViewportSize({ width, height: 1024 });
      await page.goto("/");
      const heights = await page
        .locator("section.sec-articles .card .rows")
        .evaluateAll((els) =>
          els.map((el) => el.getBoundingClientRect().height),
        );
      expect(heights.length).toBeGreaterThanOrEqual(5);
      expect(
        Math.max(...heights) - Math.min(...heights),
        `${width}px 槽位空间一致`,
      ).toBeLessThanOrEqual(1);
    }
  });

  test("可访问性：5 徽标 deep 小字与「查看全部」对比度 ≥4.5:1；标题聚焦后 Enter 激活", async ({
    page,
    request,
  }) => {
    await stubMedia(page);
    // 五分区各 1 条 → 5 个 tone 徽标全部渲染
    const at = "2026-09-10T08:00:00+08:00";
    const five: [string, string, string][] = [
      ["chronicle", "社史纪事", "/chronicle/jwc/library-hours/"],
      ["events", "社团活动", "/events/jwc/a/"],
      ["materials", "资料专区", "/materials/jwc/a/"],
      ["software", "常用软件", "/software/jwc/a/"],
      ["guide", "生活指南", "/guide/jwc/a/"],
    ];
    for (const [slug, title, url] of five) {
      await control(request, {
        endpoint: `section-list:${slug}`,
        mode: "ok",
        payload: sectionListPayload(slug, title, [
          { title: `${title}文章`, url, published_at: at },
        ]),
      });
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    const module = page.locator("section.sec-articles");
    await expect(module.locator(".card")).toHaveCount(5);

    // 徽标：deep 字（color）对 soft 底（background）实算对比度
    for (const [slug] of five) {
      const tag = module.locator(`.tag.tone-${slug}`);
      const { color, background } = await computedColors(tag);
      expect(
        contrastRatio(color, background),
        `${slug} 徽标对比度`,
      ).toBeGreaterThanOrEqual(4.5);
    }

    // 「查看全部」（13px 小字）：品牌青对卡片底色
    const more = module.locator(".more").first();
    const moreColors = await computedColors(more);
    expect(
      contrastRatio(moreColors.color, moreColors.background),
      "查看全部对比度",
    ).toBeGreaterThanOrEqual(4.5);

    // 标题行聚焦后 Enter 激活（原生链接键盘路径；落点渲染由既有详情测试覆盖）
    const link = module.getByRole("link", { name: "社史纪事文章" });
    await link.focus();
    expect(
      await page.evaluate(() => document.activeElement?.textContent),
    ).toContain("社史纪事文章");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/chronicle\/jwc\/library-hours\//);
  });

  test("/home 既有字段零变化复验：顶层字段冻结集合不变", async ({
    request,
  }) => {
    // 运行时抽验（客户端 ajv 每请求校验为常态守护）；openapi/夹具零 diff
    // 由 git diff 佐证（PR 描述记录）。
    const res = await request.get(`${MOCK}/api/v1/home`);
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual([
      "alert",
      "campus_news",
      "carousel",
      "sections",
      "title",
    ]);
    for (const section of body.sections as Record<string, unknown>[]) {
      expect(Object.keys(section).sort()).toEqual(["slug", "title", "url"]);
    }
  });
});
