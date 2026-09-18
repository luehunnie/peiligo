// 搜索关键词高亮切片（SPEC-001-F07）。等价转写 v1
// frontend/templatetags/peiligo_extras.py highlight 过滤器的安全管线语义
// （docs/api/openapi.json /search 冻结描述："切片→逐片段转义→仅自产
// <mark>，见 peiligo_extras.highlight"）：
//   1. 在原文上按 re.escape 后的 query 忽略大小写切片——模式本身不携带
//      任何 HTML 语义；
//   2. 命中/非命中片段一律是纯文本数据（本函数零 HTML 产出）；
//   3. 渲染层（ResultRow.astro）以 Astro 文本插值输出（框架逐字转义），
//      仅 <mark> 为自产标签——注入面为零。
// 与 v1 的差异仅在转义责任位置：v1 过滤器内部 escape + mark_safe；Astro
// 侧转义由模板引擎承担，故本函数只返回惰性片段。测试：
// tests/unit/highlight.test.ts + e2e search.spec（XSS 形查询零脚本落 DOM）。

export interface HighlightFragment {
  text: string;
  hit: boolean;
}

/** v1 re.escape 等价：转义正则元字符，query 恒为字面量匹配。 */
function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** 把纯文本按 query（字面量、忽略大小写）切片为命中/非命中片段。
 *  query 为空串（或原文为空）→ 单一非命中片段/空数组，等价 v1 纯转义
 *  路径；相邻命中不重叠（RegExp exec 语义，与 v1 finditer 一致）。 */
export function highlightFragments(
  text: string,
  query: string,
): HighlightFragment[] {
  if (!text) return [];
  if (!query) return [{ text, hit: false }];
  const pattern = new RegExp(escapeRegExp(query), "gi");
  const fragments: HighlightFragment[] = [];
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const start = match.index;
    if (start > last) {
      fragments.push({ text: text.slice(last, start), hit: false });
    }
    fragments.push({ text: match[0], hit: true });
    last = start + match[0].length;
  }
  if (last < text.length) {
    fragments.push({ text: text.slice(last), hit: false });
  }
  return fragments;
}
