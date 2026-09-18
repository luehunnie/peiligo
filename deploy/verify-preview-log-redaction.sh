#!/usr/bin/env bash
# SPEC-001 · 预览票据不落 Caddy 访问日志——一次性集成栈哨兵实测。
#
# 证明什么：deploy/Caddyfile 的 filter 编码器（内置，caddy:2 自带）在真实
# 四容器栈（db/web/frontend/scheduler/caddy，与生产同构）下——
#   1) 携唯一哨兵票据请求 /preview/?token=<哨兵> 后，caddy 日志零哨兵
#      （URI 查询参数已删、Referer 票据值已抹成 REDACTED）；
#   2) 普通日志健在：非票据查询参数原样、路径/状态/耗时字段照常；
#   3) 顺带核验：Caddyfile 在容器内 validate 通过；/api/v1/* 公开面恒
#      404；https 响应 HSTS 在位。
# 怎么跑（仓库根）：deploy/verify-preview-log-redaction.sh
# 前提：Docker daemon 在跑；本机 80/443 空闲；deploy/.env 就绪
#       （.env.example 填法见 docs/guides/LOCAL_RUN_AND_VALIDATION_GUIDE.md）。
# 用后即弃：独立 compose 项目名 peiligo-logproof（独立网络/卷），退出时
# `down -v` 全部拆除，不触碰任何常驻栈。

set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose -p peiligo-logproof --env-file deploy/.env -f deploy/docker-compose.yml)
SENTINEL="SENTINEL-logproof-$(date +%s)-$RANDOM"
BASE="https://localhost"

fail() { echo "FAIL: $*" >&2; exit 1; }

cleanup() {
  echo "== 拆除一次性栈（down -v，网络/卷全清）=="
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

# ── 前提 ────────────────────────────────────────────────────────────────
docker info >/dev/null 2>&1 || fail "Docker daemon 不可用"
[ -f deploy/.env ] || fail "缺 deploy/.env（先从 .env.example 复制填写）"
for port in 80 443; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "本机 $port 端口被占用——先停常驻栈或改用空闲环境"
  fi
done

# ── 起栈（构建→启动；entrypoint 自动等库＋迁移，caddy 等 web/frontend healthy）──
echo "== 构建并启动一次性集成栈（哨兵：${SENTINEL}）=="
"${COMPOSE[@]}" up -d --build || fail "compose up 失败"

echo "== 等待就绪（web migrate＋caddy 出证书，上限 300s）=="
ready=""
for _ in $(seq 1 150); do
  if curl -kfsS "${BASE}/healthz/" 2>/dev/null | grep -q '"ok"'; then
    ready=1; break
  fi
  sleep 2
done
[ -n "$ready" ] || { "${COMPOSE[@]}" logs caddy web >&2 || true; fail "300s 内未就绪"; }

# ── 配置在容器内 validate（caddy:2 本体裁决）────────────────────────────
"${COMPOSE[@]}" exec -T caddy caddy validate --config /etc/caddy/Caddyfile 2>/dev/null \
  | grep -q "Valid configuration" || fail "caddy validate 未通过"

# ── 哨兵请求（经 Caddy 的真实 https 面）────────────────────────────────
code_preview=$(curl -ksS -o /dev/null -w '%{http_code}' \
  -H "Referer: ${BASE}/preview/?token=${SENTINEL}" \
  "${BASE}/preview/?token=${SENTINEL}&keep=ctl")
code_search=$(curl -ksS -o /dev/null -w '%{http_code}' "${BASE}/search/?q=logproof-ctl-query")
code_api=$(curl -ksS -o /dev/null -w '%{http_code}' "${BASE}/api/v1/chrome")
hsts=$(curl -ksS -D - -o /dev/null "${BASE}/" | grep -i '^strict-transport-security:' || true)
echo "preview(垃圾票)=${code_preview} search=${code_search} api/v1=${code_api}"
echo "${hsts}"
[ "${code_preview}" = "404" ] || fail "/preview/ 垃圾票应 404（失败闭合），得 ${code_preview}"
[ "${code_search}" = "200" ] || fail "/search/ 应 200，得 ${code_search}"
[ "${code_api}" = "404" ] || fail "/api/v1/* 公开面应恒 404，得 ${code_api}"
[ -n "${hsts}" ] || fail "https 响应缺 Strict-Transport-Security（Caddy 头块被动过）"

# ── 日志裁决 ────────────────────────────────────────────────────────────
logs=$("${COMPOSE[@]}" logs caddy 2>&1)

assert_absent() { if echo "${logs}" | grep -q "${1}"; then fail "caddy 日志出现哨兵/票据：${1}"; fi; }
assert_present() { if ! echo "${logs}" | grep -q "${1}"; then fail "caddy 日志缺：${1}"; fi; }

assert_absent "${SENTINEL}"                       # 票据值零出现（URI 与 Referer 双面已抹）
assert_absent 'token=SENTINEL'                  # 双保险：即便哨兵换值形态也不落
assert_present 'token=REDACTED'                 # Referer 票据值被抹成 REDACTED（过滤器确实在作用）
assert_present '"uri":"/preview/?keep=ctl"'     # token 参数已删；路径与其余参数原样
assert_present '"uri":"/search/?q=logproof-ctl-query"'  # 普通查询参数照常记录
assert_present '"status":404'                   # 状态照常
assert_present '"duration":'                    # 耗时照常

echo "== 哨兵请求的访问日志行（证据）=="
echo "${logs}" | grep '"uri":"/preview/?keep=ctl"' | tail -1

echo "PASS：哨兵票据零落 caddy 日志（URI 删参＋Referer 抹值）；路径/普通查询/状态/耗时照常；"
echo "      caddy validate 通过；/api/v1/* 公开面 404；HSTS 在位。一次性栈已拆除。"
