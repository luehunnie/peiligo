// e2e 专用 mock B02 API（Playwright webServer，端口 4319）。
//
// 为什么需要独立进程：F05 为请求时 SSR，/home 与 /chrome 由 Astro 服务端
// fetch——page.route 拦不到服务端请求，只能以真实 HTTP 服务替代 B02。
// 职责最小面：
//   - GET /api/v1/chrome|home|sections/{slug}|sections/{slug}/archive|
//     search|pages/{section}/{dept}/{slug}|link-confirm|sitemap：从内存态
//     返回（初始 = src/tests/fixtures/api/ 下的契约夹具），no-store；每端点
//     维护请求计数（供测试断言「每请求直连」）。详情按 slug 路由到对应
//     夹具（library-hours/zotero/spring-sports/calculus-review/
//     library-guide），未知 slug 与未知 section → 契约 404 封装；
//   - POST /__control：测试控制面 { endpoint: <名称|"all">,
//     mode: "ok"|"fail"|"invalid"|"notfound", payload? } —— ok+payload 覆写
//     返回体（验证发布在下一次请求可见）、ok 无 payload 恢复夹具、fail 返回
//     契约错误封装 500、invalid 返回不合契约 JSON（触发客户端
//     schema-violation 分类）、notfound 返回契约 404 封装（合法 slug 但资源
//     缺失，真实 B02 同应答）；"all" = chrome+home（F05 语义不变）；
//   - POST /__control/reset：恢复夹具、解除故障、清零计数（各测试自清理）；
//   - GET /__requests：计数读数；
//   - GET /media/*：确定性 SVG 占位图（fixture 引用的图片路径不必真实存在）；
//   - GET /healthz：就绪探测（webServer url）。
// 不做鉴权/缓存语义模拟——被测对象是前端的取数与渲染，不是 B02 本身。
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const PORT = Number(process.env.MOCK_API_PORT ?? 4319);
// 缺省回环仅够本机 e2e；compose.mock.yaml 容器内经 MOCK_API_HOST=0.0.0.0 放开。
const HOST = process.env.MOCK_API_HOST ?? "127.0.0.1";
const FIXTURES_DIR = fileURLToPath(
  new URL("../fixtures/api/", import.meta.url),
);

const SECTION_SLUGS = ["chronicle", "events", "materials", "software", "guide"];

/** 详情夹具按内容 slug 路由（URL 段 section/dept 不参与路由——被测对象
 *  是前端渲染，段合法性由前端 404 逻辑与契约客户端分类覆盖）。 */
const PAGE_DETAIL_FILES = {
  "library-hours": "page-detail-notice.json",
  "spring-sports": "page-detail-article.json",
  "calculus-review": "page-detail-material.json",
  zotero: "page-detail-software.json",
  "library-guide": "page-detail-guide.json",
};

async function loadFixture(file) {
  return JSON.parse(await readFile(`${FIXTURES_DIR}${file}`, "utf8"));
}

/** /search 无参数（解析后无有效维度）＝表单态：契约冻结「不查全量，
 *  entries 恒空」（openapi /search 描述）。mock 与 B02 同口径，供断言
 *  表单态渲染；chips 恒 6 项（契约 minItems/maxItems=6）。 */
const searchFixture = await loadFixture("search.json");
const SEARCH_FORM_STATE = {
  q: "",
  entries: [],
  pagination: {
    total: 0,
    page: 1,
    page_count: 1,
    per_page: 20,
    has_next: false,
    has_previous: false,
  },
  filters: {
    q: "",
    section: null,
    dept: null,
    type: null,
    tag: null,
    active: false,
    conditions: [],
  },
  chips: searchFixture.chips,
};

/** 启动时读入夹具；此后所有恢复/覆写均为同步内存操作，无竞态。
 *  详情端点按内容 slug 各持一份状态（控制面覆写作用于全部 slug）。 */
const fixtures = {
  chrome: await loadFixture("chrome.json"),
  home: await loadFixture("home.json"),
  "section-list": await loadFixture("section-list.json"),
  "section-archive": await loadFixture("section-archive.json"),
  search: searchFixture,
  "link-confirm": await loadFixture("link-confirm.json"),
  sitemap: await loadFixture("sitemap.json"),
};
const detailFixtures = Object.fromEntries(
  await Promise.all(
    Object.entries(PAGE_DETAIL_FILES).map(async ([slug, file]) => [
      slug,
      await loadFixture(file),
    ]),
  ),
);

/** 内存态：endpoint → { mode: "ok"|"fail"|"invalid", data }。 */
const state = Object.fromEntries(
  Object.entries(fixtures).map(([name, data]) => [name, { mode: "ok", data }]),
);
state["page-detail"] = Object.fromEntries(
  Object.entries(detailFixtures).map(([slug, data]) => [
    slug,
    { mode: "ok", data },
  ]),
);
const counters = Object.fromEntries(
  [...Object.keys(fixtures), "page-detail"].map((name) => [name, 0]),
);

function reset() {
  for (const [name, data] of Object.entries(fixtures)) {
    state[name] = { mode: "ok", data };
    counters[name] = 0;
  }
  state["page-detail"] = Object.fromEntries(
    Object.entries(detailFixtures).map(([slug, data]) => [
      slug,
      { mode: "ok", data },
    ]),
  );
  counters["page-detail"] = 0;
}

function sendJson(res, status, body) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    // 契约 F1：API 全响应 no-store——mock 与真实 B02 同口径
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(body));
}

function sendErrorEnvelope(res, status, code, message) {
  sendJson(res, status, { error: { code, message } });
}

/** /media/* 确定性占位图：以路径文本哈希生成可区分的纯色 SVG。 */
function mediaSvg(pathname) {
  let hash = 0;
  for (const ch of pathname) hash = (hash * 31 + ch.codePointAt(0)) >>> 0;
  const hue = hash % 360;
  const label =
    pathname
      .split("/")
      .pop()
      ?.replace(/\.[a-z]+$/i, "") ?? "media";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 260">
  <rect width="400" height="260" fill="hsl(${hue} 38% 78%)"/>
  <circle cx="330" cy="52" r="36" fill="hsl(${hue} 55% 42%)"/>
  <text x="24" y="232" font-family="sans-serif" font-size="20" fill="hsl(${hue} 55% 30%)">${label}</text>
</svg>`;
}

const server = createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://${HOST}:${PORT}`);
  const apiPath = url.pathname.replace(/\/+$/, "");

  if (req.method === "GET" && apiPath === "/healthz") {
    res.writeHead(200, { "content-type": "text/plain" });
    res.end("ok");
    return;
  }

  if (req.method === "GET" && apiPath === "/__requests") {
    sendJson(res, 200, { ...counters });
    return;
  }

  if (req.method === "POST" && apiPath === "/__control/reset") {
    reset();
    sendJson(res, 200, { reset: true });
    return;
  }

  if (req.method === "POST" && apiPath === "/__control") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        const { endpoint, mode, payload } = JSON.parse(body);
        const names = endpoint === "all" ? ["chrome", "home"] : [endpoint];
        for (const name of names) {
          if (name === "page-detail") {
            // 覆写作用于全部内容 slug（控制面粒度＝端点，非单页）
            for (const slug of Object.keys(state["page-detail"])) {
              state["page-detail"][slug] =
                mode === "ok"
                  ? { mode, data: payload ?? detailFixtures[slug] }
                  : { mode, data: null };
            }
            continue;
          }
          if (!(name in state)) throw new Error(`未知 endpoint: ${name}`);
          if (mode === "ok") {
            state[name] = { mode, data: payload ?? fixtures[name] };
          } else if (
            mode === "fail" ||
            mode === "invalid" ||
            mode === "notfound"
          ) {
            state[name] = { mode, data: null };
          } else {
            throw new Error(`未知 mode: ${mode}`);
          }
        }
        sendJson(res, 200, { ok: true });
      } catch (error) {
        sendJson(res, 400, { ok: false, error: String(error) });
      }
    });
    return;
  }

  // ---- 契约端点 ----
  if (req.method === "GET" && apiPath.startsWith("/api/v1/")) {
    const rest = apiPath.slice("/api/v1/".length);
    let name = null;
    if (rest === "chrome" || rest === "home" || rest === "search") {
      name = rest;
    } else if (rest === "link-confirm" || rest === "sitemap") {
      name = rest;
    } else if (rest.startsWith("sections/")) {
      const [, section, maybeArchive] = rest.split("/");
      if (!SECTION_SLUGS.includes(section)) {
        sendErrorEnvelope(res, 404, "not_found", "未知板块");
        return;
      }
      name = maybeArchive === "archive" ? "section-archive" : "section-list";
    } else if (rest.startsWith("pages/")) {
      const slug = rest.split("/").at(-1);
      if (!slug || !(slug in state["page-detail"])) {
        sendErrorEnvelope(res, 404, "not_found", "页面不存在或不可见");
        return;
      }
      counters["page-detail"] += 1;
      const entry = state["page-detail"][slug];
      if (entry.mode === "fail") {
        sendErrorEnvelope(res, 500, "server_error", "模拟后端暂时不可用");
        return;
      }
      if (entry.mode === "invalid") {
        sendJson(res, 200, { unexpected: "shape" });
        return;
      }
      sendJson(res, 200, structuredClone(entry.data));
      return;
    }
    if (!name) {
      sendErrorEnvelope(res, 404, "not_found", "未知路径");
      return;
    }
    counters[name] += 1;
    const entry = state[name];
    if (entry.mode === "fail") {
      sendErrorEnvelope(res, 500, "server_error", "模拟后端暂时不可用");
      return;
    }
    if (entry.mode === "notfound") {
      // 合法 slug 但资源缺失（如板块页未建）＝真实 B02 的契约 404 应答
      sendErrorEnvelope(res, 404, "not_found", "板块不存在或未发布");
      return;
    }
    if (entry.mode === "invalid") {
      sendJson(res, 200, { unexpected: "shape" });
      return;
    }
    // /search 无查询串＝表单态（B02 契约冻结行为；控制面覆写只作用于
    // 带参请求，与「无有效维度不查全量」语义不冲突）
    if (name === "search" && url.search === "") {
      sendJson(res, 200, SEARCH_FORM_STATE);
      return;
    }
    sendJson(res, 200, structuredClone(entry.data));
    return;
  }

  if (req.method === "GET" && url.pathname.startsWith("/media/")) {
    res.writeHead(200, {
      "content-type": "image/svg+xml; charset=utf-8",
      "cache-control": "no-store",
    });
    res.end(mediaSvg(url.pathname));
    return;
  }

  sendErrorEnvelope(res, 404, "not_found", "未知路径");
});

server.listen(PORT, HOST, () => {
  console.log(`[mock-api] listening on http://${HOST}:${PORT}`);
});
