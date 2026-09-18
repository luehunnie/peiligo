// SPEC-001 F04 契约快照溯源与漂移守卫：docs/api/openapi.json 是 peiligo 仓库
// 机器契约的快照副本（两临时仓库并存期间）。本测试把守：
//   1. 溯源区块（docs/api/README.md 内 contract-snapshot 注释）字段完整、格式合法；
//   2. 快照文件未被手改——其规范化形式（递归按键排序）SHA-256 必须等于区块记录的
//      snapshot-sha256（该值同时等于上游 pinned 提交的语义内容，仅排版差异）。
// 任何契约再同步都必须走 README「快照溯源与漂移守卫」§的更新命令并刷新该区块，
// 否则本测试即红。最终合并（两仓库归一）后随该区块一并删除（移除路径见同节）。
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const repoRoot = new URL("../../../", import.meta.url);
const readme = readFileSync(new URL("docs/api/README.md", repoRoot), "utf8");

/** 递归按键排序后 JSON.stringify——与 README 更新命令中的 node 单行脚本一致。 */
function canonicalForm(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalForm);
  if (value !== null && typeof value === "object") {
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      sorted[key] = canonicalForm((value as Record<string, unknown>)[key]);
    }
    return sorted;
  }
  return value;
}

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

/** 解析 README 的 contract-snapshot 区块；字段缺失/格式非法一律在这里即红。 */
function parseSnapshotBlock(): Record<string, string> {
  const match = readme.match(/<!--\s*contract-snapshot\n([\s\S]*?)-->/);
  expect(
    match,
    "docs/api/README.md 缺少 contract-snapshot 溯源区块",
  ).toBeTruthy();
  const fields: Record<string, string> = {};
  for (const line of match![1]!.split("\n")) {
    const kv = line.match(/^([a-z0-9-]+):\s*(.+)$/);
    if (kv) fields[kv[1]!] = kv[2]!.trim();
  }
  for (const key of [
    "source-repo",
    "source-commit",
    "content-commit",
    "copied",
    "carrier-sha256",
    "snapshot-sha256",
  ]) {
    expect(fields[key], `溯源区块缺少字段 ${key}`).toBeTruthy();
  }
  for (const key of ["source-commit", "content-commit"]) {
    expect(fields[key], `${key} 须为 40 位十六进制 git 提交 SHA`).toMatch(
      /^[0-9a-f]{40}$/,
    );
  }
  for (const key of ["carrier-sha256", "snapshot-sha256"]) {
    expect(fields[key], `${key} 须为 64 位十六进制 SHA-256`).toMatch(
      /^[0-9a-f]{64}$/,
    );
  }
  expect(fields.copied, `copied 须为 YYYY-MM-DD 日期`).toMatch(
    /^\d{4}-\d{2}-\d{2}$/,
  );
  return fields;
}

describe("契约快照溯源与漂移守卫（docs/api/README.md contract-snapshot）", () => {
  it("溯源区块字段完整且格式合法", () => {
    expect(parseSnapshotBlock()).toBeTruthy();
  });

  it("快照未漂移：openapi.json 规范化 SHA-256 === snapshot-sha256（手改或未按更新命令再同步即红）", () => {
    const { "snapshot-sha256": recorded } = parseSnapshotBlock();
    const raw = readFileSync(
      new URL("docs/api/openapi.json", repoRoot),
      "utf8",
    );
    const actual = sha256(JSON.stringify(canonicalForm(JSON.parse(raw))));
    expect(actual).toBe(recorded);
  });
});
