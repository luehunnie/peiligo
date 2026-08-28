# Admin Visual Recovery Contract

## 1. Human Failure Summary

截图 A 的 Dashboard 可用但仍是 Wagtail 原生骨架：鸟标占据侧栏首屏，`peiligo` 仅为普通标题；Pages / Images / Documents 与搜索横向散落，其余区域形成巨量空白，任务优先级不清。截图 B 实际为“新建：部门容器”编辑表单（并非 Pages Explorer 列表），同时印证侧栏、表单与内容区缺少 Peiligo 识别。Explorer 的表格层级问题采用 Human 反馈裁决，必须另补真实 Explorer 截图验收。

## 2. Visual Direction

后台定位为校园内容维护者的高效率工作台，单一视觉签名是贯穿品牌、当前导航、选中行与焦点的“青绿操作轨道”，不做宣传页。`DIRECT_REUSE` 前台青绿、中文系统字体、6/8px 圆角和清晰边框；`ADAPT` 1120px 节奏为后台 1180–1280px 弹性工作区；`NEW` 紧凑数据入口与状态语言；`REJECT` Hero、营销大卡、3+2 展示网格。色板：品牌 `#2F7A6E`、品牌深 `#266359`、浅底 `#E8F1EE`、浅色表面 `#FFFFFF`、浅色画布 `#F5F7FA`、深色画布 `#202322`；最终须映射 Wagtail 主题变量，不硬编码单主题。

## 3. Branding

缩小并降权 Wagtail 鸟标，不让其成为视觉中心；优先以官方 branding 扩展点替换为 Peiligo 简洁字标或“P”标，品牌名统一为大小写规范的 `Peiligo`，禁造中文品牌名。侧栏顶部采用小图标＋清晰字标，青绿只用于识别与操作。后台与前台同源于色彩、字体、圆角和 focus，布局与密度则按生产力工具重构，绝不复制前台 Header/Hero。

## 4. Sidebar

侧栏保持 Wagtail 菜单结构和折叠行为。深色主题用近黑中性底，浅色主题用白色/浅灰底；品牌区高度收紧。当前项用 3px 青绿轨道＋有对比度的底纹＋字重三重提示，hover 仅轻微底色，focus-visible 清楚外框。图标尺寸统一，分组间以 16–20px 留白或细边界区隔；禁止厚阴影、漂浮菜单及重写 Menu。

## 5. Dashboard

主容器最大 1200px 左右并左对齐工作流，避免全宽漂散。标题区只保留“Peiligo 内容管理”与当前用户的克制欢迎语；首行将真实 Pages / Images / Documents 做成紧凑入口条，数字、名称、图标层级清楚但不做三张悬浮大卡。搜索置于其后，宽度受控、label 可见，不能凭大尺寸压过标题。快捷操作只呈现 Wagtail 已提供且用户有权的动作；最近编辑等官方能力有数据才显示。禁止假用户数、阅读量、活跃度、排行或示例内容。

## 6. Page Explorer

不改变 Page Tree、排序、分页、选择与操作菜单行为。层级导航采用明确面包屑/父级标题，表头弱底色且滚动时可辨。每行以“页面标题”为第一层，类型与更新时间为次层，状态为短 badge；行高约 52–60px、列间距稳定。草稿、已发布、需审核等沿用真实状态语义，颜色同时配文字/图形，不能只靠颜色。hover 作用于整行，键盘 focus 包络当前可操作项；操作菜单固定于行尾且可触达。窄屏优先保留标题、状态和菜单，次要 meta 可重排，不能截断树操作。

## 7. Forms / Buttons / Badges

表单 label、帮助文本、必填、错误形成连续垂直层级，控件高度约 40px，内容区不使用截图中夸张的超大标题输入。主按钮使用品牌青绿，次按钮为中性描边，危险按钮保留 Wagtail 危险语义且不得品牌化；disabled 降低强调但文字仍可读。badge 紧凑、轻底、6px 圆角；同一状态全后台同名同色。任何权限不可用动作应由服务端决定是否出现，CSS 不“隐藏代替鉴权”。

## 8. Light / Dark Theme

两主题共享语义 token：canvas、surface、surface-hover、border、text、muted、brand、focus、danger、disabled；通过 Wagtail 现有主题机制映射。Dark 不用纯黑纯白，边框须比表面清楚；Light 保持浅灰画布承托白表面。品牌色分别校准对比度，不覆盖主题切换，不用截图专属选择器；表格、菜单、输入、提示和 badge 均须双主题逐项检查。

## 9. Accessibility

正文与交互文字满足 WCAG AA；focus-visible 至少 2px 且有 offset，当前态、错误、状态均非纯色表达。保持语义标题、label、表头、菜单键盘操作与 Wagtail ARIA。触控目标约 44px；尊重 reduced-motion，过渡仅限 120–160ms 色彩/边框，不做位移动画。缩放 200% 与 375px 下无关键操作丢失或横向页面滚动。

## 10. Allowed Wagtail Customization Surface

实现优先级：官方 branding 定制、admin hooks、admin CSS 注入及官方允许的少量模板覆盖；其次少量稳定 override；再其次经核验的稳定 CSS selector。所有具体 API 名称均须由 GLM 对照 Wagtail 7.4.2 实际代码/官方文档验证，不凭记忆断言。禁止复制整个 Admin 或大量 Core 模板；以未来 7.4.x 小版本升级可低成本维护为准。

## 11. Do Not

不得改变权限、Page Tree、业务模型或服务端行为；不得显示用户无权的危险操作，也不得暗示可绕过 permission。不得大面积渐变、玻璃拟态、Neon、无意义大圆角、巨型留白、巨型 Hero、过度阴影或动画堆砌；不得为“高级感”牺牲密度、把每块都做成漂浮卡片、引入不必要 icon library 或大量 JS。不得 fork 大量 Wagtail Core 模板。

## 12. Screenshot Acceptance Checklist

- [ ] Dashboard 首屏清楚呈现 Peiligo、真实数据入口、受控搜索与允许的快捷任务，无假数据和巨量空白。
- [ ] 鸟标不再支配视觉；侧栏当前态具青绿轨道、底纹和字重，hover/focus 明确。
- [ ] 补拍真实 Pages Explorer：标题、类型、更新时间、状态、层级与行尾菜单层级清楚，树行为不变。
- [ ] 补拍截图 B 所示编辑表单：标题输入、label、帮助、错误和按钮密度合理。
- [ ] Light / Dark 各覆盖 Dashboard、Explorer、表单；切换后无硬编码失真。
- [ ] 1440px 内容宽度稳定；375px 与 200% 缩放无关键动作丢失。
- [ ] 键盘遍历顺序正确、focus 可见，状态/当前态不只依赖颜色。
- [ ] 无禁止风格、无权限泄露、无 Core 大面积复制。
