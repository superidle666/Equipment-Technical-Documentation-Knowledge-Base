import type { Document, Library, User } from '../../../api/mysql'

// 管理端列表展示模型：将后端字段转换为表格可读文本。

/** 文档列表的派生行模型，补充知识库名称和格式化展示字段。 */
export type DocumentRow = Document & {
  name: string
  library: string
  type: string
  size: string
  updated: string
  statusLabel: string
}

/** 用户列表的派生行模型，补充首个角色和本地化状态文本。 */
export type UserRow = User & {
  name: string
  role: string
  last: string
  statusLabel: string
}

/** 文档状态到中文标签的映射。 */
export const documentStatusLabels: Record<string, string> = {
  published: '已发布',
  processing: '处理中',
  failed: '失败',
  archived: '已删除',
  uploaded: '待处理',
}

/** 将文档生命周期状态转换为管理端中文显示文本。 */
export function formatDocumentStatus(status: string) {
  return documentStatusLabels[status] || status
}

/** 用户状态到中文标签的映射。 */
const userStatusLabels: Record<string, string> = {
  active: '正常',
  disabled: '已停用',
  locked: '已锁定',
}

/** 将 ISO 时间转换为中文短日期时间；空值显示占位符。 */
export function formatTime(value: string | null | undefined, includeYear = false) {
  if (!value) {
    return '-'
  }

  return new Date(value).toLocaleString('zh-CN', {
    ...(includeYear ? { year: 'numeric' as const } : {}),
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 将字节数转换为 KB/MB 展示文本。 */
export function formatSize(value: number | null) {
  if (value === null || value === undefined) {
    return '-'
  }

  if (value > 1024 * 1024) {
    return `${(value / 1024 / 1024).toFixed(1)} MB`
  }

  return `${Math.max(1, Math.round(value / 1024))} KB`
}

/** 将字节数转换为统一的 MB 展示文本。 */
export function formatSizeInMb(value: number | null) {
  if (value === null || value === undefined) {
    return '-'
  }
  return `${(value / 1024 / 1024).toFixed(2)} MB`
}

/** 将文档接口数据映射为管理端文档表格行。 */
export function mapDocument(document: Document, libraries: Library[]): DocumentRow {
  const library = libraries.find((item) => item.id === document.library_id)
  const extension = document.original_filename.split('.').pop() || 'FILE'

  return {
    ...document,
    name: document.title,
    library: document.library_name || library?.name || '原知识库已不存在',
    // 文件名是存储时的真实后缀；浏览器提交的 MIME 值可能被错误标记为 PDF。
    type: extension.toUpperCase(),
    size: formatSizeInMb(document.file_size),
    updated: formatTime(document.updated_at, true),
    statusLabel: documentStatusLabels[document.status] || document.status,
  }
}

/** 将用户接口数据映射为管理端用户表格行。 */
export function mapUser(user: User): UserRow {
  return {
    ...user,
    name: user.display_name,
    role: user.roles[0] || 'user',
    last: formatTime(user.last_login_at, true),
    statusLabel: userStatusLabels[user.status] || user.status,
  }
}

/** 判断用户是否为受保护的系统管理员。 */
export function isSystemAdminUser(row: Pick<User, 'username' | 'roles'>) {
  return row.username === 'admin' || row.roles.includes('admin')
}

/** 判断角色编码是否为不可编辑的内置 admin。 */
export function isSystemAdminRole(code: string) {
  return code === 'admin'
}
