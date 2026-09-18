// @ts-check
import node from "@astrojs/node";
import { defineConfig } from "astro/config";

// https://astro.build/config
export default defineConfig({
  // SPEC-001 契约 4（内容新鲜度）：首页等公开页必须请求时直连 Wagtail
  // （发布 ≤30s 可见、不触发 Astro 重建），故自 F05 起整站 output: server
  // ＋官方 Node 适配器（standalone，生产容器入口 dist/server/entry.mjs，
  // 部署拓扑属 F11）。取数一律经 F04 服务端客户端（src/services/api.ts，
  // 基址 fail closed），浏览器零直接 API 调用。
  output: "server",
  adapter: node({ mode: "standalone" }),
  // SPEC-001 契约 3（严格 CSP，无 unsafe-inline）：禁止把样式内联为
  // <style>（Astro 默认 auto 会内联小样式表），一律外链同源 CSS。
  build: { inlineStylesheets: "never" },
});
