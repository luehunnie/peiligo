/**
 * 内容模型：本文件为冻结模型，M1-2 阶段不得偏离。
 * 仅包含静态内容所需的最小结构，不引入作者、图片、标签、浏览量、DTO、Entity 或 API 类型。
 */

/** 五个内容板块类型 */
export type ContentType =
  | 'campus-story'
  | 'campus-activity'
  | 'learning-resource'
  | 'software-resource'
  | 'college-guide'

/** 内容状态：草稿 / 已发布 */
export type ContentStatus = 'draft' | 'published'

/** 板块专属字段允许的值类型 */
export type ContentExtraValue = string | number | boolean | string[]

/** 板块专属字段集合，键由板块配置决定 */
export type ContentExtraData = Record<string, ContentExtraValue>

/** 单条内容条目 */
export interface ContentItem {
  id: string
  contentType: ContentType
  title: string
  summary: string
  body: string[]
  sourceName?: string
  sourceUrl?: string
  publishedAt: string
  status: ContentStatus
  extraData?: ContentExtraData
}
