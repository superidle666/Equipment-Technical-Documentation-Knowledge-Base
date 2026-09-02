<!-- 文档详情弹窗，展示元数据、标签和当前已有的 Chunk。 -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { mysqlApi, type Document, type DocumentChunk } from '../../../api/mysql'
import { formatDocumentStatus } from '../shared/formatters'

const props = defineProps<{ visible: boolean; documentId?: number }>()
const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'updated'): void
  (event: 'error', message: string): void
}>()

const detail = ref<Document>()
const chunks = ref<DocumentChunk[]>([])
const loading = ref(false)
const savingTitle = ref(false)
const savingTags = ref(false)
const errorMessage = ref('')
const titleInput = ref('')
const tagOptions = ref<Array<{ label: string; value: string }>>([])
const selectedTags = ref<string[]>([])
const tagSearch = ref('')

async function loadDetail() {
  if (!props.documentId) return
  loading.value = true
  errorMessage.value = ''
  detail.value = undefined
  chunks.value = []
  try {
    detail.value = await mysqlApi.getDocument(props.documentId)
    titleInput.value = detail.value.title
    chunks.value = await mysqlApi.listChunks(props.documentId)
    selectedTags.value = detail.value.tags || []
    const tags = await mysqlApi.listTags()
    tagOptions.value = tags.map((tag) => ({ label: tag.name, value: tag.name }))
    tagSearch.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档详情加载失败'
  } finally {
    loading.value = false
  }
}

/** 保存文档标题并通知列表刷新。 */
async function saveTitle() {
  if (!detail.value) return
  if (!titleInput.value.trim()) {
    errorMessage.value = '文档名称不能为空。'
    return
  }

  errorMessage.value = ''
  savingTitle.value = true
  try {
    const updated = await mysqlApi.updateDocument(detail.value.id, {
      title: titleInput.value.trim(),
    })
    detail.value = { ...detail.value, ...updated }
    emit('updated')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档名称保存失败'
  } finally {
    savingTitle.value = false
  }
}

/** 记录标签选择器输入，用于提示尚未创建的标签。 */
function handleTagInput(value: string) {
  tagSearch.value = value
}

/** 将首次输入的标签加入选中项，保存时由后端完成标签创建。 */
function handleTagCreate(value: string) {
  const name = value.trim()
  if (!name || selectedTags.value.includes(name)) return
  selectedTags.value = [...selectedTags.value, name]
  tagSearch.value = ''
}

function isUnknownTag(value: string) {
  const name = value.trim()
  return Boolean(name) && !tagOptions.value.some((option) => option.value === name)
}

async function saveTags() {
  if (!detail.value) return

  const names = Array.from(new Set([
    ...selectedTags.value,
    tagSearch.value,
  ].map((item) => item.trim()).filter(Boolean)))
  if (names.length > 30) {
    errorMessage.value = '每个文档最多可关联 30 个标签。'
    return
  }

  errorMessage.value = ''
  savingTags.value = true
  try {
    selectedTags.value = names
    detail.value = await mysqlApi.updateDocumentTags(detail.value.id, names)
    const tags = await mysqlApi.listTags()
    tagOptions.value = tags.map((tag) => ({ label: tag.name, value: tag.name }))
    emit('updated')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '标签保存失败'
  } finally {
    savingTags.value = false
  }
}

watch(
  () => [props.visible, props.documentId],
  ([visible]) => {
    if (visible) void loadDetail()
  },
)
</script>

<template>
  <t-dialog
    :visible="visible"
    header="文档详情"
    width="760px"
    :footer="false"
    @update:visible="emit('update:visible', $event)"
  >
    <div v-if="loading" class="admin-loading">正在加载...</div>
    <div v-else>
      <div v-if="errorMessage" class="dialog-form-error">{{ errorMessage }}</div>
      <template v-if="detail">
      <div class="detail-title-row">
        <t-input v-model="titleInput" label="文档名称" />
        <t-button
          theme="primary"
          variant="outline"
          :loading="savingTitle"
          @click="saveTitle"
        >
          保存名称
        </t-button>
      </div>
      <p class="detail-filename">原始文件：{{ detail.original_filename }}</p>
      <p class="detail-meta">
        状态：{{ formatDocumentStatus(detail.status) }}　大小：
        {{ detail.file_size === null ? '-' : `${(detail.file_size / 1024 / 1024).toFixed(2)} MB` }}
      </p>
      <div class="dialog-fields">
        <p v-if="isUnknownTag(tagSearch)" class="tag-create-hint">
          该标签未被创建, 使用该标签会自动创建标签
        </p>
        <t-select
          v-model="selectedTags"
          :options="tagOptions"
          multiple
          filterable
          creatable
          placeholder="选中或者输入标签"
          @input-change="handleTagInput"
          @create="handleTagCreate"
        />
        <t-button theme="primary" variant="outline" :loading="savingTags" @click="saveTags">
          保存标签
        </t-button>
      </div>
      <h3>Chunk 预览（{{ chunks.length }}）</h3>
      <div class="chunk-list">
        <article v-for="chunk in chunks" :key="chunk.id">
          <header>
            #{{ chunk.chunk_index }} · 第 {{ chunk.page_number || '-' }} 页 ·
            {{ chunk.token_count || 0 }} tokens
          </header>
          <p>{{ chunk.content }}</p>
          <small>向量 ID：{{ chunk.vector_id || '未生成' }}</small>
        </article>
        <p v-if="!chunks.length" class="empty-state">暂无切分内容</p>
      </div>
      </template>
    </div>
  </t-dialog>
</template>
