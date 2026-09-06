<script setup lang="ts">
import { computed } from 'vue'
import { AddIcon, ChevronLeftIcon, ChevronRightIcon, SearchIcon, SettingIcon, ViewListIcon } from 'tdesign-icons-vue-next'
import type { UserConversation, UserLibrary } from '../../types/user'

const props = defineProps<{
  collapsed: boolean
  mobileOpen: boolean
  libraries: UserLibrary[]
  activeLibrary: string
  conversations: UserConversation[]
  searchOpen: boolean
  searchQuery: string
  displayName: string
  roleLabel: string
  avatarText: string
}>()
const emit = defineEmits<{
  (event: 'create-conversation'): void
  (event: 'select-library', name: string): void
  (event: 'select-conversation', item: UserConversation): void
  (event: 'toggle-search'): void
  (event: 'update:search-query', value: string): void
  (event: 'close-mobile'): void
  (event: 'toggle-collapse'): void
}>()
const filteredConversations = computed(() => {
  const value = props.searchQuery.trim().toLowerCase()
  return value ? props.conversations.filter((item) => item.title.toLowerCase().includes(value)) : props.conversations
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed, 'is-mobile-open': mobileOpen }">
    <div class="brand-row"><div class="brand-mark">工</div><div v-if="!collapsed" class="brand-copy"><strong>工智库</strong><span>设备技术知识平台</span></div><t-button v-if="!collapsed" variant="text" shape="square" class="sidebar-close" @click="emit('close-mobile')"><ChevronLeftIcon /></t-button></div>
    <div class="sidebar-content">
      <t-button theme="primary" block class="new-chat" @click="emit('create-conversation')"><AddIcon /><span v-if="!collapsed">新建咨询</span></t-button>
      <nav class="nav-list"><div v-if="!collapsed" class="nav-label">工作台</div><button class="nav-item active"><ViewListIcon /><span v-if="!collapsed">知识库</span><span v-if="!collapsed" class="nav-count">{{ libraries.length }}</span></button><div v-if="!collapsed" class="library-list"><button v-for="library in libraries" :key="library.name" class="library-item" :class="{ selected: activeLibrary === library.name }" @click="emit('select-library', library.name)"><span class="library-dot" :style="{ background: library.color }"></span><span>{{ library.name }}</span><small>{{ library.count }}</small></button></div><button class="nav-item" @click="emit('toggle-search')"><SearchIcon /><span v-if="!collapsed">搜索会话</span></button></nav>
      <div v-if="!collapsed" class="conversation-section"><div class="section-heading"><span>最近会话</span><button title="刷新会话"><ChevronRightIcon /></button></div><div v-if="searchOpen" class="search-box"><SearchIcon /><input :value="searchQuery" placeholder="搜索会话" @input="emit('update:search-query', ($event.target as HTMLInputElement).value)" /></div><button v-for="item in filteredConversations" :key="item.id" class="conversation-item" :class="{ selected: item.active }" @click="emit('select-conversation', item)"><span class="conversation-dot"></span><span class="conversation-title">{{ item.title }}</span><span class="conversation-time">{{ item.time }}</span></button></div>
    </div>
    <div class="sidebar-footer"><div class="user-card"><div class="avatar small">{{ avatarText }}</div><div v-if="!collapsed" class="user-copy"><strong>{{ displayName }}</strong><span>{{ roleLabel }}</span></div><SettingIcon v-if="!collapsed" class="setting-icon" /></div><button class="collapse-button" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle-collapse')"><ChevronRightIcon v-if="collapsed" /><ChevronLeftIcon v-else /></button></div>
  </aside>
</template>
