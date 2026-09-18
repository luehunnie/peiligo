// 首页展示层冻结映射（SPEC-001-F05）。唯一权威来源：
// v1 frontend/templatetags/peiligo_extras.py（SECTION_SHORT/SECTION_TONE）
// 与 notices/models.py EventFieldsMixin 的三态中文标签（v1 模板直接渲染
// 该中文标签；B02 契约改为机器码 upcoming/ongoing/ended，此处回译等价展示）。
// 未识别 slug 一律中性回落（不猜色、不猜名），与 v1 过滤器行为逐字一致。

/** 板块 slug → 两字短名（hero chip/快讯卡徽标；未识别原样回落）。 */
const SECTION_SHORT: Record<string, string> = {
  chronicle: "纪事",
  events: "活动",
  materials: "资料",
  software: "软件",
  guide: "指南",
};

/** 板块 slug → tone 类后缀（ico/tone/cat 类共用；未识别返回空串）。 */
const SECTION_TONE: Record<string, string> = {
  chronicle: "jishi",
  events: "huodong",
  materials: "ziliao",
  software: "gongju",
  guide: "zhinan",
};

/** B02 事件状态码 → v1 中文标签（v1 模板渲染的既有口径）。 */
const EVENT_STATUS_LABELS: Record<string, string> = {
  upcoming: "即将开始",
  ongoing: "进行中",
  ended: "已结束",
};

/** 五板块一句话定位（SPEC-001-F06）。唯一权威来源：v1
 * templates/includes/section_positioning.html（IA §2 冻结文案，语义引源
 * PRD §7；定位属展示层文案，零数据字段）。未识别 slug 回落中性文案，
 * 与 v1 else 分支逐字一致。 */
const SECTION_POSITIONING: Record<string, string> = {
  chronicle: "记录校园动态、通知公告与长期报道的板块",
  events: "发布校园活动预告、进行中与回顾信息的板块",
  materials: "按学科/专业方向与资料类型组织的学习资源共享板块",
  software: "汇集校园常用软件与在线工具入口及使用说明的板块",
  guide: "面向全校的生活与办事固定信息板块",
};

export function sectionPositioning(slug: string): string {
  return SECTION_POSITIONING[slug] ?? "校园信息板块";
}

export function sectionShort(slug: string): string {
  return SECTION_SHORT[slug] ?? slug;
}

export function sectionTone(slug: string): string {
  return SECTION_TONE[slug] ?? "";
}

export function eventStatusLabel(code: string): string {
  return EVENT_STATUS_LABELS[code] ?? code;
}
