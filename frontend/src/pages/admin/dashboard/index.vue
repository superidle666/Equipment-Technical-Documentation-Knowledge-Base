<!--
 * @FilePath: @/pages/admin/dashboard/index.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 管理端仪表盘，展示知识库、文档和用户统计
 * @BusinessRule: 会话数与回答命中率当前为 Mock 数据
 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ChatIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  FileIcon,
  TimeIcon,
  UsergroupIcon,
} from 'tdesign-icons-vue-next'
import { mysqlApi, type Library } from '../../../api/mysql'
import { useRequest } from '../../../composables'

const emit = defineEmits<{
  (event: 'navigate', key: 'documents'): void
  (event: 'update-counts', counts: {
    documents: number
    users: number
    roles: number
    permissions: number
  }): void
}>()

const libraries = ref<Library[]>([])
const documentCount = ref(0)
const userCount = ref(0)
const overviewRequest = useRequest(async () => {
  const [libraryData, documentData, userData, roleData, permissionData] = await Promise.all([
    mysqlApi.listLibraries(true),
    mysqlApi.listDocuments(),
    mysqlApi.listUsers(),
    mysqlApi.listRoles(),
    mysqlApi.listPermissions(),
  ])

  libraries.value = libraryData
  documentCount.value = documentData.length
  userCount.value = userData.length
  emit('update-counts', {
    documents: documentData.length,
    users: userData.length,
    roles: roleData.length,
    permissions: permissionData.length,
  })
}, { immediate: true })
const loading = overviewRequest.loading
const errorMessage = computed(() => overviewRequest.error.value?.message || '')

const libraryBarData = computed(() => {
  return libraries.value.map((library) => ({
    name: library.name,
    count: library.document_count,
    color: library.cover_color || '#2563eb',
  }))
})

const maxLibraryCount = computed(() => {
  return Math.max(1, ...libraryBarData.value.map((item) => item.count))
})

/** 将知识库文档量换算为相对进度条宽度。 */
function getBarWidth(count: number) {
  return `${Math.round((count / maxLibraryCount.value) * 100)}%`
}

/** 刷新仪表盘统计，并向父页面同步侧栏数量。 */
async function loadOverview() {
  try {
    await overviewRequest.execute()
  } catch {
    // Error is exposed through the composable for the template.
  }
}
</script>

<template>
  <section class="admin-module">
    <div class="admin-page-head">
      <div>
        <div class="eyebrow">OVERVIEW</div>
        <h1>仪表盘</h1>
        <p>欢迎回来，系统管理员。这里是知识库运行概况。</p>
      </div>
      <t-button theme="primary" @click="emit('navigate', 'documents')">
        <FileIcon />
        管理文档
      </t-button>
    </div>

    <div v-if="errorMessage" class="admin-error">
      {{ errorMessage }}
      <button @click="loadOverview">重试</button>
    </div>
    <div v-if="loading" class="admin-loading">正在加载仪表盘数据...</div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon blue"><FileIcon /></div>
        <div>
          <span>知识库文档</span>
          <strong>{{ documentCount }}</strong>
          <em>当前已入库</em>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><UsergroupIcon /></div>
        <div>
          <span>平台用户</span>
          <strong>{{ userCount }}</strong>
          <em>当前可用账户</em>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon orange"><ChatIcon /></div>
        <div>
          <span>本月会话</span>
          <strong>3,842</strong>
          <em>Mock 统计数据</em>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon purple"><CheckCircleIcon /></div>
        <div>
          <span>回答命中率</span>
          <strong>92.6%</strong>
          <em>Mock 统计数据</em>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>知识库分布</h2>
            <p>各知识库文档数量</p>
          </div>
          <t-button variant="text" size="small" @click="emit('navigate', 'documents')">
            查看详情
            <ChevronRightIcon />
          </t-button>
        </div>
        <div class="library-bars">
          <div v-for="item in libraryBarData" :key="item.name" class="bar-row">
            <div>
              <span class="bar-dot" :style="{ background: item.color }" />
              {{ item.name }}
              <strong>{{ item.count }}</strong>
            </div>
            <div class="bar-track">
              <span :style="{ width: getBarWidth(item.count), background: item.color }" />
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>最近活动</h2>
            <p>系统近期操作记录</p>
          </div>
          <TimeIcon class="panel-icon" />
        </div>
        <div class="activity-list">
          <div class="activity">
            <span class="activity-dot blue" />
            <div>
              <strong>林工完成了一次技术咨询</strong>
              <p>HAK180 转印温度怎么调？</p>
            </div>
            <time>10:24</time>
          </div>
          <div class="activity">
            <span class="activity-dot green" />
            <div>
              <strong>新增文档《LA2608 网关配置说明》</strong>
              <p>网络设备资料</p>
            </div>
            <time>09:18</time>
          </div>
          <div class="activity">
            <span class="activity-dot orange" />
            <div>
              <strong>张师傅登录了系统</strong>
              <p>IP：192.168.1.108</p>
            </div>
            <time>08:30</time>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.stat-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 22px; }
.stat-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 7px; padding: 18px; display: flex; align-items: flex-start; gap: 13px; }
.stat-icon { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 7px; flex: 0 0 auto; }
.stat-icon svg { width: 17px; }
.stat-icon.blue { color: #2563eb; background: #eff6ff; }
.stat-icon.green { color: #0f9d78; background: #ecfdf5; }
.stat-icon.orange { color: #c47f1d; background: #fffbeb; }
.stat-icon.purple { color: #7c3aed; background: #f5f3ff; }
.stat-card div:last-child { display: grid; gap: 4px; }
.stat-card span { color: #6b7280; font-size: 11px; }
.stat-card strong { font-size: 23px; line-height: 1.1; }
.stat-card em { color: #15803d; font-size: 10px; font-style: normal; }
.dashboard-grid { display: grid; grid-template-columns: 1.15fr .85fr; gap: 16px; }
.library-bars { padding: 20px; display: grid; gap: 20px; }
.bar-row > div:first-child { display: flex; align-items: center; gap: 8px; font-size: 12px; margin-bottom: 8px; }
.bar-row strong { margin-left: auto; font-size: 12px; }
.bar-dot { width: 7px; height: 7px; border-radius: 50%; }
.bar-track { height: 7px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.bar-track span { display: block; height: 100%; border-radius: 4px; }
.activity-list { padding: 7px 20px; }
.activity { display: grid; grid-template-columns: 8px 1fr auto; align-items: start; gap: 10px; padding: 14px 0; border-bottom: 1px solid #f1f5f9; }
.activity:last-child { border-bottom: 0; }
.activity-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; }
.activity-dot.blue { background: #2563eb; }
.activity-dot.green { background: #0f9d78; }
.activity-dot.orange { background: #c47f1d; }
.activity strong { font-size: 12px; font-weight: 600; }
.activity p { color: #9ca3af; font-size: 11px; margin: 4px 0 0; }
.activity time { color: #9ca3af; font-size: 10px; white-space: nowrap; }
@media (max-width: 1100px) { .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .dashboard-grid { grid-template-columns: 1fr; } }
@media (max-width: 480px) { .stat-grid { grid-template-columns: 1fr 1fr; gap: 9px; } .stat-card { padding: 12px; gap: 8px; } .stat-icon { width: 28px; height: 28px; } .stat-card strong { font-size: 18px; } .stat-card em { font-size: 9px; } }
</style>
