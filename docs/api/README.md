# Headless API 契约（SPEC-001 · ADR-0008）

## 来源与权威

- **权威契约自 SPEC-001 最终集成起回归本仓库**：`docs/api/openapi.json`
  （机器契约，v1.0.0 冻结）即唯一权威载体；本 README 是人的契约。
- `webapp/docs/api/openapi.json` 是 F04 消费侧的运行时校验载体（ajv 直接
  对照校验，校验零复制）——与权威载体的**规范化 SHA-256 相同**
  （`ae3e9811…706`，递归按键排序后紧凑序列化），两侧守卫测试
  （`tests/test_api_contract.py` 与 `webapp/src/tests/unit/contract-provenance.test.ts`）
  任何一侧漂移即红。收敛（去重）属 14 天稳定窗口后的清理决策，须 Human 批准。
- 端点总览：`/api/v1/` 下 9 个只读 GET（chrome / home / sections /
  sections-archive / search / pages / link-confirm / sitemap / preview）；
  全部响应 `Cache-Control: no-store`。
- 实现＝根目录 `api/` Django app（E1–E9 只读视图/序列化/路由/预览出口，
  **零模型零迁移**，红线：不加模型、不改内容模型/权限/Wagtail Admin/现有
  v1 行为）。行为等价基线：peiligo/main = 48fd5d6（SPEC-001 冻结）。
- 设计决策见 `docs/adr/0008-headless-api-contract.md`；部署拓扑与路由表见
  `docs/adr/0009-staging-topology.md` 与 `deploy/Caddyfile` 头注。

## 安全边界（冻结）

- `/api/v1/` **不公开路由**：仅经 Compose 内网供 Astro SSR 取数（
  `PEILIGO_API_BASE_URL=http://web:8000/api/v1`），浏览器零直接调用；
  Caddy 对 `/api/v1/*` 恒 404（ADR-0008 §S1，两个开关态下皆然）。
- 无 CORS、无写入、无新公开认证面；预览票据（E9）＝`django.core.signing`
  ＋既有 SECRET_KEY（专用 salt），有效期 ≤60s，绑定（会话、用户、页面），
  兑换全程零写入，失败一律 404（防预言机）。
- 契约演进：加字段/加端点＝非破坏；删字段/改语义/改错误码＝breaking，
  须先走 Human 评审（R3+），禁止静默变更。机器契约与人契约两载体同一提交更新。
