import { describe, expect, it } from "vitest";
import { publishedDateParts } from "../../lib/dates";

// v1 首页日期口径：Django TIME_ZONE="Asia/Shanghai" 下 date:"Y-m-d"
// （datetime 属性）与 date:"m-d"（展示）；B02 契约 published_at 为 ISO 8601
// （UTC 或带偏移），前端统一换算到 Asia/Shanghai 后取日期部分。

describe("publishedDateParts（v1 date 过滤器 Asia/Shanghai 等价）", () => {
  it("带 +08:00 偏移的 ISO 时间取当日", () => {
    expect(publishedDateParts("2026-09-10T09:00:00+08:00")).toEqual({
      datetime: "2026-09-10",
      display: "09-10",
    });
  });

  it("UTC 时间换算到 Asia/Shanghai，跨日进位正确", () => {
    // 17:30Z = 次日 01:30 +08:00 → 日期进到 09-11
    expect(publishedDateParts("2026-09-10T17:30:00Z")).toEqual({
      datetime: "2026-09-11",
      display: "09-11",
    });
    // 15:59Z = 23:59 同日；16:00Z 即翻日
    expect(publishedDateParts("2026-09-10T15:59:00Z")).toEqual({
      datetime: "2026-09-10",
      display: "09-10",
    });
  });

  it("null / 非法值返回空串（v1 无日期即不输出 time 同口径）", () => {
    expect(publishedDateParts(null)).toEqual({ datetime: "", display: "" });
    expect(publishedDateParts("not-a-date")).toEqual({
      datetime: "",
      display: "",
    });
  });
});
