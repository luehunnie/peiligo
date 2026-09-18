// SPEC-001 F04：机器契约（docs/api/openapi.json）的加载与响应校验。
// 契约是唯一来源：端点索引、成功/错误 schema 均直接取自该文件做运行时校验，
// 校验层零复制——契约一变，校验即变；刻意改动由契约测试（api-contract.test.ts）拦截。
import Ajv2020 from "ajv/dist/2020";
import type { ValidateFunction } from "ajv";
import openapiJson from "../../docs/api/openapi.json";

export const OPENAPI_VERSION = "3.1.0" as const;

/** F04 客户端覆盖的端点（operationId），与 docs/api/openapi.json 的 operations 一一对应。 */
export const API_OPERATIONS = [
  "getChrome",
  "getHome",
  "getSectionList",
  "getSectionArchive",
  "getSearch",
  "getPageDetail",
  "getLinkConfirm",
  "getSitemap",
  "getPreview",
] as const;

export type ApiOperationId = (typeof API_OPERATIONS)[number];

interface JsonSchema {
  type?: string | string[];
  required?: string[];
  properties?: Record<string, unknown>;
  enum?: unknown[];
  [key: string]: unknown;
}

interface OpenapiDoc {
  openapi: string;
  components: { schemas: Record<string, JsonSchema> };
  paths: Record<
    string,
    Record<
      string,
      | {
          operationId?: string;
          responses?: Record<
            string,
            { content?: Record<string, { schema?: object }> }
          >;
        }
      | undefined
    >
  >;
}

const doc = openapiJson as unknown as OpenapiDoc;

export interface OperationInfo {
  /** 契约中的路径模板，如 /sections/{slug} */
  path: string;
  responseSchema: object;
}

function indexOperations(): Record<ApiOperationId, OperationInfo> {
  const index = {} as Record<ApiOperationId, OperationInfo>;
  const missing = new Set<string>(API_OPERATIONS);
  for (const [path, item] of Object.entries(doc.paths)) {
    const operation = item.get;
    const operationId = operation?.operationId;
    if (!operationId || !missing.has(operationId)) continue;
    const schema =
      operation.responses?.["200"]?.content?.["application/json"]?.schema;
    if (!schema) {
      throw new Error(
        `[peiligo-api] 契约漂移：${operationId} 缺少 200 application/json schema`,
      );
    }
    index[operationId as ApiOperationId] = { path, responseSchema: schema };
    missing.delete(operationId);
  }
  if (missing.size > 0) {
    throw new Error(
      `[peiligo-api] 契约漂移：openapi.json 缺少端点 ${[...missing].join(", ")}`,
    );
  }
  return index;
}

export const OPERATIONS = indexOperations();

// validateFormats 关闭：date-time 等格式由 Django 侧保证，客户端只校验数据形状；
// strict 关闭：根 schema 挂载 components 供 $ref 解析，且契约含 OpenAPI 扩展关键字（discriminator）。
const ajv = new Ajv2020({ strict: false, validateFormats: false });

/** E6/E9 判别联合按 OpenAPI oneOf 严格语义（恰好一个分支）编译：上游 B02 已以既有
 * type 字段的 const 钉死五个 *Detail 分支（peiligo@2f7fa021，无新字段、载荷零变化），
 * 无需任何运行时放宽。严格前提（五分支 type 必有且 const 互异）由契约测试
 * （api-contract.test.ts「严格 exactly-one 前提」）持续把守——未来契约同步若回退该
 * 修复，测试即红，禁止再引入 anyOf 放宽。
 */
export const DETAIL_DISCRIMINATOR_VALUES = [
  "notice",
  "article",
  "material",
  "software",
  "guide",
] as const;

/** 以 openapi.json 全量 components 为 $ref 解析根编译单个 schema。
 * 根须为 {components:{schemas}, ...}——契约内 $ref 均为 "#/components/schemas/X"；
 * 每次编译交给 ajv 一份全新对象图（structuredClone），杜绝 ajv 实例级缓存跨根共享
 * 同一内层对象带来的状态串扰。 */
function compile(schema: object): ValidateFunction {
  return ajv.compile(
    structuredClone({
      components: { schemas: doc.components.schemas },
      ...schema,
    }),
  );
}

export interface ContractVerdict {
  ok: boolean;
  /** ajv 错误摘要（仅字段路径与原因，不含数据值） */
  message?: string;
}

const responseValidators = new Map<ApiOperationId, ValidateFunction>();

/** 校验端点 200 响应体是否符合机器契约（运行时契约漂移防线）。 */
export function validateResponse(
  operationId: ApiOperationId,
  body: unknown,
): ContractVerdict {
  let validate = responseValidators.get(operationId);
  if (!validate) {
    validate = compile(OPERATIONS[operationId].responseSchema);
    responseValidators.set(operationId, validate);
  }
  if (validate(body)) return { ok: true };
  return { ok: false, message: ajv.errorsText(validate.errors) };
}

let errorEnvelopeValidator: ValidateFunction | undefined;

/** 校验非 2xx 统一错误封装 {error:{code,message}}（§2.4）。 */
export function validateErrorEnvelope(body: unknown): ContractVerdict {
  errorEnvelopeValidator ??= compile(doc.components.schemas.Error);
  if (errorEnvelopeValidator(body)) return { ok: true };
  return { ok: false, message: ajv.errorsText(errorEnvelopeValidator.errors) };
}
