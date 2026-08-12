import type {
  ContentItem,
  ContentExtraData,
  ContentType,
  ContentStatus,
} from '../types/content'

/**
 * 公开内容只读 API client（原生 fetch）。
 * 端点经 Vite /api 代理转发，本文件不硬编码主机名或端口。
 */

const CONTENTS_ENDPOINT = '/api/contents'

/**
 * 公开内容 API 错误：保留 HTTP 状态码，便于调用方区分失败类型。
 * - status === 0：请求未送达（网络失败 / DNS / 超时 / 中断）。
 * - status === 404：内容不存在 / 草稿 / 已下线（详情专用）。
 * - 其它非 2xx：原样保留，如 500、502、503。
 */
export class ContentsApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ContentsApiError'
    this.status = status
  }
}

// fetch 抛出时无法细分 DNS / 超时 / 离线，统一为可操作的恢复提示，不吞异常
async function safeFetch(url: string): Promise<Response> {
  try {
    return await fetch(url)
  } catch {
    throw new ContentsApiError('网络连接失败，请检查网络后重试', 0)
  }
}

// response.ok 校验：404 与其它错误给出可区分的状态码与文案
function ensureOk(response: Response): void {
  if (response.ok) return
  throw new ContentsApiError(
    response.status === 404
      ? '内容不存在或已下线'
      : `服务器返回错误（${response.status}）`,
    response.status,
  )
}

// JSON 解析失败同样包装为 ContentsApiError，不吞异常
async function parseBody(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new ContentsApiError('服务器响应不是有效的数据格式', response.status)
  }
}

/**
 * 后端公开 JSON 的线类型（wire type），与 ContentItemResponse 逐字段对齐。
 * sourceName / sourceUrl 在 JSON 中可显式为 null；extraData 始终为对象（含 {}）。
 * 其余字段按冻结契约的窄类型声明。
 */
interface ContentItemWire {
  id: string
  contentType: ContentType
  title: string
  summary: string
  body: string[]
  sourceName: string | null
  sourceUrl: string | null
  publishedAt: string
  status: ContentStatus
  extraData: ContentExtraData
}

/**
 * 在网络边界将 wire type 归一化为冻结契约 ContentItem：
 * 非 null sourceName / sourceUrl → 保留 string；null → 省略（undefined）。
 * 其余字段原值透传，extraData 对象与 publishedAt 字符串不变。
 */
function normalizeContentItem(wire: ContentItemWire): ContentItem {
  const { sourceName, sourceUrl, ...rest } = wire
  return {
    ...rest,
    ...(sourceName !== null ? { sourceName } : {}),
    ...(sourceUrl !== null ? { sourceUrl } : {}),
  }
}

/**
 * 获取已发布内容列表（后端已按 publishedAt DESC 排序、仅返回 published）。
 */
export async function getPublishedContents(): Promise<ContentItem[]> {
  const response = await safeFetch(CONTENTS_ENDPOINT)
  ensureOk(response)
  const wire = (await parseBody(response)) as ContentItemWire[]
  return wire.map(normalizeContentItem)
}

/**
 * 获取单条已发布内容详情；不存在 / 草稿 / 已下线统一返回 404。
 * 本批次列表页不调用，预留给 M3-4 详情页使用。
 */
export async function getPublishedContentById(id: string): Promise<ContentItem> {
  const response = await safeFetch(
    `${CONTENTS_ENDPOINT}/${encodeURIComponent(id)}`,
  )
  ensureOk(response)
  const wire = (await parseBody(response)) as ContentItemWire
  return normalizeContentItem(wire)
}
