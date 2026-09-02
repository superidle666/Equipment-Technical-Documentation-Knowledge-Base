<!--
 * @FilePath: @/pages/admin/users/index.vue
 * @Author: 项目维护者
 * @Date: 2026-08-31
 * @Description: 管理端用户管理，支持手机号、角色和启停用状态维护
 * @BusinessRule: 系统管理员不可编辑或停用
 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AddIcon, ChevronDownIcon, SearchIcon } from 'tdesign-icons-vue-next'
import { mysqlApi, type Role } from '../../../api/mysql'
import {
  isSystemAdminUser,
  mapUser,
  type UserRow,
} from '../shared/formatters'

type UserForm = {
  username: string
  display_name: string
  email: string
  phone: string
  role_codes: string[]
}

type UserEditForm = UserForm & {
  password: string
  status: string
}

const emit = defineEmits<{
  (event: 'update-counts', counts: { users: number; roles: number }): void
}>()

const users = ref<UserRow[]>([])
const roles = ref<Role[]>([])
const search = ref('')
const loading = ref(false)
const errorMessage = ref('')
const createError = ref('')
const editError = ref('')
const creatingUser = ref(false)
const savingUser = ref(false)
const updatingUserId = ref<number>()
const deletingUserId = ref<number>()
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingUserId = ref<number>()
const newUser = ref<UserForm>(createUserForm())
const editUser = ref<UserEditForm>(createEditUserForm())

const columns = [
  { colKey: 'name', title: '用户' },
  { colKey: 'username', title: '登录账号', width: 150 },
  { colKey: 'email', title: '邮箱' },
  { colKey: 'phone', title: '手机号', width: 140 },
  { colKey: 'role', title: '角色', width: 130 },
  { colKey: 'statusLabel', title: '状态', width: 100, align: 'center' },
  { colKey: 'last', title: '最近登录', width: 140 },
  { colKey: 'op', title: '操作', width: 220, align: 'center' },
]

const roleOptions = computed(() => {
  return roles.value.map((role) => ({
    label: role.name,
    value: role.code,
  }))
})

const filteredUsers = computed(() => {
  const query = search.value.trim().toLowerCase()

  if (!query) {
    return users.value
  }

  return users.value.filter((user) => {
    return [user.name, user.email, user.phone, user.username]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(query)
  })
})

/** 创建新增用户表单的默认值。 */
function createUserForm(): UserForm {
  return {
    username: '',
    display_name: '',
    email: '',
    phone: '',
    role_codes: ['user'],
  }
}

/** 创建编辑用户表单的默认值。 */
function createEditUserForm(): UserEditForm {
  return {
    username: '',
    display_name: '',
    email: '',
    phone: '',
    password: '',
    role_codes: [],
    status: 'active',
  }
}

/** 打开新增弹窗时重置表单，避免上一次失败提示残留。 */
function openCreateDialog() {
  newUser.value = createUserForm()
  createError.value = ''
  showCreateDialog.value = true
}

const PHONE_PATTERN = /^1[3-9]\d{9}$/

/** 校验 11 位中国大陆手机号。 */
function validatePhone(phone: string) {
  if (!phone.trim()) return '请输入手机号。'
  if (!PHONE_PATTERN.test(phone.trim())) {
    return '请输入正确的 11 位中国大陆手机号。'
  }
  return ''
}

/** 检查新增用户的账号、手机号和必填字段。 */
function validateNewUser() {
  const username = newUser.value.username.trim()
  if (!username) return '请输入登录账号。'
  if (!/^[A-Za-z]{3,20}$/.test(username)) {
    return '登录账号只能使用 3 至 20 个英文字母，不能包含数字、中文或特殊字符。'
  }
  if (!newUser.value.display_name.trim()) return '请输入显示名称。'
  return validatePhone(newUser.value.phone)
}

/** 检查编辑用户的登录账号、显示名称和可选手机号。 */
function validateEditUser() {
  const username = editUser.value.username.trim()
  if (!username) return '请输入登录账号。'
  if (!/^[A-Za-z]{3,20}$/.test(username)) {
    return '登录账号只能使用 3 至 20 个英文字母，不能包含数字、中文或特殊字符。'
  }
  if (!editUser.value.display_name.trim()) return '请输入显示名称。'
  return editUser.value.phone.trim() ? validatePhone(editUser.value.phone) : ''
}

/** 将用户状态映射为 TDesign 标签主题。 */
function getStatusTheme(row: UserRow) {
  return row.status === 'active' ? 'success' : 'default'
}

/** 并行加载用户和角色数据，并同步侧栏统计。 */
async function loadUsers() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [userData, roleData] = await Promise.all([
      mysqlApi.listUsers(),
      mysqlApi.listRoles(),
    ])

    users.value = userData.map(mapUser)
    roles.value = roleData
    emit('update-counts', {
      users: users.value.length,
      roles: roles.value.length,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用户数据加载失败'
  } finally {
    loading.value = false
  }
}

/** 校验并创建用户；初始密码由后端按账号和手机号自动生成。 */
async function createUser() {
  createError.value = validateNewUser()
  if (createError.value) return

  creatingUser.value = true
  try {
    await mysqlApi.createUser({
      ...newUser.value,
      username: newUser.value.username.trim(),
      display_name: newUser.value.display_name.trim(),
      email: newUser.value.email.trim() || null,
      phone: newUser.value.phone.trim(),
    })
    showCreateDialog.value = false
    await loadUsers()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '用户创建失败'
  } finally {
    creatingUser.value = false
  }
}

/** 打开编辑弹窗；系统管理员保持只读。 */
function openEditDialog(row: UserRow) {
  if (isSystemAdminUser(row)) {
    return
  }

  editingUserId.value = row.id
  editError.value = ''
  editUser.value = {
    username: row.username,
    display_name: row.display_name,
    email: row.email || '',
    phone: row.phone || '',
    password: '',
    role_codes: [...row.roles],
    status: row.status,
  }
  showEditDialog.value = true
}

/** 提交用户资料、角色和可选密码变更。 */
async function saveUser() {
  if (!editingUserId.value) return

  editError.value = validateEditUser()
  if (editError.value) return

  savingUser.value = true
  try {
    await mysqlApi.updateUser(editingUserId.value, {
      username: editUser.value.username.trim(),
      display_name: editUser.value.display_name.trim(),
      email: editUser.value.email.trim() || null,
      phone: editUser.value.phone.trim() || null,
      password: editUser.value.password || undefined,
      role_codes: editUser.value.role_codes,
      status: editUser.value.status,
    })
    showEditDialog.value = false
    await loadUsers()
  } catch (error) {
    editError.value = error instanceof Error ? error.message : '用户更新失败'
  } finally {
    savingUser.value = false
  }
}

/** 切换用户启用状态；系统管理员不可操作。 */
async function toggleUserStatus(row: UserRow) {
  if (isSystemAdminUser(row) || updatingUserId.value || deletingUserId.value) return

  const status = row.status === 'active' ? 'disabled' : 'active'
  updatingUserId.value = row.id
  try {
    await mysqlApi.updateUser(row.id, { status })
    await loadUsers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用户状态更新失败'
  } finally {
    updatingUserId.value = undefined
  }
}

/** 二次确认后软删除用户；系统管理员不可操作。 */
async function deleteUser(row: UserRow) {
  if (isSystemAdminUser(row) || updatingUserId.value || deletingUserId.value) return
  if (!window.confirm(`确定删除用户“${row.name}”吗？删除后将不再显示在列表中。`)) return

  deletingUserId.value = row.id
  try {
    await mysqlApi.deleteUser(row.id)
    await loadUsers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用户删除失败'
  } finally {
    deletingUserId.value = undefined
  }
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <section class="admin-module">
    <div class="admin-page-head compact">
      <div>
        <div class="eyebrow">ACCESS CONTROL</div>
        <h1>用户管理</h1>
        <p>管理平台用户与角色权限。</p>
      </div>
      <t-button theme="primary" class="create-action" @click="openCreateDialog">
        <AddIcon />
        新增用户
      </t-button>
    </div>

    <div v-if="errorMessage" class="admin-error">
      {{ errorMessage }}
      <button @click="loadUsers">重试</button>
    </div>
    <div v-if="loading" class="admin-loading">正在加载用户数据...</div>

    <div class="toolbar simple">
      <t-input v-model="search" placeholder="搜索姓名、账号、邮箱或手机号" class="table-search">
        <template #prefix-icon>
          <SearchIcon />
        </template>
      </t-input>
      <t-button variant="outline">
        筛选
        <ChevronDownIcon />
      </t-button>
    </div>

    <div class="panel table-panel">
      <t-table :data="filteredUsers" :columns="columns" row-key="id">
        <template #name="{ row }">
          <div class="user-cell">
            <div class="avatar tiny">{{ row.name.slice(0, 1) }}</div>
            <strong>{{ row.name }}</strong>
          </div>
        </template>
        <template #statusLabel="{ row }">
          <t-tag :theme="getStatusTheme(row)" variant="light">
            {{ row.statusLabel }}
          </t-tag>
        </template>
        <template #op="{ row }">
          <template v-if="!isSystemAdminUser(row)">
            <div class="table-actions table-actions--multiple">
              <t-button
                variant="text"
                class="edit-action"
                size="small"
                :disabled="Boolean(updatingUserId || deletingUserId)"
                @click="openEditDialog(row)"
              >
                编辑
              </t-button>
              <t-button
                variant="text"
                :theme="row.status === 'active' ? 'danger' : 'success'"
                size="small"
                :loading="updatingUserId === row.id"
                :disabled="Boolean(updatingUserId || deletingUserId) && updatingUserId !== row.id"
                @click="toggleUserStatus(row)"
              >
                {{ row.status === 'active' ? '停用' : '启用' }}
              </t-button>
              <t-button
                variant="text"
                theme="danger"
                size="small"
                :loading="deletingUserId === row.id"
                :disabled="Boolean(updatingUserId || deletingUserId) && deletingUserId !== row.id"
                @click="deleteUser(row)"
              >
                删除
              </t-button>
            </div>
          </template>
          <span v-else class="protected-label">系统内置</span>
        </template>
      </t-table>
    </div>

    <t-dialog
      v-model:visible="showCreateDialog"
      header="新增用户"
      :confirm-btn="{ content: '创建用户', theme: 'primary', loading: creatingUser }"
      @confirm="createUser"
    >
      <div class="dialog-fields">
        <p v-if="createError" class="dialog-form-error">{{ createError }}</p>
        <t-input
          v-model="newUser.username"
          label="登录账号"
          placeholder="3 至 20 个英文字母，例如：wang"
        />
        <t-input v-model="newUser.display_name" label="显示名称" placeholder="例如：王工" />
        <t-input v-model="newUser.email" label="邮箱" placeholder="可选" />
        <t-input v-model="newUser.phone" label="手机号" placeholder="请输入 11 位中国大陆手机号" />
        <p class="form-field-tip">初始密码由系统自动设置为：账号前三个字符 + 手机号。</p>
        <t-select
          v-model="newUser.role_codes"
          :options="roleOptions"
          label="角色"
          multiple
        />
      </div>
    </t-dialog>

    <t-dialog
      v-model:visible="showEditDialog"
      header="编辑用户"
      :confirm-btn="{ content: '保存', theme: 'primary', loading: savingUser }"
      @confirm="saveUser"
    >
      <div class="dialog-fields">
        <p v-if="editError" class="dialog-form-error">{{ editError }}</p>
        <t-input
          v-model="editUser.username"
          label="登录账号"
          placeholder="3 至 20 个英文字母"
        />
        <t-input v-model="editUser.display_name" label="显示名称" />
        <t-input v-model="editUser.email" label="邮箱" />
        <t-input v-model="editUser.phone" label="手机号" placeholder="未登记可留空；填写时须为 11 位中国大陆手机号" />
        <t-input
          v-model="editUser.password"
          type="password"
          label="重置密码"
          placeholder="留空表示不修改"
        />
        <t-select
          v-model="editUser.role_codes"
          :options="roleOptions"
          label="角色"
          multiple
        />
        <t-select
          v-model="editUser.status"
          :options="[
            { label: '正常', value: 'active' },
            { label: '已停用', value: 'disabled' },
            { label: '已锁定', value: 'locked' },
          ]"
          label="状态"
        />
      </div>
    </t-dialog>
  </section>
</template>
