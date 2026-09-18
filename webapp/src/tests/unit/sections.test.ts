import { describe, expect, it } from "vitest";
import {
  eventStatusLabel,
  sectionShort,
  sectionTone,
} from "../../lib/sections";

// v1 冻结显示映射（frontend/templatetags/peiligo_extras.py 同口径）：
// SHORT/TONE 为 CSS 类与栏目徽标文字；未识别 slug 时 short 回落原 slug、
// tone 回落空串（首页 hero chip 的「推荐」回落属页面层，不在映射内）。

describe("sectionShort（v1 section_short）", () => {
  it("五个冻结板块返回既有短名", () => {
    expect(sectionShort("chronicle")).toBe("纪事");
    expect(sectionShort("events")).toBe("活动");
    expect(sectionShort("materials")).toBe("资料");
    expect(sectionShort("software")).toBe("软件");
    expect(sectionShort("guide")).toBe("指南");
  });

  it("未识别 slug 回落原 slug（v1 default:section.slug 同口径）", () => {
    expect(sectionShort("chronicle-extra")).toBe("chronicle-extra");
  });

  it("空 slug 回落空串（null 由调用方空值合并处理，类型已约束）", () => {
    expect(sectionShort("")).toBe("");
  });
});

describe("sectionTone（v1 section_tone）", () => {
  it("五个冻结板块返回既有 tone 类名", () => {
    expect(sectionTone("chronicle")).toBe("jishi");
    expect(sectionTone("events")).toBe("huodong");
    expect(sectionTone("materials")).toBe("ziliao");
    expect(sectionTone("software")).toBe("gongju");
    expect(sectionTone("guide")).toBe("zhinan");
  });

  it("未识别 slug 回落空串（不产生 tone- 类）", () => {
    expect(sectionTone("unknown")).toBe("");
    expect(sectionTone("")).toBe("");
  });
});

describe("eventStatusLabel（v1 冻结活动状态文案）", () => {
  it("三种契约状态返回既有中文文案", () => {
    expect(eventStatusLabel("upcoming")).toBe("即将开始");
    expect(eventStatusLabel("ongoing")).toBe("进行中");
    expect(eventStatusLabel("ended")).toBe("已结束");
  });

  it("未知值原样透传（不静默改写后端新增状态）", () => {
    expect(eventStatusLabel("postponed" as never)).toBe("postponed");
  });
});
