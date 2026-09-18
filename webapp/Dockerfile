# SPEC-001-F11a：Astro SSR 生产容器（@astrojs/node standalone，入口
# dist/server/entry.mjs）。staging/同源部署拓扑属 F11（blocked by B02）——
# 本镜像只定义应用容器本体，不部署任何环境。环境契约见 docs/docker.md。
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
# standalone entry 外部化部分运行时依赖（如 devalue）——剥掉 devDeps 随镜像带走。
RUN npm prune --omit=dev

FROM node:22-alpine
WORKDIR /app
# HOST 必须绑 0.0.0.0：容器内回环不可被 compose/编排层探针访问。
# PEILIGO_API_BASE_URL 生产必显式注入（api.ts fail-closed，无缺省回退）。
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=4321
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
# 健康语义冻结于 src/pages/healthz.ts：进程活着即 200（上游 API 故障不翻转，
# 编排层不得据此重启——见 F08 契约注释）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1
USER node
EXPOSE 4321
CMD ["node", "./dist/server/entry.mjs"]
