import type { Page } from "@playwright/test";

// WCAG 2.x 对比度判定共享层（SPEC-001-F09 自 contrast.spec 上提，两个
// 消费方同口径）：首页视觉门（contrast.spec）与全站可达性审计
// （a11y.spec）共用同一套「计算样式事实源」数学与取值原语。
//   - 普通文本 ≥ 4.5:1；大字（≥24px 或 ≥18.66px 粗体）≥ 3:1；
//   - 非文本 UI（控件指示/焦点指示）≥ 3:1。
// 半透明色先按 alpha 合成到视觉底色上再计算（口径详见 contrast.spec 头注）。

export type Rgb = { r: number; g: number; b: number; a: number };

export type Pair = { fg: string; bg: string };

export function parseColor(css: string): Rgb {
  const m = css.match(
    /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)/,
  );
  if (!m) throw new Error(`无法解析颜色：${css}`);
  return {
    r: Number(m[1]),
    g: Number(m[2]),
    b: Number(m[3]),
    a: m[4] === undefined ? 1 : Number(m[4]),
  };
}

/** 半透明色按 alpha 合成到底色（CSS sRGB 分量插值口径）。 */
export function blend(fg: Rgb, backdrop: Rgb): Rgb {
  return {
    r: fg.a * fg.r + (1 - fg.a) * backdrop.r,
    g: fg.a * fg.g + (1 - fg.a) * backdrop.g,
    b: fg.a * fg.b + (1 - fg.a) * backdrop.b,
    a: 1,
  };
}

export function luminance({ r, g, b }: Rgb): number {
  const [lr, lg, lb] = [r, g, b]
    .map((v) => v / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

export function contrastRatio(fg: Rgb, bg: Rgb): number {
  const solid = fg.a < 1 ? blend(fg, bg) : fg; // 前景含 alpha 先合成（bg 已不透明）
  const [l1, l2] = [luminance(solid), luminance(bg)].sort((a, b) => b - a);
  return (l1 + 0.05) / (l2 + 0.05);
}

/** 前景 = 元素计算 color（可指定伪元素）；背景 = 沿祖先首个不透明背景。 */
export async function readPair(
  page: Page,
  selector: string,
  pseudo?: string,
): Promise<Pair> {
  return page.evaluate(
    ({ selector, pseudo }) => {
      const el = document.querySelector(selector);
      if (!el) throw new Error(`未找到元素：${selector}`);
      const opaque = (c: string) => {
        const m = c.match(/,\s*([\d.]+)\)$/);
        return c !== "transparent" && (!m || Number(m[1]) > 0);
      };
      const fg = getComputedStyle(el, pseudo ?? null).color;
      let bg = "rgb(255, 255, 255)";
      let node: Element | null = el;
      while (node) {
        const c = getComputedStyle(node).backgroundColor;
        if (opaque(c)) {
          bg = c;
          break;
        }
        node = node.parentElement;
      }
      return { fg, bg };
    },
    { selector, pseudo },
  );
}
