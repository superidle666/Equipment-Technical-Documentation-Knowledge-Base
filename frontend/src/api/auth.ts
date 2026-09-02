/** Browser-side auth session handling for the administration console. */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const ACCESS_TOKEN_KEY = 'kb-admin-access-token'
const REFRESH_TOKEN_KEY = 'kb-admin-refresh-token'
const USER_KEY = 'kb-admin-user'

export type AuthUser = {
  id: number
  username: string
  display_name: string
  avatar_url: string | null
  roles: string[]
  permissions: string[]
}

type TokenPair = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}

function errorMessage(body: unknown, fallback: string) {
  return body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
    ? body.detail
    : fallback
}

const sessionKeys = [ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_KEY] as const

function getStoredItem(key: typeof sessionKeys[number]) {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key)
}

function getSessionStorage() {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ? localStorage : sessionStorage
}

function saveSession(session: TokenPair, rememberLogin = true) {
  const storage = rememberLogin ? localStorage : sessionStorage
  const otherStorage = rememberLogin ? sessionStorage : localStorage
  for (const key of sessionKeys) otherStorage.removeItem(key)
  storage.setItem(ACCESS_TOKEN_KEY, session.access_token)
  storage.setItem(REFRESH_TOKEN_KEY, session.refresh_token)
  storage.setItem(USER_KEY, JSON.stringify(session.user))
}

export function clearSession() {
  for (const key of sessionKeys) {
    localStorage.removeItem(key)
    sessionStorage.removeItem(key)
  }
}

export function hasAccessToken() {
  return Boolean(getStoredItem(ACCESS_TOKEN_KEY))
}
async function rawRequest(path: string, options: RequestInit = {}) {
  return fetch(API_BASE + path, options)
}

async function refreshSession(): Promise<boolean> {
  const refreshToken = getStoredItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return false
  try {
    const response = await rawRequest('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    const body = await response.json().catch(() => null)
    if (!response.ok || !body) return false
    saveSession(body as TokenPair, getSessionStorage() === localStorage)
    return true
  } catch {
    return false
  }
}

export async function authenticatedFetch(path: string, options: RequestInit = {}, retried = false): Promise<Response> {
  const accessToken = getStoredItem(ACCESS_TOKEN_KEY)
  const headers = new Headers(options.headers)
  if (accessToken) headers.set('Authorization', 'Bearer ' + accessToken)
  const response = await rawRequest(path, { ...options, headers })
  if (response.status !== 401) return response
  if (!retried && await refreshSession()) return authenticatedFetch(path, options, true)
  clearSession()
  window.dispatchEvent(new Event('auth-expired'))
  return response
}

export async function login(username: string, password: string, rememberLogin = true): Promise<AuthUser> {
  const response = await rawRequest('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const body = await response.json().catch(() => null)
  if (!response.ok || !body) throw new Error(errorMessage(body, '登录失败'))
  saveSession(body as TokenPair, rememberLogin)
  return (body as TokenPair).user
}

export async function logout() {
  const refreshToken = getStoredItem(REFRESH_TOKEN_KEY)
  try {
    await authenticatedFetch('/api/v1/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } finally {
    clearSession()
  }
}

export async function currentUser(): Promise<AuthUser> {
  const response = await authenticatedFetch('/api/v1/auth/me')
  const body = await response.json().catch(() => null)
  if (!response.ok || !body) throw new Error(errorMessage(body, '登录状态已失效'))
  getSessionStorage().setItem(USER_KEY, JSON.stringify(body))
  return body as AuthUser
}

