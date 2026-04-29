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
            <Lightbulb :size="18" style="color: var(--pk-accent)" />
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
        <div ref="scrollContainerRef" class="ai-sidepanel__body" @wheel="onSidepanelWheel">
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
                  <Target :size="13" style="color: var(--pk-accent)" />
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

              <!-- 各分组进展（任务令AI概览：分组卡片+进度条） -->
              <div v-if="panelData.groupCards?.length" class="ai-sidepanel__industries">
                <div class="ai-sidepanel__section-title">
                  <Target :size="13" style="color: var(--pk-accent)" />
                  <span>各分组进展</span>
                </div>
                <div class="ai-sidepanel__industry-list">
                  <div
                    v-for="(card, i) in panelData.groupCards"
                    :key="i"
                    class="ai-sidepanel__industry-card"
                  >
                    <div class="ai-sidepanel__industry-header">
                      <span class="ai-sidepanel__industry-name">📋 {{ card.name }}</span>
                      <span class="ai-sidepanel__industry-pct" :class="`ai-sidepanel__industry-pct--${card.status}`">
                        {{ card.completed }}/{{ card.total }}（{{ card.pct }}%）
                      </span>
                    </div>
                    <div class="ai-sidepanel__industry-bar">
                      <div
                        class="ai-sidepanel__industry-bar-fill"
                        :class="`ai-sidepanel__industry-bar-fill--${card.status}`"
                        :style="{ width: card.pct + '%' }"
                      />
                    </div>
                    <div class="ai-sidepanel__industry-meta">
                      <span class="ai-sidepanel__industry-meta-item">已完成 {{ card.completed }}</span>
                      <span v-if="card.highRisk > 0" class="ai-sidepanel__industry-meta-item ai-sidepanel__industry-meta-item--danger">高风险 {{ card.highRisk }}</span>
                      <span v-if="card.mediumRisk > 0" class="ai-sidepanel__industry-meta-item ai-sidepanel__industry-meta-item--warning">中风险 {{ card.mediumRisk }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 关键风险项（任务令AI概览：critical/high 风险的任务令） -->
              <div v-if="panelData.criticalOrders?.length" class="ai-sidepanel__critical-orders">
                <div class="ai-sidepanel__section-title">
                  <AlertTriangle :size="13" style="color: var(--pk-danger-dark)" />
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
                  <Target :size="13" style="color: var(--pk-group-v2)" />
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
                  <Target :size="13" style="color: var(--pk-accent)" />
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
                        <svg v-if="phase.status === 'completed'" viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="var(--pk-chart-green)"/><path d="M5 8l2 2 4-4" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        <svg v-else-if="phase.status === 'active'" viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="var(--pk-warning)"/><path d="M6 5l4 3-4 3z" fill="white"/></svg>
                        <svg v-else viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="7" fill="var(--pk-border-hover)"/><circle cx="8" cy="8" r="3" fill="var(--pk-card-bg)"/></svg>
                      </span>
                      <span class="ai-sidepanel__phase-name">{{ phase.name }}</span>

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
                  <Target :size="13" style="color: var(--pk-accent)" />
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
                  <Sparkles :size="13" style="color: var(--pk-group-v3)" />
                  <span>AI 分析</span>
                </div>
                <div class="ai-sidepanel__reasoning-text" v-html="formatReasoning(panelData.reasoning)" />
              </div>

              <!-- 风险详情 -->
              <div v-if="panelData.risks?.length" class="ai-sidepanel__risks">
                <div class="ai-sidepanel__section-title">
                  <AlertTriangle :size="13" style="color: var(--pk-warning)" />
                  <span>风险详情</span>
                  <span class="ai-sidepanel__risk-count">{{ panelData.risks.length }}项</span>
                </div>
                <div class="ai-sidepanel__risk-list">
                <div
                  v-for="(risk, i) in panelData.risks"
                  :key="i"
                  class="ai-sidepanel__risk-card"
                >
                  <div class="ai-sidepanel__risk-header" @click="toggleRisk(i)">
                    <span
                      class="ai-sidepanel__risk-dot"
                      :class="`ai-sidepanel__risk-dot--${riskLevel(risk.level)}`"
                    />
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
                          <span style="font-weight: 600;">根因分析</span>
                        </div>
                        <div class="ai-sidepanel__risk-section-content">{{ risk.detail }}</div>
                      </div>
                      <div v-if="risk.impact" class="ai-sidepanel__risk-section">
                        <div class="ai-sidepanel__risk-section-header">
                          <Info :size="12" />
                          <span style="font-weight: 600;">影响范围</span>
                        </div>
                        <div class="ai-sidepanel__risk-section-content">{{ risk.impact }}</div>
                      </div>
                      <div v-if="risk.suggestion" class="ai-sidepanel__risk-section ai-sidepanel__risk-section--suggestion">
                        <div class="ai-sidepanel__risk-section-header">
                          <CheckCircle :size="12" />
                          <span style="font-weight: 600;">消减建议</span>
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
                  <MessageCircle :size="13" style="color: var(--pk-group-v2)" />
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
import { buildDataContext } from '../composables/useAISidepanel'

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
  resetAutoScroll,
  setStreamActive,
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

// ==================== Body 滚动锁定 & 滚轮穿透阻止 ====================
let scrollY = 0

/**
 * 阻止侧边栏滚轮事件穿透到背景页面
 * - 侧边栏内容可正常滚动
 * - 滚到顶部再往上滚 / 滚到底部再往下滚 → 阻止冒泡，不穿透到背景
 */
function onSidepanelWheel(e) {
  const el = e.currentTarget
  const { scrollTop, scrollHeight, clientHeight } = el
  const atTop = scrollTop <= 0
  const atBottom = scrollHeight - scrollTop - clientHeight <= 1

  // 向上滚且已在顶部 → 阻止穿透
  if (e.deltaY < 0 && atTop) {
    e.preventDefault()
    return
  }
  // 向下滚且已在底部 → 阻止穿透
  if (e.deltaY > 0 && atBottom) {
    e.preventDefault()
    return
  }
  // 中间正常滚动，不阻止
}

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
// 注意：滚动容器在 v-if="visible" 内部，每次 visible 变 true 时 DOM 重建，
// template ref 会更新但 onMounted 不会重跑，所以必须 watch ref 变化
watch(scrollContainerRef, (el) => {
  if (el) {
    setScrollContainer(el)
  }
})

onMounted(() => {
  // 初始可见时也注册一次（watch immediate 不适合 template ref）
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

// ==================== 自动滚动 ====================
// 滚动触发点：
//   1. handleSend → resetAutoScroll() + scrollToBottom(true) → 发消息时强制滚底
//   2. setStreamActive(true) → 启动 RAF 跟滚循环
// 用户向上滚轮 → wheel 事件立即停止 RAF（比 scroll 事件更早，消除竞态）
// 用户滚回底部 → onScrollChange 恢复跟滚（仅流式活跃时）
// 流式结束 → setStreamActive(false) → 停止 RAF，永不自动重启

watch(
  () => isProcessing.value,
  (processing) => {
    if (processing) {
      nextTick(() => scrollToBottom(true))
      setStreamActive(true)
    } else {
      setStreamActive(false)
    }
  }
)

// 组件卸载时清理 RAF
onBeforeUnmount(() => setStreamActive(false))

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
  groupCards: [],
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
    panelData.groupCards = data.groupCards || []
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

  // 发送前重置滚动状态（恢复自动跟滚）
  resetAutoScroll()

  if (typeof payload === 'object' && payload?.image) {
    console.warn('[KanbanChat] Image upload not yet implemented for kanban')
  }

  // 从数据概览生成隐藏上下文，注入到 AI 对话中
  const context = hasPanelData.value ? buildDataContext(panelData) : ''

  // sendMessage 内部会同步添加消息到 threadMessages
  sendMessage(text, { context })

  // 强制滚到底部（用户消息气泡 + 即将开始的流式回复）
  nextTick(() => scrollToBottom(true))
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
      axisName: { color: 'var(--pk-text-secondary)', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(99,102,241,0.02)', 'rgba(99,102,241,0.04)', 'rgba(99,102,241,0.06)', 'rgba(99,102,241,0.08)'] } },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        areaStyle: { color: 'rgba(99,102,241,0.18)' },
        lineStyle: { color: 'var(--pk-accent)', width: 2 },
        itemStyle: { color: 'var(--pk-accent)' },
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
  background: var(--gray-0);
  z-index: 1001;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

/* 拖拽手柄 */
.resize-handle {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 64px;
  cursor: col-resize;
  z-index: 10;
  border-radius: 0 3px 3px 0;
  background: rgba(99, 102, 241, 0.35);
  transition: all 0.2s ease;
}

.resize-handle:hover,
.ai-sidepanel.is-resizing .resize-handle {
  width: 5px;
  background: rgba(99, 102, 241, 0.6);
  box-shadow: 1px 0 6px rgba(99, 102, 241, 0.2);
}

/* Header */
.ai-sidepanel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, var(--pk-accent-gradient-from) 0%, var(--pk-accent-gradient-to) 100%);
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
  color: var(--pk-text);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-sidepanel__subtitle {
  font-size: 13px;
  color: var(--gray-500);
  margin: 2px 0 0;
}
.ai-sidepanel__close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--pk-card-bg);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-500);
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.ai-sidepanel__close:hover {
  background: var(--gray-100);
  transform: scale(1.05);
}

/* ===== 统一滚动区域 ===== */
.ai-sidepanel__body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-200) transparent;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: var(--gray-200);
    border-radius: 4px;
  }
}

/* ===== Data Section (可折叠，无独立滚动) ===== */
.ai-sidepanel__data-section {
  border-bottom: 1px solid var(--gray-100);
}

.ai-sidepanel__data-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 20px;
  border: none;
  background: var(--gray-50);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  transition: background 0.15s;
  position: sticky;
  top: 0;
  z-index: 1;

  &:hover {
    background: var(--gray-100);
  }
}

.ai-sidepanel__data-toggle-arrow {
  transition: transform 0.2s;
  color: var(--gray-400);
}

.ai-sidepanel__data-toggle-arrow--open {
  transform: rotate(180deg);
}

.ai-sidepanel__data-toggle-badge {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
  color: var(--pk-warning);
  background: var(--pk-warning-lighter);
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
  border-top: 1px solid var(--gray-100);
  background: var(--gray-0);
  flex-shrink: 0;
  overflow: visible;
}

/* Progress */
.ai-sidepanel__progress {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.ai-sidepanel__progress-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}
.ai-sidepanel__progress-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ai-sidepanel__progress-dot--normal { background: var(--pk-chart-green); }
.ai-sidepanel__progress-dot--warning { background: var(--pk-warning); }
.ai-sidepanel__progress-dot--danger { background: var(--pk-danger); }
.ai-sidepanel__progress-label {
  font-size: 13px;
  color: var(--gray-500);
  white-space: nowrap;
  flex-shrink: 0;
}
.ai-sidepanel__progress-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
  min-width: 0;
  word-break: break-word;
}
.ai-sidepanel__progress-value--danger { color: var(--pk-danger); }
.ai-sidepanel__progress-value--warning { color: var(--pk-warning); }

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
.ai-sidepanel__overview-stat--completed { background: var(--pk-success-lighter); }
.ai-sidepanel__overview-stat--progress { background: var(--pk-group-v2-light); }
.ai-sidepanel__overview-stat--pending { background: var(--pk-page-bg); }
.ai-sidepanel__overview-num {
  display: block;
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}
.ai-sidepanel__overview-stat--completed .ai-sidepanel__overview-num { color: var(--pk-chart-green); }
.ai-sidepanel__overview-stat--progress .ai-sidepanel__overview-num { color: var(--pk-group-v2); }
.ai-sidepanel__overview-stat--pending .ai-sidepanel__overview-num { color: var(--pk-text-secondary); }
.ai-sidepanel__overview-label {
  display: block;
  font-size: 13px;
  color: var(--pk-text-secondary);
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
  background: var(--pk-page-bg);
  border-radius: 8px;
}
.ai-sidepanel__industry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.ai-sidepanel__industry-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--pk-text);
}
.ai-sidepanel__industry-pct {
  font-size: 13px;
  font-weight: 600;
}
.ai-sidepanel__industry-pct--danger { color: var(--pk-danger); }
.ai-sidepanel__industry-pct--warning { color: var(--pk-warning); }
.ai-sidepanel__industry-pct--normal { color: var(--pk-chart-green); }
.ai-sidepanel__industry-bar {
  width: 100%;
  height: 4px;
  background: var(--pk-border);
  border-radius: 2px;
  overflow: hidden;
}
.ai-sidepanel__industry-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}
.ai-sidepanel__industry-bar-fill--danger { background: var(--pk-danger); }
.ai-sidepanel__industry-bar-fill--warning { background: var(--pk-warning); }
.ai-sidepanel__industry-bar-fill--normal { background: var(--pk-chart-green); }
.ai-sidepanel__industry-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.ai-sidepanel__industry-meta-item {
  font-size: 12px;
  color: var(--pk-text-tertiary);
}
.ai-sidepanel__industry-meta-item--danger { color: var(--pk-danger-dark); }
.ai-sidepanel__industry-meta-item--warning { color: var(--pk-warning); }

/* Critical Orders (任务令概览) */
.ai-sidepanel__critical-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-sidepanel__critical-item {
  padding: 8px 10px;
  background: var(--pk-danger-lighter);
  border-radius: 6px;
}
.ai-sidepanel__critical-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--pk-danger-dark);
}
.ai-sidepanel__critical-meta {
  font-size: 13px;
  color: var(--pk-text-tertiary);
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
  background: var(--pk-group-v2-light);
  border-radius: 6px;
}
.ai-sidepanel__time-dist-num {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: var(--pk-group-v2);
}
.ai-sidepanel__time-dist-label {
  display: block;
  font-size: 12px;
  color: var(--pk-text-secondary);
  margin-top: 2px;
}

/* Current Phase */
.ai-sidepanel__current-phase {
  border-radius: 8px;
  font-size: 13px;
  color: var(--pk-group-v2);
  line-height: 1.6;
  margin-bottom: 2px;
}

/* OBP Phases (Structured) */
.ai-sidepanel__phases-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-sidepanel__phase-card {
  padding: 12px 14px;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: box-shadow 0.2s ease;
}
.ai-sidepanel__phase-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04);
}
.ai-sidepanel__phase-card--active {
  border-left: 2px solid var(--pk-warning);
  padding-left: 12px;
}
.ai-sidepanel__phase-card--risk-high {
  border-left: 2px solid var(--pk-danger);
  padding-left: 12px;
}
.ai-sidepanel__phase-card--risk-medium {
  border-left: 2px solid var(--pk-warning);
  padding-left: 12px;
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
  font-size: 14px;
  color: var(--pk-text);
}
.ai-sidepanel__phase-status {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
}
.ai-sidepanel__phase-status--completed {
  color: var(--pk-success);
}
.ai-sidepanel__phase-status--active {
  color: var(--pk-warning);
}
.ai-sidepanel__phase-status--pending {
  color: var(--pk-text-tertiary);
}
.ai-sidepanel__phase-date {
  font-size: 12px;
  color: var(--pk-text-tertiary);
  margin-left: 6px;
}
.ai-sidepanel__phase-objectives {
  margin-top: 6px;
}
.ai-sidepanel__phase-objectives-label {
  font-size: 12px;
  color: var(--pk-text-secondary);
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
  background: var(--pk-page-bg);
  border-radius: 6px;
  font-size: 13px;
  color: var(--pk-text-secondary);
  line-height: 1.5;
}
.ai-sidepanel__phase-obj-check {
  color: var(--pk-chart-green);
  font-size: 14px;
  flex-shrink: 0;
}
.ai-sidepanel__phase-risk-reason {
  margin-top: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--pk-danger-dark);
  line-height: 1.5;
}

/* Standalone Risk Reason (阶段详情页) */
.ai-sidepanel__standalone-risk-reason {
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--pk-danger-light);
  border-left: 3px solid var(--pk-danger);
  border-radius: 6px;
}
.ai-sidepanel__standalone-risk-reason-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--pk-danger-dark);
  margin-bottom: 4px;
}
.ai-sidepanel__standalone-risk-reason-text {
  font-size: 13px;
  color: var(--pk-danger-dark);
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
  color: var(--gray-700);
  position: relative;
}
.ai-sidepanel__keypoints-list li::marker {
  color: var(--pk-accent);
  font-size: 13px;
}

/* Section Title */
.ai-sidepanel__section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-600);
  margin-bottom: 10px;
}

/* Reasoning */
.ai-sidepanel__reasoning-text {
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.7;
  padding: 8px 0;
}
.ai-sidepanel__reasoning-text :deep(strong) {
  color: var(--gray-900);
}

/* Risk Cards */
.ai-sidepanel__risk-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--gray-400);
  font-weight: 400;
}

.ai-sidepanel__risk-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-sidepanel__risk-card {
  padding: 12px 14px;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: box-shadow 0.2s ease;
}
.ai-sidepanel__risk-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04);
}

.ai-sidepanel__risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: opacity 0.15s;
}
.ai-sidepanel__risk-header:hover {
  opacity: 0.7;
}

.ai-sidepanel__risk-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8), 0 0 4px rgba(0, 0, 0, 0.08);
}
.ai-sidepanel__risk-dot--danger { background: var(--pk-danger); }
.ai-sidepanel__risk-dot--warning { background: var(--pk-warning); }
.ai-sidepanel__risk-dot--normal { background: var(--pk-chart-green); }

.ai-sidepanel__risk-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
  line-height: 1.4;
}

.ai-sidepanel__risk-arrow {
  color: var(--gray-400);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.ai-sidepanel__risk-arrow--open {
  transform: rotate(180deg);
}

.ai-sidepanel__risk-body {
  padding: 8px 0 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 三段式分区 */
.ai-sidepanel__risk-section {
  padding: 6px 0;
}

.ai-sidepanel__risk-section-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 800 !important;
  color: var(--gray-800);
  margin-bottom: 4px;
}

.ai-sidepanel__risk-section-content {
  font-size: 13px;
  line-height: 1.7;
  color: var(--gray-700);
}

.ai-sidepanel__risk-section--suggestion {
  padding-left: 10px;
  border-left: 2px solid var(--pk-accent);
}
.ai-sidepanel__risk-section--suggestion .ai-sidepanel__risk-section-header {
  color: var(--pk-accent-dark);
}
.ai-sidepanel__risk-section--suggestion .ai-sidepanel__risk-section-header :deep(svg) {
  color: var(--pk-accent);
}

/* Quick Questions */
.ai-sidepanel__question-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ai-sidepanel__question-btn {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--gray-600);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.4;
}
.ai-sidepanel__question-btn:hover {
  color: var(--pk-accent);
  border-color: var(--pk-accent-light);
  background: var(--pk-accent-light);
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
  right: 0;
  width: 480px; /* JS 拖拽时会动态更新 */
  height: 75vh;
  background: var(--gray-0);
  z-index: 1002;
  border-radius: 0 0 0 16px;
  border: 1px solid var(--gray-150);
  border-right: none;
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
    border-radius: 0;
    top: auto;
    bottom: 0;
    height: 50vh;
    border: 1px solid var(--gray-150);
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
