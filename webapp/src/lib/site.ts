export const site = {
  title: "Peiligo",
  description: "Peiligo 公共前端（Astro 重建版）",
} as const;

/**
 * 页脚反馈 mailto（v1 base.html 默认 feedback_mailto 块：subject=页面标题、
 * body=当前页绝对地址）。邮箱实参自 F05 起取 /chrome 的 feedback_email
 * （v1 取值链 SiteSettings.feedback_email → settings.FEEDBACK_EMAIL 环境
 * 兜底，契约端点每请求直连回传，SSR 等价接入；构建期常量已废止）。
 * 外链确认页的隐私覆盖（body 只带站内路径）属其所属页面票，经
 * BaseLayout footer 具名插槽自渲染页脚实现。
 */
export function feedbackMailto(
  email: string,
  subject: string,
  pageUrl: string,
): string {
  const subjectOrFallback = subject.trim() ? subject : "页面反馈";
  return `mailto:${email}?subject=${encodeURIComponent(subjectOrFallback)}&body=${encodeURIComponent(pageUrl)}`;
}
