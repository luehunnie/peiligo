import { defineConfig, devices } from "@playwright/test";

// F05 起首页为请求时 SSR：Playwright 需两个前置服务——
//   1. mock B02 API（4319）：替代真实 Wagtail 契约端点，带测试控制面；
//   2. Astro 生产构建产物经 @astrojs/node standalone 伺服（4321），
//      以 PEILIGO_API_BASE_URL 指向 mock——同时验证「生产显式注入基址」
//      这一 fail-closed 部署姿态（unset 基址在生产必须失败，见 api.ts）。
export default defineConfig({
  testDir: "src/tests/e2e",
  // 控制面（/__control）改写的是共享 mock 状态：单 worker 串行执行，
  // 杜绝跨文件/跨用例的读改写竞争（用例总量小，串行成本可忽略）
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4321",
  },
  webServer: [
    {
      command: "node src/tests/e2e/mock-api-server.mjs",
      url: "http://127.0.0.1:4319/healthz",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run build && node ./dist/server/entry.mjs",
      url: "http://127.0.0.1:4321/",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        HOST: "127.0.0.1",
        PORT: "4321",
        PEILIGO_API_BASE_URL: "http://127.0.0.1:4319/api/v1",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
