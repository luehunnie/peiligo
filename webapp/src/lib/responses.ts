// SSR 错误边界响应（SPEC-001-F06，自 F05 index.astro 上提共享）。
// v1 口径：服务端异常由 Django 500 页承载、未知路径由 404 页承载
// （templates/500.html / templates/404.html）。F08 起分工：
//   - 本文件的「最小自包含页」保留给 chrome 不可用＝全站取数边界
//     （页头/页脚无从渲染，v1 500 页同构：零模板变量、零内联样式、
//     不泄露环境细节）与 404 页的无壳回退分支（v1 404 页壳数据在
//     新架构下来自 chrome，不可得时降级为无壳最小 404）；
//   - chrome 可用时的样式化 404 页与站内失败态由
//     components/system/NotFoundPage.astro 与 FailureState.astro 承担。
// 导出 HTML 常量：NotFoundPage 的无壳回退分支复用同一份标记（单一出处）。
export const INTERNAL_ERROR_HTML = `<!DOCTYPE html>
<html lang="zh-hans" dir="ltr">
    <head>
        <meta charset="utf-8" />
        <title>服务暂时不可用</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body>
        <h1>服务暂时不可用</h1>
        <p>抱歉，Peiligo 出现了临时故障，请稍后重试。</p>
        <p><a href="/">返回首页</a></p>
    </body>
</html>`;

export const NOT_FOUND_HTML = `<!DOCTYPE html>
<html lang="zh-hans" dir="ltr">
    <head>
        <meta charset="utf-8" />
        <title>页面不存在</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body>
        <h1>页面不存在</h1>
        <p>你访问的地址不存在或已移动。</p>
        <p><a href="/">返回首页</a></p>
    </body>
</html>`;

function htmlResponse(status: number, html: string): Response {
  return new Response(html, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

/** v1 templates/500.html 逐字等价（取数失败/契约违约等不可用边界）。 */
export function unavailableResponse(): Response {
  return htmlResponse(500, INTERNAL_ERROR_HTML);
}
