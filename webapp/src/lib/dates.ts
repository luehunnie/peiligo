// 发布日期展示（SPEC-001-F05）。v1 模板以 Django date 过滤器按站点时区
// （settings.TIME_ZONE = "Asia/Shanghai"）渲染快讯卡日期：datetime 属性
// `Y-m-d`、可见文本 `m-d`（零填充）。B02 契约 published_at 为 ISO 8601
// （USE_TZ 下多为 UTC 偏移），此处按同一站点时区回译，跨时区日期边界
// 与 v1 一致；null（理论不出现：live 页恒有发布时间）渲染为空，同 v1。

export const SITE_TIME_ZONE = "Asia/Shanghai";

export interface PublishedDateParts {
  /** datetime 属性值（v1 date:'Y-m-d'） */
  datetime: string;
  /** 可见文本（v1 date:'m-d'） */
  display: string;
}

const dayFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: SITE_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export function publishedDateParts(iso: string | null): PublishedDateParts {
  if (!iso) return { datetime: "", display: "" };
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return { datetime: "", display: "" };
  // en-CA 恒为 YYYY-MM-DD（零填充），即 v1 date:'Y-m-d'
  const datetime = dayFormat.format(date);
  return { datetime, display: datetime.slice(5) };
}
