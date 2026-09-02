<!--
 * @FilePath: @/components/admin/AdminSidebar.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 管理端侧栏导航，包含用户、角色和权限子菜单
 * @BusinessRule: 用户管理展开项共享同一权限管理入口
 -->
<script setup lang="ts">
import { ChevronDownIcon, CloseIcon } from 'tdesign-icons-vue-next'
import type { Component } from 'vue'

type NavKey =
  | 'dashboard'
  | 'documents'
  | 'users'
  | 'roles'
  | 'permissions'
  | 'sessions'
  | 'settings'

type NavItem = {
  key: NavKey
  label: string
  icon: Component
}

const props = defineProps<{
  collapsed: boolean
  mobileOpen: boolean
  activeNav: NavKey
  userMenuExpanded: boolean
  navItems: NavItem[]
  documentCount: number
  userCount: number
  roleCount: number
  permissionCount: number
  displayName: string
  roleLabel: string
}>()

const emit = defineEmits<{
  (event: 'navigate', key: NavKey): void
  (event: 'toggle-users'): void
  (event: 'update:mobile-open', value: boolean): void
}>()

/** 触发模块导航，并由父组件统一维护当前路由状态。 */
function handleNav(key: NavKey) {
  if (key === 'users') {
    emit('navigate', 'users')

    if (!props.collapsed) {
      emit('toggle-users')
    }

    return
  }

  emit('navigate', key)
}
</script>

<template>
  <aside class="admin-sidebar" :class="{ collapsed: props.collapsed, open: props.mobileOpen }">
    <div class="admin-brand">
      <div class="admin-mark">工</div>
      <div v-if="!props.collapsed" class="admin-brand-copy">
        <strong>工智库</strong>
        <span>管理控制台</span>
      </div>
      <button
        class="mobile-close"
        aria-label="关闭导航"
        @click="emit('update:mobile-open', false)"
      >
        <CloseIcon />
      </button>
    </div>

    <nav class="admin-nav">
      <div v-if="!props.collapsed" class="admin-nav-label">管理中心</div>
      <template v-for="item in props.navItems" :key="item.key">
        <button
          class="admin-nav-item"
          :class="{ active: props.activeNav === item.key }"
          @click="handleNav(item.key)"
        >
          <component :is="item.icon" />
          <span v-if="!props.collapsed">{{ item.label }}</span>
          <span
            v-if="!props.collapsed && item.key === 'documents'"
            class="admin-nav-count"
          >
            {{ props.documentCount }}
          </span>
          <ChevronDownIcon
            v-if="!props.collapsed && item.key === 'users'"
            class="user-nav-chevron"
            :class="{ expanded: props.userMenuExpanded }"
          />
        </button>

        <div
          v-if="!props.collapsed && item.key === 'users' && props.userMenuExpanded"
          class="admin-subnav"
        >
          <button
            :class="{ active: props.activeNav === 'users' }"
            @click="emit('navigate', 'users')"
          >
            用户列表
            <span>{{ props.userCount }}</span>
          </button>
          <button
            :class="{ active: props.activeNav === 'roles' }"
            @click="emit('navigate', 'roles')"
          >
            角色管理
            <span>{{ props.roleCount }}</span>
          </button>
          <button
            :class="{ active: props.activeNav === 'permissions' }"
            @click="emit('navigate', 'permissions')"
          >
            权限管理
            <span>{{ props.permissionCount }}</span>
          </button>
        </div>
      </template>
    </nav>

    <div class="admin-sidebar-bottom">
      <div class="admin-profile">
        <div class="avatar admin-avatar">{{ props.displayName.slice(0, 1) }}</div>
        <div v-if="!props.collapsed">
          <strong>{{ props.displayName }}</strong>
          <span>{{ props.roleLabel }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>
