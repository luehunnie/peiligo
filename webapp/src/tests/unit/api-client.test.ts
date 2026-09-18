// SPEC-001 F04 客户端行为测试：取数、错误分类、新鲜度（≤5min 陈旧回退 vs 永不陈旧面）、
// no-store 行为与预览票据边界（token 不落日志/错误对象、不缓存）。
import { afterEach, describe, expect, it, vi, type Mock } from "vitest";
import { createApiClient, type PeiligoApiClient } from "../../services/api";
import chrome from "../fixtures/api/chrome.json";
import errorEnvelope from "../fixtures/api/error.json";
import home from "../fixtures/api/home.json";
import preview from "../fixtures/api/preview.json";
import search from "../fixtures/api/search.json";
import sectionList from "../fixtures/api/section-list.json";

const BASE = "http://api.internal:8000/api/v1";
const TOKEN = "a".repeat(40);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function clientWith(
  fetchImpl: Mock,
  now: () => number = () => 0,
): PeiligoApiClient {
  return createApiClient({
    baseUrl: BASE,
    fetchImpl: fetchImpl as unknown as typeof fetch,
    now,
  });
}

describe("取数与类型化返回", () => {
  it("getChrome 成功：URL、no-store/accept 头、超时 signal、类型化数据", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = clientWith(fetchImpl);
    const result = await client.getChrome();
    expect(result).toEqual({ ok: true, data: chrome, stale: false });
    expect(fetchImpl).toHaveBeenCalledWith(`${BASE}/chrome`, {
      headers: { accept: "application/json", "cache-control": "no-store" },
      signal: expect.any(AbortSignal),
    });
  });

  it("路径与查询参数按契约模板构造，undefined 查询项跳过", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(search));
    const client = clientWith(fetchImpl);
    await client.getSectionList("chronicle", {
      q: "图书馆",
      page: "2",
      type: undefined,
    });
    const expectedQuery = new URLSearchParams({
      q: "图书馆",
      page: "2",
    }).toString();
    expect(fetchImpl).toHaveBeenCalledWith(
      `${BASE}/sections/chronicle?${expectedQuery}`,
      expect.anything(),
    );
  });

  it("路径片段做 URL 编码", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(search));
    const client = clientWith(fetchImpl);
    await client.getSearch({ q: "a b" });
    const expectedQuery = new URLSearchParams({ q: "a b" }).toString();
    expect(fetchImpl).toHaveBeenCalledWith(
      `${BASE}/search?${expectedQuery}`,
      expect.anything(),
    );
  });

  it("baseUrl 结尾斜杠被归一化", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = createApiClient({
      baseUrl: `${BASE}/`,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    await client.getChrome();
    expect(fetchImpl).toHaveBeenCalledWith(`${BASE}/chrome`, expect.anything());
  });

  it("getPreview 把 token 原样（传输编码）透传 /preview", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(preview));
    const client = clientWith(fetchImpl);
    const result = await client.getPreview(TOKEN);
    expect(result).toEqual({ ok: true, data: preview, stale: false });
    expect(fetchImpl).toHaveBeenCalledWith(
      `${BASE}/preview?token=${encodeURIComponent(TOKEN)}`,
      expect.anything(),
    );
  });
});

describe("错误分类（SPEC-001 契约 4 的样式化错误路径）", () => {
  it("404 + 契约错误封装 → not-found，带访客文案", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(errorEnvelope, 404));
    const client = clientWith(fetchImpl);
    const result = await client.getPageDetail("chronicle", "jwc", "missing");
    expect(result).toEqual({
      ok: false,
      reason: "not-found",
      status: 404,
      message: "资源不存在",
    });
  });

  it("404 无契约错误体 → 仍分类为 not-found，无文案", async () => {
    const fetchImpl = vi.fn(
      async () => new Response("<html>gateway</html>", { status: 404 }),
    );
    const client = clientWith(fetchImpl);
    const result = await client.getPageDetail("chronicle", "jwc", "missing");
    expect(result).toEqual({ ok: false, reason: "not-found", status: 404 });
  });

  it("500/503 → server-error，带状态与访客文案", async () => {
    for (const status of [500, 503]) {
      const fetchImpl = vi.fn(async () =>
        jsonResponse(
          { error: { code: "server_error", message: "服务暂时不可用" } },
          status,
        ),
      );
      const client = clientWith(fetchImpl);
      const result = await client.getHome();
      expect(result).toEqual({
        ok: false,
        reason: "server-error",
        status,
        message: "服务暂时不可用",
      });
    }
  });

  it("网络层失败（含超时中止）→ network", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("connect ECONNREFUSED");
    });
    const client = clientWith(fetchImpl);
    const result = await client.getHome();
    expect(result).toEqual({ ok: false, reason: "network" });
  });

  it("2xx 非 JSON → invalid-json", async () => {
    const fetchImpl = vi.fn(
      async () => new Response("<html>", { status: 200 }),
    );
    const client = clientWith(fetchImpl);
    const result = await client.getHome();
    expect(result).toEqual({ ok: false, reason: "invalid-json" });
  });

  it("2xx 不符合契约 schema → schema-violation（服务端日志留痕，访客侧按不可用）", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const bad = { ...chrome } as Record<string, unknown>;
    delete bad.alert;
    const fetchImpl = vi.fn(async () => jsonResponse(bad));
    const client = clientWith(fetchImpl);
    const result = await client.getChrome();
    expect(result).toEqual({ ok: false, reason: "schema-violation" });
    // 两行留痕：契约漂移详情（仅字段路径）+ F08 失败信号（分类计数）
    expect(consoleError).toHaveBeenCalledTimes(2);
    expect(consoleError.mock.calls[1]?.[0]).toContain("getChrome");
    expect(consoleError.mock.calls[1]?.[0]).toContain("schema-violation");
    consoleError.mockRestore();
  });

  it("4xx（如 405）→ unexpected-status", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        { error: { code: "method_not_allowed", message: "方法不允许" } },
        405,
      ),
    );
    const client = clientWith(fetchImpl);
    const result = await client.getChrome();
    expect(result).toEqual({
      ok: false,
      reason: "unexpected-status",
      status: 405,
      message: "方法不允许",
    });
  });
});

describe("新鲜度语义（SPEC-001 契约 4）", () => {
  it("普通内容：失败时回退 ≤5min 内的最近成功版本，带 stale:true", async () => {
    let t = 1_000;
    const fetchImpl = vi.fn(async () => jsonResponse(home));
    const client = clientWith(fetchImpl, () => t);
    expect(await client.getHome()).toMatchObject({ ok: true, stale: false });

    fetchImpl.mockImplementation(async () => {
      throw new Error("boom");
    });
    t = 1_000 + 5 * 60 * 1000; // 恰好 5 分钟：窗口内
    const stale = await client.getHome();
    expect(stale).toMatchObject({ ok: true, stale: true });
    expect(stale.ok && stale.data).toEqual(home);

    t = 1_000 + 5 * 60 * 1000 + 1; // 超窗：必须走失败路径
    const expired = await client.getHome();
    expect(expired).toEqual({ ok: false, reason: "network" });
  });

  it("普通内容按 URL 区分缓存（不同查询参数互不串用）", async () => {
    let t = 0;
    const fetchImpl = vi.fn(async () => jsonResponse(sectionList));
    const client = clientWith(fetchImpl, () => t);
    await client.getSectionList("chronicle", { page: "1" });

    fetchImpl.mockImplementation(async () => {
      throw new Error("boom");
    });
    t = 1000;
    expect(await client.getSectionList("chronicle", { page: "2" })).toEqual({
      ok: false,
      reason: "network",
    });
  });

  it("chrome（永不陈旧面）：成功也不缓存，失败绝不回退", async () => {
    let t = 0;
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = clientWith(fetchImpl, () => t);
    expect(await client.getChrome()).toMatchObject({ ok: true });

    fetchImpl.mockImplementation(async () => {
      throw new Error("boom");
    });
    t = 1000;
    expect(await client.getChrome()).toEqual({ ok: false, reason: "network" });
  });

  it("search（永不陈旧面）：失败必须走样式化错误路径，不出陈旧结果", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(search));
    const client = clientWith(fetchImpl);
    expect(await client.getSearch({ q: "图书馆" })).toMatchObject({ ok: true });

    fetchImpl.mockImplementation(async () => jsonResponse({}, 503));
    const result = await client.getSearch({ q: "图书馆" });
    expect(result).toMatchObject({ ok: false, reason: "server-error" });

    // 网络层失败（含超时中止）同属永不陈旧面：已预热成功版本也绝不回退
    fetchImpl.mockImplementation(async () => {
      throw new Error("abort: timeout");
    });
    expect(await client.getSearch({ q: "图书馆" })).toEqual({
      ok: false,
      reason: "network",
    });
  });

  it("getLinkConfirm 与 getSitemap 分别属于永不陈旧面 / 普通内容", async () => {
    let t = 0;
    const linkConfirmPayload = {
      ok: false,
      target_domain: "example.com",
      notice_text: "提示",
      source: null,
      go_href: null,
      problem: "",
    };
    const sitemapPayload = { entries: [] };
    const fetchImpl = vi.fn(async (url: string | URL) =>
      jsonResponse(
        String(url).includes("/link-confirm")
          ? linkConfirmPayload
          : sitemapPayload,
      ),
    );
    const client = clientWith(fetchImpl, () => t);

    expect(
      await client.getLinkConfirm({ url: "https://example.com/" }),
    ).toMatchObject({
      ok: true,
    });
    expect(await client.getSitemap()).toMatchObject({ ok: true });

    fetchImpl.mockImplementation(async () => {
      throw new Error("boom");
    });
    t = 1000;
    expect(
      await client.getLinkConfirm({ url: "https://example.com/" }),
    ).toEqual({
      ok: false,
      reason: "network",
    });
    expect(await client.getSitemap()).toMatchObject({ ok: true, stale: true });
  });
});

describe("预览票据边界（B01 契约 §3.1/S8）", () => {
  it("票据校验失败（一律 404）→ not-found，页面须渲染样式化 404", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(errorEnvelope, 404));
    const client = clientWith(fetchImpl);
    const result = await client.getPreview(TOKEN);
    expect(result).toMatchObject({ ok: false, reason: "not-found" });
  });

  it("preview 成功响应不进缓存：随后失败不得回退陈旧预览", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(preview));
    const client = clientWith(fetchImpl);
    expect(await client.getPreview(TOKEN)).toMatchObject({ ok: true });

    fetchImpl.mockImplementation(async () => jsonResponse(errorEnvelope, 404));
    expect(await client.getPreview(TOKEN)).toMatchObject({ ok: false });
  });

  it("token 不落入错误对象与服务端日志（含 schema 违规日志路径）", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const badPreview = { ...preview } as Record<string, unknown>;
    delete badPreview.preview; // 制造 schema-violation 日志路径
    const fetchImpl = vi.fn(async () => jsonResponse(badPreview));
    const client = clientWith(fetchImpl);
    const result = await client.getPreview(TOKEN);

    expect(result.ok).toBe(false);
    expect(JSON.stringify(result)).not.toContain(TOKEN);
    const logged = consoleError.mock.calls
      .map((call) => call.join(" "))
      .join("\n");
    expect(logged).not.toContain(TOKEN);
    consoleError.mockRestore();
  });
});

describe("健康信号与失败日志（F08 契约 5：服务器日志 + 进程内计数）", () => {
  it("连续失败进入 health() 快照；≥2 次判 degraded；成功即清零并留恢复日志", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const consoleInfo = vi.spyOn(console, "info").mockImplementation(() => {});
    let fail = true;
    const fetchImpl = vi.fn(async () => {
      if (fail) throw new Error("boom");
      return jsonResponse(home);
    });
    const client = clientWith(fetchImpl);

    await client.getHome();
    await client.getHome();
    let snap = client.health();
    expect(snap.degraded).toBe(true);
    expect(snap.failures.getHome).toMatchObject({
      consecutive: 2,
      lastReason: "network",
    });

    fail = false;
    await client.getHome();
    snap = client.health();
    expect(snap).toEqual({ degraded: false, failures: {} });
    expect(
      consoleInfo.mock.calls.some((c) => String(c[0]).includes("已恢复")),
    ).toBe(true);
    consoleError.mockRestore();
    consoleInfo.mockRestore();
  });

  it("单次失败：degraded 仍为 false（抖动不算降级）", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const fetchImpl = vi.fn(async () => jsonResponse(errorEnvelope, 500));
    const client = clientWith(fetchImpl);
    await client.getChrome();
    const snap = client.health();
    expect(snap.degraded).toBe(false);
    expect(snap.failures.getChrome).toMatchObject({
      consecutive: 1,
      lastReason: "server-error",
    });
    consoleError.mockRestore();
  });

  it("失败日志只含端点名与分类，绝不含 URL、查询值或 token", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const SECRET = "s3cret-query-value";
    const fetchImpl = vi.fn(async () => jsonResponse(errorEnvelope, 500));
    const client = clientWith(fetchImpl);
    await client.getSearch({ q: SECRET });
    const previewClient = clientWith(
      vi.fn(async () => jsonResponse(errorEnvelope, 404)),
    );
    await previewClient.getPreview(TOKEN);
    const logged = consoleError.mock.calls
      .map((call) => call.join(" "))
      .join("\n");
    expect(logged).toContain("getSearch");
    expect(logged).toContain("server-error");
    expect(logged).not.toContain(SECRET);
    expect(logged).not.toContain(TOKEN);
    consoleError.mockRestore();
  });

  it("陈旧回退留痕：回退 ≤5min 版本时服务器日志一行（契约 4）", async () => {
    const consoleInfo = vi.spyOn(console, "info").mockImplementation(() => {});
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    let t = 1_000;
    const fetchImpl = vi.fn(async () => jsonResponse(home));
    const client = clientWith(fetchImpl, () => t);
    await client.getHome();
    fetchImpl.mockImplementation(async () => {
      throw new Error("boom");
    });
    t = 1_000 + 5 * 60 * 1000; // 恰好 5 分钟：窗口内
    const stale = await client.getHome();
    expect(stale).toMatchObject({ ok: true, stale: true });
    expect(
      consoleInfo.mock.calls.some((c) => String(c[0]).includes("陈旧")),
    ).toBe(true);
    consoleError.mockRestore();
    consoleInfo.mockRestore();
  });
});

describe("基址解析 fail closed（PEILIGO_API_BASE_URL；SPEC-001 部署边界）", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  /** 未显式传 baseUrl 的客户端：基址延迟到首次取数从环境解析（每实例缓存一次）。 */
  function envClient(): PeiligoApiClient {
    return createApiClient({
      fetchImpl: vi.fn(async () =>
        jsonResponse(chrome),
      ) as unknown as typeof fetch,
    });
  }

  it("生产（NODE_ENV=production）未设置基址 → 首次取数抛错，绝不静默指向 127.0.0.1", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PEILIGO_API_BASE_URL", "");
    await expect(envClient().getChrome()).rejects.toThrow(
      /PEILIGO_API_BASE_URL/,
    );
  });

  it("生产 + 本地门开启 + 未设置基址 → 仍抛错：NODE_ENV 硬门优先于显式 flag", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PEILIGO_API_ALLOW_LOCAL_DEFAULT", "1");
    await expect(envClient().getChrome()).rejects.toThrow(
      /PEILIGO_API_BASE_URL/,
    );
  });

  it("生产 + 显式配置非法（缺协议）→ 抛错，不回显配置值", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PEILIGO_API_BASE_URL", "api.internal:8000/api/v1");
    const err = await envClient()
      .getChrome()
      .catch((e: unknown) => e as Error);
    expect(err).toBeInstanceOf(Error);
    expect((err as Error).message).toMatch(/配置无效/);
    expect((err as Error).message).not.toContain("api.internal");
  });

  it("非生产 + 未设置基址 + 无显式门 → 抛错：缺省即拒绝（默认安全）", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("PEILIGO_API_BASE_URL", "");
    await expect(envClient().getChrome()).rejects.toThrow(
      /PEILIGO_API_BASE_URL/,
    );
  });

  it("非生产 + PEILIGO_API_ALLOW_LOCAL_DEFAULT=1 + 未设置基址 → 放行本地缺省", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("PEILIGO_API_BASE_URL", "");
    vi.stubEnv("PEILIGO_API_ALLOW_LOCAL_DEFAULT", "1");
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = createApiClient({
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const result = await client.getChrome();
    expect(result).toMatchObject({ ok: true });
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/chrome",
      expect.anything(),
    );
  });

  it('门值必须恰为 "1"（窄门）：其他真值不生效', async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("PEILIGO_API_BASE_URL", "");
    vi.stubEnv("PEILIGO_API_ALLOW_LOCAL_DEFAULT", "true");
    await expect(envClient().getChrome()).rejects.toThrow(
      /PEILIGO_API_BASE_URL/,
    );
  });

  it("本地门开启 + 显式配置非法 → 仍抛错：门只豁免「未设置」，不豁免「写错」", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("PEILIGO_API_BASE_URL", "not a url");
    vi.stubEnv("PEILIGO_API_ALLOW_LOCAL_DEFAULT", "1");
    await expect(envClient().getChrome()).rejects.toThrow(/配置无效/);
  });

  it("显式合法配置在生产照常生效，结尾斜杠被归一化", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PEILIGO_API_BASE_URL", `${BASE}/`);
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = createApiClient({
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const result = await client.getChrome();
    expect(result).toMatchObject({ ok: true });
    expect(fetchImpl).toHaveBeenCalledWith(`${BASE}/chrome`, expect.anything());
  });

  it("显式 options.baseUrl 优先于环境（测试注入路径不受环境干扰）", async () => {
    vi.stubEnv("PEILIGO_API_BASE_URL", "");
    const fetchImpl = vi.fn(async () => jsonResponse(chrome));
    const client = createApiClient({
      baseUrl: BASE,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    await client.getChrome();
    expect(fetchImpl).toHaveBeenCalledWith(`${BASE}/chrome`, expect.anything());
  });
});
