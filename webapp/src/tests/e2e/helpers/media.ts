import type { Page } from "@playwright/test";

/**
 * 生产拓扑里 /media/* 由 F11 反代同源代理到 Wagtail；e2e 拓扑中前端 SSR
 * (4321) 与 mock API(4319) 分端口，浏览器对页面内 <img src="/media/…"> 的
 * 请求落在 4321 而 404（SSR 的 JSON 取数在服务端、不受影响）。此处在浏览器
 * 侧拦截补图：以路径哈希着色的确定性 SVG 占位，保证截图呈现真实版式而非
 * 坏图 alt 文本。只需对含图用例调用（通常放 test.beforeEach）。
 */
export async function stubMedia(page: Page): Promise<void> {
  await page.route("**/media/**", (route) => {
    const pathname = new URL(route.request().url()).pathname;
    let hash = 0;
    for (const ch of pathname)
      hash = (hash * 31 + (ch.codePointAt(0) ?? 0)) >>> 0;
    const hue = hash % 360;
    void route.fulfill({
      status: 200,
      contentType: "image/svg+xml",
      body:
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 260">` +
        `<rect width="400" height="260" fill="hsl(${hue} 34% 80%)"/>` +
        `<circle cx="322" cy="58" r="44" fill="hsl(${hue} 48% 46%)" opacity=".85"/>` +
        `<circle cx="96" cy="204" r="66" fill="hsl(${hue} 48% 60%)" opacity=".5"/>` +
        `</svg>`,
    });
  });
}
