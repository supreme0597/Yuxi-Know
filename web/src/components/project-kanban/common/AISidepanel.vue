<template>
  <!-- 遮罩层 -->
  <Teleport to="body">
    <Transition name="ai-overlay">
      <div v-if="visible" class="ai-sidepanel__overlay" @click="close" />
    </Transition>
    <Transition name="ai-sidepanel">
      <div v-if="visible" class="ai-sidepanel">
        <!-- 头部 -->
        <div class="ai-sidepanel__header">
          <div class="ai-sidepanel__header-left">
            <Lightbulb :size="18" style="color: #6366f1" />
            <div>
              <h2 class="ai-sidepanel__title">{{ panelData.title }}</h2>
              <p class="ai-sidepanel__subtitle">{{ panelData.subtitle || 'AI 智能分析' }}</p>
            </div>
          </div>
          <button class="ai-sidepanel__close" @click="close" aria-label="关闭">
            <X :size="18" />
          </button>
        </div>

        <!-- 统一滚动区域：数据概览 + 对话消息 -->
        <div ref="scrollContainerRef" class="ai-sidepanel__body">
          <!-- 可折叠的 AI 数据概览 -->
          <div class="ai-sidepanel__data-section" :class="{ 'ai-sidepanel__data-section--collapsed': dataCollapsed }">
            <!-- 折叠触发器（有数据时始终显示） -->
            <button
              v-if="hasPanelData"
              class="ai-sidepanel__data-toggle"
              @click="dataCollapsed = !dataCollapsed"
            >
              <ChevronDown
                :size="14"
                class="ai-sidepanel__data-toggle-arrow"
                :class="{ 'ai-sidepanel__data-toggle-arrow--open': !dataCollapsed }"
              />
              <span>数据概览</span>
              <span v-if="panelData.risks?.length" class="ai-sidepanel__data-toggle-badge">
                {{ panelData.risks.length }}项风险
              </span>
            </button>

            <div class="ai-sidepanel__data-content">
              <!-- 关键数据条 -->
              <div v-if="panelData.progress?.length" class="ai-sidepanel__progress">
                <div
                  v-for="(item, i) in panelData.progress"
                  :key="i"
                  class="ai-sidepanel__progress-item"
                >
                  <span
                    class="ai-sidepanel__progress-dot"
                    :class="`ai-sidepanel__progress-dot--${item.status || 'normal'}`"
                  />
                  <span class="ai-sidepanel__progress-label">{{ item.label }}</span>
                  <span
                    class="ai-sidepanel__progress-value"
                    :class="`ai-sidepanel__progress-value--${item.status || 'normal'}`"
                  >{{ item.value }}</span>
                </div>
              </div>

              <!-- AI 分析推理 -->
              <div v-if="panelData.reasoning" class="ai-sidepanel__reasoning">
                <div class="ai-sidepanel__section-title">
                  <Sparkles :size="13" style="color: #8b5cf6" />
                  <span>AI 分析</span>
                </div>
                <div class="ai-sidepanel__reasoning-text" v-html="formatReasoning(panelData.reasoning)" />
              </div>

              <!-- 风险详情 -->
              <div v-if="panelData.risks?.length" class="ai-sidepanel__risks">
                <div class="ai-sidepanel__section-title">
                  <AlertTriangle :size="13" style="color: #f59e0b" />
                  <span>风险详情</span>
                  <span class="ai-sidepanel__risk-count">{{ panelData.risks.length }}项</span>
                </div>
                <div class="ai-sidepanel__risk-list">
                  <div
                    v-for="(risk, i) in panelData.risks"
                    :key="i"
                    class="ai-sidepanel__risk-card"
                    :class="`ai-sidepanel__risk-card--${riskLevel(risk.level)}`"
                  >
                    <div class="ai-sidepanel__risk-header" @click="toggleRisk(i)">
                      <span
                        class="ai-sidepanel__risk-badge"
                        :class="`ai-sidepanel__risk-badge--${riskLevel(risk.level)}`"
                      >{{ riskLevelText(risk.level) }}</span>
                      <span class="ai-sidepanel__risk-title">{{ risk.title }}</span>
                      <ChevronDown
                        :size="14"
                        class="ai-sidepanel__risk-arrow"
                        :class="{ 'ai-sidepanel__risk-arrow--open': expandedRisks.has(i) }"
                      />
                    </div>

                    <Transition name="ai-collapse">
                      <div v-if="expandedRisks.has(i)" class="ai-sidepanel__risk-body">
                        <div v-if="risk.detail" class="ai-sidepanel__risk-section">
                          <div class="ai-sidepanel__risk-section-header">
                            <Search :size="12" />
                            <span>根因分析</span>
                          </div>
                          <div class="ai-sidepanel__risk-section-content">{{ risk.detail }}</div>
                        </div>
                        <div v-if="risk.impact" class="ai-sidepanel__risk-section ai-sidepanel__risk-section--impact">
                          <div class="ai-sidepanel__risk-section-header">
                            <Info :size="12" />
                            <span>影响范围</span>
                          </div>
                          <div class="ai-sidepanel__risk-section-content">{{ risk.impact }}</div>
                        </div>
                        <div v-if="risk.suggestion" class="ai-sidepanel__risk-section ai-sidepanel__risk-section--suggestion">
                          <div class="ai-sidepanel__risk-section-header">
                            <CheckCircle :size="12" />
                            <span>消减建议</span>
                          </div>
                          <div class="ai-sidepanel__risk-section-content">{{ risk.suggestion }}</div>
                        </div>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>

              <!-- 猜你想问（对话激活后隐藏） -->
              <div v-if="panelData.quickQuestions?.length && !chatActive" class="ai-sidepanel__questions">
                <div class="ai-sidepanel__section-title">
                  <MessageCircle :size="13" style="color: #3b82f6" />
                  <span>猜你想问</span>
                </div>
                <div class="ai-sidepanel__question-list">
                  <button
                    v-for="(q, i) in panelData.quickQuestions"
                    :key="i"
                    class="ai-sidepanel__question-btn"
                    @click="handleQuickQuestion(q)"
                  >
                    {{ q }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 对话消息区域（有对话内容时展示） -->
          <div v-if="conversations.length > 0" class="ai-sidepanel__chat-messages">
            <KanbanChatArea />
          </div>
        </div>

        <!-- 固定底部输入区 -->
        <div class="ai-sidepanel__input-bar">
          <AgentInputArea
            ref="inputAreaRef"
            v-model="inputText"
            :is-loading="isProcessing"
            :disabled="!isInitialized"
            :send-button-disabled="!inputText.trim() && !isProcessing"
            :mention="mentionConfig"
            :supports-file-upload="supportsFileUpload"
            :has-active-thread="true"
            :todos="currentTodos"
            placeholder="输入问题，深入分析... 使用 @ 可以提及文件哦~"
            @send="handleSend"
            @upload-attachment="handleAttachmentUpload"
            @toggle-panel="handleTogglePanel"
          />
        </div>
      </div>
    </Transition>

    <!-- 文件系统面板（独立浮动，在侧边栏左侧） -->
    <Transition name="ai-filepanel">
      <div
        v-if="filePanelOpen && visible && currentThreadId"
        ref="filePanelRef"
        class="ai-sidepanel__file-panel"
        :class="{ 'is-expanded': filePanelExpanded }"
      >
        <AgentPanel
          :agent-state="agentState"
          :thread-files="threadFiles"
          :thread-id="currentThreadId"
          :agent-id="currentAgentId"
          :agent-config-id="selectedAgentConfigId"
          :panel-ratio="1"
          :is-expanded="filePanelExpanded"
          @close="filePanelOpen = false"
          @refresh="handleFilePanelRefresh"
          @resize="handleFilePanelResize"
          @resizing="handleFilePanelResizing"
          @toggle-expand="filePanelExpanded = !filePanelExpanded"
        />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { Lightbulb, X, Sparkles, AlertTriangle, ChevronDown, MessageCircle, Search, Info, CheckCircle } from 'lucide-vue-next'
import KanbanChatArea from './KanbanChatArea.vue'
import AgentInputArea from '@/components/AgentInputArea.vue'
import AgentPanel from '@/components/AgentPanel.vue'
import { useKanbanChat, setScrollContainer } from '../composables/useKanbanChat'

const props = defineProps({
  visible: { type: Boolean, default: false },
  data: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:visible', 'close', 'question-click'])

// ==================== 对话状态 ====================
const {
  chatActive,
  conversations,
  isProcessing,
  isInitialized,
  currentThreadId,
  currentAgentId,
  selectedAgentConfigId,
  agentState,
  threadFiles,
  mentionConfig,
  supportsFileUpload,
  currentTodos,
  sendMessage,
  stopGeneration,
  scrollToBottom,
  handleAttachmentUpload,
  initialize
} = useKanbanChat()

const inputText = ref('')
const inputAreaRef = ref(null)
const scrollContainerRef = ref(null)
const filePanelOpen = ref(false)
const filePanelRef = ref(null)
const filePanelExpanded = ref(false)

// 文件面板拖拽状态
let startResizeX = 0
let startResizeWidth = 0

const FILE_PANEL_MIN_WIDTH = 300
const FILE_PANEL_MAX_WIDTH = 800

// 处理文件面板宽度调整（拖拽左侧手柄）
// 右边缘锚定不动，只有 width 变化（左边缘跟随拖拽移动）
const handleFilePanelResize = (clientX) => {
  if (!filePanelRef.value) return
  const deltaX = clientX - startResizeX
  const newWidth = startResizeWidth - deltaX

  if (newWidth >= FILE_PANEL_MIN_WIDTH && newWidth <= FILE_PANEL_MAX_WIDTH) {
    filePanelRef.value.style.width = `${newWidth}px`
  }
}

const handleFilePanelResizing = (isResizingState, clientX = 0) => {
  if (isResizingState && filePanelRef.value) {
    startResizeX = clientX
    startResizeWidth = filePanelRef.value.offsetWidth
  } else if (!isResizingState) {
    startResizeX = 0
    startResizeWidth = 0
  }
}

// ==================== Body 滚动锁定 ====================
let scrollY = 0
watch(() => props.visible, (vis) => {
  if (vis) {
    scrollY = window.scrollY
    document.body.style.position = 'fixed'
    document.body.style.top = `-${scrollY}px`
    document.body.style.left = '0'
    document.body.style.right = '0'
    document.body.style.overflowY = 'scroll'
  } else {
    document.body.style.position = ''
    document.body.style.top = ''
    document.body.style.left = ''
    document.body.style.right = ''
    document.body.style.overflowY = ''
    window.scrollTo(0, scrollY)
  }
})

onBeforeUnmount(() => {
  document.body.style.position = ''
  document.body.style.top = ''
  document.body.style.left = ''
  document.body.style.right = ''
  document.body.style.overflowY = ''
})

// ==================== 滚动容器注册 ====================
onMounted(() => {
  if (scrollContainerRef.value) {
    setScrollContainer(scrollContainerRef.value)
  }
  initialize()
})

// ==================== 数据概览折叠 ====================
const dataCollapsed = ref(false)

// 发送/流式开始时立即折叠数据概览
watch(isProcessing, (processing) => {
  if (processing) {
    dataCollapsed.value = true
  }
})

// 对话激活后也折叠（双保险）
watch(chatActive, (active) => {
  if (active) {
    dataCollapsed.value = true
  }
})

// ==================== 面板数据 ====================
const panelData = reactive({
  title: '',
  subtitle: '',
  progress: [],
  reasoning: '',
  risks: [],
  quickQuestions: []
})

const expandedRisks = reactive(new Set())

const hasPanelData = computed(() => {
  return panelData.progress?.length || panelData.reasoning || panelData.risks?.length
})

watch(() => [props.visible, props.data], ([vis, data]) => {
  if (vis && data) {
    panelData.title = data.title || 'AI 分析'
    panelData.subtitle = data.subtitle || ''
    panelData.progress = data.progress || []
    panelData.reasoning = data.reasoning || ''
    panelData.risks = data.risks || []
    panelData.quickQuestions = data.quickQuestions || []
    // 猜你想问点击时隐藏数据概览
    dataCollapsed.value = !!data.hideData
    expandedRisks.clear()
    if (panelData.risks.length > 0) expandedRisks.add(0)
    // 自动发送消息（猜你想问场景）
    if (data.autoSend) {
      inputText.value = data.autoSend
      nextTick(() => handleSend())
    }
  }
}, { immediate: true, deep: true })

// ==================== 发送逻辑 ====================
function handleSend(payload) {
  if (isProcessing.value) {
    stopGeneration()
    return
  }
  const text = inputText.value.trim()
  if (!text) return

  inputText.value = ''
  nextTick(() => scrollToBottom(true))

  if (typeof payload === 'object' && payload?.image) {
    console.warn('[KanbanChat] Image upload not yet implemented for kanban')
  }

  sendMessage(text)
}

// ==================== 面板操作 ====================
function handleQuickQuestion(question) {
  emit('question-click', question)
  // 直接发送问题到对话
  inputText.value = question
  nextTick(() => handleSend())
}

function close() {
  emit('update:visible', false)
  emit('close')
}

// 侧边栏关闭时同步关闭文件面板
watch(() => props.visible, (vis) => {
  if (!vis) {
    filePanelOpen.value = false
    filePanelExpanded.value = false
  }
})

// 侧边栏中文件按钮：打开/关闭文件系统面板
function handleTogglePanel() {
  if (!currentThreadId.value) {
    antMessage.warning('请先开始对话后使用文件系统')
    return
  }
  filePanelOpen.value = !filePanelOpen.value
}

// 文件面板刷新回调
function handleFilePanelRefresh() {
  // AgentPanel 内部自行处理刷新，这里无需额外操作
}

function toggleRisk(index) {
  if (expandedRisks.has(index)) {
    expandedRisks.delete(index)
  } else {
    expandedRisks.add(index)
  }
}

function riskLevel(level) {
  if (level === 'critical' || level === 'high' || level === 'danger') return 'danger'
  if (level === 'warning' || level === 'yellow' || level === 'medium') return 'warning'
  return 'normal'
}

function riskLevelText(level) {
  const n = riskLevel(level)
  const map = { danger: '高风险', warning: '中风险', normal: '低风险' }
  return map[n] || '风险'
}

function formatReasoning(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
/* Overlay */
.ai-sidepanel__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
}

/* Panel */
.ai-sidepanel {
  position: fixed;
  top: 0;
  right: 0;
  width: 480px;
  height: 100vh;
  background: var(--gray-0, #fff);
  z-index: 1001;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

/* Header */
.ai-sidepanel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}
.ai-sidepanel__header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-sidepanel__title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-sidepanel__subtitle {
  font-size: 11px;
  color: var(--gray-500, #6b7280);
  margin: 2px 0 0;
}
.ai-sidepanel__close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-500, #6b7280);
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.ai-sidepanel__close:hover {
  background: var(--gray-100, #f3f4f6);
  transform: scale(1.05);
}

/* ===== 统一滚动区域 ===== */
.ai-sidepanel__body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-200, #e5e7eb) transparent;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: var(--gray-200, #e5e7eb);
    border-radius: 4px;
  }
}

/* ===== Data Section (可折叠，无独立滚动) ===== */
.ai-sidepanel__data-section {
  border-bottom: 1px solid var(--gray-100, #f3f4f6);
}

.ai-sidepanel__data-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 20px;
  border: none;
  background: var(--gray-50, #f9fafb);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600, #4b5563);
  transition: background 0.15s;
  position: sticky;
  top: 0;
  z-index: 1;

  &:hover {
    background: var(--gray-100, #f3f4f6);
  }
}

.ai-sidepanel__data-toggle-arrow {
  transition: transform 0.2s;
  color: var(--gray-400, #9ca3af);
}

.ai-sidepanel__data-toggle-arrow--open {
  transform: rotate(180deg);
}

.ai-sidepanel__data-toggle-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 500;
  color: #f59e0b;
  background: #fffbeb;
  padding: 2px 6px;
  border-radius: 8px;
}

.ai-sidepanel__data-content {
  overflow: hidden;
  transition: max-height 0.3s ease, opacity 0.25s ease, padding 0.3s ease;
  max-height: 9999px;
  opacity: 1;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ai-sidepanel__data-section--collapsed .ai-sidepanel__data-content {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

/* ===== 对话消息区域 ===== */
.ai-sidepanel__chat-messages {
  padding: 12px 16px;
}

/* ===== 固定底部输入区 ===== */
.ai-sidepanel__input-bar {
  padding: 8px 12px 12px;
  border-top: 1px solid var(--gray-100, #f3f4f6);
  background: var(--gray-0, #fff);
  flex-shrink: 0;
  overflow: visible;
}

/* Progress */
.ai-sidepanel__progress {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ai-sidepanel__progress-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--gray-50, #f9fafb);
  border-radius: 8px;
  border: 1px solid var(--gray-100, #f3f4f6);
}
.ai-sidepanel__progress-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ai-sidepanel__progress-dot--normal { background: #10b981; }
.ai-sidepanel__progress-dot--warning { background: #f59e0b; }
.ai-sidepanel__progress-dot--danger { background: #ef4444; }
.ai-sidepanel__progress-label {
  font-size: 11px;
  color: var(--gray-500, #6b7280);
}
.ai-sidepanel__progress-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800, #1f2937);
}
.ai-sidepanel__progress-value--danger { color: #ef4444; }
.ai-sidepanel__progress-value--warning { color: #d97706; }

/* Section Title */
.ai-sidepanel__section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600, #4b5563);
  margin-bottom: 10px;
}

/* Reasoning */
.ai-sidepanel__reasoning-text {
  font-size: 13px;
  color: var(--gray-700, #374151);
  line-height: 1.7;
  padding: 12px 14px;
  background: linear-gradient(135deg, #faf5ff, #eff6ff);
  border-radius: 8px;
}
.ai-sidepanel__reasoning-text :deep(strong) {
  color: var(--gray-900, #111827);
}

/* Risk Cards */
.ai-sidepanel__risk-count {
  margin-left: auto;
  font-size: 10px;
  color: var(--gray-400, #9ca3af);
  font-weight: 400;
}

.ai-sidepanel__risk-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-sidepanel__risk-card {
  border: 1px solid var(--gray-100, #f3f4f6);
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.ai-sidepanel__risk-card--danger {
  border-left: 3px solid #ef4444;
  background: linear-gradient(135deg, #fff5f5, #fff);
}
.ai-sidepanel__risk-card--warning {
  border-left: 3px solid #f59e0b;
  background: linear-gradient(135deg, #fffbeb, #fff);
}
.ai-sidepanel__risk-card--normal {
  border-left: 3px solid #10b981;
  background: linear-gradient(135deg, #ecfdf5, #fff);
}

.ai-sidepanel__risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.ai-sidepanel__risk-header:hover {
  background: rgba(0, 0, 0, 0.02);
}

.ai-sidepanel__risk-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  letter-spacing: 0.5px;
}
.ai-sidepanel__risk-badge--danger {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}
.ai-sidepanel__risk-badge--warning {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
}
.ai-sidepanel__risk-badge--normal {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.ai-sidepanel__risk-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800, #1f2937);
  line-height: 1.4;
}

.ai-sidepanel__risk-arrow {
  color: var(--gray-400, #9ca3af);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.ai-sidepanel__risk-arrow--open {
  transform: rotate(180deg);
}

.ai-sidepanel__risk-body {
  padding: 4px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 三段式分区 */
.ai-sidepanel__risk-section {
  padding: 10px 12px;
  border-radius: 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
}

.ai-sidepanel__risk-section--impact {
  background: #fffbeb;
  border-color: #fef3c7;
}

.ai-sidepanel__risk-section--suggestion {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.ai-sidepanel__risk-section-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--gray-600, #4b5563);
  margin-bottom: 4px;
}

.ai-sidepanel__risk-section--impact .ai-sidepanel__risk-section-header {
  color: #b45309;
}

.ai-sidepanel__risk-section--suggestion .ai-sidepanel__risk-section-header {
  color: #15803d;
}

.ai-sidepanel__risk-section-content {
  font-size: 12px;
  line-height: 1.7;
  color: var(--gray-700, #374151);
}

.ai-sidepanel__risk-section--suggestion .ai-sidepanel__risk-section-content {
  color: #166534;
}

/* Quick Questions */
.ai-sidepanel__question-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ai-sidepanel__question-btn {
  padding: 6px 12px;
  font-size: 11px;
  color: var(--gray-600, #4b5563);
  background: var(--gray-50, #f9fafb);
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.4;
}
.ai-sidepanel__question-btn:hover {
  color: #6366f1;
  border-color: #c7d2fe;
  background: #eef2ff;
}

/* Transitions */
.ai-overlay-enter-active,
.ai-overlay-leave-active {
  transition: opacity 0.3s ease;
}
.ai-overlay-enter-from,
.ai-overlay-leave-to {
  opacity: 0;
}

.ai-sidepanel-enter-active,
.ai-sidepanel-leave-active {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.ai-sidepanel-enter-from,
.ai-sidepanel-leave-to {
  transform: translateX(100%);
}

.ai-collapse-enter-active,
.ai-collapse-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.ai-collapse-enter-from,
.ai-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
.ai-collapse-enter-to,
.ai-collapse-leave-from {
  opacity: 1;
  max-height: 500px;
}

/* Responsive */
@media (max-width: 640px) {
  .ai-sidepanel {
    width: 100%;
  }
}

/* ===== 文件系统浮动面板 ===== */
.ai-sidepanel__file-panel {
  position: fixed;
  top: 0;
  right: 480px;
  width: 480px; /* JS 拖拽时会动态更新 */
  height: 75vh;
  background: var(--gray-0, #fff);
  z-index: 1002;
  border-radius: 0 0 16px 16px;
  border: 1px solid var(--gray-150, #e5e7eb);
  border-top: none;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.ai-sidepanel__file-panel.is-expanded {
  height: 100vh;
  border-radius: 0;
}

/* 文件面板过渡动画 */
.ai-filepanel-enter-active,
.ai-filepanel-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
}

.ai-filepanel-enter-from,
.ai-filepanel-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@media (max-width: 640px) {
  .ai-sidepanel__file-panel {
    right: 0;
    width: 100%;
    border-radius: 16px 16px 0 0;
    top: auto;
    bottom: 0;
    height: 50vh;
    border: 1px solid var(--gray-150, #e5e7eb);
    border-bottom: none;
  }

  .ai-sidepanel__file-panel.is-expanded {
    height: 85vh;
  }
}
</style>

<!-- 非scoped: 确保弹窗层级高于文件面板(z-index:1002) -->
<style lang="less">
.ant-modal-wrap,
.ant-modal-mask {
  z-index: 1010 !important;
}
</style>
