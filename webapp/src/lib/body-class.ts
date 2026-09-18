// v1 {% block body_class %}：template-<模型蛇形名>（五型各自冻结值）。
// 单一出处：正式详情页（pages/[section]/[dept]/[slug].astro）与 E9 预览
// 消费页（pages/preview.astro）同模板渲染共用——openapi /preview
// 「同模板渲染」义务的一部分（body class 属模板壳）。
import type { PageType } from "../schemas/api-schema";

const BODY_CLASSES: Record<PageType, string> = {
  notice: "template-noticepage",
  article: "template-articlepage",
  material: "template-materialpage",
  software: "template-softwaretoolpage",
  guide: "template-guidepage",
};

export function bodyClassForType(type: PageType): string {
  return BODY_CLASSES[type];
}
