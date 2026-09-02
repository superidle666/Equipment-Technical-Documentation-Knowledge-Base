<!--
 * @FilePath: @/components/admin/AdminHeader.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 管理端顶部栏，展示当前模块标题和移动端菜单入口
 -->
<script setup lang="ts">
import {
  ChevronRightIcon,
  MenuIcon,
  LogoutIcon,
} from 'tdesign-icons-vue-next'

const props = defineProps<{ title: string; displayName: string; roleLabel: string }>()

const emit = defineEmits<{
  (event: 'open-menu'): void
  (event: 'logout'): void
}>()
</script>

<template>
  <header class="admin-topbar">
    <div class="admin-top-left">
      <t-button
        variant="text"
        shape="square"
        class="admin-mobile-menu"
        aria-label="打开导航"
        @click="emit('open-menu')"
      >
        <MenuIcon />
      </t-button>
      <span class="admin-breadcrumb">管理端</span>
      <ChevronRightIcon />
      <strong>{{ title }}</strong>
    </div>
    <div class="admin-top-right">
      <span class="admin-env">
        <span />
        已认证
      </span>
      <div class="admin-top-account">
        <strong>{{ props.displayName }}</strong>
        <span>{{ props.roleLabel }}</span>
      </div>
      <div class="avatar admin-avatar">{{ props.displayName.slice(0, 1) }}</div>
      <t-tooltip content="退出登录">
        <t-button
          variant="text"
          shape="square"
          class="admin-top-logout"
          aria-label="退出登录"
          @click="emit('logout')"
        >
          <LogoutIcon />
        </t-button>
      </t-tooltip>
    </div>
  </header>
</template>
