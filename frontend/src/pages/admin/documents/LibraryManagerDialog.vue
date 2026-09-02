<!-- 知识库管理弹窗：分离新增、行内编辑、状态切换和软删除操作。 -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { mysqlApi, type Library } from '../../../api/mysql'

const props = defineProps<{ visible: boolean; libraries: Library[] }>()
const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'updated', library?: Library): void
  (event: 'error', message: string): void
}>()

const createName = ref('')
const createCode = ref('')
const createDescription = ref('')
const editingId = ref<number>()
const editName = ref('')
const editDescription = ref('')
const creating = ref(false)
const savingEdit = ref(false)
const changingStatusId = ref<number>()
const deletingId = ref<number>()
const errorMessage = ref('')

/** 只清空新增知识库表单，不影响正在编辑的知识库。 */
function resetCreateForm() {
  createName.value = ''
  createCode.value = ''
  createDescription.value = ''
}

/** 打开指定知识库下方的独立编辑表单。 */
function startEdit(library: Library) {
  if (library.deleted_at) return
  editingId.value = library.id
  editName.value = library.name
  editDescription.value = library.description || ''
}

/** 关闭行内编辑并清除临时编辑值。 */
function cancelEdit() {
  editingId.value = undefined
  editName.value = ''
  editDescription.value = ''
}

/** 根据名称生成符合后端约束的知识库编码。 */
function createLibraryCode(value: string) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  return normalized || `library-${Date.now()}`
}

/** 创建知识库，成功后仅重置新增表单。 */
async function createLibrary() {
  const name = createName.value.trim()
  if (!name) {
    errorMessage.value = '请输入知识库名称。'
    return
  }

  errorMessage.value = ''
  creating.value = true
  try {
    const library = await mysqlApi.createLibrary({
      name,
      code: createCode.value.trim() || createLibraryCode(name),
      description: createDescription.value.trim() || null,
    })
    resetCreateForm()
    emit('updated', library)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库创建失败'
  } finally {
    creating.value = false
  }
}

/** 保存当前行的知识库名称和描述。 */
async function saveLibraryEdit() {
  if (!editingId.value) return
  if (!editName.value.trim()) {
    errorMessage.value = '请输入知识库名称。'
    return
  }

  errorMessage.value = ''
  savingEdit.value = true
  try {
    await mysqlApi.updateLibrary(editingId.value, {
      name: editName.value.trim(),
      description: editDescription.value.trim() || null,
    })
    cancelEdit()
    emit('updated')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库修改失败'
  } finally {
    savingEdit.value = false
  }
}

/** 在启用和停用状态之间切换，不改变软删除状态。 */
async function toggleLibraryStatus(library: Library) {
  const status = library.status === 'active' ? 'disabled' : 'active'
  errorMessage.value = ''
  changingStatusId.value = library.id
  try {
    const updatedLibrary = await mysqlApi.updateLibrary(library.id, { status })
    emit('updated', updatedLibrary)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库状态更新失败'
  } finally {
    changingStatusId.value = undefined
  }
}

/** 恢复旧版本中已软删除的知识库及其原有文档归属。 */
async function restoreLibrary(library: Library) {
  errorMessage.value = ''
  changingStatusId.value = library.id
  try {
    const restoredLibrary = await mysqlApi.restoreLibrary(library.id)
    emit('updated', restoredLibrary)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库恢复失败'
  } finally {
    changingStatusId.value = undefined
  }
}

/** 仅删除没有有效文档的空知识库。 */
async function deleteLibrary(library: Library) {
  if (library.document_count > 0) return
  if (!window.confirm(`确定删除空知识库“${library.name}”吗？`)) return
  errorMessage.value = ''
  deletingId.value = library.id
  try {
    await mysqlApi.deleteLibrary(library.id)
    if (editingId.value === library.id) cancelEdit()
    emit('updated')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库删除失败'
  } finally {
    deletingId.value = undefined
  }
}

function getStatusLabel(library: Library) {
  if (library.deleted_at) return '已删除'
  return library.status === 'active' ? '已启用' : '已停用'
}

function getStatusTheme(library: Library): 'danger' | 'success' | 'warning' {
  if (library.deleted_at) return 'danger'
  return library.status === 'active' ? 'success' : 'warning'
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    resetCreateForm()
    cancelEdit()
    errorMessage.value = ''
  },
)
</script>

<template>
  <t-dialog
    :visible="visible"
    header="知识库管理"
    width="720px"
    :footer="false"
    @update:visible="emit('update:visible', $event)"
  >
    <p v-if="errorMessage" class="dialog-form-error">{{ errorMessage }}</p>
    <section class="library-create-section">
      <h3>新增知识库</h3>
      <div class="dialog-fields">
        <t-input v-model="createName" label="知识库名称" placeholder="例如：工业设备资料" />
        <t-input v-model="createCode" label="编码（可选）" placeholder="例如：industrial-equipment" />
        <t-textarea
          v-model="createDescription"
          label="描述"
          placeholder="知识库用途说明（可选）"
        />
      </div>
      <div class="library-form-actions">
        <t-button variant="outline" @click="resetCreateForm">清空新增内容</t-button>
        <t-button theme="primary" :loading="creating" @click="createLibrary">
          新增知识库
        </t-button>
      </div>
    </section>

    <section class="library-list-section">
      <h3>现有知识库</h3>
      <div class="library-manager-list">
        <div
          v-for="library in libraries"
          :key="library.id"
          class="library-manager-entry"
        >
          <div class="library-manager-item">
            <div>
              <strong>{{ library.name }}</strong>
              <span>{{ library.code }} · {{ library.document_count }} 篇文档</span>
              <p v-if="library.description" class="library-description">
                说明：{{ library.description }}
              </p>
            </div>
            <div class="library-manager-actions">
              <t-tag :theme="getStatusTheme(library)" variant="light">
                {{ getStatusLabel(library) }}
              </t-tag>
              <template v-if="library.deleted_at">
                <t-button
                  variant="text"
                  class="edit-action"
                  size="small"
                  :loading="changingStatusId === library.id"
                  @click="restoreLibrary(library)"
                >恢复</t-button>
              </template>
              <template v-else>
                <t-button
                  variant="text"
                  class="edit-action"
                  size="small"
                  @click="startEdit(library)"
                >编辑</t-button>
                <t-button
                  variant="text"
                  class="edit-action"
                  size="small"
                  :loading="changingStatusId === library.id"
                  @click="toggleLibraryStatus(library)"
                >{{ library.status === 'active' ? '停用' : '启用' }}</t-button>
                <t-button
                  variant="text"
                  theme="danger"
                  size="small"
                  :disabled="library.document_count > 0"
                  :loading="deletingId === library.id"
                  :title="library.document_count > 0 ? '请先迁移或删除知识库中的文档' : '删除空知识库'"
                  @click="deleteLibrary(library)"
                >删除</t-button>
              </template>
            </div>
          </div>

          <div v-if="editingId === library.id" class="library-inline-edit">
            <h4>编辑“{{ library.name }}”</h4>
            <t-input v-model="editName" label="知识库名称" />
            <t-textarea v-model="editDescription" label="描述" />
            <div class="library-form-actions">
              <t-button variant="outline" @click="cancelEdit">取消</t-button>
              <t-button
                theme="primary"
                :loading="savingEdit"
                @click="saveLibraryEdit"
              >保存修改</t-button>
            </div>
          </div>
        </div>
        <p v-if="!libraries.length" class="empty-state">暂无知识库</p>
      </div>
    </section>
  </t-dialog>
</template>
