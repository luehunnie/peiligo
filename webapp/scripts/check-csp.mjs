// SPEC-001 契约 3（安全 parity）构建产物自检：严格 CSP 兼容。
// 在 astro build 之后运行（npm run check:csp），对 dist/ 逐文件断言：
//   - 无内联 <style> / 无 style 属性 / 无无 src 的 <script>
//   - <script src> 与所有 src|href 均为同源相对路径（禁止第三方 origin）
//   - CSS 无 url() / @import / @font-face（无网络字体、无外部资源引用）
// 本阶段前端零运行时 JS；引入脚本后本检查仍按上述规则拦截回归。
import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";

const DIST = "dist";

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) files.push(...walk(p));
    else files.push(p);
  }
  return files;
}

const problems = [];
let checked = 0;

for (const file of walk(DIST)) {
  const rel = relative(DIST, file);
  const ext = extname(file);
  if (ext !== ".html" && ext !== ".css") continue;
  checked += 1;
  const text = readFileSync(file, "utf8");

  if (ext === ".html") {
    for (const m of text.matchAll(/<script\b([^>]*)>/gi)) {
      const attrs = m[1];
      const src = attrs.match(/\bsrc="([^"]*)"/i);
      if (!src) problems.push(`${rel}: 内联 <script>（无 src）`);
      else if (src[1].startsWith("//") || !src[1].startsWith("/"))
        problems.push(`${rel}: 非同源脚本 ${src[1]}`);
    }
    if (/<style[\s>]/i.test(text)) problems.push(`${rel}: 内联 <style>`);
    if (/\sstyle\s*=/i.test(text)) problems.push(`${rel}: 内联 style 属性`);
    for (const m of text.matchAll(/\b(?:src|href)="([^"]*)"/gi)) {
      if (/^(https?:)?\/\//i.test(m[1]))
        problems.push(`${rel}: 跨源引用 ${m[1]}`);
    }
  }

  if (ext === ".css") {
    if (/url\(/i.test(text)) problems.push(`${rel}: CSS url() 引用`);
    if (/@import\b/i.test(text)) problems.push(`${rel}: CSS @import`);
    if (/@font-face\b/i.test(text))
      problems.push(`${rel}: @font-face（禁止网络字体）`);
  }
}

if (problems.length > 0) {
  console.error("check:csp 未通过：");
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(
  `check:csp 通过：${checked} 个 HTML/CSS 产物无内联样式/脚本、无跨源引用。`,
);
