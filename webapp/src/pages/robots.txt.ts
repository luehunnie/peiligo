// robots.txt（SPEC-001-F06）。等价转写自 v1 templates/robots.txt
// （TemplateView，text/plain）：管理面与外链确认页禁抓；/search/ 刻意不
// Disallow（noindex 是收录语义，robots Disallow 会让爬虫读不到 meta）。
// Sitemap 行取请求 scheme+host（v1 request.get_host 同口径；站点未配置
// astro.config site，部署公开域由请求头经适配器给出）。
import type { APIRoute } from "astro";

export const GET: APIRoute = ({ request }) => {
  const origin = new URL(request.url).origin;
  const body = [
    "User-agent: *",
    "Disallow: /django-admin/",
    "Disallow: /admin/",
    "Disallow: /link-confirm/",
    "",
    `Sitemap: ${origin}/sitemap.xml`,
    "",
  ].join("\n");
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
