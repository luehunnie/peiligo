// sitemap.xml（SPEC-001-F06）。等价 wagtail contrib sitemaps 输出
// （django.contrib.sitemaps sitemap.xml 模板口径）：urlset 0.9，每条
// <loc>＋可选 <lastmod>（无 changefreq/priority——v1 未设即不输出）。
// 条目模型与排除口径在契约 /sitemap 端点（仅 live；容器类与 noindex 页
// 排除）；loc 契约为路径形态，公开域绝对化在此完成（request origin，
// 与 robots.txt Sitemap 行同源）。lastmod 为 ISO date-time，v1 模板以
// date:"Y-m-d"（站点时区 Asia/Shanghai）渲染 → publishedDateParts 同一
// 转译。失败 → v1 500 页等价最小错误响应（爬虫侧语义＝重试）。
import type { APIRoute } from "astro";
import { unavailableResponse } from "../lib/responses";
import { publishedDateParts } from "../lib/dates";
import type { SitemapEntry } from "../schemas/api-schema";
import { api } from "../services/api";

/** XML 文本转义（loc 理论为站内路径，转义保证任何值下输出仍良构）。 */
function xmlEscape(text: string) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export const GET: APIRoute = async ({ request }) => {
  let sitemap;
  try {
    const result = await api.getSitemap();
    if (result.ok) sitemap = result.data;
  } catch {
    // 客户端抛错（含基址 fail-closed 配置错误）＝部署边界事故，同一错误边界
  }
  if (!sitemap) return unavailableResponse();

  const origin = new URL(request.url).origin;
  const urls = sitemap.entries
    .map((entry: SitemapEntry) => {
      const loc = `${origin}${entry.loc.startsWith("/") ? "" : "/"}${entry.loc}`;
      const lastmod = entry.lastmod
        ? `\n    <lastmod>${publishedDateParts(entry.lastmod).datetime}</lastmod>`
        : "";
      return `  <url>\n    <loc>${xmlEscape(loc)}</loc>${lastmod}\n  </url>`;
    })
    .join("\n");
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
