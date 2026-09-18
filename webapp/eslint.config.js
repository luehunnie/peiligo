// @ts-check
import eslint from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import astro from "eslint-plugin-astro";
import tseslint from "typescript-eslint";

export default defineConfig(
  // overlay-checkout/＝apply_overlay.py 产出的冻结基线 checkout
  // （peiligo@pin 只读产物，见 backend/apply_overlay.py）——基线代码永不被
  // 本仓库 lint；docs/staging.md 指引在本仓 checkout 后 lint 仍须绿。
  globalIgnores([
    "dist/",
    ".astro/",
    "test-results/",
    "playwright-report/",
    "overlay-checkout/",
  ]),
  eslint.configs.recommended,
  tseslint.configs.recommended,
  astro.configs.recommended,
  {
    // 浏览器运行面：public 静态脚本（免打包直出，如首页轮播）
    files: ["public/**/*.js"],
    languageOptions: {
      globals: { document: "readonly", window: "readonly" },
    },
  },
  {
    // Node 运行面：构建脚本与 e2e mock 服务（浏览器 globals 之外的进程内工具）
    files: ["scripts/**/*.mjs", "src/tests/e2e/*.mjs"],
    languageOptions: {
      globals: {
        process: "readonly",
        console: "readonly",
        URL: "readonly",
        structuredClone: "readonly",
      },
    },
  },
);
