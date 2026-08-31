# AVR② Admin 视觉恢复 Evidence

截图环境：`127.0.0.1:8001`（AVR② 专用 dev server，`peiligo_restart_dev` 库），
Wagtail 7.4.2 + `feat/admin-visual-recovery` 分支工作区，playwright-cli 实拍。
浅/深主题均经 **Wagtail 内置开关**（`/admin/account/` → Theme preferences →
Admin theme）切换，无任何自定义主题 JS。

| 文件 | 视口 | 主题 | 内容与核验点 |
| --- | --- | --- | --- |
| `dashboard-light.png` | 1440×900 | 浅 | 白侧栏+墨色标签、方章字标、画布 #F5F7FA、概览计数中文（locale 补译生效）、链接 #2F7A6E |
| `dashboard-dark.png` | 1440×900 | 深 | 画布 #202322、链接/字标 #54A290（≈4.9:1）、侧栏保持 Wagtail 近黑默认 |
| `explorer-light.png` | 1440×900 | 浅 | 激活项淡青底 #E7F1EE+青导轨+无文字投影；选中行淡青 #D8EAE5+3px 品牌导轨 |
| `explorer-dark.png` | 1440×900 | 深 | 激活项导轨随 border 令牌变 #54A290；选中行深青 #2C6A5D+导轨 #35816F |
| `notice-edit-form-dark.png` | 1440×900 | 深 | 通知页编辑表单：字段、按钮（#35816F 面/白字 4.63:1）、状态徽章走核心令牌 |
| `notice-edit-form-light.png` | 1440×900 | 浅 | 同上表单浅色视角（附：标题「编辑 通知页: …」locale 生效） |
| `admin-375px-dark.png` | 375×812 | 深 | 窄屏仪表盘：1rem 水平留白、**零横向滚动**（scrollWidth=clientWidth） |

核验方式：全部关键值为 `getComputedStyle` 实测（非目测），明细见
`static/css/admin.css` 头注与提交说明。核心公式缺陷一例：Wagtail
secondary-75 派生式 `saturation − 47%` 在本品牌饱和度（44.4%/41.8%）下
为负、浏览器钳为灰——已按主题直钉（浅 #D8EAE5 / 深 #82C3B2）。
