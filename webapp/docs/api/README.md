# Headless API 契约（SPEC-001 · F04 消费侧）

## 来源与权威

- 本目录的 `openapi.json` 是机器契约的**快照副本**，复制自 peiligo 仓库的
  `docs/api/openapi.json`（SPEC-001-B01 / ADR-0008，来源 PR：luehunnie/peiligo#18）。
- 权威契约始终在 peiligo 仓库：`docs/api/README.md`（人的契约）＋ `docs/api/openapi.json`
  （机器契约，两载体同一提交更新）。本仓库副本只服务 F04 的类型与运行时校验。
- 端点总览：`/api/v1/` 下 9 个只读 GET（chrome / home / sections / sections-archive /
  search / pages / link-confirm / sitemap / preview）；全部响应 `Cache-Control: no-store`。
- 本次快照含上游 **F04 联合修复**（peiligo@2f7fa021）：E6/E9 五个 `*Detail` 分支以既有
  `type` 字段 const 钉死判别值，`oneOf` 恢复 OpenAPI 严格「恰好一个分支」语义（见
  §严格 exactly-one 语义）。快照逐字节溯源与漂移守卫见 §快照溯源与漂移守卫。

## 快照溯源与漂移守卫

<!-- contract-snapshot
source-repo: luehunnie/peiligo (worktree 分支 luehunnie/spec-001-b02-headless-api)
source-commit: 7df6dc05d7de81fedf52456a796b833250433d8d
content-commit: 2f7fa021afd6777c611c86e3b78622b776a3b732
copied: 2026-09-15
carrier-sha256: 4c453c27eaa43844ec2a85e526425ca08027d0f3c33ca7f1fc158be40ef56430
snapshot-sha256: ae3e98115479d19c75aa968797cb4903ede262ad36070056843aa706b4124706
-->

- `source-commit`：复制时 peiligo 分支 HEAD（含 7df6dc0 的治理收尾：契约
  version `1.0.0-proposed` → `1.0.0` 冻结、ADR-0008 转 Accepted；schema/路径零变化）；
  `content-commit`：本快照语义内容（含 F04 联合修复）落入 peiligo 的提交（上游
  docs/api/README.md §8 明确记载修复版载体唯一出处＝2f7fa02）；`copied`：复制日期。
- `carrier-sha256`：上游 openapi.json 原始字节的 SHA-256（上游为单行紧凑 JSON 风格）。
- `snapshot-sha256`：**规范化形式**（递归按键排序后 JSON.stringify）的 SHA-256。上游
  载体与本仓库副本仅排版差异（本副本经 Prettier 归一化以过 format 门），规范化后二者
  相等（已验证），故该值同时把守本仓库副本与上游 pinned 提交的语义一致。
- **漂移守卫**：`src/tests/unit/contract-provenance.test.ts` 断言本区块字段完整，且
  `docs/api/openapi.json` 的规范化 SHA-256 等于 `snapshot-sha256`——任何手改契约文件
  或再同步后未刷新溯源，单元测试即红。
- **更新命令**（契约演进时，步骤 1 的具体化）：

  ```sh
  # 1. 从 peiligo 仓库复制最新载体覆盖本副本（换入新的 source-commit）
  cp <peiligo-worktree>/docs/api/openapi.json docs/api/openapi.json
  npx prettier --write docs/api/openapi.json
  # 2. 重算两个 SHA-256 并更新上方溯源区块
  shasum -a 256 <peiligo-worktree>/docs/api/openapi.json   # → carrier-sha256
  node -e 'const fs=require("fs"),c=require("crypto");const f=v=>Array.isArray(v)?v.map(f):v&&typeof v==="object"?Object.fromEntries(Object.keys(v).sort().map(k=>[k,f(v[k])])):v;console.log(c.createHash("sha256").update(JSON.stringify(f(JSON.parse(fs.readFileSync("docs/api/openapi.json","utf8"))))).digest("hex"))'  # → snapshot-sha256
  # 3. 按下方「契约演进时的更新流程」同步类型/fixture/客户端，npm test 全绿后同一提交
  ```

- **移除路径**：SPEC-001 最终合并、两仓库归一后，契约载体随主仓库唯一化，本区块、
  `contract-provenance.test.ts` 与上方更新命令一并删除（PR 删除说明引用本行）。

## F04 消费方式

| 层         | 位置                                  | 说明                                                                                                      |
| ---------- | ------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 类型层     | `src/schemas/api-schema.ts`           | 手写 TS 类型，逐字段镜像 openapi.json                                                                     |
| 运行时校验 | `src/schemas/api-contract.ts`         | ajv（JSON Schema 2020-12）直接对 `openapi.json` 校验每个 200 响应与错误封装——校验零复制，契约一变校验即变 |
| 服务层     | `src/services/api.ts`                 | 类型化客户端：新鲜度语义、错误分类、预览票据边界（文件头注释有完整条款）                                  |
| 契约测试   | `src/tests/unit/api-contract.test.ts` | 端点清单 / 错误码 / fixture 驱动校验；契约漂移时失败                                                      |
| 行为测试   | `src/tests/unit/api-client.test.ts`   | 失败路径、≤5min 陈旧回退 vs 永不陈旧面、no-store、token 边界                                              |

环境变量（基址 **fail closed**，见 `src/services/api.ts` 头注）：

- `PEILIGO_API_BASE_URL`（含 `/api/v1` 前缀）：必须显式设置为合法 http(s) URL——
  未设置时取数即抛错，绝不静默回退；生产 Astro 容器（`NODE_ENV=production`）不可能
  被静默指到 `127.0.0.1`。Compose 内由部署注入内网服务地址（B03 拓扑 ADR 定稿）。
  配置存在但非法（非 http/https URL）时同样抛错（门只豁免「未设置」，不豁免「写错」）。
- `PEILIGO_API_ALLOW_LOCAL_DEFAULT=1`：窄门，仅**非生产**环境下放行本地测试缺省
  `http://127.0.0.1:8000/api/v1`（供 `npm run dev`/本地联调）；生产设置无效
  （`NODE_ENV` 硬门优先）。文档化于本节与 `api.ts` 头注，误配时错误信息亦指回本文。

本模块仅限服务端 import；基址解析延迟到首次取数，import 期不读环境。

## 契约演进时的更新流程

1. 从 peiligo 仓库复制最新 `docs/api/openapi.json` 覆盖本目录副本（具体命令与溯源
   区块刷新见「快照溯源与漂移守卫」§；契约 §7：加字段/加端点
   ＝非破坏；删字段/改语义/改错误码＝breaking → 必须先走 R3+ 升级，禁止静默变更）。
2. 契约测试与客户端校验会即时暴露差异；按提示同步 `src/schemas/api-schema.ts`、
   `src/tests/fixtures/api/` fixture。
3. 若端点增删：同步 `src/schemas/api-contract.ts` 的 `API_OPERATIONS` 与
   `src/services/api.ts` 的客户端方法。
4. `npm test && npm run check` 全绿后与第 1 步同一提交提交。

## 严格 exactly-one 语义（上游 F04 联合修复已落地）

E6/E9 的判别联合（`PageDetail` / `PreviewDetail`）在 `openapi.json` 中以 `oneOf` 表达。
此前 notice/article 两分支字段集完全相同且 `type` 未按分支钉死，严格「恰好一个分支」
语义对真实响应必然双匹配误报——该缺口已上报并由上游修复（peiligo@2f7fa021，控制器
裁定、Human 批准）：五个 `*Detail` schema 以既有 `type` 字段 const 钉死判别值（无新
字段、载荷零变化）。本仓库消费侧已**删除运行时 oneOf→anyOf 放宽**，按 OpenAPI 严格
oneOf 语义编译；其结构前提（五分支 required `type` 且 const 互异）由
`api-contract.test.ts`「严格 exactly-one 前提」持续把守，上游回退即测试红。

## 类型生成说明

F04 评估过 `openapi-typescript` 从 `openapi.json` 自动生成类型：其 peer 依赖目前仅声明
`typescript ^5.x`，与本仓库锁定的 `typescript 6.0.3` 冲突（需 `--legacy-peer-deps` 安装，
工作流不简单，故弃用，采用手写类型＋运行时 ajv 校验的组合）。待其支持 TS 6 后可切换：

```sh
npm i -D -E openapi-typescript
npx openapi-typescript docs/api/openapi.json -o src/schemas/api-types.gen.ts
```

切换后以生成文件替代 `api-schema.ts` 中的对应类型，ajv 运行时校验不受影响；
移除路径＝卸载 devDependency＋删除生成文件。
