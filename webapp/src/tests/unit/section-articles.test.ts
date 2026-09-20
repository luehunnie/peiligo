import { describe, expect, it } from "vitest";
import { toSectionCards } from "../../lib/sectionArticles";
import type { SectionList } from "../../schemas/api-schema";

// SPEC-003 #48（M2）数据整形单测：取数失败/抛错 → 分区隐藏（前端过滤）；
// 0 篇 → 不渲染；>3 篇 → 仅取前 3；题名/落点取自 E3 section 字段。
// e2e（section-articles.spec.ts）另覆盖渲染、留白、陈旧回退与响应式。

function sectionList(slug: SectionList["section"]["slug"], count: number) {
  return {
    section: {
      slug,
      title: `题-${slug}`,
      url: `/${slug}/`,
      archive_url: `/${slug}/archive/`,
    },
    entries: Array.from({ length: count }, (_, index) => ({
      type: "notice" as const,
      id: index + 1,
      title: `文章${index + 1}`,
      url: `/${slug}/jwc/post-${index + 1}/`,
      expired: false,
      section_slug: slug,
      section_title: `题-${slug}`,
      department_name: "教务处",
      published_at: "2026-09-10T09:00:00+08:00",
      event_status: null,
      list_summary: "",
    })),
    pagination: {
      total: count,
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
  } as SectionList;
}

const ok = (data: SectionList) => ({ ok: true as const, data, stale: false });

describe("toSectionCards（SPEC-003 #48 数据整形）", () => {
  it("成功结果映射为卡片：题名/落点取自 section，行仅 title/url", () => {
    const cards = toSectionCards([ok(sectionList("chronicle", 2))]);
    expect(cards).toEqual([
      {
        slug: "chronicle",
        title: "题-chronicle",
        url: "/chronicle/",
        entries: [
          { title: "文章1", url: "/chronicle/jwc/post-1/" },
          { title: "文章2", url: "/chronicle/jwc/post-2/" },
        ],
      },
    ]);
  });

  it("超过 3 条仅取前 3（固定 3 槽）", () => {
    const cards = toSectionCards([ok(sectionList("guide", 7))]);
    expect(cards[0]!.entries).toHaveLength(3);
    expect(cards[0]!.entries.map((entry) => entry.title)).toEqual([
      "文章1",
      "文章2",
      "文章3",
    ]);
  });

  it("0 篇分区不渲染", () => {
    expect(toSectionCards([ok(sectionList("software", 0))])).toEqual([]);
  });

  it("取数失败（!ok）与抛错（null）的分区被隐藏", () => {
    const cards = toSectionCards([
      { ok: false, reason: "server-error" },
      ok(sectionList("events", 1)),
      null,
      ok(sectionList("guide", 3)),
      { ok: false, reason: "schema-violation" },
    ]);
    expect(cards.map((card) => card.slug)).toEqual(["events", "guide"]);
  });

  it("全部分区失败/抛错 → 空数组（整个模块不渲染）", () => {
    expect(
      toSectionCards([null, { ok: false, reason: "network" }, null]),
    ).toEqual([]);
  });

  it("陈旧回退结果（ok+stale）同样渲染（契约 4：页面不破损）", () => {
    const stale = { ...ok(sectionList("materials", 1)), stale: true };
    expect(toSectionCards([stale]).map((card) => card.slug)).toEqual([
      "materials",
    ]);
  });
});
