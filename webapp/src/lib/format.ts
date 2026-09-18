// v1 展示格式化助手（SPEC-001-F06）。等价转写自 v1 Django 模板过滤器在
// 内容页消费口径下的行为（peiligo/main = 48fd5d6）：
//   - truncatechars ← Django truncatechars（B02 契约 list_summary 不截断，
//     90 字截断责任在消费端，见 api/serializers.py ListEntry 注）
//   - filesizeformat ← Django humanize filesizeformat（附件块/附件列表）
//   - formatDateTime ← date:"Y-m-d H:i"（活动起止/确认页来源时间；站点
//     时区 Asia/Shanghai，与 lib/dates.ts publishedDateParts 同一口径）
//   - pageLinks ← search/services._page_links 分页窗口（1、末页恒在，
//     当前页 ±window，其余以 "…" 折叠；页码为数字、缺口恒为字符串）
import { publishedDateParts, SITE_TIME_ZONE } from "./dates";

/** Django truncatechars：超过 num 个字符（Unicode 码点）截为 num 字符
 * （末位为省略号本身），恰好等长不截。 */
export function truncatechars(text: string, num: number): string {
  const chars = Array.from(text);
  if (chars.length <= num) return text;
  return `${chars.slice(0, num - 1).join("")}…`;
}

const SIZE_STEPS = [
  { limit: 1024 ** 2, divisor: 1024, unit: "KB" },
  { limit: 1024 ** 3, divisor: 1024 ** 2, unit: "MB" },
  { limit: 1024 ** 4, divisor: 1024 ** 3, unit: "GB" },
  { limit: 1024 ** 5, divisor: 1024 ** 4, unit: "TB" },
  { limit: 1024 ** 6, divisor: 1024 ** 5, unit: "PB" },
  { limit: 1024 ** 7, divisor: 1024 ** 6, unit: "EB" },
  { limit: 1024 ** 8, divisor: 1024 ** 7, unit: "ZB" },
  { limit: 1024 ** 9, divisor: 1024 ** 8, unit: "YB" },
] as const;

/** Django filesizeformat：<1024 计数字节（"512 bytes"/"1 byte"），此后按
 * 1024 进制取首个命中的单位、恒一位小数（"100.0 KB"）。null/0 由调用方
 * 按 v1 {% if file_size %} 口径整体省略，不进本函数。 */
export function filesizeformat(bytes: number): string {
  if (!Number.isFinite(bytes)) return "0 bytes";
  if (bytes < 1024)
    return bytes === 1 ? "1 byte" : `${Math.trunc(bytes)} bytes`;
  for (const { limit, divisor, unit } of SIZE_STEPS) {
    if (bytes < limit) return `${(bytes / divisor).toFixed(1)} ${unit}`;
  }
  return `${(bytes / 1024 ** 9).toFixed(1)} YB`;
}

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  timeZone: SITE_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** v1 date:"Y-m-d H:i"（站点时区回译；null/非法 → 空串，理论不出现）。 */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${publishedDateParts(iso).datetime} ${timeFormat.format(date)}`;
}

/** search/services.py PAGE_GAP：分页窗口的缺口占位字面值（非页码）。 */
export const PAGE_GAP = "…";

export type PageLink = number | typeof PAGE_GAP;

/** v1 _page_links：页码窗口表——1、末页恒在，当前页 ±window，其余以
 * PAGE_GAP 折叠（页码恒为数字、缺口恒为字符串，消费方以类型区分）。 */
export function pageLinks(
  number: number,
  total: number,
  window = 1,
): PageLink[] {
  const shown = new Set<number>([1, total]);
  for (
    let p = Math.max(1, number - window);
    p <= Math.min(total, number + window);
    p++
  ) {
    shown.add(p);
  }
  const links: PageLink[] = [];
  let previous = 0;
  for (const value of [...shown].sort((a, b) => a - b)) {
    if (previous && value - previous > 1) links.push(PAGE_GAP);
    links.push(value);
    previous = value;
  }
  return links;
}
