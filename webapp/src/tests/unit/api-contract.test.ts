// SPEC-001 F04 契约测试（fixture 驱动）：拦截 docs/api/openapi.json 与客户端
// schema/校验层之间的契约漂移。契约更新流程见 docs/api/README.md。
import { describe, expect, it } from "vitest";
import openapiDoc from "../../../docs/api/openapi.json";
import {
  API_OPERATIONS,
  DETAIL_DISCRIMINATOR_VALUES,
  OPENAPI_VERSION,
  OPERATIONS,
  validateErrorEnvelope,
  validateResponse,
  type ApiOperationId,
} from "../../schemas/api-contract";
import chrome from "../fixtures/api/chrome.json";
import errorEnvelope from "../fixtures/api/error.json";
import home from "../fixtures/api/home.json";
import linkConfirm from "../fixtures/api/link-confirm.json";
import pageDetailNotice from "../fixtures/api/page-detail-notice.json";
import pageDetailSoftware from "../fixtures/api/page-detail-software.json";
import preview from "../fixtures/api/preview.json";
import search from "../fixtures/api/search.json";
import sectionArchive from "../fixtures/api/section-archive.json";
import sectionList from "../fixtures/api/section-list.json";
import sitemap from "../fixtures/api/sitemap.json";

const CONTRACT = openapiDoc as unknown as {
  openapi: string;
  components: {
    schemas: Record<
      string,
      {
        allOf?: unknown[];
        required?: string[];
        properties?: Record<string, unknown>;
      }
    >;
  };
  paths: Record<string, Record<string, { operationId?: string } | undefined>>;
};

/** 每个端点至少一个成功响应 fixture（形状与 openapi.json 一致）。 */
const FIXTURES: ReadonlyArray<readonly [ApiOperationId, unknown]> = [
  ["getChrome", chrome],
  ["getHome", home],
  ["getSectionList", sectionList],
  ["getSectionArchive", sectionArchive],
  ["getSearch", search],
  ["getPageDetail", pageDetailNotice],
  ["getPageDetail", pageDetailSoftware],
  ["getLinkConfirm", linkConfirm],
  ["getSitemap", sitemap],
  ["getPreview", preview],
];

describe("机器契约结构（openapi.json）", () => {
  it("是 OpenAPI 3.1", () => {
    expect(CONTRACT.openapi).toBe(OPENAPI_VERSION);
  });

  it("端点清单恰好为 F04 已知的 9 个 operationId，全部 GET——契约增删端点时本测试失败，需按 docs/api/README.md 流程同步客户端", () => {
    const contractOperations = new Set<string>();
    for (const item of Object.values(CONTRACT.paths)) {
      for (const method of ["get", "post", "put", "patch", "delete"] as const) {
        const operationId = item[method]?.operationId;
        if (operationId) {
          expect(
            contractOperations.has(operationId),
            `重复 operationId：${operationId}`,
          ).toBe(false);
          contractOperations.add(operationId);
          if (method !== "get") {
            throw new Error(
              `契约出现非 GET 方法 ${method}（${operationId}）：只读契约被破坏`,
            );
          }
        }
      }
    }
    expect(contractOperations).toEqual(new Set<string>(API_OPERATIONS));
    expect(API_OPERATIONS).toHaveLength(9);
  });

  it("错误封装 schema 保持 {error:{code,message}} 四码枚举", () => {
    const errorSchema = CONTRACT.components.schemas.Error;
    expect(errorSchema.required).toEqual(["error"]);
    const inner = errorSchema.properties?.error as {
      required?: string[];
      properties?: { code?: { enum?: string[] } };
    };
    expect(inner.required).toEqual(["code", "message"]);
    expect(inner.properties?.code?.enum).toEqual([
      "not_found",
      "method_not_allowed",
      "server_error",
      "unavailable",
    ]);
  });

  it("每个 F04 端点都有可解析的 200 JSON schema（OPERATIONS 索引完整构建）", () => {
    for (const operationId of API_OPERATIONS) {
      expect(OPERATIONS[operationId].path).toMatch(/^\/[a-z-]/);
    }
  });

  it("严格 exactly-one 前提：五个 *Detail 分支均 required type 且 const 互异——oneOf 恰一分支语义的结构保证；契约同步若回退上游 const 钉死修复，本测试即红", () => {
    const seen = new Set<string>();
    for (const name of [
      "NoticeDetail",
      "ArticleDetail",
      "MaterialDetail",
      "SoftwareToolDetail",
      "GuideDetail",
    ]) {
      const schema = CONTRACT.components.schemas[name];
      expect(schema, `契约缺少 ${name}`).toBeTruthy();
      // 分支形如 allOf:[{$ref: PageDetailBase},{type:object, required:[type,…], properties:{type:{const}}}]
      const members: unknown[] = Array.isArray(schema.allOf)
        ? schema.allOf
        : [schema];
      const pinning = members.find(
        (
          member,
        ): member is {
          required: string[];
          properties?: { type?: { const?: string } };
        } =>
          member !== null &&
          typeof member === "object" &&
          Array.isArray((member as { required?: unknown }).required) &&
          ((member as { required?: unknown[] }).required as unknown[]).includes(
            "type",
          ),
      );
      expect(pinning, `${name} 缺少钉死 type 的 allOf 成员`).toBeTruthy();
      const typeSchema = pinning?.properties?.type;
      expect(typeSchema?.const, `${name}.type 缺 const 判别值`).toBeTruthy();
      expect(seen.has(typeSchema!.const!), `${name} const 重复`).toBe(false);
      seen.add(typeSchema!.const!);
    }
    expect([...seen].sort()).toEqual([...DETAIL_DISCRIMINATOR_VALUES].sort());
  });
});

describe("成功响应 fixture 校验（对机器契约零复制）", () => {
  it.each(FIXTURES)("%s fixture 符合契约 schema", (operationId, fixture) => {
    expect(validateResponse(operationId, fixture).ok).toBe(true);
  });

  it("错误封装 fixture 符合错误 schema", () => {
    expect(validateErrorEnvelope(errorEnvelope).ok).toBe(true);
  });
});

describe("契约约束真实生效（负面 fixture 必须被拒绝）", () => {
  it("chrome 缺少 alert 字段 → 拒绝", () => {
    const bad: Record<string, unknown> = { ...chrome };
    delete bad.alert;
    expect(validateResponse("getChrome", bad).ok).toBe(false);
  });

  it("chrome nav_sections 少于 5 项 → 拒绝", () => {
    const bad = structuredClone(chrome) as typeof chrome;
    bad.nav_sections = bad.nav_sections.slice(0, 4);
    expect(validateResponse("getChrome", bad).ok).toBe(false);
  });

  it("search chips 不足 6 项 → 拒绝", () => {
    const bad = structuredClone(search) as typeof search;
    bad.chips = bad.chips.slice(0, 5);
    expect(validateResponse("getSearch", bad).ok).toBe(false);
  });

  it("pagination per_page ≠ 20 → 拒绝（const 约束）", () => {
    const bad = structuredClone(sectionList) as typeof sectionList;
    bad.pagination.per_page = 50;
    expect(validateResponse("getSectionList", bad).ok).toBe(false);
  });

  it("Block 判别联合出现未知 type → 拒绝", () => {
    const bad = structuredClone(pageDetailNotice) as typeof pageDetailNotice;
    bad.body = [
      { type: "mystery", value: {} } as unknown as (typeof bad.body)[number],
    ];
    expect(validateResponse("getPageDetail", bad).ok).toBe(false);
  });

  it("严格 oneOf 判别值驱动分支：notice 载荷改标 article → 经 ArticleDetail 分支通过（分支随判别值切换）", () => {
    // notice/article 字段集同构：载荷合法性完全由 type const 决定——修复前双匹配、
    // 修复后恰一分支，判别值即分支选择器
    const switched = structuredClone(
      pageDetailNotice,
    ) as typeof pageDetailNotice;
    switched.type = "article";
    expect(validateResponse("getPageDetail", switched).ok).toBe(true);
  });

  it("严格 oneOf 零分支匹配 → 拒绝：notice 载荷改标 guide（缺 guide 专属必填字段）", () => {
    const bad = structuredClone(pageDetailNotice) as typeof pageDetailNotice;
    bad.type = "guide";
    expect(validateResponse("getPageDetail", bad).ok).toBe(false);
  });

  it("preview 响应缺少顶层 preview:true → 拒绝", () => {
    const bad = structuredClone(preview) as typeof preview;
    delete (bad as Record<string, unknown>).preview;
    expect(validateResponse("getPreview", bad).ok).toBe(false);
  });

  it("错误体缺 message → 拒绝", () => {
    expect(validateErrorEnvelope({ error: { code: "server_error" } }).ok).toBe(
      false,
    );
  });
});
