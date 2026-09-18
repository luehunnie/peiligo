// SPEC-001 F04 服务层：类型化 Headless API 客户端（Astro SSR 专用）。
//
// 网络边界（B01 契约 S1/S2）：/api/v1 仅经 Peiligo Docker 内网供本模块取数，
// 浏览器零直接调用——本模块禁止被客户端脚本 import（首次取数即抛错），
// 基址取自服务端环境变量 PEILIGO_API_BASE_URL（不经 import.meta.env，避免被打包内联）。
// 基址 fail closed：未设置或非法时抛错、绝不静默回退——生产（NODE_ENV=production）
// 必须显式注入内网基址；127.0.0.1 本地缺省仅在 PEILIGO_API_ALLOW_LOCAL_DEFAULT=1
// 且非生产时允许（双重门，见 docs/api/README.md），生产 Astro 容器不可能静默指向本机回环。
// 无 CORS 逻辑：服务端取数不需要，也禁止为浏览器访问 API 打开任何通路。
//
// 新鲜度语义（SPEC-001 契约 4 / B01 契约 F1–F6）：
//   - chrome / search / link-confirm / preview：严格每请求直连，绝不缓存、
//     绝不回退陈旧结果，失败即返回错误（页面须展示样式化错误/404）；
//   - 其余普通内容：每请求直连；仅当本次请求失败时，允许回退最近一次成功
//     版本（≤5 分钟窗口，结果带 stale:true）。API 全响应 no-store（F1），
//     请求端同样声明 no-store，且不依赖任何 HTTP 共享缓存。
//
// 预览边界（B01 契约 §3.1/S8）：token 原样透传给 /api/v1/preview，不解析、
// 不校验、不缓存、不写入日志或错误对象；不转发任何浏览器 Cookie/会话。
//
// 权限与业务规则全部留在 Django 侧（SPEC-001 约束 1）：本客户端只做取数、
// 契约校验与错误分类，不做可见性判定、不做过滤/排序/分页语义、不构造外链。
import {
  OPERATIONS,
  validateErrorEnvelope,
  validateResponse,
  type ApiOperationId,
} from "../schemas/api-contract";
import type {
  Chrome,
  Home,
  LinkConfirm,
  PageDetail,
  PreviewDetail,
  SectionArchive,
  SectionList,
  SectionSlug,
  SearchResults,
  Sitemap,
} from "../schemas/api-schema";

/** 普通内容的陈旧回退窗口（SPEC-001 契约 4：≤5 分钟）。 */
const STALE_WINDOW_MS = 5 * 60 * 1000;

/** 单请求超时：内网取数不应阻塞页面渲染超过此值。 */
const REQUEST_TIMEOUT_MS = 10_000;

/** 契约 F4「永不陈旧面」+ E9 预览：严格直连，无缓存无回退。 */
const NEVER_STALE: ReadonlySet<ApiOperationId> = new Set([
  "getChrome",
  "getSearch",
  "getLinkConfirm",
  "getPreview",
]);

export interface ApiOk<T> {
  ok: true;
  data: T;
  /** true = 本次请求失败，回退了 ≤5 分钟内的最近成功版本（仅普通内容） */
  stale: boolean;
}

export interface ApiFailure {
  ok: false;
  /**
   * 错误分类（SPEC-001 契约 4 的页面义务）：
   * - "not-found" → 页面展示样式化 404；
   * - 其余 → 页面展示样式化错误态 + 重试引导。
   */
  reason:
    | "not-found"
    | "server-error"
    | "network"
    | "invalid-json"
    | "schema-violation"
    | "unexpected-status";
  /** HTTP 状态码（网络层失败时缺省） */
  status?: number;
  /** 错误封装里的 zh-Hans 访客文案（§2.4），可直接用于样式化错误态 */
  message?: string;
}

export type ApiResult<T> = ApiOk<T> | ApiFailure;

export interface ListParams {
  q?: string;
  dept?: string;
  type?: string;
  tag?: string;
  page?: string;
}

export interface SearchParams extends ListParams {
  section?: SectionSlug;
}

export interface LinkConfirmParams {
  url?: string;
  from?: string;
}

export interface PeiligoApiClient {
  getChrome(): Promise<ApiResult<Chrome>>;
  getHome(): Promise<ApiResult<Home>>;
  getSectionList(
    slug: SectionSlug,
    params?: ListParams,
  ): Promise<ApiResult<SectionList>>;
  getSectionArchive(slug: SectionSlug): Promise<ApiResult<SectionArchive>>;
  getSearch(params?: SearchParams): Promise<ApiResult<SearchResults>>;
  getPageDetail(
    section: SectionSlug,
    dept: string,
    slug: string,
  ): Promise<ApiResult<PageDetail>>;
  getLinkConfirm(params?: LinkConfirmParams): Promise<ApiResult<LinkConfirm>>;
  getSitemap(): Promise<ApiResult<Sitemap>>;
  getPreview(token: string): Promise<ApiResult<PreviewDetail>>;
  /** 前端自有上游健康快照（F08；/healthz 消费，测试注入断言用） */
  health(): ApiHealthSnapshot;
}

export interface ApiClientOptions {
  /** API 基址（含 /api/v1 前缀）；缺省首次取数时读 PEILIGO_API_BASE_URL（fail closed，见 resolveEnvBaseUrl） */
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  now?: () => number;
}

/** 单端点连续失败信号（SPEC-001-F08 契约 5：前端自有健康信号，进程内、无 Redis）。 */
export interface ApiFailureSignal {
  /** 连续失败次数（成功即清零） */
  consecutive: number;
  /** 最近一次失败分类（reason，不含 URL/查询值/token） */
  lastReason: ApiFailure["reason"];
  /** 最近一次失败的 Unix 毫秒时间 */
  lastAt: number;
}

/** 前端自有上游健康快照（/healthz 消费）：进程内计数，重启即归零。 */
export interface ApiHealthSnapshot {
  /** 任一端点连续失败 ≥2 时为 true（1 次抖动不算降级） */
  degraded: boolean;
  failures: Partial<Record<ApiOperationId, ApiFailureSignal>>;
}

/** 本地测试缺省基址：仅在显式门（PEILIGO_API_ALLOW_LOCAL_DEFAULT=1 且非生产）后可达。 */
const LOCAL_DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1";

function isHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.hostname !== ""
    );
  } catch {
    return false;
  }
}

/**
 * 从服务端环境解析 API 基址（首次取数时调用，不在 import 期求值）：
 * - 显式配置：必须为合法 http(s) URL，否则一律抛错（含生产与本地门开启时）——
 *   配置写错时立刻暴露，绝不静默回退任何缺省值；
 * - 未配置：fail closed 抛错；仅当 PEILIGO_API_ALLOW_LOCAL_DEFAULT=1 且
 *   NODE_ENV !== "production" 时放行本地缺省（双重门：显式 flag 挡误配，
 *   NODE_ENV 硬门挡生产容器）。
 */
function resolveEnvBaseUrl(): string {
  // process.env 只在服务端运行时存在，也不会被 Vite 内联进浏览器 bundle；
  // 客户端脚本误 import 本模块时在首次取数即抛错，杜绝内网基址与取数逻辑进浏览器。
  if (typeof process === "undefined" || typeof process.env === "undefined") {
    throw new Error(
      "[peiligo-api] 服务端专用模块：禁止从浏览器/客户端脚本 import（契约 S1：浏览器零直接 API 调用）",
    );
  }
  const raw = process.env.PEILIGO_API_BASE_URL?.trim();
  if (raw) {
    if (!isHttpUrl(raw)) {
      // 不回显原值：env 值可能含凭据片段，错误信息只描述规则。
      throw new Error(
        "[peiligo-api] PEILIGO_API_BASE_URL 配置无效（须为可解析的 http/https URL）——拒绝以无效配置取数",
      );
    }
    return raw;
  }
  const localGate =
    process.env.PEILIGO_API_ALLOW_LOCAL_DEFAULT === "1" &&
    process.env.NODE_ENV !== "production";
  if (!localGate) {
    throw new Error(
      "[peiligo-api] PEILIGO_API_BASE_URL 未设置——拒绝路由到缺省地址（fail closed）。生产部署必须显式注入内网 API 基址；本地开发可设 PEILIGO_API_ALLOW_LOCAL_DEFAULT=1 启用本地缺省（见 docs/api/README.md）",
    );
  }
  return LOCAL_DEFAULT_BASE_URL;
}

function failure(
  reason: ApiFailure["reason"],
  status?: number,
  message?: string,
): ApiFailure {
  return { ok: false, reason, status, message };
}

export function createApiClient(
  options: ApiClientOptions = {},
): PeiligoApiClient {
  const fetchImpl = options.fetchImpl ?? fetch;
  const now = options.now ?? Date.now;
  // 基址延迟到首次取数才解析：模块 import（含生产构建时的页面求值）不触发
  // 环境检查；配置缺失/非法在生产容器首次请求即抛错（fail closed，页面渲染
  // 以错误态暴露），绝不静默指到本机回环。显式 baseUrl（测试注入）同路径缓存。
  let resolvedBase: string | undefined;
  function base(): string {
    resolvedBase ??= (options.baseUrl ?? resolveEnvBaseUrl()).replace(
      /\/+$/,
      "",
    );
    return resolvedBase;
  }
  // 普通内容的最近成功版本（stale-while-error），进程内 Map：端点少、体积小、无 Redis。
  const staleCache = new Map<string, { data: unknown; storedAt: number }>();
  // 连续失败计数（F08 健康信号 + 服务器日志留痕）：进程内，成功即清零。
  const failureSignals = new Map<ApiOperationId, ApiFailureSignal>();

  function buildUrl(
    operationId: ApiOperationId,
    path: Record<string, string>,
    query: Record<string, string | undefined>,
  ): string {
    let pathname = OPERATIONS[operationId].path;
    for (const [name, value] of Object.entries(path)) {
      if (!value)
        throw new Error(`[peiligo-api] ${operationId} 缺少路径参数 ${name}`);
      pathname = pathname.replace(`{${name}}`, encodeURIComponent(value));
    }
    if (pathname.includes("{")) {
      throw new Error(
        `[peiligo-api] ${operationId} 路径模板存在未绑定参数：${pathname}`,
      );
    }
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) search.set(key, value);
    }
    const qs = search.toString();
    return qs ? `${base()}${pathname}?${qs}` : `${base()}${pathname}`;
  }

  async function errorDetail(
    response: Response,
  ): Promise<{ status: number; message?: string }> {
    let message: string | undefined;
    try {
      const body: unknown = await response.json();
      if (validateErrorEnvelope(body).ok) {
        message = (body as { error: { message?: string } }).error.message;
      }
    } catch {
      // 错误体不是契约 JSON（如反代拦截页）：无访客文案可用，保持静默分类
    }
    return { status: response.status, message };
  }

  // ---- F08 健康信号与日志（契约 5：服务器日志 + healthcheck 是 Non-goals 3
  // 明确保留的唯一观测通道；无监控/统计）。日志只含端点名/分类/状态码/次数，
  // 绝不含 URL、查询值或预览 token（token 边界同 §预览）。 ----
  function trackFailure(
    operationId: ApiOperationId,
    result: ApiFailure,
  ): ApiFailure {
    const signal: ApiFailureSignal = {
      consecutive: (failureSignals.get(operationId)?.consecutive ?? 0) + 1,
      lastReason: result.reason,
      lastAt: now(),
    };
    failureSignals.set(operationId, signal);
    console.error(
      `[peiligo-api] ${operationId} 取数失败（${result.reason}${result.status ? ` ${result.status}` : ""}），连续第 ${signal.consecutive} 次`,
    );
    return result;
  }

  function trackSuccess(operationId: ApiOperationId): void {
    const prev = failureSignals.get(operationId);
    if (prev) {
      console.info(
        `[peiligo-api] ${operationId} 已恢复（此前连续失败 ${prev.consecutive} 次）`,
      );
      failureSignals.delete(operationId);
    }
  }

  function health(): ApiHealthSnapshot {
    const failures: ApiHealthSnapshot["failures"] = {};
    for (const [id, signal] of failureSignals) failures[id] = { ...signal };
    return {
      degraded: [...failureSignals.values()].some((s) => s.consecutive >= 2),
      failures,
    };
  }

  async function callOperation<T>(
    operationId: ApiOperationId,
    path: Record<string, string> = {},
    query: Record<string, string | undefined> = {},
  ): Promise<ApiResult<T>> {
    const url = buildUrl(operationId, path, query);
    let response: Response;
    try {
      response = await fetchImpl(url, {
        headers: { accept: "application/json", "cache-control": "no-store" },
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
    } catch {
      return trackFailure(operationId, failure("network"));
    }
    if (!response.ok) {
      const detail = await errorDetail(response);
      if (response.status === 404) {
        // 404 是契约内正常应答（内容不存在/预览令牌失效），非上游健康
        // 问题：不计入失败信号，避免健康探针被流量模式污染（F08 契约 5）
        return failure("not-found", detail.status, detail.message);
      }
      if (response.status >= 500)
        return trackFailure(
          operationId,
          failure("server-error", detail.status, detail.message),
        );
      // 405（method_not_allowed）是契约内唯一其他错误，客户端只发 GET，不该出现
      return trackFailure(
        operationId,
        failure("unexpected-status", detail.status, detail.message),
      );
    }
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return trackFailure(operationId, failure("invalid-json"));
    }
    const verdict = validateResponse(operationId, body);
    if (!verdict.ok) {
      // 契约漂移＝上游事故：服务端日志留痕（仅字段路径，无数据值），访客侧按不可用处理
      console.error(
        `[peiligo-api] ${operationId} 响应不符合机器契约：${verdict.message ?? ""}`,
      );
      return trackFailure(operationId, failure("schema-violation"));
    }
    trackSuccess(operationId);
    if (!NEVER_STALE.has(operationId)) {
      staleCache.set(url, { data: body, storedAt: now() });
    }
    return { ok: true, data: body as T, stale: false };
  }

  /** 直连取数 + 普通内容的 ≤5min 陈旧回退（失败时）。 */
  async function callWithFreshness<T>(
    operationId: ApiOperationId,
    path: Record<string, string> = {},
    query: Record<string, string | undefined> = {},
  ): Promise<ApiResult<T>> {
    const result = await callOperation<T>(operationId, path, query);
    if (result.ok || NEVER_STALE.has(operationId)) return result;
    const url = buildUrl(operationId, path, query);
    const cached = staleCache.get(url);
    if (cached && now() - cached.storedAt <= STALE_WINDOW_MS) {
      // 陈旧回退留痕（契约 4）：服务器日志一行，页面不再各自记
      console.info(
        `[peiligo-api] ${operationId} 本次回退 ≤5min 陈旧版本（契约 4）`,
      );
      return { ok: true, data: cached.data as T, stale: true };
    }
    return result;
  }

  return {
    getChrome: () => callWithFreshness<Chrome>("getChrome"),
    getHome: () => callWithFreshness<Home>("getHome"),
    getSectionList: (slug, params = {}) =>
      callWithFreshness<SectionList>("getSectionList", { slug }, { ...params }),
    getSectionArchive: (slug) =>
      callWithFreshness<SectionArchive>("getSectionArchive", { slug }),
    getSearch: (params = {}) =>
      callWithFreshness<SearchResults>("getSearch", {}, { ...params }),
    getPageDetail: (section, dept, slug) =>
      callWithFreshness<PageDetail>("getPageDetail", { section, dept, slug }),
    getLinkConfirm: (params = {}) =>
      callWithFreshness<LinkConfirm>("getLinkConfirm", {}, { ...params }),
    getSitemap: () => callWithFreshness<Sitemap>("getSitemap"),
    // preview 直连（不经 callWithFreshness）：永不回退陈旧结果，失败即样式化 404
    getPreview: (token) =>
      callOperation<PreviewDetail>("getPreview", {}, { token }),
    health,
  };
}

/** 生产用单例；测试用 createApiClient(options) 构造隔离实例。 */
export const api: PeiligoApiClient = createApiClient();

/** 生产单例的上游健康快照（/healthz 消费；F08 契约 5：前端自有健康信号）。 */
export function apiHealthSnapshot(): ApiHealthSnapshot {
  return api.health();
}
