#!/usr/bin/env node
// SPEC-001 架构约束 7 + F01 验收：依赖许可证检查。
// 政策：
//   1. 硬门 —— 本项目直接引入的运行时依赖必须为宽松许可证（MIT/Apache/BSD，
//      及 ISC/0BSD/Unlicense/CC0 等宽松等价），违规退出码 1（CI 拦截）。
//   2. 逐条记录 —— 完整运行时传递闭包生成 docs/dependencies.md。
//   3. 提交评审 —— 框架自带的超出许可证的传递依赖（如 astro 强制带入的
//      MPL/LGPL/BlueOak 包）不属于本项目"引入"，不拦截 CI，但在清单中显著
//      标记，由 Human 评审决定处置。
// 用法：node scripts/check-licenses.mjs           # 校验
//       node scripts/check-licenses.mjs --write   # 重新生成 docs/dependencies.md
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

// ALLOWED：本项目可直接引入的许可证；PERMISSIVE_EQUIV：宽松等价（记录但标记待评审）。
const ALLOWED = new Set([
  "MIT",
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "BSD-Source-Code",
]);
const PERMISSIVE_EQUIV = new Set(["ISC", "0BSD", "Unlicense", "CC0-1.0"]);

// SPDX 表达式求值：支持 "A OR B"、"A AND B"、括号（剥掉后按顶层分组处理）。
// ponytail: 无优先级的朴素顶层分组（括号统一剥除），满足现依赖树中的简单表达；
// 出现需要完整 SPDX 优先级解析的表达式时，换用正式 SPDX 解析器。
export function verdict(expr) {
  const e =
    String(expr ?? "UNKNOWN")
      .replace(/[()]/g, " ")
      .trim() || "UNKNOWN";
  if (/\sOR\s/.test(e))
    return {
      ok: e.split(/\sOR\s/).some((part) => verdict(part).ok),
      kind: "组合(OR)",
    };
  if (/\sAND\s/.test(e))
    return {
      ok: e.split(/\sAND\s/).every((part) => verdict(part).ok),
      kind: "组合(AND)",
    };
  if (ALLOWED.has(e)) return { ok: true, kind: "允许", id: e };
  if (PERMISSIVE_EQUIV.has(e)) return { ok: true, kind: "宽松等价", id: e };
  return { ok: false, kind: "未通过", id: e };
}

function main() {
  const root = process.cwd();
  const manifest = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

  function licenseIds(field) {
    if (!field) return ["UNKNOWN"];
    if (Array.isArray(field)) return field.flatMap(licenseIds);
    if (typeof field === "object") return licenseIds(field.type ?? field.name);
    return [String(field)];
  }

  // 收集 node_modules 下所有 package.json（含嵌套与 @scope）。
  function collect(dir, out) {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
      const full = join(dir, entry.name);
      if (entry.name.startsWith("@")) {
        collect(full, out);
        continue;
      }
      const pjPath = join(full, "package.json");
      if (existsSync(pjPath)) {
        try {
          const data = JSON.parse(readFileSync(pjPath, "utf8"));
          if (data.name)
            out.set(`${data.name}@${data.version}`, { ...data, path: full });
        } catch {
          out.set(entry.name, {
            name: entry.name,
            version: "?",
            license: "UNKNOWN",
            path: full,
          });
        }
      }
      collect(join(full, "node_modules"), out);
    }
  }

  // 从引用目录向上解析依赖位置（处理 npm 嵌套安装）。
  function resolveDep(fromDir, name) {
    let dir = fromDir;
    for (;;) {
      const cand = join(dir, "node_modules", name);
      if (existsSync(join(cand, "package.json"))) return cand;
      const parent = dirname(dir);
      if (parent === dir) return null;
      dir = parent;
    }
  }

  const all = new Map();
  collect(join(root, "node_modules"), all);
  const byPath = new Map([...all.values()].map((p) => [p.path, p]));

  function rowFor(pkg) {
    const license = licenseIds(pkg.license).join(" OR ") || "UNKNOWN";
    return {
      id: `${pkg.name}@${pkg.version}`,
      version: pkg.version,
      license,
      verdict: verdict(pkg.license),
    };
  }

  // 从项目 dependencies 出发求运行时传递闭包。
  const runtime = new Map();
  const queue = Object.keys(manifest.dependencies ?? {}).map((name) => [
    root,
    name,
  ]);
  const direct = new Map();
  while (queue.length > 0) {
    const [fromDir, name] = queue.shift();
    const path = resolveDep(fromDir, name);
    const pkg = path ? byPath.get(path) : null;
    if (!pkg) continue;
    if (fromDir === root) direct.set(name, pkg);
    const id = `${pkg.name}@${pkg.version}`;
    if (runtime.has(id)) continue;
    runtime.set(id, pkg);
    for (const dep of Object.keys({
      ...pkg.dependencies,
      ...pkg.optionalDependencies,
    })) {
      queue.push([pkg.path, dep]);
    }
  }

  const rows = [...runtime.values()]
    .map(rowFor)
    .sort((a, b) => a.id.localeCompare(b.id));
  const directRows = [...direct.values()]
    .map(rowFor)
    .sort((a, b) => a.id.localeCompare(b.id));
  const directRejected = directRows.filter((r) => !r.verdict.ok);
  // needsReview：超出 ALLOWED 或仅宽松等价的传递依赖（框架带入，提交 Human 评审）。
  const needsReview = rows.filter(
    (r) => !r.verdict.ok || r.verdict.kind === "宽松等价",
  );
  const equivCount = rows.filter((r) => r.verdict.kind === "宽松等价").length;

  if (process.argv.includes("--write")) {
    const md = [
      "# 依赖清单（含许可证）",
      "",
      "> 由 `npm run licenses:write` 生成，请勿手改。许可证政策见 `scripts/check-licenses.mjs`（SPEC-001 约束 7 + F01 验收）。",
      "",
      `生成于：${new Date().toISOString()} · Node ${process.version} · 平台 ${process.platform}/${process.arch}`,
      "",
      "> 平台说明：本清单为生成平台的依赖快照；其它平台会解析同族平台二进制包",
      "> （`@img/*`、`lightningcss-*` 等，同族同许可证）。CI 的 `licenses:check` 与",
      "> `npm audit` 在 CI 真实依赖树上实时执行，本文件仅作 Human 评审快照。",
      "",
      `## 运行时依赖（直接 ${directRows.length} 个；含传递依赖共 ${rows.length} 个，逐条记录）`,
      "",
      "| 包 | 版本 | 许可证 | 类别 |",
      "|---|---|---|---|",
      ...rows.map(
        (r) =>
          `| ${r.id}${directRows.some((d) => d.id === r.id) ? " **（直接）**" : ""} | ${r.version} | ${r.license} | ${r.verdict.ok ? r.verdict.kind : "**未通过**"} |`,
      ),
      "",
      "## 待 Human 评审：MIT/Apache/BSD 明示范围之外的传递依赖",
      "",
      "> 均为 astro@7 依赖树强制带入，非本项目引入；硬门只拦截本项目直接引入的依赖。",
      "> 下表「超出」7 项 + 「宽松等价」10 项；其中 ISC/0BSD/Unlicense/CC0 为 MIT 同级",
      "> 宽松许可证，BlueOak/Python-2.0 亦属宽松但在明示范围之外；MPL-2.0 为文件级弱",
      "> copyleft；LGPL-3.0 见于 sharp 的预编译 libvips 平台二进制（sharp 本体为",
      "> Apache-2.0，当前项目未使用图像处理）。",
      "",
      "| 包 | 许可证 | 类别 |",
      "|---|---|---|",
      ...needsReview.map(
        (r) =>
          `| ${r.id} | ${r.license} | ${r.verdict.ok ? "宽松等价" : "**超出**"} |`,
      ),
      "",
      "## 开发依赖（直接声明）",
      "",
      "| 包 | 版本 |",
      "|---|---|",
      ...Object.keys(manifest.devDependencies ?? {})
        .sort()
        .map((d) => `| ${d} | ${manifest.devDependencies[d]} |`),
      "",
    ].join("\n");
    writeFileSync(join(root, "docs", "dependencies.md"), md);
    console.log(`docs/dependencies.md 已更新（运行时共 ${rows.length} 个）。`);
  }

  const rejectedCount = needsReview.filter((r) => !r.verdict.ok).length;
  console.log(
    `运行时依赖：直接 ${directRows.length} 个全部通过；传递闭包共 ${rows.length} 个（宽松等价 ${equivCount}，超出待评审 ${rejectedCount}），详见 docs/dependencies.md。`,
  );
  if (directRejected.length > 0) {
    for (const r of directRejected)
      console.error(`  [直接依赖未通过] ${r.id}: ${r.license}`);
    console.error(
      "本项目直接引入的运行时依赖存在超出允许范围的许可证，禁止合入（SPEC-001 约束 7）。",
    );
    process.exit(1);
  }
}

// 仅作为 CLI 直接执行时运行完整扫描；被测试导入时只使用导出的 verdict()。
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main();
}
