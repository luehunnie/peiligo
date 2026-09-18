import { describe, expect, it } from "vitest";
import { feedbackMailto, site } from "../../lib/site";

describe("site", () => {
  it("提供 BaseLayout 使用的站点标题与描述", () => {
    expect(site.title).toBe("Peiligo");
    expect(site.description.length).toBeGreaterThan(0);
  });

  it("不再持有构建期反馈邮箱常量（F05 起每请求经 /chrome 直连，契约 4）", () => {
    // chrome.feedback_email 为唯一取值链（v1 SiteSettings → FEEDBACK_EMAIL
    // 环境兜底由后端承担）；本模块若复活该常量即构成构建期快照回归
    expect(Object.keys(site)).not.toContain("feedbackEmail");
  });
});

describe("feedbackMailto（v1 base.html 默认 feedback_mailto 块）", () => {
  it("构造 subject=页面标题、body=当前页地址 的 mailto 链接", () => {
    const href = feedbackMailto(
      "hello@peiligo.example",
      "活动预告",
      "https://peiligo.example.edu/events/",
    );
    expect(href).toBe(
      "mailto:hello@peiligo.example?subject=" +
        encodeURIComponent("活动预告") +
        "&body=" +
        encodeURIComponent("https://peiligo.example.edu/events/"),
    );
  });

  it("标题缺省回落「页面反馈」（v1 page.title|default 同口径）", () => {
    for (const subject of ["", "   "]) {
      expect(feedbackMailto("a@b.c", subject, "https://x/")).toContain(
        `subject=${encodeURIComponent("页面反馈")}`,
      );
    }
  });

  it("对主题与地址做百分号编码（防止 & 断链、地址进入新参数）", () => {
    const href = feedbackMailto("a@b.c", "a&b=c", "https://x/p?a=1&b=2");
    expect(href).not.toMatch(/subject=a&b=c/);
    expect(href).toBe(
      "mailto:a@b.c?subject=a%26b%3Dc&body=https%3A%2F%2Fx%2Fp%3Fa%3D1%26b%3D2",
    );
  });
});
