<!--
 * @FilePath: @/pages/admin/dashboard/index.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 管理端仪表盘，展示知识库、文档和用户统计
 * @BusinessRule: 会话数与回答命中率当前为 Mock 数据
 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ChatIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  FileIcon,
  TimeIcon,
  UsergroupIcon,
} from 'tdesign-icons-vue-next'
import { mysqlApi, type Library } from '../../../api/mysql'

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
const loading = ref(false)
const errorMessage = ref('')

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

/** 并行加载仪表盘统计，并向父页面同步侧栏数量。 */
async function loadOverview() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [libraryData, documentData, userData, roleData, permissionData] =
      await Promise.all([
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
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '仪表盘数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadOverview()
})
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
