// 源码体量/职责审计（SPEC-001-F05 P1 维护性守护）。仅告警，恒退出 0——
// 绝不作为 CI 硬门（SPEC-001 明令「never a rigid CI failure」）；用途是
// 给评审与重构一个一眼可见的信号：一个文件接近 WARN_LINES 时，检查它是否
// 已混入第二职责（如页面文件开始内联某个区块的完整标记/样式，或一个组件
// 同时承担取数＋多区块组装）。职责边界比行数本身重要：大而内聚（如整组
// 板块海报 SVG）可接受，需在文件头注释说明其单一职责。
// 范围：src/ 生产前端源码。排除：测试（src/tests/）、夹具、生成契约
// （src/schemas/，由 docs/api 契约生成）、声明文件；配置/证据/文档不在
// src/ 下，天然不涉及。
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("../src/", import.meta.url);
const WARN_LINES = 400;
const EXCLUDED_DIRS = new Set(["tests", "schemas"]);
const SOURCE_EXTS = new Set([".astro", ".ts", ".css", ".mjs"]);

/** 收集 src/ 下生产源文件（排除 tests/schemas/.d.ts）。 */
function collect(dir, out = []) {
  for (const name of readdirSync(dir).sort()) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      if (!EXCLUDED_DIRS.has(name)) collect(path, out);
    } else if (
      SOURCE_EXTS.has(name.slice(name.lastIndexOf("."))) &&
      !name.endsWith(".d.ts")
    ) {
      out.push(path);
    }
  }
  return out;
}

const offenders = [];
for (const path of collect(ROOT.pathname.replace(/\/$/, ""))) {
  const lines = readFileSync(path, "utf8").split("\n").length;
  if (lines > WARN_LINES) offenders.push({ path, lines });
}

if (offenders.length === 0) {
  console.info(`source-size audit: OK（${WARN_LINES} 行以下）`);
} else {
  console.warn(
    `source-size audit: ${offenders.length} 个文件超过 ${WARN_LINES} 行（仅告警）：`,
  );
  for (const { path, lines } of offenders) {
    console.warn(`  ${lines} 行  ${path}`);
  }
  console.warn(
    "检查该文件是否混入第二职责；大而内聚需在文件头说明（见脚本头注释）。",
  );
}
