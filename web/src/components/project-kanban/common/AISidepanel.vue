<template>
  <!-- 遮罩层 -->
  <Teleport to="body">
    <Transition name="ai-overlay">
      <div v-if="visible" class="ai-sidepanel__overlay" @click="close" />
    </Transition>
    <Transition name="ai-sidepanel">
      <div
        v-if="visible"
        ref="sidepanelRef"
        class="ai-sidepanel"
        :class="{ 'is-resizing': isResizing }"
      >
        <!-- 拖拽手柄 -->
        <div class="resize-handle" @pointerdown="startResize" />
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

              <!-- 雷达图（项目级数据才有） -->
              <div v-if="panelData.radarData" class="ai-sidepanel__radar">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: #6366f1" />
                  <span>综合评估</span>
                </div>
                <div ref="radarChartRef" class="ai-sidepanel__radar-chart" />
              </div>

              <!-- 概览统计（任务令AI概览：已完成/进行中/待启动 三格大数字） -->
              <div v-if="panelData.overviewStats" class="ai-sidepanel__overview-stats">
                <div class="ai-sidepanel__overview-stat ai-sidepanel__overview-stat--completed">
                  <span class="ai-sidepanel__overview-num">{{ panelData.overviewStats.completed }}</span>
                  <span class="ai-sidepanel__overview-label">已完成</span>
                </div>
                <div class="ai-sidepanel__overview-stat ai-sidepanel__overview-stat--progress">
                  <span class="ai-sidepanel__overview-num">{{ panelData.overviewStats.inProgress }}</span>
                  <span class="ai-sidepanel__overview-label">进行中</span>
                </div>
                <div class="ai-sidepanel__overview-stat ai-sidepanel__overview-stat--pending">
                  <span class="ai-sidepanel__overview-num">{{ panelData.overviewStats.pending }}</span>
                  <span class="ai-sidepanel__overview-label">待启动</span>
                </div>
              </div>

              <!-- 各产业进展（任务令AI概览：产业分组卡片+进度条） -->
              <div v-if="panelData.industryCards?.length" class="ai-sidepanel__industries">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: #6366f1" />
                  <span>各产业进展</span>
                </div>
                <div class="ai-sidepanel__industry-list">
                  <div
                    v-for="(ind, i) in panelData.industryCards"
                    :key="i"
                    class="ai-sidepanel__industry-card"
                  >
                    <div class="ai-sidepanel__industry-header">
                      <span class="ai-sidepanel__industry-name">🏭 {{ ind.name }}</span>
                      <span class="ai-sidepanel__industry-pct" :class="`ai-sidepanel__industry-pct--${ind.status}`">
                        {{ ind.completed }}/{{ ind.total }}（{{ ind.pct }}%）
                      </span>
                    </div>
                    <div class="ai-sidepanel__industry-bar">
                      <div
                        class="ai-sidepanel__industry-bar-fill"
                        :class="`ai-sidepanel__industry-bar-fill--${ind.status}`"
                        :style="{ width: ind.pct + '%' }"
                      />
                    </div>
                    <div class="ai-sidepanel__industry-meta">
                      <span class="ai-sidepanel__industry-meta-item">已完成 {{ ind.completed }}</span>
                      <span v-if="ind.highRisk > 0" class="ai-sidepanel__industry-meta-item ai-sidepanel__industry-meta-item--danger">高风险 {{ ind.highRisk }}</span>
                      <span v-if="ind.mediumRisk > 0" class="ai-sidepanel__industry-meta-item ai-sidepanel__industry-meta-item--warning">中风险 {{ ind.mediumRisk }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 关键风险项（任务令AI概览：critical/high 风险的任务令） -->
              <div v-if="panelData.criticalOrders?.length" class="ai-sidepanel__critical-orders">
                <div class="ai-sidepanel__section-title">
                  <AlertTriangle :size="13" style="color: #dc2626" />
                  <span>关键风险项</span>
                </div>
                <div class="ai-sidepanel__critical-list">
                  <div
                    v-for="(o, i) in panelData.criticalOrders"
                    :key="i"
                    class="ai-sidepanel__critical-item"
                  >
                    <div class="ai-sidepanel__critical-name">{{ o.name }}（{{ o.industry }}）</div>
                    <div class="ai-sidepanel__critical-meta">进度 {{ o.progress }}% · 截止 {{ o.deadline }} · {{ o.owner }}</div>
                  </div>
                </div>
              </div>

              <!-- 时间分布（任务令AI概览：本月/下月截止数量） -->
              <div v-if="panelData.timeDistribution" class="ai-sidepanel__time-dist">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: #3b82f6" />
                  <span>时间分布</span>
                </div>
                <div class="ai-sidepanel__time-dist-cards">
                  <div class="ai-sidepanel__time-dist-card">
                    <span class="ai-sidepanel__time-dist-num">{{ panelData.timeDistribution.thisMonth }}</span>
                    <span class="ai-sidepanel__time-dist-label">本月截止</span>
                  </div>
                  <div class="ai-sidepanel__time-dist-card">
                    <span class="ai-sidepanel__time-dist-num">{{ panelData.timeDistribution.nextMonth }}</span>
                    <span class="ai-sidepanel__time-dist-label">下月截止</span>
                  </div>
                </div>
              </div>

              <!-- 当前状态（里程碑子卡片） -->
              <div v-if="panelData.currentPhase" class="ai-sidepanel__current-phase">
                📍 当前状态：{{ panelData.currentPhase }}
              </div>

              <!-- OBP 里程碑节点（结构化卡片，与设计稿一致） -->
              <div v-if="panelData.phases?.length" class="ai-sidepanel__phases">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: #6366f1" />
                  <span>OBP 里程碑节点</span>
                </div>
                <div class="ai-sidepanel__phases-list">
                  <div
                    v-for="(phase, i) in panelData.phases"
                    :key="i"
                    class="ai-sidepanel__phase-card"
                    :class="{
                      'ai-sidepanel__phase-card--active': phase.status === 'active',
                      'ai-sidepanel__phase-card--risk-high': phase.risk === 'high',
                      'ai-sidepanel__phase-card--risk-medium': phase.risk === 'medium'
                    }"
                  >
                    <div class="ai-sidepanel__phase-header">
                      <span class="ai-sidepanel__phase-icon">
                        <svg v-if="phase.status === 'completed'" viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="#22c55e"/><path d="M5 8l2 2 4-4" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        <svg v-else-if="phase.status === 'active'" viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="#f59e0b"/><path d="M6 5l4 3-4 3z" fill="white"/></svg>
                        <svg v-else viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="#d1d5db"/><circle cx="8" cy="8" r="3" fill="white"/></svg>
                      </span>
                      <span class="ai-sidepanel__phase-name">{{ phase.name }}</span>
                      <span v-if="phase.risk && phase.risk !== 'none'" class="ai-sidepanel__phase-risk-tag" :class="`ai-sidepanel__phase-risk-tag--${phase.risk}`">
                        {{ phase.risk === 'high' ? '高风险' : '中风险' }}
                      </span>
                      <span class="ai-sidepanel__phase-status" :class="`ai-sidepanel__phase-status--${phase.status}`">{{ phase.statusText }}</span>
                      <span class="ai-sidepanel__phase-date">{{ phase.date }}</span>
                    </div>
                    <!-- 技术目标 (Gate Criteria) -->
                    <div v-if="phase.objectives?.length" class="ai-sidepanel__phase-objectives">
                      <div class="ai-sidepanel__phase-objectives-label">技术目标</div>
                      <ul class="ai-sidepanel__phase-objectives-list">
                        <li v-for="(obj, j) in phase.objectives" :key="j">
                          <span class="ai-sidepanel__phase-obj-check">✓</span>
                          {{ obj }}
                        </li>
                      </ul>
                    </div>
                    <!-- 风险原因 -->
                    <div v-if="phase.riskReason" class="ai-sidepanel__phase-risk-reason">
                      ⚠️ 风险原因：{{ phase.riskReason }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 关键进度列表 / 技术目标（标题可自定义） -->
              <div v-if="panelData.keyPoints?.length" class="ai-sidepanel__keypoints">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: #6366f1" />
                  <span>{{ panelData.keyPointsTitle || '关键进度' }}</span>
                </div>
                <ul class="ai-sidepanel__keypoints-list">
                  <li v-for="(point, i) in panelData.keyPoints" :key="i">{{ point }}</li>
                </ul>
              </div>

              <!-- 独立风险提示框（阶段详情页的风险原因） -->
              <div v-if="panelData.riskReason" class="ai-sidepanel__standalone-risk-reason">
                <div class="ai-sidepanel__standalone-risk-reason-title">⚠️ 风险详情</div>
                <div class="ai-sidepanel__standalone-risk-reason-text">{{ panelData.riskReason }}</div>
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
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Lightbulb, X, Sparkles, AlertTriangle, ChevronDown, MessageCircle, Search, Info, CheckCircle, Target } from 'lucide-vue-next'

echarts.use([RadarChart, TooltipComponent, CanvasRenderer])
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
const radarChartRef = ref(null)
const sidepanelRef = ref(null)
let radarChart = null

// 文件面板拖拽状态
let startResizeX = 0
let startResizeWidth = 0

// ==================== 主侧边栏拖拽调整宽度 ====================
const isResizing = ref(false)
const SIDE_PANEL_MIN_WIDTH = 400
const SIDE_PANEL_MAX_WIDTH = 1200
const SIDE_PANEL_WIDTH_KEY = 'kanban-sidepanel-width'

let resizePointerId = null
let pendingClientX = 0
let resizeFrameId = 0
let sidepanelStartX = 0
let sidepanelStartWidth = 0

const flushResize = () => {
  resizeFrameId = 0
  if (!isResizing.value || !sidepanelRef.value) return
  const deltaX = pendingClientX - sidepanelStartX
  const newWidth = Math.max(SIDE_PANEL_MIN_WIDTH, Math.min(SIDE_PANEL_MAX_WIDTH, sidepanelStartWidth - deltaX))
  sidepanelRef.value.style.width = `${newWidth}px`
  // 同步更新文件面板位置
  if (filePanelRef.value) {
    filePanelRef.value.style.right = `${newWidth}px`
  }
}

const queueResize = (clientX) => {
  pendingClientX = clientX
  if (resizeFrameId) return
  resizeFrameId = window.requestAnimationFrame(flushResize)
}

const startResize = (e) => {
  if (e.button !== 0) return
  if (!sidepanelRef.value) return

  isResizing.value = true
  resizePointerId = e.pointerId
  pendingClientX = e.clientX
  sidepanelStartX = e.clientX
  sidepanelStartWidth = sidepanelRef.value.offsetWidth
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  e.currentTarget?.setPointerCapture?.(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', stopResize)
  window.addEventListener('pointercancel', stopResize)
}

const onPointerMove = (e) => {
  if (!isResizing.value || e.pointerId !== resizePointerId) return
  queueResize(e.clientX)
}

const stopResize = (e) => {
  if (!isResizing.value || (e && e.pointerId !== resizePointerId)) return

  if (resizeFrameId) {
    window.cancelAnimationFrame(resizeFrameId)
    resizeFrameId = 0
  }

  if (e) {
    pendingClientX = e.clientX
    flushResize()
  }

  isResizing.value = false
  resizePointerId = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopResize)
  window.removeEventListener('pointercancel', stopResize)

  // 持久化宽度
  if (sidepanelRef.value) {
    const width = sidepanelRef.value.offsetWidth
    localStorage.setItem(SIDE_PANEL_WIDTH_KEY, String(width))
  }
}

/** 应用保存的侧边栏宽度 */
function applySavedWidth() {
  if (!sidepanelRef.value) return
  const saved = localStorage.getItem(SIDE_PANEL_WIDTH_KEY)
  if (!saved) return
  const width = parseInt(saved, 10)
  if (Number.isNaN(width) || width < SIDE_PANEL_MIN_WIDTH || width > SIDE_PANEL_MAX_WIDTH) {
    localStorage.removeItem(SIDE_PANEL_WIDTH_KEY)
    return
  }
  sidepanelRef.value.style.width = `${width}px`
  if (filePanelRef.value) {
    filePanelRef.value.style.right = `${width}px`
  }
}

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
    nextTick(() => applySavedWidth())
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
  if (radarChart) { radarChart.dispose(); radarChart = null }
  if (resizeFrameId) {
    window.cancelAnimationFrame(resizeFrameId)
    resizeFrameId = 0
  }
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopResize)
  window.removeEventListener('pointercancel', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
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
  keyPoints: [],
  keyPointsTitle: '',
  phases: [],
  currentPhase: '',
  riskReason: '',
  overviewStats: null,
  industryCards: [],
  criticalOrders: [],
  timeDistribution: null,
  reasoning: '',
  risks: [],
  quickQuestions: []
})

const expandedRisks = reactive(new Set())

const hasPanelData = computed(() => {
  return panelData.progress?.length || panelData.keyPoints?.length || panelData.phases?.length || panelData.reasoning || panelData.risks?.length
})

watch(() => [props.visible, props.data], ([vis, data]) => {
  if (vis && data) {
    panelData.title = data.title || 'AI 分析'
    panelData.subtitle = data.subtitle || ''
    panelData.progress = data.progress || []
    panelData.keyPoints = data.keyPoints || []
    panelData.keyPointsTitle = data.keyPointsTitle || ''
    panelData.phases = data.phases || []
    panelData.currentPhase = data.currentPhase || ''
    panelData.riskReason = data.riskReason || ''
    panelData.overviewStats = data.overviewStats || null
    panelData.industryCards = data.industryCards || []
    panelData.criticalOrders = data.criticalOrders || []
    panelData.timeDistribution = data.timeDistribution || null
    panelData.reasoning = data.reasoning || ''
    panelData.risks = data.risks || []
    panelData.quickQuestions = data.quickQuestions || []
    // 猜你想问点击时隐藏数据概览
    dataCollapsed.value = !!data.hideData
    expandedRisks.clear()
    if (panelData.risks.length > 0) {
      // 支持 riskIndex：自动展开指定索引的风险
      const expandIdx = data.expandedRiskIndex ?? 0
      if (expandIdx >= 0 && expandIdx < panelData.risks.length) {
        expandedRisks.add(expandIdx)
      } else if (panelData.risks.length > 0) {
        expandedRisks.add(0)
      }
    }
    // 自动发送消息（猜你想问场景）
    if (data.autoSend) {
      inputText.value = data.autoSend
      nextTick(() => handleSend())
    }
    // 雷达图：数据加载后初始化
    nextTick(() => initOrUpdateRadar())
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

// ==================== 雷达图 ====================
function initOrUpdateRadar() {
  if (!panelData.radarData || !radarChartRef.value) {
    if (radarChart) { radarChart.dispose(); radarChart = null }
    return
  }
  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value)
  }
  const { indicators, values } = panelData.radarData
  radarChart.setOption({
    radar: {
      indicator: indicators,
      shape: 'circle',
      splitNumber: 4,
      axisName: { color: '#6b7280', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(99,102,241,0.02)', 'rgba(99,102,241,0.04)', 'rgba(99,102,241,0.06)', 'rgba(99,102,241,0.08)'] } },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        areaStyle: { color: 'rgba(99,102,241,0.18)' },
        lineStyle: { color: '#6366f1', width: 2 },
        itemStyle: { color: '#6366f1' },
        symbol: 'circle',
        symbolSize: 5
      }]
    }],
    tooltip: {
      trigger: 'item',
      formatter(params) {
        const names = indicators.map(i => i.name)
        return params.value.map((v, i) => `${names[i]}: ${v}`).join('<br/>')
      }
    }
  })
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
  width: clamp(560px, 34vw, 960px);
  height: 100vh;
  background: var(--gray-0, #fff);
  z-index: 1001;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

/* 拖拽手柄 */
.resize-handle {
  position: absolute;
  left: -3px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 48px;
  cursor: col-resize;
  background: var(--gray-300, #d1d5db);
  border-radius: 3px;
  z-index: 10;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.ai-sidepanel:hover .resize-handle,
.ai-sidepanel.is-resizing .resize-handle {
  opacity: 1;
}

.resize-handle:hover,
.ai-sidepanel.is-resizing .resize-handle {
  background: var(--gray-400, #9ca3af);
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
  white-space: nowrap;
  flex-shrink: 0;
}
.ai-sidepanel__progress-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800, #1f2937);
  min-width: 0;
  word-break: break-word;
}
.ai-sidepanel__progress-value--danger { color: #ef4444; }
.ai-sidepanel__progress-value--warning { color: #d97706; }

/* Radar Chart */
.ai-sidepanel__radar-chart {
  width: 100%;
  height: 200px;
}

/* Overview Stats (任务令概览) */
.ai-sidepanel__overview-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 2px;
}
.ai-sidepanel__overview-stat {
  flex: 1;
  text-align: center;
  padding: 10px;
  border-radius: 8px;
}
.ai-sidepanel__overview-stat--completed { background: #f0fdf4; }
.ai-sidepanel__overview-stat--progress { background: #eff6ff; }
.ai-sidepanel__overview-stat--pending { background: #f3f4f6; }
.ai-sidepanel__overview-num {
  display: block;
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}
.ai-sidepanel__overview-stat--completed .ai-sidepanel__overview-num { color: #22c55e; }
.ai-sidepanel__overview-stat--progress .ai-sidepanel__overview-num { color: #3b82f6; }
.ai-sidepanel__overview-stat--pending .ai-sidepanel__overview-num { color: #6b7280; }
.ai-sidepanel__overview-label {
  display: block;
  font-size: 11px;
  color: #6b7280;
  margin-top: 4px;
}

/* Industry Cards (任务令概览) */
.ai-sidepanel__industry-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-sidepanel__industry-card {
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 8px;
}
.ai-sidepanel__industry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.ai-sidepanel__industry-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.ai-sidepanel__industry-pct {
  font-size: 12px;
  font-weight: 600;
}
.ai-sidepanel__industry-pct--danger { color: #ef4444; }
.ai-sidepanel__industry-pct--warning { color: #f59e0b; }
.ai-sidepanel__industry-pct--normal { color: #22c55e; }
.ai-sidepanel__industry-bar {
  width: 100%;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}
.ai-sidepanel__industry-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}
.ai-sidepanel__industry-bar-fill--danger { background: #ef4444; }
.ai-sidepanel__industry-bar-fill--warning { background: #f59e0b; }
.ai-sidepanel__industry-bar-fill--normal { background: #22c55e; }
.ai-sidepanel__industry-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.ai-sidepanel__industry-meta-item {
  font-size: 10px;
  color: #9ca3af;
}
.ai-sidepanel__industry-meta-item--danger { color: #ef4444; }
.ai-sidepanel__industry-meta-item--warning { color: #f59e0b; }

/* Critical Orders (任务令概览) */
.ai-sidepanel__critical-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-sidepanel__critical-item {
  padding: 8px 10px;
  background: #fef2f2;
  border-radius: 6px;
}
.ai-sidepanel__critical-name {
  font-size: 13px;
  font-weight: 500;
  color: #7f1d1d;
}
.ai-sidepanel__critical-meta {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
}

/* Time Distribution (任务令概览) */
.ai-sidepanel__time-dist-cards {
  display: flex;
  gap: 8px;
}
.ai-sidepanel__time-dist-card {
  flex: 1;
  text-align: center;
  padding: 8px;
  background: #eff6ff;
  border-radius: 6px;
}
.ai-sidepanel__time-dist-num {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #3b82f6;
}
.ai-sidepanel__time-dist-label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-top: 2px;
}

/* Current Phase */
.ai-sidepanel__current-phase {
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 8px;
  font-size: 12px;
  color: #0369a1;
  line-height: 1.6;
  margin-bottom: 2px;
}

/* OBP Phases (Structured) */
.ai-sidepanel__phases-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-sidepanel__phase-card {
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  transition: border-color 0.2s;
}
.ai-sidepanel__phase-card--active {
  background: #fffbeb;
}
.ai-sidepanel__phase-card--risk-high {
  border-color: #fca5a5;
}
.ai-sidepanel__phase-card--risk-medium {
  border-color: #fde68a;
}
.ai-sidepanel__phase-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.ai-sidepanel__phase-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
.ai-sidepanel__phase-name {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
}
.ai-sidepanel__phase-risk-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  color: white;
}
.ai-sidepanel__phase-risk-tag--high {
  background: #ef4444;
}
.ai-sidepanel__phase-risk-tag--medium {
  background: #f59e0b;
}
.ai-sidepanel__phase-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 500;
}
.ai-sidepanel__phase-status--completed {
  color: #22c55e;
}
.ai-sidepanel__phase-status--active {
  color: #f59e0b;
}
.ai-sidepanel__phase-status--pending {
  color: #9ca3af;
}
.ai-sidepanel__phase-date {
  font-size: 11px;
  color: #9ca3af;
  margin-left: 6px;
}
.ai-sidepanel__phase-objectives {
  margin-top: 6px;
}
.ai-sidepanel__phase-objectives-label {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 4px;
}
.ai-sidepanel__phase-objectives-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-sidepanel__phase-objectives-list li {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 12px;
  color: #374151;
  line-height: 1.5;
}
.ai-sidepanel__phase-obj-check {
  color: #22c55e;
  font-size: 13px;
  flex-shrink: 0;
}
.ai-sidepanel__phase-risk-reason {
  margin-top: 8px;
  padding: 6px 8px;
  background: #fef2f2;
  border-left: 3px solid #ef4444;
  border-radius: 4px;
  font-size: 11px;
  color: #dc2626;
  line-height: 1.5;
}

/* Standalone Risk Reason (阶段详情页) */
.ai-sidepanel__standalone-risk-reason {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fef2f2;
  border-left: 3px solid #ef4444;
  border-radius: 6px;
}
.ai-sidepanel__standalone-risk-reason-title {
  font-size: 11px;
  font-weight: 600;
  color: #dc2626;
  margin-bottom: 4px;
}
.ai-sidepanel__standalone-risk-reason-text {
  font-size: 12px;
  color: #7f1d1d;
  line-height: 1.6;
}

/* Key Points */
.ai-sidepanel__keypoints-list {
  margin: 0;
  padding: 0 0 0 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-sidepanel__keypoints-list li {
  font-size: 12px;
  line-height: 1.6;
  color: var(--gray-700, #374151);
  position: relative;
}
.ai-sidepanel__keypoints-list li::marker {
  color: #6366f1;
  font-size: 10px;
}

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
  right: clamp(560px, 34vw, 960px);
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
