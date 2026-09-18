// SPEC-001-F08 /healthz 路由测试：探针语义冻结——恒 200（进程活着即健康，
// 上游故障不得触发编排层重启循环：恢复靠下一请求直连，契约 4/5）、no-store、
// body 附带前端自有上游健康快照（纯分类计数）。
import { describe, expect, it, vi } from "vitest";
import { GET } from "../../pages/healthz";

vi.mock("../../services/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../services/api")>();
  return {
    ...actual,
    apiHealthSnapshot: () => ({
      degraded: true,
      failures: {
        getHome: { consecutive: 3, lastReason: "network", lastAt: 42 },
      },
    }),
  };
});

describe("GET /healthz", () => {
  it("上游降级时仍 200：进程健康与上游健康解耦", async () => {
    const res = GET();
    expect(res.status).toBe(200);
    expect(res.headers.get("cache-control")).toBe("no-store");
    expect(res.headers.get("content-type")).toContain("application/json");
    const body = (await res.json()) as {
      status: string;
      upstream: { degraded: boolean };
    };
    expect(body.status).toBe("ok");
    expect(body.upstream.degraded).toBe(true);
  });
});
