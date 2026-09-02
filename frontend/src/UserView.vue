<!--
 * @FilePath: @/UserView.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 用户端知识库问答工作台，包含会话、回答和来源面板
 * @BusinessRule: 当前问答内容和主题切换均为前端 Mock 状态
 -->
<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { marked } from 'marked'
import {
  AddIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CopyIcon,
  FileIcon,
  LightbulbIcon,
  LinkIcon,
  MoonIcon,
  SearchIcon,
  SendIcon,
  SettingIcon,
  ThumbUpIcon,
  UserIcon,
  ViewListIcon,
} from 'tdesign-icons-vue-next'

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  streaming?: boolean
}

type Conversation = { id: number; title: string; time: string; active?: boolean }

const darkMode = ref(false)
const collapsed = ref(false)
const mobileSidebarOpen = ref(false)
const sourcePanelOpen = ref(true)
const searchOpen = ref(false)
const query = ref('')
const isSending = ref(false)
const webSearch = ref(false)
const activeLibrary = ref('工业设备手册')
const inputText = ref('')

const libraries = [
  { name: '工业设备手册', count: 1284, color: '#2563eb' },
  { name: '网络设备资料', count: 486, color: '#0f9d78' },
  { name: '售后服务知识', count: 356, color: '#c47f1d' },
]

const conversations = ref<Conversation[]>([
  { id: 1, title: 'HAK180 转印温度怎么调？', time: '刚刚', active: true },
  { id: 2, title: 'LA2608 网关如何恢复出厂设置', time: '昨天' },
  { id: 3, title: '设备日常保养周期', time: '8 月 28 日' },
  { id: 4, title: '伺服电机报警代码 E-17', time: '8 月 26 日' },
])

const messages = ref<Message[]>([
  {
    id: 1,
    role: 'user',
    content: 'Brother HAK180 烫金机的转印温度怎么调？',
    time: '10:24',
  },
  {
    id: 2,
    role: 'assistant',
    content:
      'HAK180 的转印温度需要根据材料类型进行调整。建议先从 **110°C** 开始测试，再按照以下步骤微调：\n\n1. 在操作面板选择「温度设定」，设定目标温度并等待实际温度稳定。\n2. 使用同批次材料试印 2-3 次，观察图案是否完整、边缘是否清晰。\n3. 若图案不牢固，可每次上调 5°C；出现粘版或变形时，下调 5°C。\n\n常用材料的参考范围：\n- PVC / PU：105-120°C\n- 纸张：95-110°C\n- 涤纶织物：120-135°C\n\n每次调节后请等待约 30 秒再进行下一次试印。',
    time: '10:24',
  },
])

const sources = [
  { title: 'HAK180 用户手册', type: 'PDF · 第 42-43 页', score: '98%', color: '#2563eb' },
  { title: 'HAK180 维护指南', type: 'PDF · 第 18 页', score: '91%', color: '#0f9d78' },
  { title: '设备厂商技术支持中心', type: '网页资料 · 2024-06', score: '84%', color: '#c47f1d' },
]

const filteredConversations = computed(() => {
  const value = query.value.trim().toLowerCase()
  return value ? conversations.value.filter((item) => item.title.toLowerCase().includes(value)) : conversations.value
})

/** 将助手 Markdown 内容转换为可渲染的 HTML。 */
const renderMarkdown = (value: string) => marked.parse(value, { breaks: true }) as string

/** 选择历史会话并关闭移动端侧栏。 */
function selectConversation(item: Conversation) {
  conversations.value.forEach((conversation) => (conversation.active = conversation.id === item.id))
  mobileSidebarOpen.value = false
}

/** 创建空白会话并清空当前消息。 */
function createConversation() {
  conversations.value.unshift({ id: Date.now(), title: '新建技术咨询', time: '刚刚', active: true })
  messages.value = []
  inputText.value = ''
  mobileSidebarOpen.value = false
}

/** 发送问题并以逐字方式模拟助手回答。 */
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isSending.value) return
  messages.value.push({ id: Date.now(), role: 'user', content: text, time: '现在' })
  inputText.value = ''
  isSending.value = true
  await nextTick()
  const answer = '根据当前知识库资料，建议先确认设备处于待机状态，并按照对应型号的操作手册逐项排查。你可以告诉我设备的具体报警代码或现象，我会继续帮你定位。'
  const assistant: Message = { id: Date.now() + 1, role: 'assistant', content: '', time: '现在', streaming: true }
  messages.value.push(assistant)
  for (const char of answer) {
    await new Promise((resolve) => setTimeout(resolve, 12))
    assistant.content += char
  }
  assistant.streaming = false
  isSending.value = false
}

/** 将推荐问题填入输入框，等待用户确认发送。 */
function useSuggestion(text: string) {
  inputText.value = text
}

/** 在浅色和深色主题之间切换本地状态。 */
function toggleTheme() {
  darkMode.value = !darkMode.value
}
</script>

<template>
  <div class="app-shell" :class="{ 'is-dark': darkMode }">
    <aside class="sidebar" :class="{ collapsed, 'is-mobile-open': mobileSidebarOpen }">
      <div class="brand-row">
        <div class="brand-mark">工</div>
        <div v-if="!collapsed" class="brand-copy"><strong>工智库</strong><span>设备技术知识平台</span></div>
        <t-button v-if="!collapsed" variant="text" shape="square" class="sidebar-close" @click="mobileSidebarOpen = false"><ChevronLeftIcon /></t-button>
      </div>
      <div class="sidebar-content">
        <t-button theme="primary" block class="new-chat" @click="createConversation"><AddIcon /><span v-if="!collapsed">新建咨询</span></t-button>
        <nav class="nav-list">
          <div class="nav-label" v-if="!collapsed">工作台</div>
          <button class="nav-item active"><ViewListIcon /><span v-if="!collapsed">知识库</span><span v-if="!collapsed" class="nav-count">{{ libraries.length }}</span></button><div v-if="!collapsed" class="library-list"><button v-for="library in libraries" :key="library.name" class="library-item" :class="{ selected: activeLibrary === library.name }" @click="activeLibrary = library.name"><span class="library-dot" :style="{ background: library.color }"></span><span>{{ library.name }}</span><small>{{ library.count }}</small></button></div>
          <button class="nav-item" @click="searchOpen = !searchOpen"><SearchIcon /><span v-if="!collapsed">搜索会话</span></button>
        </nav>
        <div v-if="!collapsed" class="conversation-section">
          <div class="section-heading"><span>最近会话</span><button title="刷新会话"><ChevronRightIcon /></button></div>
          <div v-if="searchOpen" class="search-box"><SearchIcon /><input v-model="query" placeholder="搜索会话" /></div>
          <button v-for="item in filteredConversations" :key="item.id" class="conversation-item" :class="{ selected: item.active }" @click="selectConversation(item)">
            <span class="conversation-dot"></span><span class="conversation-title">{{ item.title }}</span><span class="conversation-time">{{ item.time }}</span>
          </button>
        </div>
      </div>
      <div class="sidebar-footer">
        <div class="user-card"><div class="avatar small">林</div><div v-if="!collapsed" class="user-copy"><strong>林工</strong><span>技术工程师</span></div><SettingIcon v-if="!collapsed" class="setting-icon" /></div>
        <button class="collapse-button" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="collapsed = !collapsed"><ChevronRightIcon v-if="collapsed" /><ChevronLeftIcon v-else /></button>
      </div>
    </aside>
    <div v-if="mobileSidebarOpen" class="mobile-backdrop" @click="mobileSidebarOpen = false"></div>

    <main class="workspace">
      <header class="topbar">
        <div class="topbar-left"><t-button variant="text" shape="square" class="mobile-menu" @click="mobileSidebarOpen = true"><ViewListIcon /></t-button><span class="workspace-label">用户端</span><span class="divider"></span><button class="library-selector"><span class="library-dot"></span>{{ activeLibrary }}<ChevronDownIcon /></button></div>
        <div class="topbar-right"><span class="mock-badge"><span class="pulse-dot"></span> Mock 数据</span><t-button variant="text" shape="square" :title="darkMode ? '切换浅色模式' : '切换深色模式'" @click="toggleTheme"><MoonIcon v-if="!darkMode" /><LightbulbIcon v-else /></t-button><div class="avatar">林</div></div>
      </header>

      <div class="content-grid">
        <section class="chat-panel">
          <div class="chat-head"><div><div class="eyebrow">知识库咨询</div><h1>HAK180 转印温度怎么调？</h1></div><div class="chat-actions"><t-button variant="outline" size="small" @click="sourcePanelOpen = !sourcePanelOpen"><LinkIcon /> <span class="source-toggle-label">{{ sourcePanelOpen ? '隐藏来源' : '查看来源' }}</span></t-button></div></div>
          <div class="chat-scroll">
            <div v-if="messages.length === 0" class="empty-chat"><div class="empty-icon">工</div><h2>开始一次新的技术咨询</h2><p>从设备型号、故障代码或操作方法开始提问。</p></div>
            <template v-else>
              <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
                <div class="message-avatar" :class="message.role"><UserIcon v-if="message.role === 'user'" /><span v-else>工</span></div>
                <div class="message-body"><div class="message-meta"><strong>{{ message.role === 'user' ? '林工' : '工智库助手' }}</strong><span>{{ message.time }}</span><span v-if="message.role === 'assistant'" class="source-tag">基于 3 个来源</span></div><div v-if="message.role === 'assistant'" class="markdown-content" v-html="renderMarkdown(message.content)"></div><div v-else class="user-text">{{ message.content }}</div><div v-if="message.streaming" class="typing-indicator"><i></i><i></i><i></i></div><div v-if="message.role === 'assistant' && !message.streaming" class="message-tools"><t-button variant="text" size="small"><CopyIcon />复制</t-button><t-button variant="text" size="small"><ThumbUpIcon />有帮助</t-button></div></div>
              </div>
            </template>
            <div v-if="messages.length" class="suggestions"><span>你还可以问</span><button @click="useSuggestion('HAK180 的日常维护有哪些注意事项？')">HAK180 的日常维护有哪些注意事项？</button><button @click="useSuggestion('转印压力应该如何设置？')">转印压力应该如何设置？</button></div>
          </div>
          <div class="composer-wrap"><div class="composer"><textarea v-model="inputText" rows="1" placeholder="输入设备型号、故障代码或你的问题..." @keydown.enter.exact.prevent="sendMessage"></textarea><div class="composer-bottom"><div class="composer-hints"><label class="switch-label"><t-switch v-model="webSearch" size="small" /><span>联网搜索</span></label><span class="hint-text">内容将基于当前知识库回答</span></div><t-button theme="primary" :disabled="!inputText.trim() || isSending" @click="sendMessage"><SendIcon />发送</t-button></div></div><div class="privacy-note">工智库可能会产生不准确的信息，请结合设备手册进行确认</div></div>
        </section>

        <aside v-if="sourcePanelOpen" class="source-panel"><div class="source-head"><div><div class="eyebrow">检索上下文</div><h2>回答来源</h2></div><t-button variant="text" shape="square" title="关闭来源" @click="sourcePanelOpen = false">×</t-button></div><div class="source-summary"><span class="summary-icon">✓</span><div><strong>已找到 3 个相关来源</strong><p>回答内容经过本地知识库检索</p></div></div><div class="source-list"><article v-for="source in sources" :key="source.title" class="source-card"><div class="source-card-top"><div class="file-icon" :style="{ background: source.color + '16', color: source.color }"><FileIcon /></div><span class="score">{{ source.score }}</span></div><h3>{{ source.title }}</h3><p>{{ source.type }}</p><button>查看文档 <ChevronRightIcon /></button></article></div><div class="online-section"><div class="section-heading"><span>联网资料</span><span class="optional">已关闭</span></div><div class="online-empty"><LinkIcon /><p>打开「联网搜索」后，将补充公开技术资料</p></div></div><div class="library-status"><div class="section-heading"><span>当前知识库</span><span class="status-ok">正常</span></div><div class="status-row"><span class="library-dot"></span><strong>{{ activeLibrary }}</strong><span class="doc-count">1,284 份文档</span></div><div class="status-progress"><span></span></div><p>最后更新于今天 09:42</p></div></aside>
      </div>
    </main>
  </div>
</template>
