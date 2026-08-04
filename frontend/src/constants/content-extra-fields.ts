import type { ContentType } from '../types/content'

/** 专属字段值类型：仅文本与字符串列表 */
export type ContentExtraFieldValueType = 'text' | 'string-list'

/** 单个专属字段的配置：键、标签、值类型与占位提示 */
export interface ContentExtraFieldConfig {
  key: string
  label: string
  valueType: ContentExtraFieldValueType
  placeholder: string
}

/**
 * 各板块专属字段配置，严格匹配 ContentType 全部五个键。
 * 除 platforms 使用 string-list 外，其余字段均使用 text。
 */
export const CONTENT_EXTRA_FIELDS: Record<ContentType, readonly ContentExtraFieldConfig[]> = {
  'campus-story': [
    { key: 'location', label: '发生地点', valueType: 'text', placeholder: '如：图书馆三楼自习区' },
    { key: 'timeRange', label: '时间范围', valueType: 'text', placeholder: '如：工作日 07:30–08:30' },
    { key: 'category', label: '内容分类', valueType: 'text', placeholder: '如：学习日常' },
  ],
  'campus-activity': [
    { key: 'eventTime', label: '活动时间', valueType: 'text', placeholder: '如：2024-10-12 14:00–16:00' },
    { key: 'eventLocation', label: '活动地点', valueType: 'text', placeholder: '如：学生活动中心 201' },
    { key: 'organizer', label: '主办方', valueType: 'text', placeholder: '如：示例社团' },
  ],
  'learning-resource': [
    { key: 'courseName', label: '所属课程', valueType: 'text', placeholder: '如：高等数学' },
    { key: 'resourceType', label: '资源类型', valueType: 'text', placeholder: '如：复习笔记' },
    { key: 'applicableStage', label: '适用阶段', valueType: 'text', placeholder: '如：大一上学期' },
  ],
  'software-resource': [
    { key: 'platforms', label: '支持平台', valueType: 'string-list', placeholder: '如：Windows、macOS（多选）' },
    { key: 'softwareVersion', label: '软件版本', valueType: 'text', placeholder: '如：2024 教育版' },
    { key: 'licenseType', label: '授权类型', valueType: 'text', placeholder: '如：教育版授权（演示）' },
  ],
  'college-guide': [
    { key: 'targetAudience', label: '适用对象', valueType: 'text', placeholder: '如：新生' },
    { key: 'guideTopic', label: '指南主题', valueType: 'text', placeholder: '如：选课流程' },
    { key: 'applicableSemester', label: '适用学期', valueType: 'text', placeholder: '如：第一学期' },
  ],
}
