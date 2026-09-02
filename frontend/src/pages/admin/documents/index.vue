<!-- 文档管理：文件上传、元数据维护、标签关联和 Chunk 预览。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AddIcon, EditIcon, FileIcon, SearchIcon } from 'tdesign-icons-vue-next'
import {
  mysqlApi,
  type Library,
} from '../../../api/mysql'
import { mapDocument, type DocumentRow } from '../shared/formatters'
import DocumentDetailDialog from './DocumentDetailDialog.vue'
import DocumentUploadDialog from './DocumentUploadDialog.vue'
import LibraryManagerDialog from './LibraryManagerDialog.vue'
import TagManagerDialog from './TagManagerDialog.vue'

const emit = defineEmits<{
  (event: 'update-counts', counts: { documents: number }): void
}>()
const libraries = ref<Library[]>([])
const documents = ref<DocumentRow[]>([])
const search = ref('')
const selectedLibrary = ref('全部知识库')
const selectedTags = ref<string[]>([])
const tags = ref<Array<{ id: number; name: string }>>([])
const loading = ref(false)
const errorMessage = ref('')
const documentAction = ref<{ id: number; type: 'status' | 'delete' }>()
const showUpload = ref(false)
const showDetail = ref(false)
const selectedDocumentId = ref<number>()
const showLibraryManager = ref(false)
const showTagManager = ref(false)

const columns = [
  { colKey: 'name', title: '文档名称', width: 280 },
  { colKey: 'library', title: '所属知识库' },
  { colKey: 'type', title: '类型', width: 90, align: 'center' },
  { colKey: 'size', title: '大小', width: 110, align: 'center' },
  { colKey: 'updated', title: '更新时间', width: 160, align: 'center' },
  { colKey: 'statusLabel', title: '状态', width: 100, align: 'center' },
  { colKey: 'tags', title: '标签', width: 180 },
  { colKey: 'op', title: '操作', width: 190, align: 'center' },
]
const libraryTabs = computed(() => [
  '全部知识库',
  ...libraries.value
    .filter((item) => item.status === 'active' && !item.deleted_at)
    .map((item) => item.name),
])
const libraryOptions = computed(() =>
  libraries.value
    .filter((item) => item.status === 'active' && !item.deleted_at)
    .map((item) => ({ label: item.name, value: item.id })),
)
const tagOptions = computed(() => tags.value.map((tag) => ({ label: tag.name, value: tag.name })))
const filteredDocuments = computed(() => {
  const query = search.value.trim().toLowerCase()
  return documents.value.filter((item) => {
    const matchesSearch = !query || item.name.toLowerCase().includes(query)
    const matchesLibrary =
      selectedLibrary.value === '全部知识库' || item.library === selectedLibrary.value
    const matchesTags =
      !selectedTags.value.length ||
      selectedTags.value.every((tag) => item.tags?.includes(tag))
    return matchesSearch && matchesLibrary && matchesTags
  })
})

function getDocumentTheme(row: DocumentRow) {
  if (row.status === 'published') return 'success'
  if (row.status === 'failed') return 'danger'
  return 'warning'
}
async function loadDocuments() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [libraryData, documentData, tagData] = await Promise.all([
      mysqlApi.listLibraries(true, true),
      mysqlApi.listDocuments(),
      mysqlApi.listTags(),
    ])
    libraries.value = libraryData
    if (
      selectedLibrary.value !== '全部知识库' &&
      !libraryData.some(
        (library) =>
          library.status === 'active' &&
          !library.deleted_at &&
          library.name === selectedLibrary.value,
      )
    ) {
      selectedLibrary.value = '全部知识库'
    }
    tags.value = tagData
    selectedTags.value = selectedTags.value.filter((selectedTag) =>
      tagData.some((tag) => tag.name === selectedTag),
    )
    // 文档列表只展示启用知识库中的文档；重新启用知识库后文档会恢复显示。
    const activeLibraryIds = new Set(
      libraryData
        .filter((library) => library.status === 'active' && !library.deleted_at)
        .map((library) => library.id),
    )
    documents.value = documentData
      .filter((document) => activeLibraryIds.has(document.library_id))
      .map((document) => mapDocument(document, libraryData))
    emit('update-counts', { documents: documents.value.length })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档加载失败'
  } finally {
    loading.value = false
  }
}
function openDetail(row: DocumentRow) {
  selectedDocumentId.value = row.id
  showDetail.value = true
}
function showError(message: string) {
  errorMessage.value = message
}
/** 发布或下架文档；接口失败时保留当前列表并显示可重试提示。 */
async function togglePublish(row: DocumentRow) {
  if (documentAction.value) return

  const status = row.status === 'published' ? 'uploaded' : 'published'
  documentAction.value = { id: row.id, type: 'status' }
  try {
    await mysqlApi.updateDocument(row.id, { status })
    await loadDocuments()
  } catch (error) {
    showError(error instanceof Error ? error.message : '文档状态更新失败')
  } finally {
    documentAction.value = undefined
  }
}

/** 删除文档前二次确认；失败时不会从当前列表中移除。 */
async function deleteDocument(row: DocumentRow) {
  if (documentAction.value) return
  if (!window.confirm(`确定删除文档“${row.name}”吗？删除后不可在列表中查看。`)) return

  documentAction.value = { id: row.id, type: 'delete' }
  try {
    await mysqlApi.deleteDocument(row.id)
    await loadDocuments()
  } catch (error) {
    showError(error instanceof Error ? error.message : '文档删除失败')
  } finally {
    documentAction.value = undefined
  }
}
function handleLibraryUpdated(library?: Library) {
  void loadDocuments().then(() => {
    if (library && library.status === 'active' && !library.deleted_at) {
      selectedLibrary.value = library.name
      return
    }
    if (library && selectedLibrary.value === library.name) {
      selectedLibrary.value = '全部知识库'
    }
  })
}
function handleTagUpdated() {
  void loadDocuments()
}
onMounted(() => void loadDocuments())
</script>

<template>
  <section class="admin-module">
    <div class="admin-page-head compact">
      <div><div class="eyebrow">KNOWLEDGE BASE</div><h1>文档管理</h1><p>上传、整理和维护设备技术资料。</p></div>
      <t-button theme="primary" class="create-action" @click="showUpload = true"><AddIcon />新增文档</t-button>
    </div>
    <div v-if="errorMessage" class="admin-error">{{ errorMessage }}<button @click="loadDocuments">重试</button></div>
    <div v-if="loading" class="admin-loading">正在加载文档数据...</div>
    <div class="toolbar">
      <div class="library-filter">
        <div class="library-tabs"><button v-for="library in libraryTabs" :key="library" :class="{ active: selectedLibrary === library }" @click="selectedLibrary = library">{{ library }}</button></div>
        <t-button theme="primary" size="small" class="metadata-action-button" @click="showLibraryManager = true">
          <template #icon><FileIcon /></template>
          知识库管理
        </t-button>
      </div>
      <div class="document-filters">
        <t-select v-model="selectedTags" :options="tagOptions" multiple filterable clearable placeholder="按标签筛选" class="tag-filter" />
        <t-button theme="primary" size="small" class="metadata-action-button" @click="showTagManager = true">
          <template #icon><EditIcon /></template>
          标签管理
        </t-button>
        <t-input v-model="search" placeholder="搜索文档名称" class="table-search"><template #prefix-icon><SearchIcon /></template></t-input>
      </div>
    </div>
    <div class="panel table-panel">
      <t-table :data="filteredDocuments" :columns="columns" row-key="id" bordered="false">
        <template #name="{ row }"><div class="doc-name"><FileIcon />{{ row.name }}</div></template>
        <template #statusLabel="{ row }"><t-tag :theme="getDocumentTheme(row)" variant="light">{{ row.statusLabel }}</t-tag></template>
        <template #tags="{ row }"><div class="document-tags"><t-tag v-for="tag in row.tags || []" :key="tag" variant="light-outline">{{ tag }}</t-tag><span v-if="!row.tags?.length">-</span></div></template>
        <template #op="{ row }">
          <div class="table-actions table-actions--multiple">
            <t-button
              variant="text"
              size="small"
              class="edit-action"
              :disabled="Boolean(documentAction)"
              @click="openDetail(row)"
            >详情</t-button>
            <t-button
              variant="text"
              size="small"
              :loading="documentAction?.id === row.id && documentAction?.type === 'status'"
              :disabled="Boolean(documentAction) && documentAction?.id !== row.id"
              @click="togglePublish(row)"
            >{{ row.status === 'published' ? '下架' : '发布' }}</t-button>
            <t-button
              variant="text"
              theme="danger"
              size="small"
              :loading="documentAction?.id === row.id && documentAction?.type === 'delete'"
              :disabled="Boolean(documentAction) && documentAction?.id !== row.id"
              @click="deleteDocument(row)"
            >删除</t-button>
          </div>
        </template>
      </t-table>
    </div>
    <DocumentUploadDialog
      v-model:visible="showUpload"
      :library-options="libraryOptions"
      @uploaded="loadDocuments"
      @error="showError"
    />
    <DocumentDetailDialog
      v-model:visible="showDetail"
      :document-id="selectedDocumentId"
      @updated="loadDocuments"
      @error="showError"
    />
    <LibraryManagerDialog
      v-model:visible="showLibraryManager"
      :libraries="libraries"
      @updated="handleLibraryUpdated"
      @error="showError"
    />
    <TagManagerDialog
      v-model:visible="showTagManager"
      @updated="handleTagUpdated"
      @error="showError"
    />
  </section>
</template>
