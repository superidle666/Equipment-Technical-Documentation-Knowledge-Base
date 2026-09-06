<script setup lang="ts">
import { ChevronDownIcon, LightbulbIcon, MoonIcon, ViewListIcon } from 'tdesign-icons-vue-next'
defineProps<{ darkMode: boolean; activeLibrary: string; liveData: boolean; loggedIn: boolean; displayName: string; avatarText: string }>()
defineEmits<{ (event: 'open-menu'): void; (event: 'toggle-theme'): void; (event: 'login'): void; (event: 'logout'): void }>()
</script>
<template>
  <header class="topbar"><div class="topbar-left"><t-button variant="text" shape="square" class="mobile-menu" @click="$emit('open-menu')"><ViewListIcon /></t-button><span class="workspace-label">用户端</span><span class="divider"></span><button class="library-selector"><span class="library-dot"></span>{{ activeLibrary }}<ChevronDownIcon /></button></div><div class="topbar-right"><span class="mock-badge"><span class="pulse-dot"></span>{{ liveData ? '实时数据' : '等待连接' }}</span><span class="topbar-user">{{ displayName }}</span><t-button v-if="loggedIn" variant="outline" size="small" @click="$emit('logout')">退出登录</t-button><t-button v-else variant="outline" size="small" @click="$emit('login')">登录</t-button><t-button variant="text" shape="square" :title="darkMode ? '切换浅色模式' : '切换深色模式'" @click="$emit('toggle-theme')"><MoonIcon v-if="!darkMode" /><LightbulbIcon v-else /></t-button><div class="avatar">{{ avatarText }}</div></div></header>
</template>
