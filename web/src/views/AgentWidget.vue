<!-- 父页面调用示例
const iframe = document.getElementById('my-widget-iframe')

// 监听结果回执
window.addEventListener('message', (event) => {
  if (event.data?.type === 'xiaobei-send-result') {
    console.log(event.data.success ? '✅ 发送成功' : `❌ 失败: ${event.data.error}`)
  }

  // 监听高度变化（可选，用于动态调整 iframe 高度）
  if (event.data?.type === 'xiaobei-resize') {
    iframe.style.height = event.data.height + 'px'
  }
})

// 发送消息
iframe.contentWindow.postMessage(
  { type: 'xiaobei-send-message', text: '请总结一下' },
  '*'
)
-->

<template>
  <div class="agent-widget">
    <!-- 顶栏区域 -->
    <div class="widget-topbar">
      <div class="topbar-left">
        <button type="button" class="topbar-btn topbar-close" title="关闭" @click="handleWidgetClose">
          <X size="18" />
        </button>
      </div>
      <div class="topbar-right">
        <button type="button" class="topbar-btn" title="新对话" @click="handleNewChat">
          <Plus size="18" />
          <span class="btn-text">新对话</span>
        </button>
        <button type="button" class="topbar-btn" title="历史" @click="historyDrawerOpen = true">
          <Clock size="18" />
          <span class="btn-text">历史</span>
        </button>
        <button type="button" class="topbar-btn" title="配置" @click="configDrawerOpen = true">
          <Settings2 size="18" />
          <span class="btn-text">配置</span>
        </button>
        <div
          v-if="userStore.isAdmin && selectedAgentId"
          ref="moreButtonRef"
          type="button"
          class="topbar-btn"
          title="更多"
          @click="toggleMoreMenu"
        >
          <Ellipsis size="18" />
        </div>
        <!-- widget 模式隐藏头像 -->
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="widget-body">
      <AgentChatComponent
        ref="chatComponentRef"
        :single-mode="false"
        @thread-change="handleThreadChange"
      >
        <template #input-actions-left>
          <a-dropdown
            v-if="selectedAgentId"
            v-model:open="configDropdownOpen"
            :trigger="['click']"
            placement="topLeft"
            overlay-class-name="config-dropdown-overlay"
          >
            <button
              type="button"
              class="input-action-btn config-dropdown-trigger"
              :class="{ disabled: isLoadingConfig }"
              @click.stop
              @mousedown.stop
            >
              <Settings2 size="18" class="nav-btn-icon" />
              <span class="hide-text config-dropdown-text">{{ currentConfigLabel }}</span>
              <ChevronDown size="15" class="config-dropdown-chevron" />
            </button>

            <template #overlay>
              <div class="config-dropdown-panel" @click.stop>
                <button
                  v-for="config in configQuickSwitchOptions"
                  :key="config.value"
                  type="button"
                  class="config-dropdown-item"
                  :class="{ selected: config.value === selectedAgentConfigId }"
                  @click="handleConfigSwitch(config.value)"
                >
                  <span class="config-dropdown-item-label">{{ config.label }}</span>
                  <span v-if="config.isDefault" class="config-dropdown-item-badge">默认</span>
                  <Check
                    v-if="config.value === selectedAgentConfigId"
                    :size="14"
                    class="config-dropdown-item-check"
                  />
                </button>

                <div class="config-dropdown-divider"></div>

                <button
                  type="button"
                  class="config-dropdown-item action-item"
                  @click="toggleConfigSidebar"
                >
                  <Settings2 :size="15" class="config-dropdown-item-icon" />
                  <span class="config-dropdown-item-label">{{ configSidebarActionLabel }}</span>
                </button>

                <button
                  v-if="userStore.isAdmin"
                  type="button"
                  class="config-dropdown-item action-item"
                  @click="openCreateConfigModal"
                >
                  <Plus :size="15" class="config-dropdown-item-icon" />
                  <span class="config-dropdown-item-label">新建配置</span>
                </button>
              </div>
            </template>
          </a-dropdown>
        </template>

        <template #header-right="{ isAgentPanelOpen, hasActiveThread, toggleAgentPanel }">
          <button
            v-if="hasActiveThread"
            type="button"
            class="agent-nav-btn agent-state-btn"
            :class="{ active: isAgentPanelOpen }"
            title="查看文件"
            @click.stop="toggleAgentPanel"
          >
            <FolderKanban size="18" class="nav-btn-icon" />
            <span class="hide-text">文件</span>
          </button>
        </template>
      </AgentChatComponent>
    </div>

    <!-- 历史面板抽屉 -->
    <a-drawer
      v-model:open="historyDrawerOpen"
      placement="right"
      :width="320"
      title="对话历史"
      @close="historyDrawerOpen = false"
    >
      <ConversationNavSection
        :currentChatId="chatThreadsStore.currentThreadId"
        :chatsList="chatThreadsStore.threads"
        :hasMoreChats="chatThreadsStore.hasMoreThreads"
        :isLoadingMore="chatThreadsStore.isLoadingMoreThreads"
        @select-chat="handleSelectChat"
        @delete-chat="handleDeleteChat"
        @rename-chat="handleRenameChat"
        @toggle-pin="handleTogglePinChat"
        @load-more-chats="handleLoadMoreChats"
      />
    </a-drawer>

    <!-- 配置面板抽屉 -->
    <a-drawer
      v-model:open="configDrawerOpen"
      placement="right"
      :width="480"
      title="智能体配置"
      :destroyOnClose="true"
      @close="configDrawerOpen = false"
    >
      <AgentConfigSidebar
        :isOpen="true"
        @close="configDrawerOpen = false"
      />
    </a-drawer>

    <!-- 反馈模态框 -->
    <FeedbackModalComponent
      v-if="userStore.isAdmin"
      ref="feedbackModal"
      :agent-id="selectedAgentId"
    />

    <!-- 新建配置模态框 -->
    <a-modal
      v-model:open="createConfigModalOpen"
      title="新建配置"
      :width="360"
      :confirm-loading="createConfigLoading"
      @ok="handleCreateConfig"
      @cancel="closeCreateConfigModal"
    >
      <a-input v-model:value="createConfigName" placeholder="请输入配置名称" allow-clear />
    </a-modal>

    <!-- 更多菜单 -->
    <Teleport to="body">
      <Transition name="menu-fade">
        <div
          v-if="userStore.isAdmin && moreMenuOpen"
          ref="moreMenuRef"
          class="more-popup-menu"
          :style="{
            left: moreMenuPosition.x + 'px',
            top: moreMenuPosition.y + 'px'
          }"
        >
          <div class="menu-item" @click="handleShareChat">
            <ShareAltOutlined class="menu-icon" />
            <span class="menu-text">分享对话</span>
          </div>
          <div class="menu-item" @click="handleFeedback">
            <MessageOutlined class="menu-icon" />
            <span class="menu-text">查看反馈</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { MessageOutlined, ShareAltOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { Settings2, Ellipsis, ChevronDown, Check, Plus, FolderKanban, Clock, X } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { onClickOutside } from '@vueuse/core'

import AgentChatComponent from '@/components/AgentChatComponent.vue'
import AgentConfigSidebar from '@/components/AgentConfigSidebar.vue'
import FeedbackModalComponent from '@/components/dashboard/FeedbackModalComponent.vue'
import ConversationNavSection from '@/components/ConversationNavSection.vue'

import { useUserStore } from '@/stores/user'
import { useAgentStore } from '@/stores/agent'
import { useChatUIStore } from '@/stores/chatUI'
import { useChatThreadsStore } from '@/stores/chatThreads'
import { useInfoStore } from '@/stores/info'

import { ChatExporter } from '@/utils/chatExporter'
import { handleChatError } from '@/utils/errorHandler'

// 组件引用
const feedbackModal = ref(null)
const chatComponentRef = ref(null)

// Stores
const userStore = useUserStore()
const agentStore = useAgentStore()
const chatUIStore = useChatUIStore()
const chatThreadsStore = useChatThreadsStore()
const infoStore = useInfoStore()
const route = useRoute()
const router = useRouter()

// 从 agentStore 中获取响应式状态
const { selectedAgentId, defaultAgentId, selectedAgentConfigId, agentConfigs, isLoadingConfig } =
  storeToRefs(agentStore)

// Drawer 与模态框状态
const historyDrawerOpen = ref(false)
const configDrawerOpen = ref(false)
const configDropdownOpen = ref(false)
const createConfigModalOpen = ref(false)
const createConfigLoading = ref(false)
const createConfigName = ref('')
const syncingRouteThread = ref(false)

// 更多菜单状态
const moreMenuRef = ref(null)
const moreButtonRef = ref(null)
const moreMenuOpen = ref(false)
const moreMenuPosition = ref({ x: 0, y: 0 })

// ===== 路由同步逻辑（同 AgentView） =====

const getRouteThreadId = () => {
  const value = route.params.thread_id
  return typeof value === 'string' ? value : ''
}

const syncSelectedThreadFromRoute = async () => {
  const chatComponent = chatComponentRef.value
  if (!chatComponent?.selectThreadFromRoute) return

  const threadId = getRouteThreadId()
  syncingRouteThread.value = true
  try {
    if (!threadId) {
      if (!agentStore.isInitialized) {
        await agentStore.initialize()
      }
      const targetAgentId = defaultAgentId.value
      if (targetAgentId && selectedAgentId.value !== targetAgentId) {
        await agentStore.selectAgent(targetAgentId)
      }
    }

    const ok = await chatComponent.selectThreadFromRoute(threadId)
    if (threadId && !ok) {
      await router.replace({ name: 'WidgetComp' })
    }
  } catch (error) {
    handleChatError(error, 'load')
  } finally {
    syncingRouteThread.value = false
  }
}

watch(
  () => route.params.thread_id,
  () => {
    syncSelectedThreadFromRoute()
  },
  { immediate: true }
)

watch(chatComponentRef, (instance) => {
  if (!instance) return
  syncSelectedThreadFromRoute()
})

const handleThreadChange = (threadId) => {
  if (syncingRouteThread.value) return
  const currentRouteThreadId = getRouteThreadId()
  const nextThreadId = threadId || ''
  if (currentRouteThreadId === nextThreadId) return

  if (nextThreadId) {
    router.replace({ name: 'WidgetCompWithThreadId', params: { thread_id: nextThreadId } })
  } else {
    router.replace({ name: 'WidgetComp' })
  }
}

// ===== 配置快速切换逻辑（同 AgentView） =====

const configQuickSwitchOptions = computed(() => {
  if (!selectedAgentId.value) return []
  const list = agentConfigs.value[selectedAgentId.value] || []
  return list.map((config) => ({
    label: config.name,
    value: config.id,
    isDefault: !!config.is_default
  }))
})

const currentConfigLabel = computed(() => {
  if (isLoadingConfig.value) return '加载中...'
  const current = configQuickSwitchOptions.value.find(
    (config) => config.value === selectedAgentConfigId.value
  )
  return current?.label || '配置'
})

const configSidebarActionLabel = computed(() => {
  return configDrawerOpen.value ? '收起配置面板' : '查看/编辑配置'
})

const handleConfigSwitch = async (configId) => {
  if (!configId || configId === selectedAgentConfigId.value) return
  try {
    await agentStore.selectAgentConfig(configId)
    configDropdownOpen.value = false
  } catch (error) {
    console.error('切换配置出错:', error)
    message.error('切换配置失败')
  }
}

const toggleConfigSidebar = () => {
  configDropdownOpen.value = false
  configDrawerOpen.value = !configDrawerOpen.value
}

const openCreateConfigModal = () => {
  if (!userStore.isAdmin) return
  configDropdownOpen.value = false
  createConfigName.value = ''
  createConfigModalOpen.value = true
}

const closeCreateConfigModal = () => {
  createConfigModalOpen.value = false
  createConfigName.value = ''
}

const handleCreateConfig = async () => {
  if (!userStore.isAdmin || !selectedAgentId.value) return

  const name = createConfigName.value.trim()
  if (!name) {
    message.error('请输入配置名称')
    return
  }

  createConfigLoading.value = true
  try {
    await agentStore.createAgentConfigProfile({
      name,
      setDefault: false,
      fromCurrent: false
    })
    closeCreateConfigModal()
    configDrawerOpen.value = true
    message.success('配置已创建')
  } catch (error) {
    console.error('创建配置出错:', error)
    message.error(error.message || '创建配置失败')
  } finally {
    createConfigLoading.value = false
  }
}

// ===== 更多菜单逻辑（同 AgentView） =====

const toggleMoreMenu = (event) => {
  event.stopPropagation()
  moreMenuOpen.value = !moreMenuOpen.value

  if (moreMenuOpen.value) {
    const rect = event.currentTarget.getBoundingClientRect()
    moreMenuPosition.value = {
      x: rect.right - 110,
      y: rect.bottom + 8
    }
  }
}

const closeMoreMenu = () => {
  moreMenuOpen.value = false
}

onClickOutside(
  moreMenuRef,
  () => {
    if (moreMenuOpen.value) {
      closeMoreMenu()
    }
  },
  { ignore: [moreButtonRef] }
)

const handleShareChat = async () => {
  closeMoreMenu()

  try {
    const exportData = chatComponentRef.value?.getExportPayload?.()

    if (!exportData) {
      message.warning('当前没有可导出的对话内容')
      return
    }

    const hasMessages = exportData.messages && exportData.messages.length > 0
    const hasOngoingMessages = exportData.onGoingMessages && exportData.onGoingMessages.length > 0

    if (!hasMessages && !hasOngoingMessages) {
      message.warning('当前对话暂无内容可导出，请先进行对话')
      return
    }

    const result = await ChatExporter.exportToHTML(exportData)
    message.success(`对话已导出为HTML文件: ${result.filename}`)
  } catch (error) {
    console.error('[AgentWidget] Export error:', error)
    if (error?.message?.includes('没有可导出的对话内容')) {
      message.warning('当前对话暂无内容可导出，请先进行对话')
      return
    }
    handleChatError(error, 'export')
  }
}

const handleFeedback = () => {
  closeMoreMenu()
  feedbackModal.value?.show()
}

// ===== 线程管理逻辑（同 AppLayout） =====

const handleNewChat = () => {
  chatComponentRef.value?.selectThreadFromRoute?.('')
  router.replace({ name: 'WidgetComp' })
}

const handleSelectChat = (threadId) => {
  if (!threadId) return
  historyDrawerOpen.value = false
  chatThreadsStore.setCurrentThreadId(threadId)
  router.push({ name: 'WidgetCompWithThreadId', params: { thread_id: threadId } })
}

const handleDeleteChat = async (threadId) => {
  if (!threadId) return
  try {
    await chatThreadsStore.deleteThread(threadId)
    if (route.params.thread_id === threadId) {
      await router.replace({ name: 'WidgetComp' })
    }
  } catch (error) {
    console.warn('删除对话失败:', error)
  }
}

const handleRenameChat = async ({ chatId, title }) => {
  try {
    await chatThreadsStore.updateThread(chatId, title)
  } catch (error) {
    console.warn('重命名对话失败:', error)
  }
}

const handleTogglePinChat = async (threadId) => {
  const thread = chatThreadsStore.threads.find((item) => item.id === threadId)
  if (!thread) return
  try {
    await chatThreadsStore.updateThread(threadId, null, !thread.is_pinned)
    await chatThreadsStore.loadThreads()
    if (chatThreadsStore.currentThreadId) {
      chatThreadsStore.setCurrentThreadId(chatThreadsStore.currentThreadId)
    }
  } catch (error) {
    console.warn('更新置顶状态失败:', error)
  }
}

const handleLoadMoreChats = () => {
  chatThreadsStore.loadMoreThreads()
}

// ===== iframe 跨域通信：通知父页面关闭 =====
const handleWidgetClose = () => {
  if (window.parent !== window) {
    try {
      window.parent.postMessage({ type: 'xiaobei-close' }, '*')
    } catch {
      // 跨域安全限制，静默失败
    }
  }
}

// ===== 生命周期 =====

onMounted(async () => {
  try {
    await infoStore.loadInfoConfig()
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
    await chatThreadsStore.loadThreads()
  } catch (error) {
    console.warn('[AgentWidget] 初始化失败:', error)
  }

  // iframe 跨域通信：通知父页面高度变化
  const notifyParentHeight = () => {
    if (window.parent !== window) {
      try {
        window.parent.postMessage(
          { type: 'widget-resize', height: document.body.scrollHeight },
          '*'
        )
      } catch {
        // 跨域安全限制，静默失败
      }
    }
  }

  // 内容变化时通知父页面
  const observer = new ResizeObserver(() => {
    notifyParentHeight()
  })
  observer.observe(document.body)

  // 处理父页面通过 postMessage 发送的消息
  const handleWidgetSendMessage = async (data) => {
    // 校验文本
    const text = data.text
    if (!text || typeof text !== 'string' || !text.trim()) {
      try {
        window.parent.postMessage(
          { type: 'xiaobei-send-result', success: false, error: '消息内容不能为空' },
          '*'
        )
      } catch { /* 跨域安全限制，静默失败 */ }
      return
    }

    // 检查聊天组件是否就绪
    const chatComponent = chatComponentRef.value
    if (!chatComponent) {
      try {
        window.parent.postMessage(
          { type: 'xiaobei-send-result', success: false, error: '聊天组件未就绪' },
          '*'
        )
      } catch { /* 跨域安全限制 */ }
      return
    }

    // 发送消息
    try {
      await chatComponent.sendTextMessage(text.trim())
      try {
        window.parent.postMessage(
          { type: 'xiaobei-send-result', success: true },
          '*'
        )
      } catch { /* 跨域安全限制 */ }
    } catch (error) {
      try {
        window.parent.postMessage(
          { type: 'xiaobei-send-result', success: false, error: error?.message || '发送失败' },
          '*'
        )
      } catch { /* 跨域安全限制 */ }
    }
  }

  // 监听来自父页面的消息
  const handleIframeMessage = (event) => {
    const data = event.data
    if (!data || typeof data !== 'object') return

    if (data.type === 'xiaobei-send-message') {
      handleWidgetSendMessage(data)
    }
  }
  window.addEventListener('message', handleIframeMessage)
})
</script>

<style lang="less" scoped>
.agent-widget {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  min-width: 320px;
  overflow: hidden;
  background: var(--gray-0);
}

.widget-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--gray-100);
  flex-shrink: 0;

  .topbar-left {
    display: flex;
    align-items: center;
  }

  .topbar-brand {
    font-size: 16px;
    font-weight: 600;
    color: var(--gray-900);
    user-select: none;
  }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .topbar-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 10px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--gray-700);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    user-select: none;

    &:hover {
      background: var(--main-10);
      color: var(--main-600);
    }

    &:active {
      background: var(--main-20);
    }
  }
}

.widget-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

// 响应式：窄屏时按钮只显示图标，隐藏文字
@media (max-width: 520px) {
  .widget-topbar {
    .topbar-btn {
      .btn-text {
        display: none;
      }
      padding: 0 8px;
    }

    .topbar-brand {
      font-size: 14px;
      max-width: 120px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

// 响应式：极小屏时更紧凑
@media (max-width: 380px) {
  .widget-topbar {
    padding: 0 8px;

    .topbar-btn {
      padding: 0 6px;
      gap: 4px;
    }
  }
}
</style>

<style lang="less">
.config-dropdown-overlay .config-dropdown-panel {
  min-width: 188px;
  max-width: min(260px, calc(100vw - 24px));
  padding: 4px;
  background: var(--gray-0);
  border: 1px solid var(--gray-100);
  border-radius: 8px;
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04);
}

.config-dropdown-overlay .config-dropdown-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  width: 100%;
  padding: 6px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.config-dropdown-overlay .config-dropdown-item:hover {
  background: var(--gray-50);
}

.config-dropdown-overlay .config-dropdown-item.selected {
  background: var(--gray-50);
}

.config-dropdown-overlay .config-dropdown-item.action-item {
  color: var(--gray-800);
}

.config-dropdown-overlay .config-dropdown-item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  line-height: 1.35;
  color: var(--gray-800);
}

.config-dropdown-overlay .config-dropdown-item-icon {
  flex-shrink: 0;
  color: var(--gray-500);
}

.config-dropdown-overlay .config-dropdown-item-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--gray-100);
  color: var(--gray-600);
  font-size: 11px;
  line-height: 1.4;
}

.config-dropdown-overlay .config-dropdown-item-check {
  flex-shrink: 0;
  color: var(--main-600);
}

.config-dropdown-overlay .config-dropdown-divider {
  height: 1px;
  margin: 4px 4px;
  background: var(--gray-100);
}

// 菜单淡入淡出动画
.menu-fade-enter-active {
  animation: menuSlideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.menu-fade-leave-active {
  animation: menuSlideOut 0.15s cubic-bezier(0.4, 0, 1, 1);
}

@keyframes menuSlideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes menuSlideOut {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-4px);
  }
}

// 更多菜单样式
.more-popup-menu {
  position: fixed;
  min-width: 100px;
  background: var(--gray-0);
  border-radius: 10px;
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--gray-100);
  padding: 4px;
  z-index: 9999;

  .menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    font-size: 14px;
    color: var(--gray-900);
    position: relative;
    user-select: none;

    .menu-icon {
      font-size: 16px;
      color: var(--gray-600);
      transition: color 0.15s ease;
      flex-shrink: 0;
    }

    .menu-text {
      font-weight: 400;
      letter-spacing: 0.01em;
    }

    &:hover {
      background: var(--gray-50);
    }

    &:active {
      background: var(--gray-100);
    }
  }

  .menu-divider {
    height: 1px;
    background: var(--gray-100);
    margin: 4px 8px;
  }
}

// Drawer 响应式宽度
@media (max-width: 520px) {
  .agent-widget {
    :deep(.ant-drawer-content-wrapper) {
      width: calc(100vw - 48px) !important;
    }
  }
}

// 暗色模式适配
[data-theme='dark'] {
  .agent-widget {
    background: var(--gray-900);
  }

  .widget-topbar {
    border-bottom-color: var(--gray-800);
  }

  .more-popup-menu {
    background: var(--gray-900);
    border-color: var(--gray-800);
    box-shadow:
      0 8px 24px rgba(0, 0, 0, 0.3),
      0 2px 8px rgba(0, 0, 0, 0.2);

    .menu-item {
      color: var(--gray-100);

      &:hover {
        background: var(--gray-800);
      }

      &:active {
        background: var(--gray-700);
      }
    }
  }

  .config-dropdown-overlay .config-dropdown-panel {
    background: var(--gray-900);
    border-color: var(--gray-800);
  }

  .config-dropdown-overlay .config-dropdown-item-label {
    color: var(--gray-200);
  }

  .config-dropdown-overlay .config-dropdown-item:hover,
  .config-dropdown-overlay .config-dropdown-item.selected {
    background: var(--gray-800);
  }

  .config-dropdown-overlay .config-dropdown-divider {
    background: var(--gray-800);
  }
}
</style>
