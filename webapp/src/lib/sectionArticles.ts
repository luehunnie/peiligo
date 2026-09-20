// 首页「分区文章」模块的纯数据整形（SPEC-003 #48，M2；仅 Astro、零后端）。
// 输入＝五分区 getSectionList 的取数结果（失败/抛错记为 null，由调用方
// Promise.all 收集）；输出＝送入 SectionArticles.astro 的卡片视图模型。
// 规则（PRD B 冻结口径在契约 4 陈旧回退语义下的确切化）：
//   - 取数失败（!ok，含 5xx/404/契约违约/超时）或调用抛错 → 该分区跳过
//     （前端隐藏）。注：api 服务层对普通内容有 ≤5min 陈旧回退（契约 4），
//     有陈旧版本可用时结果为 ok(stale:true) 而非失败——故「隐藏」实际
//     发生在无陈旧版本可回退时；有陈旧版本时展示陈旧内容（页面不破损）。
//   - 0 篇分区不渲染（数据层过滤，展示层无需再判）。
//   - 每分区仅取前 3 条（服务端 -first_published_at 排序＋CURRENT_DEFAULT
//     可见性即权威；分页语义留在服务端）。
//   - 卡片题名/落点取自 E3 的 section.title/section.url（既有分区列表页
//     /<slug>/）；文章行仅保留 title/url（仅可点击标题）。
import type { SectionList, SectionSlug } from "../schemas/api-schema";
import type { ApiResult } from "../services/api";

export interface SectionCard {
  slug: SectionSlug;
  title: string;
  url: string;
  entries: { title: string; url: string }[];
}

/** 每分区保留的文章条数（固定 3 槽；不足由展示层留白）。 */
const ENTRIES_PER_SECTION = 3;

export function toSectionCards(
  results: Array<ApiResult<SectionList> | null>,
): SectionCard[] {
  const cards: SectionCard[] = [];
  for (const result of results) {
    if (!result || !result.ok) continue;
    const { section, entries } = result.data;
    const slice = entries.slice(0, ENTRIES_PER_SECTION);
    if (slice.length === 0) continue; // 0 篇分区不渲染
    cards.push({
      slug: section.slug,
      title: section.title,
      url: section.url,
      entries: slice.map((entry) => ({
        title: entry.title,
        url: entry.url,
      })),
    });
  }
  return cards;
}
