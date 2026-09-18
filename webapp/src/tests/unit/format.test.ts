import { describe, expect, it } from "vitest";
import {
  filesizeformat,
  formatDateTime,
  pageLinks,
  truncatechars,
} from "../../lib/format";

// v1 内容页消费口径下的 Django 过滤器等价测试（peiligo/main = 48fd5d6）。

describe("truncatechars（Django truncatechars 码点口径）", () => {
  it("短于/恰好等于上限不截断", () => {
    expect(truncatechars("图书馆通知", 10)).toBe("图书馆通知");
    expect(truncatechars("恰好五个字", 5)).toBe("恰好五个字");
  });

  it("超限截为 num 码点（省略号占末位）", () => {
    expect(truncatechars("一二三四五六七", 5)).toBe("一二三四…");
    expect(Array.from(truncatechars("一二三四五六七", 5))).toHaveLength(5);
  });

  it("按 Unicode 码点计数（非 UTF-16 码元）", () => {
    // "𝐀" 为星体面码点（UTF-16 占 2 码元）
    expect(truncatechars("𝐀𝐁𝐂𝐃𝐄", 3)).toBe("𝐀𝐁…");
  });
});

describe("filesizeformat（Django humanize filesizeformat）", () => {
  it("小于 1024 为计数字节", () => {
    expect(filesizeformat(1)).toBe("1 byte");
    expect(filesizeformat(512)).toBe("512 bytes");
  });

  it("1024 进制取首个命中单位，恒一位小数", () => {
    expect(filesizeformat(1024)).toBe("1.0 KB");
    expect(filesizeformat(102400)).toBe("100.0 KB");
    expect(filesizeformat(1048576)).toBe("1.0 MB");
    expect(filesizeformat(26214400)).toBe("25.0 MB");
    expect(filesizeformat(3145728)).toBe("3.0 MB");
    expect(filesizeformat(5242880)).toBe("5.0 MB");
  });

  it("跨单位边界取小单位（< limit 严格比较）", () => {
    expect(filesizeformat(1024 ** 2 - 1)).toBe("1024.0 KB");
    expect(filesizeformat(1024 ** 2)).toBe("1.0 MB");
  });
});

describe("formatDateTime（v1 date:'Y-m-d H:i' Asia/Shanghai）", () => {
  it("带偏移 ISO 输出 Y-m-d H:i", () => {
    expect(formatDateTime("2026-04-18T08:30:00+08:00")).toBe(
      "2026-04-18 08:30",
    );
  });

  it("UTC 换算到站点时区", () => {
    expect(formatDateTime("2026-04-17T17:30:00Z")).toBe("2026-04-18 01:30");
  });

  it("null / 非法值返回空串", () => {
    expect(formatDateTime(null)).toBe("");
    expect(formatDateTime("nope")).toBe("");
  });
});

describe("pageLinks（v1 _page_links 窗口语义）", () => {
  it("单页只有当前页", () => {
    expect(pageLinks(1, 1)).toEqual([1]);
  });

  it("1 与末页恒在，窗口外折叠为缺口", () => {
    expect(pageLinks(1, 5)).toEqual([1, 2, "…", 5]);
    expect(pageLinks(3, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(pageLinks(5, 7)).toEqual([1, "…", 4, 5, 6, 7]);
    expect(pageLinks(6, 12)).toEqual([1, "…", 5, 6, 7, "…", 12]);
  });

  it("页码为数字、缺口为字符串（类型可区分）", () => {
    const links = pageLinks(2, 9);
    expect(links.some((l) => typeof l === "number")).toBe(true);
    expect(links.filter((l) => typeof l === "string")).toEqual(["…"]);
  });
});
