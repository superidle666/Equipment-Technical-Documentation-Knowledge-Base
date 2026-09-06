<!-- 用户端问答工作台页面。 -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import UserLayout from '../../layouts/UserLayout.vue'
import UserSidebar from '../../components/user/UserSidebar.vue'
import UserTopbar from '../../components/user/UserTopbar.vue'
import UserChatPanel from '../../components/user/UserChatPanel.vue'
import UserSourcePanel from '../../components/user/UserSourcePanel.vue'
import { getQuerySessionMessages, listQueryLibraries, listQuerySessions, type QueryLibrary, type QueryResponse } from '../../api/query'
import { useUserQuery } from '../../composables/useUserQuery'
import { useUserStore } from '../../store/modules/user'
import type { QueryChatMessage, QuerySession, UserConversation, UserLibrary, UserMessage, UserSource } from '../../types/user'

const ANONYMOUS_QUERY_LIMIT = 3
const ANONYMOUS_QUERY_COUNT_KEY = 'kb-user-anonymous-query-count'
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isLoggedIn, userInfo } = storeToRefs(userStore)
const darkMode = ref(false)
const collapsed = ref(false)
const mobileSidebarOpen = ref(false)
const sourcePanelOpen = ref(true)
const searchOpen = ref(false)
const searchQuery = ref('')
const activeLibrary = ref('')
const inputText = ref('')
const libraries = ref<UserLibrary[]>([])
const libraryError = ref('')
const anonymousLimitDialogVisible = ref(false)
const { isLoading: isSending, error: queryError, sources: querySources, submit: submitQuery, reset: resetQuery, restore: restoreQuery } = useUserQuery()
const queryContextVersion = ref(0)
const sessionError = ref('')
let localConversationSequence = 0

const conversations = ref<UserConversation[]>([])

const messages = ref<UserMessage[]>([])

const selectedLibrary = computed(() => libraries.value.find((item) => item.name === activeLibrary.value) || null)
const activeLibraryName = computed(() => selectedLibrary.value?.name || '未选择知识库')
const sources = computed<UserSource[]>(() => querySources.value.map((source, index) => {
  const score = source.score === null ? null : source.score > 1 ? source.score : source.score * 100
  return {
    id: String(source.chunk_id ?? `${source.document_id ?? 'source'}-${index}`),
    title: source.document_title || source.section_title || '未命名文档',
    type: source.page_number ? `知识库文档 · 第 ${source.page_number} 页` : '知识库文档',
    score: score === null ? '--' : `${Math.round(score)}%`,
    color: ['#2563eb', '#0f9d78', '#c47f1d'][index % 3],
    content: source.content,
    documentId: source.document_id,
    chunkId: source.chunk_id,
    chunkIndex: source.chunk_index,
    pageNumber: source.page_number,
    sectionTitle: source.section_title,
    parentTitle: source.parent_title,
  }
}))
const chatTitle = computed(() => messages.value.slice().reverse().find((message) => message.role === 'user')?.content || '开始一次新的技术咨询')
const queryMessage = computed(() => queryError.value || libraryError.value || sessionError.value)
const displayName = computed(() => userInfo.value?.display_name || userInfo.value?.username || '访客')
const roleLabel = computed(() => isLoggedIn.value ? '已登录用户' : '匿名体验用户')
const avatarText = computed(() => displayName.value.trim().slice(0, 1) || '访')

function getAnonymousQueryCount() {
  const storedCount = Number.parseInt(window.localStorage.getItem(ANONYMOUS_QUERY_COUNT_KEY) || '0', 10)
  return Number.isFinite(storedCount) && storedCount >= 0 ? storedCount : 0
}

function consumeAnonymousQuery() {
  window.localStorage.setItem(ANONYMOUS_QUERY_COUNT_KEY, String(getAnonymousQueryCount() + 1))
}

function goToLogin() {
  void router.push({ name: 'user-login', query: { redirect: route.fullPath, reason: 'anonymous-limit' } })
}

function handleAnonymousLimit() {
  anonymousLimitDialogVisible.value = true
}

function confirmLoginAfterLimit() {
  anonymousLimitDialogVisible.value = false
  goToLogin()
}

function createLocalConversation(): UserConversation {
  localConversationSequence += 1
  return {
    id: `query-session-local-${Date.now()}-${localConversationSequence}`,
    title: '新建技术咨询',
    time: '刚刚',
    active: true,
  }
}

function formatTimestamp(timestamp: number) {
  if (!timestamp) return '刚刚'
  const date = new Date(timestamp * 1000)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function toUserConversation(session: QuerySession): UserConversation {
  return {
    id: session.id,
    libraryId: session.library_id,
    title: session.title,
    time: formatTimestamp(session.updated_at),
    active: false,
  }
}

function toUserMessage(message: QueryChatMessage): UserMessage {
  return {
    id: `history-message-${message.id}`,
    role: message.role === 'user' ? 'user' : 'assistant',
    content: message.content,
    time: formatTimestamp(message.created_at),
  }
}

async function loadConversationsForCurrentLibrary() {
  const libraryId = selectedLibrary.value?.id
  sessionError.value = ''
  if (!isLoggedIn.value || !libraryId) {
    conversations.value = isLoggedIn.value ? [] : [createLocalConversation()]
    return
  }

  const contextVersion = queryContextVersion.value
  try {
    const sessionRows = await listQuerySessions(libraryId)
    if (contextVersion !== queryContextVersion.value || selectedLibrary.value?.id !== libraryId || !isLoggedIn.value) return
    const loadedConversations = sessionRows.map(toUserConversation)
    conversations.value = loadedConversations.length ? loadedConversations : [createLocalConversation()]
    const firstConversation = conversations.value[0]
    firstConversation.active = true
    if (firstConversation.libraryId) await restoreConversation(firstConversation)
  } catch (error) {
    if (contextVersion !== queryContextVersion.value) return
    sessionError.value = error instanceof Error ? error.message : '历史会话加载失败，请稍后重试'
    conversations.value = [createLocalConversation()]
  }
}

async function restoreConversation(item: UserConversation) {
  const libraryId = selectedLibrary.value?.id
  if (!libraryId || item.libraryId && item.libraryId !== libraryId) return
  invalidateQueryContext()
  conversations.value.forEach((conversation) => (conversation.active = conversation.id === item.id))
  mobileSidebarOpen.value = false
  sessionError.value = ''
  const context = currentQueryContext(libraryId)
  if (!isLoggedIn.value || !item.libraryId) return

  try {
    const result = await getQuerySessionMessages(item.id)
    if (!isCurrentQueryContext(context, libraryId) || result.library_id !== libraryId) return
    messages.value = result.messages.map(toUserMessage)
    const lastUserMessage = [...result.messages].reverse().find((message) => message.role === 'user')
    const lastAssistantMessage = [...result.messages].reverse().find((message) => message.role === 'assistant')
    const restoredResult: QueryResponse = {
      library_id: result.library_id,
      query: lastUserMessage?.content || '',
      answer: lastAssistantMessage?.content || '',
      sources: lastAssistantMessage?.sources || [],
    }
    restoreQuery(restoredResult)
  } catch (error) {
    if (!isCurrentQueryContext(context, libraryId)) return
    sessionError.value = error instanceof Error ? error.message : '会话消息加载失败，请稍后重试'
  }
}

async function logout() {
  invalidateQueryContext()
  try {
    await userStore.logout()
  } finally {
    conversations.value = []
    messages.value = []
    sessionError.value = ''
    mobileSidebarOpen.value = false
  }
}

function toUserLibrary(library: QueryLibrary): UserLibrary {
  return {
    id: library.id,
    name: library.name,
    count: library.document_count,
    color: library.cover_color || '#2563eb',
    status: library.status,
    updatedAt: library.updated_at,
  }
}

async function loadLibraries() {
  try {
    const libraryRows = await listQueryLibraries()
    libraries.value = libraryRows.filter((library) => library.status === 'active').map(toUserLibrary)
    if (!libraries.value.length) {
      activeLibrary.value = ''
      conversations.value = []
      libraryError.value = '当前没有可用的知识库，请联系管理员启用知识库并完成文档导入后再试'
      invalidateQueryContext()
      return
    }
    if (!selectedLibrary.value) {
      activeLibrary.value = libraries.value[0].name
      libraryError.value = ''
    }
    invalidateQueryContext()
    await loadConversationsForCurrentLibrary()
  } catch (error) {
    libraryError.value = error instanceof Error ? error.message : '知识库加载失败，请稍后重试'
  }
}

function selectConversation(item: UserConversation) {
  if (item.active && messages.value.length) {
    mobileSidebarOpen.value = false
    return
  }
  void restoreConversation(item)
}

function createConversation() {
  invalidateQueryContext()
  conversations.value.forEach((conversation) => (conversation.active = false))
  conversations.value.unshift(createLocalConversation())
  mobileSidebarOpen.value = false
}

function selectLibrary(name: string) {
  mobileSidebarOpen.value = false
  if (name === activeLibrary.value) return
  invalidateQueryContext()
  activeLibrary.value = name
  libraryError.value = ''
  void loadConversationsForCurrentLibrary()
}

function invalidateQueryContext() {
  queryContextVersion.value += 1
  resetQuery()
  messages.value = []
  inputText.value = ''
}

function currentQueryContext(libraryId: number) {
  const conversationId = conversations.value.find((conversation) => conversation.active)?.id ?? 0
  return `${queryContextVersion.value}:${conversationId}:${libraryId}`
}

function isCurrentQueryContext(context: string, libraryId: number) {
  return selectedLibrary.value?.id === libraryId && currentQueryContext(libraryId) === context
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isSending.value) return
  if (!isLoggedIn.value && getAnonymousQueryCount() >= ANONYMOUS_QUERY_LIMIT) {
    handleAnonymousLimit()
    return
  }
  const libraryId = selectedLibrary.value?.id
  if (!libraryId) {
    libraryError.value = '当前没有可用的知识库，请联系管理员启用知识库并完成文档导入后再试'
    return
  }
  libraryError.value = ''
  if (!isLoggedIn.value) consumeAnonymousQuery()
  let activeConversation = conversations.value.find((conversation) => conversation.active)
  if (!activeConversation) {
    activeConversation = createLocalConversation()
    conversations.value.unshift(activeConversation)
  }
  messages.value.push({ id: `local-message-${Date.now()}-${localConversationSequence}`, role: 'user', content: text, time: '现在' })
  inputText.value = ''
  const assistantMessageId = `local-message-${Date.now()}-${localConversationSequence + 1}`
  messages.value.push({ id: assistantMessageId, role: 'assistant', content: '', time: '现在', streaming: true })
  const context = currentQueryContext(libraryId)
  if (activeConversation && activeConversation.title === '新建技术咨询') activeConversation.title = text.slice(0, 32)
  try {
    const result = await submitQuery({
      library_id: libraryId,
      query: text,
      session_id: activeConversation?.id,
      top_k: 5,
      use_hyde: false,
      use_web_search: false,
    }, (delta) => {
      if (!isCurrentQueryContext(context, libraryId)) return
      updateAssistantMessage(assistantMessageId, {
        content: `${messages.value.find((message) => message.id === assistantMessageId)?.content || ''}${delta}`,
      })
    })
    if (!result || !isCurrentQueryContext(context, libraryId)) return
    updateAssistantMessage(assistantMessageId, { content: result.answer })
  } catch (error) {
    if (!isCurrentQueryContext(context, libraryId)) return
    inputText.value = text
    updateAssistantMessage(assistantMessageId, {
      content: error instanceof Error ? error.message : '查询失败，请稍后重试',
    })
  } finally {
    if (!isCurrentQueryContext(context, libraryId)) return
    updateAssistantMessage(assistantMessageId, { streaming: false })
  }
}

function updateAssistantMessage(messageId: string, updates: Partial<UserMessage>) {
  const messageIndex = messages.value.findIndex((message) => message.id === messageId)
  if (messageIndex < 0) return
  messages.value[messageIndex] = { ...messages.value[messageIndex], ...updates }
}

function toggleTheme() { darkMode.value = !darkMode.value }
function useSuggestion(text: string) { inputText.value = text }

watch(isLoggedIn, (loggedIn, previouslyLoggedIn) => {
  if (loggedIn === previouslyLoggedIn) return
  invalidateQueryContext()
  sessionError.value = ''
  if (loggedIn) {
    void loadConversationsForCurrentLibrary()
  } else {
    conversations.value = []
  }
})

onMounted(loadLibraries)
</script>

<template>
  <UserLayout :dark-mode="darkMode">
    <UserSidebar :collapsed="collapsed" :mobile-open="mobileSidebarOpen" :libraries="libraries" :active-library="activeLibrary" :conversations="conversations" :search-open="searchOpen" :search-query="searchQuery" :display-name="displayName" :role-label="roleLabel" :avatar-text="avatarText" @create-conversation="createConversation" @select-library="selectLibrary" @select-conversation="selectConversation" @toggle-search="searchOpen = !searchOpen" @update:search-query="searchQuery = $event" @close-mobile="mobileSidebarOpen = false" @toggle-collapse="collapsed = !collapsed" />
    <div v-if="mobileSidebarOpen" class="mobile-backdrop" @click="mobileSidebarOpen = false"></div>
    <main class="workspace"><UserTopbar :dark-mode="darkMode" :active-library="activeLibraryName" :live-data="libraries.length > 0" :logged-in="isLoggedIn" :display-name="displayName" :avatar-text="avatarText" @open-menu="mobileSidebarOpen = true" @toggle-theme="toggleTheme" @login="goToLogin" @logout="logout" /><div class="content-grid"><UserChatPanel :messages="messages" :input-text="inputText" :is-sending="isSending" :source-panel-open="sourcePanelOpen" :title="chatTitle" :source-count="sources.length" @toggle-sources="sourcePanelOpen = !sourcePanelOpen" @update:input-text="inputText = $event" @send="sendMessage" @suggestion="useSuggestion" /><UserSourcePanel :open="sourcePanelOpen" :active-library="activeLibraryName" :sources="sources" :document-count="selectedLibrary?.count || 0" :updated-at="selectedLibrary?.updatedAt || null" @close="sourcePanelOpen = false" /></div><p v-if="queryMessage" class="user-query-error">{{ queryMessage }}</p></main>
    <t-dialog v-model:visible="anonymousLimitDialogVisible" header="登录后继续咨询" confirm-btn="去登录" cancel-btn="暂不登录" @confirm="confirmLoginAfterLimit">
      <p>匿名体验已使用 3 条消息。登录后可继续使用知识库问答功能。</p>
    </t-dialog>
  </UserLayout>
</template>
