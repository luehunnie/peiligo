# M2 Visual Recovery Contract

## 1. Human Failure Summary

M2 功能骨架通过，但截图所示首页仍是“标题＋五个朴素链接框＋大段页脚”的工程占位页：第一屏没有品牌焦点和主要任务，搜索入口未进入首页，五板块只有名称而无定位，内容层级、页面节奏和交互反馈均不足；页脚相对稀薄主体过重。其根因不是单个颜色不好看，而是未形成统一 token、容器、标题、卡片与状态语言。截图结论也与当前模板/CSS互证：白底、60rem 容器、近乎无全局排版尺度，Header 仅文字横排，板块卡片仅边框和粗体。

恢复方向不是另做一套潮流 UI，而是把旧 Peiligo 已验证的安静、可信、面向学生的信息工具气质迁入 Django 模板。视觉签名冻结为：**青绿色品牌字标＋清晰的首页搜索工作台＋五板块信息卡组**。品牌色只承担识别和操作，不做装饰性大色块。

## 2. Old Peiligo Reuse Matrix

| 旧设计元素 | 裁决 | 新 Django 落点 | 理由 |
|---|---|---|---|
| tokens：色彩、1120px、8px 间距、6/8px 圆角、克制阴影 | DIRECT_REUSE | `static/css/peiligo.css` 的 `:root` | 已成体系，适合信息站 |
| 中文系统字体栈与标题尺度 | DIRECT_REUSE | 全局 typography | 无字体下载依赖，中文稳定 |
| Header 的字标、64px 高度、当前态、hover/focus | ADAPT | `templates/base.html` | 保留视觉骨架，导航改为冻结的首页＋五板块＋搜索 |
| 首页 Hero、搜索框、板块卡片结构 | ADAPT | `home_page.html` | 改用真实五板块页和服务端搜索；删除原型话术 |
| 内容卡片的 meta→标题→摘要→来源 | ADAPT | 后续 Django include / Section 列表 | 结构可复用，M2 不造内容 |
| 虚线空态卡与引导动作 | DIRECT_REUSE | `section_page.html` | 真实表达零内容且避免空白页 |
| Footer 的轻量白色表面、细分隔、次级文字 | ADAPT | `base.html` | 改写为 IA 固定的关于、反馈、版权说明 |
| Vue、RouterLink、SPA 请求四态、内存搜索 | REJECT | 无 | 与 SSR/服务端搜索架构冲突 |
| 旧导航、投稿/独立关于、原型警告、旧板块名 | REJECT | 无 | 违反冻结 IA 或已过时 |

## 3. Visual Direction

- 颜色：页面底 `#f5f7fa`，表面 `#fff`，主文 `#1f2a37`，次文 `#64748b`，品牌 `#2f7a6e`，hover `#266359`，品牌浅底 `#e8f1ee`，边框 `#e2e8f0`。
- Typography：沿用旧中文系统栈；正文 16/1.7，小字 14，H1 32/1.3/700，H2 24/1.3/600，H3 20/1.3/600；不引入网络字体。
- Spacing：8、12、16、24、40、56px；区块间距以 40/56px 为主，禁止随意值泛滥。
- Radius：控件 6px，卡片 8px。Container 最大 1120px，桌面横向 24px，移动端 16px。
- 背景与表面：浅灰页面底承托白色 Header、卡片和 Footer；不用渐变、纹理或玻璃拟态。
- Border/shadow：默认 1px 边框；仅内容卡可用旧站 subtle shadow，hover 以品牌边框为主，不浮起跳动。
- Header：64px 桌面单行；左侧品牌字标，右侧固定导航，搜索作为清晰入口；当前态须颜色＋字重/底纹双提示。窄屏允许换行或横向可用布局，不隐藏核心入口。
- Footer：白底细上边框，关于为短说明，反馈邮箱为明确动作，版权/口径用小号次文；降低高度，不重复五板块长文。
- Card：整卡可点击，标题、简短定位/摘要和方向提示形成层级；统一内边距 24px，hover/focus 同一视觉语法。

## 4. Homepage Contract

### NOW

1. 顶部使用共享 Header。
2. Hero 为首屏主命题：eyebrow“校园信息与资源入口”、H1 使用真实站名/页面标题、一句面向学生的克制说明；旁边或紧随其下放首页搜索工作台，表单 GET 到现有 `/search/`，标签可见，placeholder 具体，按钮为唯一主操作。
3. 五板块区紧随 Hero。每张卡使用冻结名称与 IA §2 的一句话定位，整卡链接真实 SectionPage；桌面建议 3＋2 的非强行等宽排布，平板 2 列，手机 1 列。不得使用无语义编号或假统计。
4. M3 内容区不展示空标题、骨架屏或“即将上线”假模块；可在板块卡组下放一条非业务数据的站点说明/反馈引导，但不得冒充内容。页面依靠 Hero、搜索、完整卡组和轻量 Footer 达到完整感。

### DEFER_TO_M3

紧急提示、FeaturedItem 推荐/置顶、最新有效通知、近期活动、正式内容卡及对应 meta 均等待真实模型与查询；到 M3 后严格按 IA §7 顺序插入，数据为空则整区隐藏，不用示例数据补位。

## 5. Section Page Contract

五页共享同一骨架：共享 Header → 面包屑 → 板块页头（H1＋IA §2 一句话定位）→ 内容区域 → Footer。M2 零内容时展示居中的白色虚线空态卡：“本板块暂无内容”，补充一句行动说明，并提供其他四板块及返回首页的次级链接；不得渲染空列表或部门容器。未来列表复用旧站内容卡结构，但不在本轮预建假卡。

## 6. Responsive / Accessibility

在 1120/768/600px 附近自然重排；手机不横向溢出，搜索输入与按钮可堆叠，导航全部可达。正文最小 14px，触控目标约 44px；保留 skip link、语义标题、可见 label、`aria-current`。focus-visible 使用 2px 品牌描边并有 offset；颜色不是当前态的唯一信号；尊重 `prefers-reduced-motion`，过渡限 150ms 色彩变化。

## 7. Implementation Scope

GLM 仅可修改：`templates/base.html`（Header/Footer 结构）、`home/templates/home/home_page.html`、`home/templates/home/section_page.html`、必要的 `templates/includes/` 展示片段、`static/css/peiligo.css`；仅在搜索表单或移动导航确有需要时调整现有少量渐进增强 JS。可补视觉截图级测试，但不得扩展业务模型。

## 8. Do Not

不得回归 Vue/SPA/Vue Router/Element Plus；不得创建或模拟 M3 模型、查询、推荐位和内容；不得改五板块、页面树、URL、权限或 Page/Snippet 语义；不得写假通知、假活动、假数量；不得加入大面积渐变、玻璃拟态、霓虹、漂浮图标等廉价 AI 模板感；不得过度动画、大量 JS、新构建链或无必要依赖。

## 9. Visual Acceptance Checklist

- [ ] 1440px 截图中内容居中且最大宽度约 1120px，背景/表面分层清晰。
- [ ] 首屏能立即识别站名、站点用途和“搜索”主任务。
- [ ] Header 为完整统一组件，七类导航无遗漏，当前态一眼可辨。
- [ ] 首页不再是孤立 H1 加五个链接框，Hero、搜索、卡组层级连续。
- [ ] 五张卡均含正确名称和真实定位，整卡可点击，顺序符合 IA。
- [ ] 卡片边框、圆角、内距、hover/focus 完全一致。
- [ ] 页面只使用冻结 token，无突兀新色和随意间距。
- [ ] 无 M3 数据时没有空业务区标题、假卡、假数字或骨架屏。
- [ ] Footer 明显弱于主体，关于、反馈邮箱、说明层级清楚且不过高。
- [ ] 五个 Section 页截图共享同一页头和空态骨架。
- [ ] 空态说明真实，并可前往其他板块或首页。
- [ ] 375px 截图无横向滚动；导航、搜索、卡片自然重排。
- [ ] 键盘截图可见清楚焦点，当前态不只靠颜色。
- [ ] 页面无渐变/玻璃拟态堆砌、过度阴影或无意义动画。
