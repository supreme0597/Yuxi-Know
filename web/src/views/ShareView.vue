<template>
  <div class="share-view">
    <div v-if="loading" class="share-loading">
      <a-spin />
      <span>正在加载分享内容...</span>
    </div>

    <div v-else-if="error" class="share-error">
      <CircleAlert size="40" class="share-error-icon" />
      <div class="share-error-title">分享链接已失效或不存在</div>
      <div class="share-error-text">{{ error }}</div>
      <a-button type="primary" class="share-error-action" @click="goHome">返回首页</a-button>
    </div>

    <div v-else-if="conversation" class="share-shell">
      <!-- 标题栏：与聊天页 header 同构，右侧为状态/文件切换按钮 -->
      <header class="share-header">
        <div class="header__left">
          <span class="share-badge">只读分享</span>
          <div
            v-if="conversation.title && conversation.title !== '新的对话'"
            class="conversation-title"
          >
            {{ conversation.title }}
          </div>
          <span v-if="conversation.created_at" class="share-meta-item">
            {{ formatDate(conversation.created_at) }}
          </span>
        </div>
        <div class="header__right">
          <button
            type="button"
            class="share-nav-btn"
            :class="{ active: statePanelOpen }"
            title="查看状态"
            aria-label="查看状态"
            @click.stop="toggleStatePanel"
          >
            <LayoutList size="16" class="nav-btn-icon" />
          </button>
          <button
            type="button"
            class="share-nav-btn"
            :class="{ active: filePanelOpen }"
            title="查看文件"
            aria-label="查看文件"
            @click.stop="toggleFilePanel"
          >
            <FolderKanban size="16" class="nav-btn-icon" />
          </button>
        </div>
      </header>

      <div class="share-body">
        <!-- 主聊天区 -->
        <div class="share-main">
          <div class="share-messages">
            <ThreadMessageList :messages="history" />
          </div>
          <!-- 交付件：复用聊天页 AgentArtifactsCard（只读 + 分享下载 URL） -->
          <div v-if="artifactItems.length" class="share-artifacts">
            <AgentArtifactsCard
              :artifacts="artifactItems"
              :thread-id="threadId"
              readonly
              :download-url-fn="artifactDownloadUrl"
            />
          </div>
          <div v-if="!history.length && !artifactItems.length" class="share-empty">
            该对话暂无内容
          </div>
        </div>

        <!-- 状态面板：复刻聊天页五分区只读版 -->
        <aside v-if="statePanelOpen" class="share-state-panel">
          <div class="share-panel-header">
            <span class="share-panel-title">状态</span>
            <span class="share-panel-summary">{{ stateSummaryLabel }}</span>
          </div>
          <div class="share-panel-body">
            <!-- 上下文使用 -->
            <section v-if="tokenUsage" class="state-section">
              <button
                type="button"
                class="state-section-header"
                @click="toggleStateSection('tokenUsage')"
              >
                <span class="state-section-label">
                  <span class="state-section-title">上下文使用</span>
                  <ChevronDown
                    size="15"
                    class="state-section-chevron"
                    :class="{ 'is-collapsed': !isStateSectionExpanded('tokenUsage') }"
                  />
                </span>
                <span class="state-section-meta">{{ tokenUsageHeaderPercentLabel }}</span>
              </button>
              <div v-show="isStateSectionExpanded('tokenUsage')" class="state-section-content">
                <div class="token-usage-content">
                  <div class="token-usage-stack">
                    <div class="token-usage-stack-head">
                      <span>当前上下文</span>
                      <strong>{{ tokenUsageStackHeadLabel }}</strong>
                    </div>
                    <div class="token-usage-stack-track" aria-label="Token 构成">
                      <div
                        v-for="segment in tokenUsageBarSegments"
                        :key="segment.key"
                        class="token-usage-stack-segment"
                        :class="segment.tone"
                        :style="{ width: segment.percent }"
                        :title="`${segment.label}: ${segment.valueLabel}`"
                      ></div>
                    </div>
                    <div class="token-usage-stack-legend">
                      <span
                        v-for="segment in tokenUsageSegments"
                        :key="segment.key"
                        class="token-usage-stack-legend-item"
                      >
                        <i :class="segment.tone"></i>
                        {{ segment.label }} {{ segment.valueLabel }}
                      </span>
                    </div>
                  </div>
                  <div v-if="tokenUsageMetaRows.length" class="token-usage-breakdown">
                    <div
                      v-for="item in tokenUsageMetaRows"
                      :key="item.key"
                      class="token-usage-breakdown-row"
                    >
                      <span>{{ item.label }}</span>
                      <strong>{{ item.value }}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 待办 -->
            <section v-if="todos.length" class="state-section">
              <button
                type="button"
                class="state-section-header"
                @click="toggleStateSection('todos')"
              >
                <span class="state-section-label">
                  <span class="state-section-title">待办</span>
                  <ChevronDown
                    size="15"
                    class="state-section-chevron"
                    :class="{ 'is-collapsed': !isStateSectionExpanded('todos') }"
                  />
                </span>
                <span v-if="todos.length" class="state-section-meta">
                  {{ completedTodoCount }}/{{ todos.length }} · {{ todoProgress }}%
                </span>
              </button>
              <div v-show="isStateSectionExpanded('todos')" class="state-section-content">
                <div class="todo-panel-list">
                  <div
                    v-for="(todo, index) in todos"
                    :key="`${todo.fullContent}-${index}`"
                    class="todo-item"
                    :class="{ completed: todo.status === 'completed' }"
                  >
                    <div class="todo-item-icon" :class="todo.status || 'unknown'">
                      <CheckCircleOutlined v-if="todo.status === 'completed'" />
                      <SyncOutlined v-else-if="todo.status === 'in_progress'" spin />
                      <ClockCircleOutlined v-else-if="todo.status === 'pending'" />
                      <CloseCircleOutlined v-else-if="todo.status === 'cancelled'" />
                      <QuestionCircleOutlined v-else />
                    </div>
                    <div class="todo-item-body">
                      <span class="todo-item-text" :title="todo.fullContent">
                        {{ todo.displayContent }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 附件/文件 -->
            <section v-if="stateFiles.length" class="state-section">
              <button
                type="button"
                class="state-section-header"
                @click="toggleStateSection('files')"
              >
                <span class="state-section-label">
                  <span class="state-section-title">附件/文件</span>
                  <ChevronDown
                    size="15"
                    class="state-section-chevron"
                    :class="{ 'is-collapsed': !isStateSectionExpanded('files') }"
                  />
                </span>
                <span class="state-section-meta">{{ stateFiles.length }}</span>
              </button>
              <div v-show="isStateSectionExpanded('files')" class="state-section-content">
                <div class="state-list">
                  <div v-for="file in stateFiles" :key="file.key" class="state-list-item">
                    <FileTypeIcon
                      :name="file.name || file.path"
                      :size="18"
                      class="state-list-item-icon"
                    />
                    <div class="state-list-item-body">
                      <div class="state-list-item-title">{{ file.name }}</div>
                      <div class="state-list-item-meta">{{ file.meta || file.path }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 产物 -->
            <section v-if="artifactItems.length" class="state-section">
              <button
                type="button"
                class="state-section-header"
                @click="toggleStateSection('artifacts')"
              >
                <span class="state-section-label">
                  <span class="state-section-title">产物</span>
                  <ChevronDown
                    size="15"
                    class="state-section-chevron"
                    :class="{ 'is-collapsed': !isStateSectionExpanded('artifacts') }"
                  />
                </span>
                <span class="state-section-meta">{{ artifactItems.length }}</span>
              </button>
              <div v-show="isStateSectionExpanded('artifacts')" class="state-section-content">
                <div class="state-list">
                  <div v-for="file in artifactItems" :key="file.path" class="state-list-item">
                    <FileTypeIcon
                      :name="file.name || file.path"
                      :size="18"
                      class="state-list-item-icon"
                    />
                    <div class="state-list-item-body">
                      <div class="state-list-item-title">{{ file.name }}</div>
                      <div class="state-list-item-meta">{{ file.meta }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 子智能体 -->
            <section v-if="subagentRuns.length" class="state-section">
              <button
                type="button"
                class="state-section-header"
                @click="toggleStateSection('subagents')"
              >
                <span class="state-section-label">
                  <span class="state-section-title">子智能体</span>
                  <ChevronDown
                    size="15"
                    class="state-section-chevron"
                    :class="{ 'is-collapsed': !isStateSectionExpanded('subagents') }"
                  />
                </span>
                <span class="state-section-meta">{{ subagentRuns.length }}</span>
              </button>
              <div v-show="isStateSectionExpanded('subagents')" class="state-section-content">
                <div class="state-list">
                  <div
                    v-for="(run, index) in subagentRuns"
                    :key="run.id || `${run.subagent_slug || 'subagent'}-${index}`"
                    class="state-list-item"
                  >
                    <FallbackAvatar
                      class="state-subagent-icon"
                      :src="getSubagentIconSrc(run)"
                      :default-src="getSubagentDefaultIconSrc(run)"
                      :name="getSubagentRunName(run)"
                      :seed="run.subagent_slug || getSubagentRunName(run)"
                      kind="agent"
                      :size="28"
                      shape="rounded"
                      :alt="`${getSubagentRunName(run)}图标`"
                    />
                    <div class="state-list-item-body">
                      <div class="state-list-item-title state-subagent-title">
                        <span>{{ getSubagentRunName(run) }}</span>
                        <CheckCircleOutlined
                          v-if="run.status === 'completed'"
                          class="state-subagent-status-icon state-subagent-completed-icon"
                        />
                        <CloseCircleOutlined
                          v-else-if="run.status === 'failed'"
                          class="state-subagent-status-icon state-subagent-failed-icon"
                        />
                        <SyncOutlined
                          v-else-if="run.status === 'running'"
                          spin
                          class="state-subagent-status-icon state-subagent-running-icon"
                        />
                      </div>
                      <div class="state-list-item-meta">{{ getSubagentRunMeta(run) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <div v-if="!hasVisibleStateSections" class="state-panel-empty">暂无状态内容</div>
          </div>
        </aside>

        <!-- 文件面板：复用聊天页文件树（FileTreeComponent + AgentFilePreview，数据源接 share API） -->
        <aside v-if="filePanelOpen" class="share-file-panel">
          <div class="share-panel-header">
            <span class="share-panel-title">文件</span>
            <div class="share-panel-header-actions">
              <button
                type="button"
                class="share-panel-action-btn"
                title="刷新文件"
                aria-label="刷新文件"
                @click.stop="refreshSharedFiles"
              >
                <RefreshCw :size="14" />
              </button>
            </div>
          </div>
          <div class="share-panel-body">
            <div v-if="previewFile" class="share-file-preview">
              <AgentFilePreview
                containerClass="side-preview-shell"
                contentClass="side-file-content"
                :file="previewFile"
                :file-path="previewFilePath"
                :editable="false"
                :full-height="true"
                :show-file-icon="false"
                :borderless="true"
                :show-close="true"
                :show-download="true"
                :show-fullscreen="true"
                @download="downloadPreviewFile"
                @close="closePreview"
              />
            </div>
            <div v-else class="share-file-tree">
              <FileTreeComponent
                v-model:selected-keys="selectedKeys"
                v-model:expanded-keys="expandedKeys"
                :tree-data="fileTreeData"
                :load-data="loadSharedData"
                @select="onSharedFileSelect"
              />
              <div v-if="!loadingSharedFiles && !fileTreeData.length" class="state-panel-empty">
                暂无文件
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  QuestionCircleOutlined,
  SyncOutlined
} from '@ant-design/icons-vue'
import { ChevronDown, CircleAlert, FolderKanban, LayoutList, RefreshCw } from 'lucide-vue-next'
import ThreadMessageList from '@/components/ThreadMessageList.vue'
import AgentArtifactsCard from '@/components/AgentArtifactsCard.vue'
import FileTreeComponent from '@/components/FileTreeComponent.vue'
import AgentFilePreview from '@/components/AgentFilePreview.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { generatePixelAvatar } from '@/utils/pixelAvatar'
import { formatFileSize } from '@/utils/file_utils'
import { normalizePreviewResponse } from '@/utils/file_preview'
import { shareApi } from '@/apis/share_api'

const route = useRoute()

const threadId = typeof route.params.thread_id === 'string' ? route.params.thread_id : ''
const token = typeof route.query.token === 'string' ? route.query.token : ''

const loading = ref(true)
const error = ref('')
const conversation = ref(null)
const history = ref([])
const stateData = ref(null)

const statePanelOpen = ref(true)
const filePanelOpen = ref(false)
const collapsedStateSections = reactive({
  tokenUsage: false,
  todos: false,
  files: false,
  artifacts: false,
  subagents: false
})

const formatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const toggleStatePanel = () => {
  statePanelOpen.value = !statePanelOpen.value
  if (statePanelOpen.value) filePanelOpen.value = false
}

const toggleFilePanel = () => {
  filePanelOpen.value = !filePanelOpen.value
  if (filePanelOpen.value) statePanelOpen.value = false
}

const isStateSectionExpanded = (key) => !collapsedStateSections[key]
const toggleStateSection = (key) => {
  collapsedStateSections[key] = !collapsedStateSections[key]
}

const goHome = () => {
  window.location.href = '/'
}

// ==================== agent_state 派生 ====================
const currentAgentState = computed(() => stateData.value || null)

const tokenUsage = computed(() => {
  const usage = currentAgentState.value?.token_usage
  return usage && typeof usage === 'object' && !Array.isArray(usage) ? usage : null
})

const toFiniteNumber = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

const TOKEN_COUNT_K_UNIT = 1024
const formatTokenCount = (value) => {
  const numeric = toFiniteNumber(value)
  if (numeric === null) return '-'
  if (numeric >= TOKEN_COUNT_K_UNIT) {
    const digits = numeric >= TOKEN_COUNT_K_UNIT * 10 ? 1 : 2
    return `${(numeric / TOKEN_COUNT_K_UNIT).toFixed(digits).replace(/\.0+$/, '')}k`
  }
  return String(Math.round(numeric))
}

const tokenUsageSegments = computed(() => {
  const usage = tokenUsage.value
  if (!usage) return []

  const summaryTokens = usage.summary_active
    ? Math.max(toFiniteNumber(usage.summary_message_tokens) || 0, 0)
    : 0
  const llmMessageTokens = Math.max(toFiniteNumber(usage.llm_messages_tokens) || 0, 0)
  const hasSplitMessageTokens =
    toFiniteNumber(usage.llm_content_message_tokens) !== null ||
    toFiniteNumber(usage.llm_tool_message_tokens) !== null
  const contentMessageTokens = hasSplitMessageTokens
    ? Math.max(toFiniteNumber(usage.llm_content_message_tokens) || 0, 0)
    : Math.max(llmMessageTokens - summaryTokens, 0)
  const toolMessageTokens = Math.max(toFiniteNumber(usage.llm_tool_message_tokens) || 0, 0)
  const stateMessageTokensBeforeCall = Math.max(
    toFiniteNumber(usage.state_messages_tokens_before_call ?? usage.state_messages_tokens) || 0,
    0
  )
  const cutMessageTokens = Math.max(stateMessageTokensBeforeCall - llmMessageTokens, 0)
  const llmMessageCount = Math.max(toFiniteNumber(usage.llm_message_count) || 0, 0)
  const contentMessageCount = hasSplitMessageTokens
    ? Math.max(toFiniteNumber(usage.llm_content_message_count) || 0, 0)
    : Math.max(llmMessageCount - (usage.summary_active ? 1 : 0), 0)
  const toolMessageCount = Math.max(toFiniteNumber(usage.llm_tool_message_count) || 0, 0)
  const stateMessageCountBeforeCall = Math.max(
    toFiniteNumber(usage.state_message_count_before_call ?? usage.state_message_count) || 0,
    0
  )
  const cutMessageCount = Math.max(stateMessageCountBeforeCall - llmMessageCount, 0)
  const systemTokens = Math.max(toFiniteNumber(usage.system_tokens) || 0, 0)
  const toolsTokens = Math.max(toFiniteNumber(usage.tools_tokens) || 0, 0)
  const inputTokens = Math.max(toFiniteNumber(usage.llm_input_tokens) || 0, 0)
  const rawSegments = [
    {
      key: 'cut',
      label: '已压缩',
      value: cutMessageTokens,
      messageCount: cutMessageCount,
      tone: 'is-cut'
    },
    {
      key: 'messages',
      label: '内容消息',
      value: contentMessageTokens,
      messageCount: contentMessageCount,
      tone: 'is-messages'
    },
    {
      key: 'toolMessages',
      label: '工具消息',
      value: toolMessageTokens,
      messageCount: toolMessageCount,
      tone: 'is-tool-messages'
    },
    {
      key: 'summary',
      label: '摘要',
      value: summaryTokens,
      messageCount: usage.summary_active ? 1 : 0,
      tone: 'is-summary'
    },
    {
      key: 'system',
      label: '系统消息',
      value: systemTokens,
      tone: 'is-system'
    },
    {
      key: 'tools',
      label: `工具定义 (${usage.tool_count || 0})`,
      value: toolsTokens,
      tone: 'is-tools'
    }
  ].filter((segment) => segment.value > 0)

  const accountedInputTokens = llmMessageTokens + systemTokens + toolsTokens
  if (inputTokens > accountedInputTokens) {
    rawSegments.push({
      key: 'overhead',
      label: '其他',
      value: inputTokens - accountedInputTokens,
      tone: 'is-overhead'
    })
  }

  const segmentTotal = rawSegments.reduce((sum, segment) => sum + segment.value, 0)
  const total = Math.max(cutMessageTokens + inputTokens, segmentTotal, 1)
  return rawSegments.map((segment) => {
    const ratio = segment.value / total
    return {
      ...segment,
      percent: `${Math.max(0, Math.min(ratio * 100, 100)).toFixed(2)}%`,
      valueLabel: segment.messageCount
        ? `${formatTokenCount(segment.value)} (${segment.messageCount}条)`
        : formatTokenCount(segment.value)
    }
  })
})

const tokenUsageStackTotal = computed(() => {
  const inputTokens = toFiniteNumber(tokenUsage.value?.llm_input_tokens)
  if (inputTokens !== null) return Math.max(inputTokens, 0)
  return tokenUsageSegments.value
    .filter((segment) => segment.key !== 'cut')
    .reduce((sum, segment) => sum + segment.value, 0)
})

const tokenUsageStackLimit = computed(() => {
  const summaryTriggerTokens = toFiniteNumber(tokenUsage.value?.summary_trigger_tokens)
  if (summaryTriggerTokens && summaryTriggerTokens > 0) return summaryTriggerTokens

  const contextWindow = toFiniteNumber(tokenUsage.value?.context_window)
  if (contextWindow && contextWindow > 0) return contextWindow

  return Math.max(tokenUsageStackTotal.value, 1)
})

const tokenUsageHeaderPercentLabel = computed(() => {
  const limit = Math.max(tokenUsageStackLimit.value, 1)
  const percent = Math.max(0, Math.min((tokenUsageStackTotal.value / limit) * 100, 100))
  if (percent > 0 && percent < 1) return '<1%'
  return `${Math.round(percent)}%`
})

const tokenUsageStackHeadLabel = computed(() => {
  const summaryTriggerTokens = toFiniteNumber(tokenUsage.value?.summary_trigger_tokens)
  if (summaryTriggerTokens && summaryTriggerTokens > 0) {
    return `${formatTokenCount(tokenUsageStackTotal.value)} / ${formatTokenCount(summaryTriggerTokens)} Token`
  }
  return `${formatTokenCount(tokenUsageStackTotal.value)} Token`
})

const tokenUsageBarSegments = computed(() => {
  const limit = Math.max(tokenUsageStackLimit.value, 1)
  let remaining = limit
  return tokenUsageSegments.value
    .filter((segment) => segment.key !== 'cut')
    .map((segment) => {
      const value = Math.min(segment.value, Math.max(remaining, 0))
      remaining -= value
      return {
        ...segment,
        percent: `${Math.max(0, Math.min((value / limit) * 100, 100)).toFixed(2)}%`
      }
    })
    .filter((segment) => segment.value > 0 && segment.percent !== '0.00%')
})

const tokenUsageMetaRows = computed(() => {
  const usage = tokenUsage.value
  if (!usage) return []
  const rows = []
  if (toFiniteNumber(usage.context_window)) {
    rows.push({
      key: 'context',
      label: '窗口/剩余',
      value: `${formatTokenCount(usage.context_window)} / ${formatTokenCount(usage.remaining_context_tokens)}`
    })
  }
  return rows
})

// ==================== 待办 / 文件 / 产物 / 子智能体 ====================
const TODO_NAME_MAX_LENGTH = 20
const formatTodoName = (content) => {
  return Array.from(String(content || ''))
    .slice(0, TODO_NAME_MAX_LENGTH)
    .join('')
}

const todos = computed(() => {
  const list = currentAgentState.value?.todos
  if (!Array.isArray(list)) return []
  return list.map((todo) => {
    const fullContent = String(todo?.content || '')
    return {
      ...todo,
      fullContent,
      displayContent: formatTodoName(fullContent)
    }
  })
})
const completedTodoCount = computed(
  () => todos.value.filter((todo) => todo?.status === 'completed').length
)
const todoProgress = computed(() => {
  if (!todos.value.length) return 0
  return Math.round((completedTodoCount.value / todos.value.length) * 100)
})

const getPanelFileName = (file) => {
  if (file?.name) return file.name
  if (file?.path) return String(file.path).split('/').pop() || String(file.path)
  return '未知文件'
}

const getArtifactMetaLabel = (path) => {
  const filename = getPanelFileName({ path })
  if (!filename.includes('.')) return '交付文件'
  const extension = filename.split('.').pop()
  return extension ? `交付文件 · ${extension.toUpperCase()}` : '交付文件'
}

const artifactItems = computed(() => {
  const artifacts = currentAgentState.value?.artifacts
  const paths = Array.isArray(artifacts) ? artifacts : []
  return paths
    .map((path) => String(path || '').trim())
    .filter(Boolean)
    .map((path) => ({
      path,
      name: getPanelFileName({ path }),
      meta: getArtifactMetaLabel(path)
    }))
})

const stateFiles = computed(() => {
  const files = []
  const seenPaths = new Set()
  const pushFile = (entry, fallbackName = '文件') => {
    const path = String(entry?.path || entry?.file_path || entry?.file_name || entry?.name || '')
    if (!path || seenPaths.has(path)) return
    seenPaths.add(path)
    const name = entry?.file_name || entry?.name || getPanelFileName({ path }) || fallbackName
    const sizeLabel = formatFileSize(entry?.file_size ?? entry?.size)
    const status = entry?.status || ''
    files.push({
      key: path,
      path,
      name,
      meta: [status, sizeLabel === '-' ? '' : sizeLabel, path].filter(Boolean).join(' · ')
    })
  }

  const rawFiles = currentAgentState.value?.files || {}
  if (typeof rawFiles === 'object' && !Array.isArray(rawFiles)) {
    Object.entries(rawFiles).forEach(([path, fileData]) => pushFile({ path, ...fileData }))
  }
  return files
})

// ==================== 子智能体 ====================
const subagentRuns = computed(() => {
  const runs = currentAgentState.value?.subagent_runs
  return Array.isArray(runs) ? runs : []
})

const getSubagentRunName = (run) => run?.subagent_name || run?.subagent_slug || '子智能体'
const getSubagentIconSrc = (run) => run?.icon || ''
const getSubagentDefaultIconSrc = (run) =>
  run?.subagent_slug ? generatePixelAvatar(run.subagent_slug) : ''
const getSubagentRunMeta = (run) => {
  const artifacts = Array.isArray(run?.artifacts) ? run.artifacts.length : 0
  return artifacts ? `${artifacts} 个产物` : run?.id || ''
}

const stateSummaryLabel = computed(() => {
  const total =
    (tokenUsage.value ? 1 : 0) +
    todos.value.length +
    stateFiles.value.length +
    artifactItems.value.length +
    subagentRuns.value.length
  return total ? `${total} 项` : '暂无内容'
})

const hasVisibleStateSections = computed(
  () =>
    Boolean(tokenUsage.value) ||
    todos.value.length > 0 ||
    stateFiles.value.length > 0 ||
    artifactItems.value.length > 0 ||
    subagentRuns.value.length > 0
)

// ==================== 文件面板（文件树 + 预览，复用聊天页组件） ====================
const fileTreeData = ref([])
const selectedKeys = ref([])
const expandedKeys = ref([])
const loadingSharedFiles = ref(false)
const previewFile = ref(null)
const previewFilePath = ref('')

const buildDisplayName = (fullPath) => {
  const normalized = String(fullPath || '').replace(/\/+$/, '')
  if (!normalized || normalized === '/') return '/'
  const parts = normalized.split('/').filter(Boolean)
  return parts[parts.length - 1] || normalized
}

const sortEntries = (entries) => {
  return [...entries].sort((left, right) => {
    const leftIsDir = Boolean(left?.is_dir)
    const rightIsDir = Boolean(right?.is_dir)
    if (leftIsDir !== rightIsDir) return leftIsDir ? -1 : 1
    return buildDisplayName(left?.path).localeCompare(buildDisplayName(right?.path), 'zh-Hans-CN')
  })
}

const createTreeNode = (entry) => {
  const fullPath = String(entry?.path || '')
  const title = buildDisplayName(fullPath)
  const isLeaf = !entry?.is_dir
  return {
    key: fullPath,
    title,
    isLeaf,
    children: isLeaf ? undefined : [],
    fileData: {
      ...entry,
      path: fullPath,
      name: title,
      type: isLeaf ? 'file' : 'directory'
    },
    class: isLeaf ? 'file-node' : 'folder-node'
  }
}

const updateTreeChildren = (nodes, targetKey, children) => {
  return nodes.map((node) => {
    if (node.key === targetKey) {
      return { ...node, children }
    }
    if (!node.children?.length) return node
    return {
      ...node,
      children: updateTreeChildren(node.children, targetKey, children)
    }
  })
}

const loadSharedDirectoryChildren = async (directoryPath) => {
  const res = await shareApi.getSharedFiles(threadId, token, directoryPath)
  return sortEntries(res?.files || []).map(createTreeNode)
}

const refreshSharedFiles = async () => {
  if (!threadId) {
    fileTreeData.value = []
    return
  }
  loadingSharedFiles.value = true
  try {
    const res = await shareApi.getSharedFiles(threadId, token)
    fileTreeData.value = sortEntries(res?.files || []).map(createTreeNode)
    expandedKeys.value = []
    selectedKeys.value = []
  } catch (e) {
    fileTreeData.value = []
    console.error('Failed to load shared files', e)
  } finally {
    loadingSharedFiles.value = false
  }
}

const loadSharedData = async (treeNode) => {
  if (treeNode.isLeaf || treeNode.children?.length || !threadId) return
  try {
    const children = await loadSharedDirectoryChildren(treeNode.key)
    fileTreeData.value = updateTreeChildren(fileTreeData.value, treeNode.key, children)
  } catch (e) {
    console.error('Failed to load children for', treeNode.key, e)
  }
}

const onSharedFileSelect = (keys, { node }) => {
  selectedKeys.value = keys
  if (!node?.isLeaf || !threadId) return
  openSharedPreview(node)
}

const revokePreviewUrl = () => {
  const url = previewFile.value?.previewUrl
  if (url) window.URL.revokeObjectURL(url)
}

const openSharedPreview = async (node) => {
  const filePath = String(node?.key || node?.fileData?.path || '')
  if (!filePath || !threadId) return
  revokePreviewUrl()

  const baseFile = {
    path: filePath,
    name: node?.fileData?.name || buildDisplayName(filePath),
    type: 'file'
  }
  previewFilePath.value = filePath
  previewFile.value = {
    ...baseFile,
    content: 'Loading...',
    supported: true,
    previewType: 'text',
    message: '',
    previewUrl: ''
  }

  try {
    const response = await fetch(shareApi.getSharedArtifactUrl(threadId, filePath, token, false))
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const nextFile = await normalizePreviewResponse(response, baseFile)
    previewFile.value = nextFile
  } catch (e) {
    previewFile.value = {
      ...baseFile,
      content: `加载文件失败：${e?.message || '未知错误'}`,
      supported: false,
      previewType: 'unsupported',
      message: e?.message || '文件预览失败',
      previewUrl: ''
    }
  }
}

const downloadPreviewFile = () => {
  if (!previewFilePath.value) return
  const url = shareApi.getSharedArtifactUrl(threadId, previewFilePath.value, token, true)
  const link = document.createElement('a')
  link.href = url
  link.download = previewFile.value?.name || buildDisplayName(previewFilePath.value)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const closePreview = () => {
  revokePreviewUrl()
  previewFile.value = null
  previewFilePath.value = ''
  selectedKeys.value = []
}

const artifactDownloadUrl = (path) => {
  if (!path) return ''
  return shareApi.getSharedArtifactUrl(threadId, path, token, true)
}

// ==================== 加载 ====================
const load = async () => {
  if (!threadId || !token) {
    error.value = '缺少分享参数'
    loading.value = false
    return
  }
  try {
    const [threadResponse, stateResponse] = await Promise.all([
      shareApi.getSharedThread(threadId, token),
      shareApi.getSharedState(threadId, token).catch(() => null)
    ])
    conversation.value = threadResponse
    history.value = threadResponse.history || []
    stateData.value = stateResponse?.agent_state || null
    refreshSharedFiles()
  } catch (e) {
    console.error('加载分享内容失败:', e)
    error.value = e?.message || '加载分享内容失败'
    message.error(error.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped lang="less">
.share-view {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
}

.share-loading,
.share-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-600);
}

.share-error {
  .share-error-icon {
    color: var(--color-error-500);
  }

  .share-error-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--gray-900);
  }
}

.share-error-action {
  margin-top: 8px;
}

.share-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.share-header {
  user-select: none;
  z-index: 10;
  height: 40px;
  min-height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--gray-150);

  .header__left,
  .header__right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .conversation-title {
    font-size: 14px;
    line-height: 20px;
    font-weight: 400;
    color: var(--text-primary);
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-left: 8px;
  }
}

.share-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--main-50);
  color: var(--main-700);
  font-size: 12px;
  font-weight: 500;
}

.share-meta-item {
  font-size: 12px;
  color: var(--gray-500);
}

.share-nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 28px;
  padding: 4px 7px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-900);
  cursor: pointer;
  transition: background-color 0.3s;

  &:hover {
    background-color: var(--gray-100);
  }

  &.active {
    color: var(--main-700);
    background-color: var(--main-20);
  }

  .nav-btn-icon {
    width: 16px;
    height: 16px;
  }
}

.share-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
}

.share-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 1rem var(--page-padding);
}

.share-messages {
  max-width: 860px;
  margin: 0 auto;
}

.share-artifacts {
  max-width: 860px;
  margin: 16px auto 0;
}

.share-empty {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 0;
  text-align: center;
  color: var(--gray-500);
  font-size: 13px;
}

// ==================== 状态 / 文件侧边面板 ====================
.share-state-panel,
.share-file-panel {
  width: min(340px, calc(100vw - 24px));
  min-width: 300px;
  flex-shrink: 0;
  margin: 8px 8px 8px 0;
  display: flex;
  flex-direction: column;
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  box-shadow: 0 4px 16px var(--shadow-0);
  overflow: auto;
  align-self: flex-start;
  max-height: calc(100% - 16px);
}

.share-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 40px;
  padding: 4px 12px;
  background: var(--gray-25);
  border-bottom: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.share-panel-title {
  min-width: 0;
  font-size: 14px;
  font-weight: 400;
  color: var(--gray-500);
}

.share-panel-summary {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--gray-500);
}

.share-panel-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.share-panel-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 6px;
  color: var(--gray-500);
  background: transparent;
  cursor: pointer;

  &:hover:not(:disabled) {
    color: var(--main-700);
    background: var(--gray-100);
  }
}

.share-file-preview {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.share-file-preview :deep(.side-preview-shell) {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  background: var(--gray-0);
  overflow: hidden;
}

.share-file-preview :deep(.side-preview-shell .file-content),
.share-file-preview :deep(.side-preview-shell .side-file-content) {
  flex: 1;
  min-height: 0;
  max-height: none;
}

.share-file-tree {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.share-panel-body {
  flex: 1;
  min-height: 0;
  padding: 8px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

// ==================== 状态分区（与聊天页同构） ====================
.state-section {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &.is-collapsed {
    gap: 0;
  }
}

.state-section-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;

  &:hover {
    .state-section-title,
    .state-section-chevron {
      color: var(--gray-900);
    }
  }
}

.state-section-label {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.state-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800);
}

.state-section-chevron {
  flex-shrink: 0;
  color: var(--gray-500);
  transition:
    transform 0.18s ease,
    color 0.18s ease;

  &.is-collapsed {
    transform: rotate(-90deg);
  }
}

.state-section-content {
  min-width: 0;
}

.state-panel-empty {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--gray-25);
  color: var(--gray-500);
  font-size: 13px;
  text-align: center;
}

// ==================== Token 用量（与聊天页同构） ====================
.token-usage-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 2px;
}

.token-usage-stack {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.token-usage-stack-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: var(--gray-500);

  strong {
    color: var(--gray-900);
    font-weight: 650;
    font-variant-numeric: tabular-nums;
  }
}

.token-usage-stack-track {
  display: flex;
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--gray-100);
}

.token-usage-stack-segment {
  height: 100%;
  min-width: 2px;
  transition: width 0.2s ease;
}

.token-usage-stack-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 10px;
  font-size: 11px;
  color: var(--gray-500);
}

.token-usage-stack-legend-item {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  line-height: 1.35;
  white-space: normal;

  i {
    width: 7px;
    height: 7px;
    flex-shrink: 0;
    border-radius: 2px;
    background: var(--gray-300);
  }
}

.token-usage-stack-segment,
.token-usage-stack-legend-item i {
  &.is-cut {
    background-color: var(--main-500);
    background-image: repeating-linear-gradient(
      135deg,
      var(--main-30) 0,
      var(--main-30) 1px,
      transparent 1px,
      transparent 4px
    );
  }

  &.is-messages {
    background: var(--main-500);
  }

  &.is-tool-messages {
    background: var(--color-primary-500);
  }

  &.is-summary {
    background: var(--color-info-500);
  }

  &.is-system {
    background: var(--color-success-500);
  }

  &.is-tools {
    background: var(--color-warning-500);
  }

  &.is-overhead {
    background: var(--gray-300);
  }
}

.token-usage-breakdown {
  display: flex;
  flex-direction: column;
  gap: 6px 10px;
  padding-top: 2px;
}

.token-usage-breakdown-row {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  color: var(--gray-500);
  flex-wrap: wrap;

  strong {
    flex: 1 1 100%;
    color: var(--gray-800);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    line-height: 1.35;
  }
}

// ==================== 待办（与聊天页同构） ====================
.todo-panel-list {
  display: flex;
  flex-direction: column;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;

  &:last-child {
    border-bottom: none;
  }
}

.todo-item-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--gray-50);
  color: var(--gray-500);

  &.completed {
    background: var(--color-success-10);
    color: var(--color-success-700);
  }

  &.in_progress {
    background: var(--color-info-10);
    color: var(--color-info-700);
  }

  &.pending {
    background: var(--color-warning-10);
    color: var(--color-warning-700);
  }

  &.cancelled {
    background: var(--color-error-10);
    color: var(--color-error-700);
  }
}

.todo-item-body {
  min-width: 0;
}

.todo-item-text {
  font-size: 13px;
  line-height: 1.5;
  color: var(--gray-700);
  word-break: break-word;
}

.todo-item.completed .todo-item-text {
  color: var(--gray-500);
  text-decoration: line-through;
}

// ==================== 文件/产物列表（与聊天页同构） ====================
.state-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.state-list-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 9px;
  border: 1px solid var(--gray-100);
  border-radius: 10px;
  background: var(--gray-25);
  color: inherit;
  text-align: left;
}

.state-list-item-icon {
  flex-shrink: 0;
  font-size: 17px;
}

.state-list-item-body {
  min-width: 0;
  flex: 1;
}

.state-list-item-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-list-item-meta {
  margin-top: 1px;
  font-size: 12px;
  line-height: 1.25;
  color: var(--gray-500);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-subagent-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-0);
  object-fit: cover;
}

.state-subagent-title {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.state-subagent-status-icon {
  flex-shrink: 0;
  font-size: 12px;
}

.state-subagent-completed-icon {
  color: var(--color-success-700);
}

.state-subagent-failed-icon {
  color: var(--color-error-700);
}

.state-subagent-running-icon {
  color: var(--color-info-700);
}

@media (max-width: 768px) {
  .share-state-panel,
  .share-file-panel {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 20;
  }
}
</style>
