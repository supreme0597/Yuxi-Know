<template>
  <!-- 遮罩层 -->
  <Teleport to="body">
    <Transition name="md-overlay">
      <div v-if="visible" class="md-sidepanel__overlay" @click="close" />
    </Transition>
    <Transition name="md-sidepanel">
      <div v-if="visible" ref="panelRef" class="md-sidepanel">
        <!-- 拖拽手柄 -->
        <div class="md-sidepanel__resize-handle" @pointerdown="startResize" />

        <!-- 头部 -->
        <div class="md-sidepanel__header">
          <div class="md-sidepanel__header-left">
            <component :is="iconComponent" :size="18" style="color: var(--pk-accent)" />
            <div>
              <h2 class="md-sidepanel__title">{{ title }}</h2>
              <p class="md-sidepanel__subtitle">{{ subtitle }}</p>
            </div>
          </div>
          <button class="md-sidepanel__close" @click="close" aria-label="关闭">
            <X :size="18" />
          </button>
        </div>

        <!-- 内容区 -->
        <div class="md-sidepanel__body">
          <div v-if="loading" class="md-sidepanel__loading">
            <div class="md-sidepanel__spinner" />
            <span>加载中...</span>
          </div>
          <div v-else-if="error" class="md-sidepanel__error">
            <AlertTriangle :size="24" style="color: var(--pk-warning)" />
            <span>{{ error }}</span>
          </div>
          <div v-else class="md-sidepanel__markdown markdown-body" v-html="renderedContent" />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { marked } from 'marked'
import { X, AlertTriangle, ClipboardList, BarChart3, RefreshCw, FileText, Target } from 'lucide-vue-next'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  toolType: { type: String, default: '' },
  currentProjectId: { type: String, default: '' },
  fetchContent: { type: Function, default: null }
})

const emit = defineEmits(['update:visible', 'close'])

const panelRef = ref(null)
const loading = ref(false)
const error = ref('')
const rawContent = ref('')

// 工具类型 -> 图标映射
const iconMap = {
  daily: ClipboardList,
  weekly: BarChart3,
  review: RefreshCw,
  aar: FileText,
  sandbox: Target
}

const iconComponent = computed(() => iconMap[props.toolType] || FileText)

// Markdown 渲染
const renderedContent = computed(() => {
  if (!rawContent.value) return ''
  try {
    return marked.parse(rawContent.value, { gfm: true, breaks: true, headerIds: false })
  } catch (e) {
    console.warn('Markdown 渲染失败:', e)
    return rawContent.value.replace(/</g, '&lt;').replace(/\n/g, '<br>')
  }
})

// 监听 visible 变化，打开时自动加载内容
watch(() => props.visible, (vis) => {
  if (vis) {
    loadContent()
    nextTick(() => applySavedWidth())
    lockBodyScroll()
  } else {
    unlockBodyScroll()
  }
})

async function loadContent() {
  loading.value = true
  error.value = ''
  rawContent.value = ''
  try {
    if (typeof props.fetchContent === 'function') {
      const content = await props.fetchContent(props.toolType, props.currentProjectId)
      rawContent.value = content || ''
    } else {
      error.value = '未提供内容获取函数'
    }
  } catch (e) {
    error.value = e?.message || '加载失败'
    console.error('[MdSidepanel] 加载内容失败:', e)
  } finally {
    loading.value = false
  }
}

function close() {
  emit('update:visible', false)
  emit('close')
}

// ==================== Body 滚动锁定 ====================
let scrollY = 0
function lockBodyScroll() {
  scrollY = window.scrollY
  document.body.style.position = 'fixed'
  document.body.style.top = `-${scrollY}px`
  document.body.style.left = '0'
  document.body.style.right = '0'
  document.body.style.overflowY = 'scroll'
}
function unlockBodyScroll() {
  document.body.style.position = ''
  document.body.style.top = ''
  document.body.style.left = ''
  document.body.style.right = ''
  document.body.style.overflowY = ''
  window.scrollTo(0, scrollY)
}

// ==================== 拖拽调整宽度 ====================
const MIN_WIDTH = 400
const MAX_WIDTH = 1200
const WIDTH_KEY = 'md-sidepanel-width'

let resizePointerId = null
let resizeFrameId = 0
let startX = 0
let startWidth = 0

const flushResize = () => {
  resizeFrameId = 0
  if (!panelRef.value) return
  const deltaX = pendingClientX - startX
  const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidth - deltaX))
  panelRef.value.style.width = `${newWidth}px`
}

let pendingClientX = 0
const queueResize = (clientX) => {
  pendingClientX = clientX
  if (resizeFrameId) return
  resizeFrameId = window.requestAnimationFrame(flushResize)
}

const startResize = (e) => {
  if (e.button !== 0) return
  if (!panelRef.value) return

  startX = e.clientX
  startWidth = panelRef.value.offsetWidth
  resizePointerId = e.pointerId
  pendingClientX = e.clientX

  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  e.currentTarget?.setPointerCapture?.(e.pointerId)

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', stopResize)
  window.addEventListener('pointercancel', stopResize)
}

const onPointerMove = (e) => {
  if (e.pointerId !== resizePointerId) return
  queueResize(e.clientX)
}

const stopResize = (e) => {
  if (e && e.pointerId !== resizePointerId) return

  if (resizeFrameId) {
    window.cancelAnimationFrame(resizeFrameId)
    resizeFrameId = 0
  }
  if (e) {
    pendingClientX = e.clientX
    flushResize()
  }

  resizePointerId = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopResize)
  window.removeEventListener('pointercancel', stopResize)

  if (panelRef.value) {
    localStorage.setItem(WIDTH_KEY, String(panelRef.value.offsetWidth))
  }
}

function applySavedWidth() {
  if (!panelRef.value) return
  const saved = localStorage.getItem(WIDTH_KEY)
  if (!saved) return
  const width = parseInt(saved, 10)
  if (Number.isNaN(width) || width < MIN_WIDTH || width > MAX_WIDTH) {
    localStorage.removeItem(WIDTH_KEY)
    return
  }
  panelRef.value.style.width = `${width}px`
}
</script>

<style scoped>
/* Overlay */
.md-sidepanel__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
}

/* Panel */
.md-sidepanel {
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
.md-sidepanel__resize-handle {
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
.md-sidepanel__resize-handle:hover {
  width: 5px;
  background: rgba(99, 102, 241, 0.6);
  box-shadow: 1px 0 6px rgba(99, 102, 241, 0.2);
}

/* Header */
.md-sidepanel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, var(--pk-accent-gradient-from) 0%, var(--pk-accent-gradient-to) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}
.md-sidepanel__header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.md-sidepanel__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--pk-text);
  margin: 0;
}
.md-sidepanel__subtitle {
  font-size: 13px;
  color: var(--gray-500);
  margin: 2px 0 0;
}
.md-sidepanel__close {
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
.md-sidepanel__close:hover {
  background: var(--gray-100);
  transform: scale(1.05);
}

/* Body */
.md-sidepanel__body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 24px 28px;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-200) transparent;
}
.md-sidepanel__body::-webkit-scrollbar {
  width: 4px;
}
.md-sidepanel__body::-webkit-scrollbar-track {
  background: transparent;
}
.md-sidepanel__body::-webkit-scrollbar-thumb {
  background: var(--gray-200);
  border-radius: 4px;
}

/* Loading */
.md-sidepanel__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--gray-400);
  font-size: 14px;
}
.md-sidepanel__spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--pk-accent);
  border-radius: 50%;
  animation: md-spin 0.8s linear infinite;
}
@keyframes md-spin {
  to { transform: rotate(360deg); }
}

/* Error */
.md-sidepanel__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--gray-500);
  font-size: 14px;
}

/* Markdown 内容样式 */
.md-sidepanel__markdown {
  font-size: 14px;
  line-height: 1.8;
  color: var(--gray-800);
}

.md-sidepanel__markdown :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  color: var(--gray-900);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--gray-200);
}
.md-sidepanel__markdown :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 24px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--gray-100);
}
.md-sidepanel__markdown :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-800);
  margin: 18px 0 10px;
}
.md-sidepanel__markdown :deep(p) {
  margin: 10px 0;
}
.md-sidepanel__markdown :deep(ul),
.md-sidepanel__markdown :deep(ol) {
  margin: 10px 0;
  padding-left: 22px;
}
.md-sidepanel__markdown :deep(li) {
  margin: 4px 0;
}
.md-sidepanel__markdown :deep(code) {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 13px;
  background: var(--gray-50);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--pk-danger-dark);
}
.md-sidepanel__markdown :deep(pre) {
  background: var(--gray-900);
  padding: 14px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.md-sidepanel__markdown :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #e6e6e6;
  font-size: 13px;
  line-height: 1.6;
}
.md-sidepanel__markdown :deep(blockquote) {
  margin: 12px 0;
  padding: 10px 14px;
  border-left: 3px solid var(--pk-accent);
  background: var(--gray-50);
  border-radius: 0 6px 6px 0;
  color: var(--gray-600);
}
.md-sidepanel__markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}
.md-sidepanel__markdown :deep(th),
.md-sidepanel__markdown :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--gray-200);
  text-align: left;
}
.md-sidepanel__markdown :deep(th) {
  background: var(--gray-50);
  font-weight: 600;
  color: var(--gray-700);
}
.md-sidepanel__markdown :deep(tr:nth-child(even)) {
  background: var(--gray-25);
}
.md-sidepanel__markdown :deep(a) {
  color: var(--pk-accent);
  text-decoration: none;
}
.md-sidepanel__markdown :deep(a:hover) {
  text-decoration: underline;
}
.md-sidepanel__markdown :deep(hr) {
  border: none;
  border-top: 1px solid var(--gray-200);
  margin: 20px 0;
}
.md-sidepanel__markdown :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

/* Transitions */
.md-overlay-enter-active,
.md-overlay-leave-active {
  transition: opacity 0.3s ease;
}
.md-overlay-enter-from,
.md-overlay-leave-to {
  opacity: 0;
}

.md-sidepanel-enter-active,
.md-sidepanel-leave-active {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.md-sidepanel-enter-from,
.md-sidepanel-leave-to {
  transform: translateX(100%);
}

/* Responsive */
@media (max-width: 640px) {
  .md-sidepanel {
    width: 100%;
  }
}
</style>
