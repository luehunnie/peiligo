import { describe, expect, it } from "vitest";
import { verdict } from "../../../scripts/check-licenses.mjs";

// 许可证门（scripts/check-licenses.mjs）的 SPDX 求值回归测试。
// 回归背景：组合表达式曾被错误恒真（对象被布尔化），GPL 可借 "X AND MIT" 溜过。
describe("verdict（许可证 SPDX 表达式求值）", () => {
  it("允许列表内的单个许可证通过", () => {
    expect(verdict("MIT")).toMatchObject({ ok: true, kind: "允许" });
    expect(verdict("Apache-2.0").ok).toBe(true);
    expect(verdict("BSD-3-Clause").ok).toBe(true);
  });

  it("宽松等价许可证通过但单独标记", () => {
    expect(verdict("ISC")).toMatchObject({ ok: true, kind: "宽松等价" });
    expect(verdict("0BSD").ok).toBe(true);
  });

  it("未知与超出许可证不通过", () => {
    expect(verdict("GPL-3.0-only").ok).toBe(false);
    expect(verdict("LGPL-3.0-or-later").ok).toBe(false);
    expect(verdict("UNKNOWN").ok).toBe(false);
    expect(verdict(undefined).ok).toBe(false);
  });

  it("AND：任一成分超出则整体不通过", () => {
    expect(verdict("GPL-3.0 AND MIT").ok).toBe(false);
    expect(verdict("MIT AND Apache-2.0").ok).toBe(true);
  });

  it("OR：存在允许成分即通过，全超出则不通过", () => {
    expect(verdict("MIT OR GPL-3.0").ok).toBe(true);
    expect(verdict("GPL-3.0 OR LGPL-3.0").ok).toBe(false);
  });

  it("括号组合表达式", () => {
    expect(verdict("(MIT OR GPL-3.0) AND ISC").ok).toBe(true);
    expect(verdict("(GPL-3.0 OR LGPL-3.0) AND MIT").ok).toBe(false);
  });
});
