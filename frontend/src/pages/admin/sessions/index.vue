<!-- 管理端操作日志页面。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RefreshIcon } from 'tdesign-icons-vue-next'
import { mysqlApi, type OperationLog } from '../../../api/mysql'
import { formatTime } from '../shared/formatters'

const logs = ref<OperationLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const errorMessage = ref('')
const resourceType = ref('')
const operation = ref('')

const resourceOptions = [
  { label: '全部资源', value: '' },
  { label: '认证会话', value: 'auth_session' },
  { label: '用户', value: 'user' },
  { label: '角色', value: 'role' },
  { label: '权限', value: 'permission' },
  { label: '知识库', value: 'library' },
  { label: '文档', value: 'document' },
  { label: '标签', value: 'tag' },
]

const operationOptions = [
  { label: '全部操作', value: '' },
  { label: '登录', value: 'login' },
  { label: '退出登录', value: 'logout' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '恢复', value: 'restore' },
  { label: '上传', value: 'upload' },
]

const columns = [
  { colKey: 'operation', title: '操作', width: 120 },
  { colKey: 'resource', title: '资源', width: 170 },
  { colKey: 'actor', title: '操作者', width: 110 },
  { colKey: 'ip', title: 'IP 地址', width: 140 },
  { colKey: 'detail', title: '变更摘要' },
  { colKey: 'time', title: '时间', width: 180 },
]

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function operationLabel(value: string) {
  return ({ login: '登录', logout: '退出登录', create: '创建', update: '更新', delete: '删除', restore: '恢复', upload: '上传', update_tags: '更新标签', add_member: '添加成员', remove_member: '移除成员' } as Record<string, string>)[value] || value
}

function resourceLabel(value: string | null) {
  return ({ auth_session: '认证会话', user: '用户', role: '角色', permission: '权限', library: '知识库', document: '文档', tag: '标签', library_member: '知识库成员' } as Record<string, string>)[value || ''] || value || '-'
}

function detailText(detail: Record<string, unknown> | null) {
  if (!detail || !Object.keys(detail).length) return '-'
  return Object.entries(detail).map(([key, value]) => key + ': ' + String(value)).join('；')
}

async function loadLogs() {
  loading.value = true
  errorMessage.value = ''
  const query = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) })
  if (resourceType.value) query.set('resource_type', resourceType.value)
  if (operation.value) query.set('operation', operation.value)
  try {
    const result = await mysqlApi.listLogs(query.toString())
    logs.value = result.items
    total.value = result.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '操作日志加载失败'
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  void loadLogs()
}

function changePage(next: number) {
  page.value = Math.min(Math.max(1, next), pageCount.value)
  void loadLogs()
}

onMounted(() => { void loadLogs() })
</script>

<template>
  <section class="admin-module">
    <div class="admin-page-head compact">
      <div>
        <div class="eyebrow">AUDIT LOGS</div>
        <h1>操作日志</h1>
        <p>追踪后台关键操作、操作者和资源变更摘要。</p>
      </div>
      <t-button variant="outline" :loading="loading" @click="loadLogs">
        <RefreshIcon />
        刷新
      </t-button>
    </div>

    <div class="toolbar log-toolbar">
      <t-select v-model="resourceType" :options="resourceOptions" placeholder="资源类型" class="log-filter" @change="search" />
      <t-select v-model="operation" :options="operationOptions" placeholder="操作类型" class="log-filter" @change="search" />
    </div>

    <div v-if="errorMessage" class="admin-error">
      {{ errorMessage }}
      <button @click="loadLogs">重试</button>
    </div>
    <div v-if="loading" class="admin-loading">正在加载操作日志...</div>

    <div class="panel table-panel">
      <t-table :data="logs" :columns="columns" row-key="id" :loading="loading">
        <template #operation="{ row }">
          <t-tag variant="light" theme="primary">{{ operationLabel(row.operation) }}</t-tag>
        </template>
        <template #resource="{ row }">
          <span>{{ resourceLabel(row.resource_type) }}<template v-if="row.resource_id"> #{{ row.resource_id }}</template></span>
        </template>
        <template #actor="{ row }">{{ row.user_display_name || (row.user_id ? '用户 #' + row.user_id : '-') }}</template>
        <template #ip="{ row }">{{ row.request_ip || '-' }}</template>
        <template #detail="{ row }"><span class="log-detail">{{ detailText(row.detail) }}</span></template>
        <template #time="{ row }">{{ formatTime(row.created_at, true) }}</template>
      </t-table>
      <div class="log-pagination">
        <span>共 {{ total }} 条</span>
        <t-button variant="text" size="small" :disabled="page <= 1" @click="changePage(page - 1)">上一页</t-button>
        <span>{{ page }} / {{ pageCount }}</span>
        <t-button variant="text" size="small" :disabled="page >= pageCount" @click="changePage(page + 1)">下一页</t-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.log-toolbar { justify-content: flex-start; }
.log-filter { width: 180px; }
.log-detail { color: #6b7280; }
.log-pagination { min-height: 52px; padding: 0 16px; display: flex; align-items: center; justify-content: flex-end; gap: 8px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }
</style>
