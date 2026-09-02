<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChatIcon,
  DashboardIcon,
  FileIcon,
  SettingIcon,
  UsergroupIcon,
  UserIcon,
  LockOnIcon,
} from 'tdesign-icons-vue-next'
import { currentUser, hasAccessToken, login as loginWithPassword, logout as logoutSession, type AuthUser } from '../../api/auth'
import AdminHeader from '../../components/admin/AdminHeader.vue'
import AdminSidebar from '../../components/admin/AdminSidebar.vue'
import AdminLayout from '../../layouts/AdminLayout.vue'
import DashboardPage from './dashboard/index.vue'
import DocumentsPage from './documents/index.vue'
import PermissionsPage from './permissions/index.vue'
import RolesPage from './roles/index.vue'
import SessionsPage from './sessions/index.vue'
import SettingsPage from './settings/index.vue'
import UsersPage from './users/index.vue'

type NavKey = 'dashboard' | 'documents' | 'users' | 'roles' | 'permissions' | 'sessions' | 'settings'

type AdminCounts = {
  documents: number
  users: number
  roles: number
  permissions: number
}

const route = useRoute()
const router = useRouter()
const isAuthenticated = ref(hasAccessToken())
const account = ref<AuthUser | null>(null)
const username = ref('')
const password = ref('')
const loginError = ref('')
const loginLoading = ref(false)
const rememberLogin = ref(true)
const activeNav = ref<NavKey>('dashboard')
const collapsed = ref(false)
const mobileOpen = ref(false)
const userMenuExpanded = ref(true)
const counts = ref<AdminCounts>({ documents: 0, users: 0, roles: 0, permissions: 0 })

const allNavItems = [
  { key: 'dashboard' as const, label: '仪表盘', icon: DashboardIcon },
  { key: 'documents' as const, label: '文档管理', icon: FileIcon },
  { key: 'users' as const, label: '用户管理', icon: UsergroupIcon },
  { key: 'sessions' as const, label: '操作日志', icon: ChatIcon },
  { key: 'settings' as const, label: '系统设置', icon: SettingIcon },
]

const navItems = computed(() => allNavItems.filter((item) => item.key !== 'settings' || account.value?.roles.includes('admin')))

const pageTitle = computed(() => navItems.value.find((item) => item.key === activeNav.value)?.label ?? '仪表盘')
const roleLabel = computed(() => account.value?.roles.includes('admin') ? '系统管理员' : '已授权用户')

async function loadCurrentUser() {
  try {
    account.value = await currentUser()
    isAuthenticated.value = true
  } catch {
    isAuthenticated.value = false
    account.value = null
    await router.replace({ name: 'admin-login' })
  }
}

async function login() {
  if (loginLoading.value) return
  loginError.value = ''
  if (!username.value.trim() || !password.value) {
    loginError.value = '请输入账号和密码'
    return
  }
  loginLoading.value = true
  try {
    account.value = await loginWithPassword(username.value.trim(), password.value, rememberLogin.value)
    isAuthenticated.value = true
    password.value = ''
    await router.replace({ name: 'admin' })
  } catch (error) {
    loginError.value = error instanceof Error ? error.message : '登录失败'
  } finally {
    loginLoading.value = false
  }
}

async function logout() {
  await logoutSession()
  isAuthenticated.value = false
  account.value = null
  username.value = ''
  password.value = ''
  await router.replace({ name: 'admin-login' })
}

function handleExpired() {
  isAuthenticated.value = false
  account.value = null
  void router.replace({ name: 'admin-login' })
}

function navigate(key: NavKey) {
  activeNav.value = key
  mobileOpen.value = false
}

function updateCounts(nextCounts: Partial<AdminCounts>) {
  counts.value = { ...counts.value, ...nextCounts }
}

onMounted(() => {
  window.addEventListener('auth-expired', handleExpired)
  if (route.name === 'admin' && hasAccessToken()) void loadCurrentUser()
})

onBeforeUnmount(() => {
  window.removeEventListener('auth-expired', handleExpired)
})
</script>

<template>
  <div v-if="route.name === 'admin-login' || !isAuthenticated" class="admin-login-page">
    <div class="login-brand">
      <div class="admin-mark">工</div>
      <div>
        <strong>工智库</strong>
        <span>管理控制台</span>
      </div>
    </div>

    <div class="login-card">
      <div class="eyebrow">ADMIN CONSOLE</div>
      <h1>登录管理端</h1>
      <p class="login-subtitle">使用已授权账号登录后管理知识库内容、用户与权限。</p>

      <t-form class="login-form" @submit="login">
        <div class="login-field">
          <t-input
            v-model="username"
            name="username"
            autocomplete="username"
            placeholder="账号"
            clearable
            autofocus
          >
            <template #prefix-icon><UserIcon /></template>
          </t-input>
        </div>
        <div class="login-field">
          <t-input
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            placeholder="登录密码"
            clearable
            @enter="login"
          >
            <template #prefix-icon><LockOnIcon /></template>
          </t-input>
        </div>
        <div class="login-options">
          <t-checkbox v-model="rememberLogin">记住登录</t-checkbox>
        </div>
        <div v-if="loginError" class="login-error" role="alert">{{ loginError }}</div>
        <t-button theme="primary" block size="large" type="submit" :loading="loginLoading">
          登录管理端
        </t-button>
      </t-form>
    </div>

    <p class="login-footer">工智库 · 设备技术知识平台</p>
  </div>

  <AdminLayout v-else>
    <AdminSidebar
      :collapsed="collapsed"
      :mobile-open="mobileOpen"
      :active-nav="activeNav"
      :user-menu-expanded="userMenuExpanded"
      :nav-items="navItems"
      :document-count="counts.documents"
      :user-count="counts.users"
      :role-count="counts.roles"
      :permission-count="counts.permissions"
      :display-name="account?.display_name || account?.username || '已登录用户'"
      :role-label="roleLabel"
      @navigate="navigate"
      @toggle-users="userMenuExpanded = !userMenuExpanded"
      @update:mobile-open="mobileOpen = $event"
    />
    <div v-if="mobileOpen" class="admin-backdrop" @click="mobileOpen = false" />

    <main class="admin-main">
      <AdminHeader
        :title="pageTitle"
        :display-name="account?.display_name || account?.username || '已登录用户'"
        :role-label="roleLabel"
        @open-menu="mobileOpen = true"
        @logout="logout"
      />
      <div class="admin-content">
        <DashboardPage v-if="activeNav === 'dashboard'" @navigate="navigate" @update-counts="updateCounts" />
        <DocumentsPage v-else-if="activeNav === 'documents'" @update-counts="updateCounts" />
        <UsersPage v-else-if="activeNav === 'users'" @update-counts="updateCounts" />
        <RolesPage v-else-if="activeNav === 'roles'" @update-counts="updateCounts" />
        <PermissionsPage v-else-if="activeNav === 'permissions'" @update-counts="updateCounts" />
        <SessionsPage v-else-if="activeNav === 'sessions'" />
        <SettingsPage v-else />
      </div>
    </main>
  </AdminLayout>
</template>

