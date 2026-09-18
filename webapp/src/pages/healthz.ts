// 前端进程健康探测（SPEC-001-F08 契约 5「healthcheck 友好」；F11 部署
// 拓扑的 compose 探针将指向本端点）。语义冻结：
//   - 恒 200：进程活着即健康。上游 API 故障不改变状态码——前端容器在
//     取数边界故障期间必须保持「健康」，恢复（契约 4/5：下一请求直连
//     即 live 内容）无需重启；若探测随上游失败，编排层重启只会清空
//     ≤5min 陈旧回退窗口、拖慢恢复。
//   - body 附带 apiHealthSnapshot()（进程内连续失败计数）：给运维与
//     日志之外的第二个前端自有健康信号；纯分类计数，无 URL/查询值/token。
//   - no-store：健康读数永不缓存。
// 不标注 APIRoute：本端点零依赖（不读 context），零参签名让单测可直接 GET()。
import { apiHealthSnapshot } from "../services/api";

export const GET = () => {
  const body = JSON.stringify({ status: "ok", upstream: apiHealthSnapshot() });
  return new Response(body, {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
};
