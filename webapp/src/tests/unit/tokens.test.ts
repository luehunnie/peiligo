import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * SPEC-001-F02 机器可校验的 token 对照表。
 * 权威值 = v1 `static/css/peiligo.css`（peiligo/main = 48fd5d6）:root，
 * 逐值冻结于此；tokens.css 偏离任一值即测试失败（防 token 漂移）。
 * 人工评审版对照表见 docs/design-tokens.md。
 */
const tokensCss = readFileSync(
  new URL("../../styles/tokens.css", import.meta.url),
  "utf8",
).replace(/\/\*[\s\S]*?\*\//g, "");
const baseCss = readFileSync(
  new URL("../../styles/base.css", import.meta.url),
  "utf8",
);

/** v1 :root 原值（逐字） */
const V1_TOKENS: Record<string, string> = {
  "--teal": "#2f7a6e",
  "--teal-deep": "#1d5a50",
  "--teal-soft": "#e8f1ee",
  "--yellow": "#ffc940",
  "--coral": "#e8590c",
  "--amber": "#e8960c",
  "--blue": "#3e7bc2",
  "--violet": "#7a5fc9",
  "--coral-soft": "#fdeee4",
  "--amber-soft": "#fdf3e0",
  "--blue-soft": "#e9f0fa",
  "--violet-soft": "#efecfa",
  "--ink": "#191f1c",
  "--ink-2": "#66716b",
  "--line": "#e7eae8",
  "--bg": "#ffffff",
  "--coral-deep": "#a63a02",
  "--amber-deep": "#8a5803",
  "--blue-deep": "#2c5e94",
  "--violet-deep": "#5b3fa0",
  "--wrap": "1160px",
};

/** v1 --font 字栈（逐字，含引号与逗号间距归一化后比较） */
const V1_FONT_PARTS = [
  "-apple-system",
  "BlinkMacSystemFont",
  '"Segoe UI"',
  '"PingFang SC"',
  '"Hiragino Sans GB"',
  '"Microsoft YaHei"',
  '"Helvetica Neue"',
  "Helvetica",
  "Arial",
  "sans-serif",
];

function declared(name: string, css: string): string | undefined {
  return css
    .match(new RegExp(`${escapeRe(name)}\\s*:\\s*([^;]+);`))?.[1]
    ?.trim();
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&");
}

describe("tokens.css 与 v1 逐值对照", () => {
  it("每个 v1 颜色/版心 token 原值照抄", () => {
    for (const [name, value] of Object.entries(V1_TOKENS)) {
      expect(declared(name, tokensCss), name).toBe(value);
    }
  });

  it("--font 为 v1 系统字栈（逐项一致、无新增字体）", () => {
    const parts = declared("--font", tokensCss)
      ?.split(",")
      .map((p) => p.trim().replace(/\s+/g, " "));
    expect(parts).toEqual(V1_FONT_PARTS);
  });

  it("不出现 v1 色值集合之外的新色值（防漂移；覆盖 tokens.css 与 base.css）", () => {
    const allowed = new Set(
      [
        ...Object.values(V1_TOKENS).filter((v) => v.startsWith("#")),
        // v1 一次性白（skip-link/页脚等文字色，v1 逐字 #fff，不作 token）
        "#fff",
      ].map((v) => v.toLowerCase()),
    );
    const hexes = [tokensCss, baseCss]
      .flatMap((css) => css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [])
      .map((h) => h.toLowerCase());
    for (const hex of hexes) {
      expect(allowed.has(hex), `非 v1 色值：${hex}`).toBe(true);
    }
  });

  it("圆角刻度与 v1 冻结口径一致（24/18/14/12/13/999）", () => {
    expect(declared("--radius-hero", tokensCss)).toBe("24px");
    expect(declared("--radius-card", tokensCss)).toBe("18px");
    expect(declared("--radius-panel", tokensCss)).toBe("14px");
    expect(declared("--radius-small", tokensCss)).toBe("12px");
    expect(declared("--radius-icon", tokensCss)).toBe("13px");
    expect(declared("--radius-pill", tokensCss)).toBe("999px");
  });

  it("动效刻度与 v1 实际使用值一致（0.15/0.18/0.2/0.25s）", () => {
    expect(declared("--motion-fast", tokensCss)).toBe("0.15s");
    expect(declared("--motion-base", tokensCss)).toBe("0.18s");
    expect(declared("--motion-card", tokensCss)).toBe("0.2s");
    expect(declared("--motion-media", tokensCss)).toBe("0.25s");
  });

  it("断点常量为 v1 三档结构阈值的移动优先反转（601/761/981）", () => {
    expect(declared("--bp-sm", tokensCss)).toBe("601px");
    expect(declared("--bp-md", tokensCss)).toBe("761px");
    expect(declared("--bp-lg", tokensCss)).toBe("981px");
  });
});

describe("base.css 壳基线（v1 基础层等价）", () => {
  it("正文 16px / 行高 1.7 / 系统字栈", () => {
    expect(baseCss).toMatch(/font-size:\s*16px/);
    expect(baseCss).toMatch(/line-height:\s*1\.7/);
    expect(baseCss).toMatch(/font-family:\s*var\(--font\)/);
  });

  it("focus-visible 为 2px 品牌青 outline、3px 偏移", () => {
    expect(baseCss).toMatch(
      /:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--teal\)[^}]*outline-offset:\s*3px/,
    );
  });

  it("保留 [hidden] 显式兜底、skip-link 与 visually-hidden", () => {
    expect(baseCss).toMatch(/\[hidden\]\s*\{[^}]*display:\s*none\s*!important/);
    expect(baseCss).toMatch(/\.skip-link\s*\{/);
    expect(baseCss).toMatch(/\.visually-hidden\s*\{/);
  });

  it("prefers-reduced-motion 全站关闭过渡/动画", () => {
    expect(baseCss).toMatch(
      /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*transition-duration:\s*0\.01ms\s*!important/,
    );
  });

  it("移动优先：main.wrap 基础 20/44，≥601px 28/56（v1 ≤600 档反转）", () => {
    expect(baseCss).toMatch(/main\.wrap\s*\{[^}]*padding-block:\s*20px 44px/);
    expect(baseCss).toMatch(
      /@media \(min-width: 601px\)\s*\{\s*main\.wrap\s*\{[^}]*padding-block:\s*28px 56px/,
    );
  });
});

describe("无第三方 origin（契约 3）", () => {
  it("token/基础样式无 @import、url()、@font-face", () => {
    for (const css of [tokensCss, baseCss]) {
      expect(css).not.toMatch(/@import\b/);
      expect(css).not.toMatch(/url\(/i);
      expect(css).not.toMatch(/@font-face\b/);
    }
  });
});
