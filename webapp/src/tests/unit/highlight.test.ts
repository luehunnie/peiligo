// highlightFragments 单元测试（SPEC-001-F07）：切片正确性 + 注入惰性面。
// 渲染侧 escaping 由 Astro 文本插值承担，e2e search.spec 另有 DOM 级
// XSS 形查询断言（零脚本/零注入元素落 DOM）。
import { describe, expect, it } from "vitest";
import { highlightFragments } from "../../lib/highlight";

describe("highlightFragments", () => {
  it("单命中：切片为 前段 + 命中 + 后段", () => {
    expect(
      highlightFragments("关于图书馆调整开放时间的通知", "图书馆"),
    ).toEqual([
      { text: "关于", hit: false },
      { text: "图书馆", hit: true },
      { text: "调整开放时间的通知", hit: false },
    ]);
  });

  it("忽略大小写；命中片段保留原文大小写（v1 match.group 口径）", () => {
    expect(highlightFragments("Campus ZOTERO Guide", "zotero")).toEqual([
      { text: "Campus ", hit: false },
      { text: "ZOTERO", hit: true },
      { text: " Guide", hit: false },
    ]);
  });

  it("多命中相邻不重叠；拼接恒等于原文", () => {
    const text = "ababab";
    const fragments = highlightFragments(text, "ab");
    expect(fragments).toEqual([
      { text: "ab", hit: true },
      { text: "ab", hit: true },
      { text: "ab", hit: true },
    ]);
    expect(fragments.map((f) => f.text).join("")).toBe(text);
  });

  it("无命中 → 单一非命中片段；空 query → 整段非命中", () => {
    expect(highlightFragments("图书馆通知", "不存在词")).toEqual([
      { text: "图书馆通知", hit: false },
    ]);
    expect(highlightFragments("图书馆通知", "")).toEqual([
      { text: "图书馆通知", hit: false },
    ]);
    expect(highlightFragments("", "q")).toEqual([]);
    expect(highlightFragments("", "")).toEqual([]);
  });

  it("正则元字符按字面量匹配（v1 re.escape 口径）", () => {
    // "a.b" 不得命中 "axb"
    expect(highlightFragments("axb a.b", "a.b")).toEqual([
      { text: "axb ", hit: false },
      { text: "a.b", hit: true },
    ]);
    expect(highlightFragments("100% ( draft )", "100% (")).toEqual([
      { text: "100% (", hit: true },
      { text: " draft )", hit: false },
    ]);
  });

  it("注入惰性面：XSS 形 query/原文只产生纯文本片段，零标记产出", () => {
    const hostileQuery = `<img src=x onerror=alert(1)>`;
    const hostileText = `<script>alert("x")</script> & <b>bold</b>`;
    const fragments = highlightFragments(hostileText, hostileQuery);
    // 无命中：片段拼接逐字等于原文，且没有任何片段被标记为命中
    expect(fragments).toHaveLength(1);
    expect(fragments[0].hit).toBe(false);
    expect(fragments[0].text).toBe(hostileText);
    // 命中注入形 query 时，命中片段文本也必须逐字等于原文对应切片
    const hit = highlightFragments(`<b>bold</b> 与普通文本`, "<b>bold</b>");
    expect(hit).toEqual([
      { text: "<b>bold</b>", hit: true },
      { text: " 与普通文本", hit: false },
    ]);
  });
});
