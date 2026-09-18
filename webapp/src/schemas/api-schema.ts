// SPEC-001 F04 schema 层：与 docs/api/openapi.json（机器契约）逐字段对应的手写 TS 类型。
// 契约演进时的更新流程见 docs/api/README.md；运行时形状约束（minItems/const/format 等）
// 由 src/schemas/api-contract.ts 的 ajv 校验兜底，此处只保留消费方需要的类型形状。

export type SectionSlug =
  "chronicle" | "events" | "materials" | "software" | "guide";
export type PageType = "notice" | "article" | "material" | "software" | "guide";
export type EventStatus = "upcoming" | "ongoing" | "ended";

/** §5.1 公共构件 */
export interface SectionRef {
  slug: SectionSlug;
  title: string;
}

export interface DepartmentRef {
  name: string;
  slug: string;
}

export interface ImageRef {
  src: string;
  width: number;
  height: number;
  alt: string;
}

export interface AttachmentRef {
  title: string;
  url: string;
  file_size: number | null;
}

export interface ExternalLinkRef {
  url: string;
  confirm_href: string;
}

export interface Alert {
  text: string;
}

export interface Pagination {
  total: number;
  page: number;
  page_count: number;
  per_page: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface FilterCondition {
  label: "关键词" | "板块" | "部门" | "内容类型" | "标签";
  value: string;
}

/** 列表/搜索/归档共享行数据（§5.1） */
export interface ListEntry {
  type: PageType;
  id: number;
  title: string;
  url: string;
  expired: boolean;
  section_slug: string | null;
  section_title: string | null;
  department_name: string | null;
  published_at: string | null;
  event_status: EventStatus | null;
  list_summary: string;
}

export interface SearchChip {
  slug: string;
  label: string;
  url: string;
  active: boolean;
}

/** Block 判别联合（type 字段判别；paragraph.html 为 Django 渲染的安全 HTML 片段，整片插入不二次加工） */
export type Block =
  | { type: "heading"; value: { text: string; level: "h2" | "h3" } }
  | { type: "paragraph"; value: { html: string } }
  | { type: "image"; value: ImageRef }
  | { type: "attachment"; value: AttachmentRef }
  | {
      type: "table";
      value: { first_row_is_table_header?: boolean; data: string[][] };
    }
  | {
      type: "external_link";
      value: { text: string; url: string; confirm_href: string };
    };

/** E1 chrome */
export interface NavSection {
  slug: SectionSlug;
  title: string;
  url: string;
}

export interface Chrome {
  site_name: string;
  nav_sections: NavSection[];
  feedback_email: string;
  alert: Alert | null;
}

/** E2 home */
export interface CarouselEntry {
  kind: "internal" | "external";
  title: string;
  href: string;
  cover: ImageRef | null;
  summary: string;
  section_slug: string | null;
}

export interface CampusNewsEntry {
  type: PageType;
  id: number;
  title: string;
  href: string;
  cover: ImageRef | null;
  summary: string;
  section_slug: string | null;
  department: string;
  published_at: string | null;
  event_status: EventStatus | null;
}

export interface Home {
  title: string;
  alert: Alert | null;
  carousel: CarouselEntry[];
  sections: NavSection[];
  campus_news: CampusNewsEntry[];
}

/** E3 / E5 共享筛选回显 */
export interface FiltersEcho {
  q: string;
  section: SectionSlug | null;
  dept: string | null;
  type: PageType | null;
  tag: string | null;
  active: boolean;
  conditions: FilterCondition[];
}

export interface SectionInfo {
  slug: SectionSlug;
  title: string;
  url: string;
  archive_url: string;
}

export interface SectionList {
  section: SectionInfo;
  entries: ListEntry[];
  pagination: Pagination;
  filters: FiltersEcho;
}

/** E4 archive */
export interface SectionArchive {
  section: { slug: SectionSlug; title: string; url: string };
  entries: ListEntry[];
  total: number;
}

/** E5 search */
export interface SearchResults {
  q: string;
  entries: ListEntry[];
  pagination: Pagination;
  filters: FiltersEcho;
  chips: SearchChip[];
}

/** E6 详情公共字段（PageDetailBase） */
export interface BreadcrumbItem {
  title: string;
  url: string | null;
}

export interface EventInfo {
  status: EventStatus;
  start_at: string;
  end_at: string;
  is_online: boolean;
  location: string;
  registration: ExternalLinkRef | null;
}

export interface PageDetailBase {
  type: PageType;
  id: number;
  title: string;
  slug: string;
  url: string;
  section: SectionRef | null;
  department: DepartmentRef | null;
  first_published_at: string | null;
  last_published_at: string | null;
  expire_at: string | null;
  noindex: boolean;
  expired: boolean;
  cover: ImageRef | null;
  breadcrumb: BreadcrumbItem[];
}

export interface NoticeDetail extends PageDetailBase {
  type: "notice";
  summary: string;
  event: EventInfo | null;
  body: Block[];
  attachments: AttachmentRef[];
  external: ExternalLinkRef | null;
  tags: string[];
}

export interface ArticleDetail extends PageDetailBase {
  type: "article";
  summary: string;
  event: EventInfo | null;
  body: Block[];
  attachments: AttachmentRef[];
  external: ExternalLinkRef | null;
  tags: string[];
}

export interface MaterialDetail extends PageDetailBase {
  type: "material";
  summary: string;
  discipline: string;
  material_type: string;
  body: Block[];
  attachments: AttachmentRef[];
  external: ExternalLinkRef | null;
  tags: string[];
}

export interface SoftwareToolDetail extends PageDetailBase {
  type: "software";
  platforms: string[];
  source: ExternalLinkRef;
  license_note: string;
  body: Block[];
}

export interface GuideDetail extends PageDetailBase {
  type: "guide";
  category: string;
  location: string;
  opening_hours: string;
  contact: string;
  extra_notes: string;
  responsible_party: string;
  maintenance_mode: "self" | "curated";
  maintenance_mode_label: string;
  last_confirmed_on: string;
}

export type PageDetail =
  | NoticeDetail
  | ArticleDetail
  | MaterialDetail
  | SoftwareToolDetail
  | GuideDetail;

/** E7 link-confirm（校验失败 = 200 + ok:false + problem，非 4xx） */
export interface LinkConfirm {
  ok: boolean;
  target_domain: string;
  notice_text: string;
  source: { title: string; url: string } | null;
  go_href: string | null;
  problem: string;
}

/** E8 sitemap */
export interface SitemapEntry {
  loc: string;
  lastmod: string | null;
}

export interface Sitemap {
  entries: SitemapEntry[];
}

/** E9 preview：E6 判别联合 + 顶层 preview:true（草稿数据） */
export type PreviewDetail = { preview: true } & PageDetail;

/** 统一错误封装（非 2xx；§2.4） */
export type ApiErrorCode =
  "not_found" | "method_not_allowed" | "server_error" | "unavailable";

export interface ApiErrorEnvelope {
  error: {
    code: ApiErrorCode;
    /** zh-Hans 面向访客文案；可直接用于样式化错误态 */
    message: string;
  };
}
