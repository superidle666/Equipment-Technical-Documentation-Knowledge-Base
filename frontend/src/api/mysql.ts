import { authenticatedFetch } from './auth'

export type User = {
  id: number
  username: string
  email: string | null
  phone: string | null
  display_name: string
  status: string
  roles: string[]
  last_login_at: string | null
}

export type Library = {
  id: number
  name: string
  code: string
  description: string | null
  cover_color: string | null
  status: string
  document_count: number
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export type Document = {
  id: number
  library_id: number
  title: string
  original_filename: string
  storage_key: string
  mime_type: string | null
  file_size: number | null
  file_hash: string | null
  status: string
  created_at: string
  updated_at: string
  chunk_count?: number
  tags?: string[]
  library_name?: string | null
}

export type DocumentChunk = {
  id: number
  document_id: number
  chunk_index: number
  content: string
  token_count: number | null
  page_number: number | null
  section_title: string | null
  vector_id: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export type Tag = {
  id: number
  name: string
  created_at: string
  updated_at: string
}

export type Role = {
  id: number
  code: string
  name: string
  description: string | null
  status: "active" | "disabled"
  deleted_at: string | null
  deleted_by: number | null
  permissions: string[]
}

export type Permission = {
  id: number
  code: string
  name: string
  description: string | null
  status: "active" | "disabled"
  deleted_at: string | null
  deleted_by: number | null
  parent_id: number | null
}

export type OperationLog = {
  id: number
  user_id: number | null
  user_display_name: string | null
  operation: string
  resource_type: string | null
  resource_id: string | null
  resource_display_name: string | null
  request_ip: string | null
  detail: Record<string, unknown> | null
  created_at: string
}

export type SystemSetting = {
  key: string
  name: string
  category: string
  description: string | null
  is_sensitive: boolean
  value: string | null
  masked_value: string | null
  has_value: boolean
  updated_at: string
  updated_by: number | null
}
export type OperationLogPage = {
  items: OperationLog[]
  total: number
  page: number
  page_size: number
}
/** 将 FastAPI 的字符串或字段校验明细转换为适合界面展示的错误信息。 */
function getApiErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object' || !('detail' in body)) return fallback

  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return fallback

  const messages = detail
    .map((item) => {
      if (!item || typeof item !== 'object' || !('msg' in item)) return ''
      return typeof item.msg === 'string' ? item.msg : ''
    })
    .filter(Boolean)

  return messages.join('；') || fallback
}

/** 发送 JSON 请求并统一处理 FastAPI 错误响应。 */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await authenticatedFetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
  } catch {
    throw new Error('无法连接后端服务，请确认 FastAPI 服务已启动')
  }
  const body = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(getApiErrorMessage(body, `请求失败（${response.status}）`))
  }

  return body as T
}

/** 统一封装管理端用户、权限、知识库和文档接口。 */
export const mysqlApi = {
  // 用户与访问控制
  listUsers: (params = '') => {
    const query = params ? `?${params}` : ''
    return request<User[]>(`/api/v1/users${query}`)
  },
  createUser: (payload: Record<string, unknown>) => {
    return request<User>('/api/v1/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  updateUser: (id: number, payload: Record<string, unknown>) => {
    return request<User>(`/api/v1/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  deleteUser: (id: number) => {
    return request<{ message: string }>(`/api/v1/users/${id}`, {
      method: 'DELETE',
    })
  },
  // 角色和权限字典
  listRoles: (params = '') => {
    const query = params ? '?' + params : ''
    return request<Role[]>('/api/v1/roles' + query)
  },
  createRole: (payload: Record<string, unknown>) => {
    return request<Role>('/api/v1/roles', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  updateRole: (id: number, payload: Record<string, unknown>) => {
    return request<Role>(`/api/v1/roles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  listPermissions: (params = '') => {
    const query = params ? '?' + params : ''
    return request<Permission[]>('/api/v1/permissions' + query)
  },
  deleteRole: (id: number, deletedBy?: number) => {
    const query = deletedBy ? '?deleted_by=' + deletedBy : ''
    return request<{ message: string }>('/api/v1/roles/' + id + query, { method: 'DELETE' })
  },
  restoreRole: (id: number) => request<Role>('/api/v1/roles/' + id + '/restore', { method: 'POST' }),
  updatePermission: (id: number, payload: Record<string, unknown>) => {
    return request<Permission>(`/api/v1/permissions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  // 知识库、文档及审计数据
  listLibraries: (includeDisabled = true, includeDeleted = false) => {
    return request<Library[]>(
      `/api/v1/libraries?include_disabled=${includeDisabled}&include_deleted=${includeDeleted}`,
    )
  },
  createLibrary: (payload: Record<string, unknown>) => {
    return request<Library>('/api/v1/libraries', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  updateLibrary: (id: number, payload: Record<string, unknown>) => {
    return request<Library>(`/api/v1/libraries/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  deleteLibrary: (id: number) => {
    return request<{ message: string }>(`/api/v1/libraries/${id}`, {
      method: 'DELETE',
    })
  },
  restoreLibrary: (id: number) => {
    return request<Library>(`/api/v1/libraries/${id}/restore`, {
      method: 'POST',
    })
  },
  listDocuments: (params = '') => {
    const query = params ? `?${params}` : ''
    return request<Document[]>(`/api/v1/documents${query}`)
  },
  getDocument: (id: number) => request<Document>(`/api/v1/documents/${id}`),
  createDocument: (payload: Record<string, unknown>) => {
    return request<Document>('/api/v1/documents', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  uploadDocument: async (file: File, libraryId: number, title?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('library_id', String(libraryId))
    if (title?.trim()) form.append('title', title.trim())
    let response: Response
    try {
      response = await authenticatedFetch('/api/v1/documents/upload', {
        method: 'POST',
        body: form,
      })
    } catch {
      throw new Error('无法连接后端服务，请确认 FastAPI 服务已启动')
    }
    const body = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(getApiErrorMessage(body, `请求失败（${response.status}）`))
    }
    return body as Document
  },
  updateDocument: (id: number, payload: Record<string, unknown>) => {
    return request<Document>(`/api/v1/documents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  deleteDocument: (id: number) => {
    return request<{ message: string }>(`/api/v1/documents/${id}`, {
      method: 'DELETE',
    })
  },
  listChunks: (id: number, params = '') => {
    const query = params ? `?${params}` : ''
    return request<DocumentChunk[]>(`/api/v1/documents/${id}/chunks${query}`)
  },
  updateDocumentTags: (id: number, tagNames: string[]) => {
    return request<Document>(`/api/v1/documents/${id}/tags`, {
      method: 'PUT',
      body: JSON.stringify({ tag_names: tagNames }),
    })
  },
  listTags: () => request<Tag[]>('/api/v1/tags'),
  createTag: (name: string) => {
    return request<Tag>('/api/v1/tags', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  },
  updateTag: (id: number, name: string) => {
    return request<Tag>(`/api/v1/tags/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    })
  },
  deleteTag: (id: number) => {
    return request<{ message: string }>(`/api/v1/tags/${id}`, {
      method: 'DELETE',
    })
  },
  listSettings: () => request<SystemSetting[]>('/api/v1/settings'),
  updateSetting: (key: string, value: string | null) => {
    return request<SystemSetting>('/api/v1/settings/' + encodeURIComponent(key), {
      method: 'PATCH',
      body: JSON.stringify({ value }),
    })
  },  listLogs: (params = '') => {
    const query = params ? '?' + params : ''
    return request<OperationLogPage>('/api/v1/operation-logs' + query)
  },
}
