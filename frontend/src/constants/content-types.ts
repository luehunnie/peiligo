import type { ContentType } from '../types/content'

/** 板块配置项：约束 value 与内容模型一致，附中文标签与中立说明 */
export interface ContentTypeOption {
  value: ContentType
  label: string
  description: string
}

/** 五个板块的集中配置，顺序即展示顺序，不含图标、颜色、路由或布局信息 */
export const CONTENT_TYPE_OPTIONS: readonly ContentTypeOption[] = [
  {
    value: 'campus-story',
    label: '院内逸事',
    description: '记录校园日常学习与生活中的趣事、观察与片段。',
  },
  {
    value: 'campus-activity',
    label: '校园活动',
    description: '面向学生组织的活动、社团与兴趣小组信息。',
  },
  {
    value: 'learning-resource',
    label: '学习资料',
    description: '整理课程复习笔记、参考资料与学习经验。',
  },
  {
    value: 'software-resource',
    label: '软件资源',
    description: '汇总学习常用软件、工具与授权信息。',
  },
  {
    value: 'college-guide',
    label: '学院指南',
    description: '提供新生入学、学习流程与校园生活的指引。',
  },
]
